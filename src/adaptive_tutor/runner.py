from __future__ import annotations

from datetime import datetime
from pathlib import Path

from adaptive_tutor.backends import create_backend
from adaptive_tutor.evaluation import score_task
from adaptive_tutor.feedback import generate_feedback_record
from adaptive_tutor.io_utils import (
    append_jsonl,
    ensure_dir,
    load_bundle_catalog,
    load_config,
    load_learners,
    load_tasks,
    write_csv,
    write_json,
    write_jsonl,
)
from adaptive_tutor.modeling import LearnerModeler
from adaptive_tutor.next_task import recommend_tasks
from adaptive_tutor.planning import generate_tutoring_plan
from adaptive_tutor.prompts import (
    build_adaptive_guidance,
    build_generic_guidance,
    build_judge_messages,
    build_learner_system_prompt,
    render_task,
)
from adaptive_tutor.reporting import build_report_text
from adaptive_tutor.schemas import (
    AppConfig,
    EvaluationResult,
    ExperimentMetric,
    FeedbackRecord,
    GuidanceMode,
    InteractionRecord,
    JudgeDecision,
    LearnerProfile,
    PlanRecord,
    RunArtifacts,
    StateRecord,
    Task,
)
from adaptive_tutor.triage import ReadingJudgeTriageRuntime
from adaptive_tutor.utils import average, deterministic_seed, parse_json_object

TASK_TYPES = ("grammar_correction", "reading_qa")


def _resolve_run_dir(config: AppConfig) -> Path:
    output_root = ensure_dir(config.output_root)
    base_name = config.run_name or datetime.now().strftime("run_%Y%m%d_%H%M%S")
    candidate = output_root / base_name
    suffix = 1
    while candidate.exists():
        candidate = output_root / f"{base_name}_{suffix}"
        suffix += 1
    candidate.mkdir(parents=True, exist_ok=False)
    return candidate


class ExperimentRunner:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.tasks = load_tasks(config.tasks_path)
        self.learners = load_learners(config.learners_path)
        self.bundles = load_bundle_catalog(config.bundles_path)
        self._validate_bundle_tasks()
        self.backend = create_backend(config.backend)
        self.triage_runtime = ReadingJudgeTriageRuntime(config.reading_judge_triage)

    def _validate_bundle_tasks(self) -> None:
        learner_ids = set(self.learners)
        assignment_ids = set(self.bundles.assignments)
        missing_learners = learner_ids - assignment_ids
        extra_learners = assignment_ids - learner_ids
        if missing_learners:
            raise ValueError(f"Bundle assignments missing learners: {sorted(missing_learners)}")
        if extra_learners:
            raise ValueError(f"Bundle assignments reference unknown learners: {sorted(extra_learners)}")
        for bundle_name, task_ids in self.bundles.bundle_definitions.items():
            if not task_ids:
                raise ValueError(f"Bundle {bundle_name} must not be empty")
            for task_id in task_ids:
                if task_id not in self.tasks:
                    raise ValueError(f"Bundle {bundle_name} references missing task {task_id}")
        for learner_id in sorted(learner_ids):
            task_map = self.bundles.assignments[learner_id]
            missing_task_types = set(TASK_TYPES) - set(task_map)
            extra_task_types = set(task_map) - set(TASK_TYPES)
            if missing_task_types:
                raise ValueError(
                    f"Bundle assignments for {learner_id} missing task types: "
                    f"{sorted(missing_task_types)}"
                )
            if extra_task_types:
                raise ValueError(
                    f"Bundle assignments for {learner_id} include unsupported task types: "
                    f"{sorted(extra_task_types)}"
                )
            for task_type in TASK_TYPES:
                assignment = task_map[task_type]
                for phase_name, bundle_name in [
                    ("pretest", assignment.pretest_bundle),
                    ("posttest", assignment.posttest_bundle),
                ]:
                    task_ids = self.bundles.bundle_definitions[bundle_name]
                    if not task_ids:
                        raise ValueError(f"{learner_id}/{task_type}/{phase_name} bundle is empty")
                    for task_id in task_ids:
                        actual_task_type = self.tasks[task_id].task_type
                        if actual_task_type != task_type:
                            raise ValueError(
                                f"{learner_id}/{task_type}/{phase_name} bundle {bundle_name} "
                                f"contains {actual_task_type} task {task_id}"
                            )

    def _judge_reading_answer(self, task: Task, learner_answer: str, rule_score: float) -> JudgeDecision:
        messages = build_judge_messages(task, learner_answer, rule_score)
        raw_text = self.backend.generate(
            messages=messages,
            model=self.config.models.judge_model,
            response_format={"type": "json_object"},
            seed=self.config.seed if self.config.generation.use_seed else None,
            temperature=self.config.generation.judge_temperature,
            metadata={
                "role": "judge",
                "rule_score": rule_score,
                "learner_answer": learner_answer,
            },
        )
        try:
            return JudgeDecision.model_validate(parse_json_object(raw_text))
        except Exception:
            if rule_score >= 0.5:
                return JudgeDecision(score=0.5, note="Fallback judge: partially correct.")
            return JudgeDecision(score=0.0, note="Fallback judge: insufficient evidence.")

    def _answer_task(
        self,
        learner: LearnerProfile,
        task: Task,
        mode: GuidanceMode,
        phase: str,
        guidance_text: str = "",
        focus_skill: str | None = None,
    ) -> str:
        configured_override = self.config.models.learner_model_overrides.get(learner.learner_id)
        model = configured_override or learner.model_id_override or self.config.models.shared_learner_model
        messages = [
            {"role": "system", "content": build_learner_system_prompt(learner)},
            {
                "role": "user",
                "content": "\n\n".join(part for part in [guidance_text, render_task(task)] if part),
            },
        ]
        learner_seed = None
        if self.config.generation.use_seed:
            learner_seed = self.config.seed
            if self.config.generation.vary_learner_seed:
                learner_seed = deterministic_seed(
                    self.config.seed,
                    learner.learner_id,
                    task.task_id,
                    mode,
                    phase,
                ) % 2_147_483_647
        return self.backend.generate(
            messages=messages,
            model=model,
            response_format=None,
            seed=learner_seed,
            temperature=self.config.generation.learner_temperature,
            metadata={
                "role": "learner",
                "learner": learner.model_dump(),
                "task": task.model_dump(),
                "mode": mode,
                "phase": phase,
                "focus_skill": focus_skill,
                "guidance_text": guidance_text,
            },
        ).strip()

    def _score_answer(self, task: Task, answer: str) -> EvaluationResult:
        triage_callback = (
            self.triage_runtime.predict
            if task.task_type == "reading_qa" and self.triage_runtime.enabled
            else None
        )
        return score_task(
            task=task,
            learner_answer=answer,
            gray_zone=self.config.judge_gray_zone,
            judge_callback=self._judge_reading_answer if task.task_type == "reading_qa" else None,
            triage_callback=triage_callback,
        )

    def _select_generic_practice_tasks(
        self,
        task_type: str,
        exclude_task_ids: set[str],
        batch_size: int,
    ) -> list[Task]:
        candidates = [
            task
            for task in self.tasks.values()
            if task.task_type == task_type and task.task_id not in exclude_task_ids
        ]
        candidates.sort(key=lambda task: (abs(task.difficulty - 2), task.task_id))
        return candidates[:batch_size]

    @staticmethod
    def _compose_post_guidance(
        mode: GuidanceMode,
        task_type: str,
        base_guidance: str,
        practice_feedback_texts: list[str],
    ) -> str:
        if not practice_feedback_texts:
            return base_guidance
        if mode == "adaptive_guidance":
            if task_type == "reading_qa":
                practice_summary = (
                    "Practice summary: use only the current passage, do not reuse names or "
                    "details from earlier practice tasks, and include the full cause/evidence "
                    "chain required by the current question."
                )
            else:
                practice_summary = (
                    "Practice summary: correct every grammar issue in the current sentence, "
                    "especially agreement, pronouns, tense, articles, and prepositions."
                )
            return "\n\n".join(
                [
                    base_guidance,
                    practice_summary,
                ]
            )
        if mode == "generic_guidance":
            return "\n\n".join(
                [
                    base_guidance,
                    "Practice reminder: apply the same checklist carefully in the next test.",
                ]
            )
        return base_guidance

    @staticmethod
    def _scoring_fields(evaluation: EvaluationResult) -> dict:
        return {
            "scoring_source": evaluation.scoring_source,
            "rule_score": evaluation.rule_score,
            "used_judge": evaluation.used_judge,
            "used_triage": evaluation.used_triage,
            "triage_candidate": evaluation.triage_candidate,
            "triage_would_skip": evaluation.triage_would_skip,
            "triage_confidence": evaluation.triage_confidence,
            "triage_prediction": evaluation.triage_prediction,
        }

    def _triage_training_row(
        self,
        learner_id: str,
        mode: GuidanceMode,
        phase: str,
        task: Task,
        answer: str,
        evaluation: EvaluationResult,
    ) -> dict | None:
        if not self.config.reading_judge_triage.collect_training_data:
            return None
        if task.task_type != "reading_qa" or not evaluation.triage_candidate:
            return None
        if not evaluation.used_judge or evaluation.triage_features is None:
            return None
        return {
            "learner_id": learner_id,
            "mode": mode,
            "phase": phase,
            "task_id": task.task_id,
            "difficulty": task.difficulty,
            "rule_score": evaluation.rule_score,
            "label_score": evaluation.score,
            "triage_prediction": evaluation.triage_prediction,
            "triage_confidence": evaluation.triage_confidence,
            "features": evaluation.triage_features,
            "learner_answer": answer,
            "reference_answer": task.reference_answer,
        }

    def run(self) -> Path:
        run_dir = _resolve_run_dir(self.config)
        self._initialize_incremental_artifacts(run_dir)
        interactions: list[InteractionRecord] = []
        states: list[StateRecord] = []
        plans: list[PlanRecord] = []
        feedback_records: list[FeedbackRecord] = []
        metrics: list[ExperimentMetric] = []
        case_payloads: list[dict] = []
        triage_training_rows: list[dict] = []

        for learner_id in sorted(self.learners):
            learner = self.learners[learner_id]
            for mode in self.config.modes:
                for task_type in TASK_TYPES:
                    assignment = self.bundles.assignments[learner_id][task_type]
                    pre_ids = self.bundles.bundle_definitions[assignment.pretest_bundle]
                    post_ids = self.bundles.bundle_definitions[assignment.posttest_bundle]
                    tracker = LearnerModeler(learner)
                    adaptive_plan = None
                    recommended_tasks: list[Task] = []
                    phase_feedback: list[FeedbackRecord] = []
                    pretest_records: list[InteractionRecord] = []
                    pretest_evaluations: dict[str, EvaluationResult] = {}
                    practice_records: list[InteractionRecord] = []
                    practice_feedback_texts: list[str] = []

                    for task_id in pre_ids:
                        task = self.tasks[task_id]
                        answer = self._answer_task(learner, task, mode, phase="pretest")
                        evaluation = self._score_answer(task, answer)
                        training_row = self._triage_training_row(
                            learner_id, mode, "pretest", task, answer, evaluation
                        )
                        if training_row:
                            triage_training_rows.append(training_row)
                            append_jsonl(run_dir / "triage_training.jsonl", training_row)
                        tracker.update(task, evaluation)
                        record = InteractionRecord(
                            interaction_id=f"{learner_id}-{mode}-{task_id}-pretest",
                            learner_id=learner_id,
                            task_id=task.task_id,
                            task_type=task.task_type,
                            difficulty=task.difficulty,
                            response_text=answer,
                            score=evaluation.score,
                            error_tags=evaluation.error_tags,
                            guidance_mode=mode,
                            round_index=1,
                            phase="pretest",
                            evaluator_note=evaluation.evaluator_note,
                            **self._scoring_fields(evaluation),
                        )
                        interactions.append(record)
                        append_jsonl(run_dir / "interactions.jsonl", record)
                        pretest_records.append(record)
                        pretest_evaluations[task.task_id] = evaluation

                    pretest_state = tracker.snapshot()
                    state_record = StateRecord(
                        learner_id=learner_id,
                        task_type=task_type,
                        guidance_mode=mode,
                        round_index=1,
                        learner_state=pretest_state,
                    )
                    states.append(state_record)
                    append_jsonl(run_dir / "states.jsonl", state_record)

                    guidance_text = ""
                    if mode == "adaptive_guidance":
                        adaptive_plan = generate_tutoring_plan(
                            backend=self.backend,
                            model=self.config.models.tutor_model,
                            learner_state=pretest_state,
                            task_type=task_type,
                            seed=self.config.seed if self.config.generation.use_seed else None,
                            temperature=self.config.generation.tutor_temperature,
                        )
                        excluded_ids = set(pre_ids) | set(post_ids)
                        recommended_tasks = recommend_tasks(self.tasks, adaptive_plan, excluded_ids)
                        plan_record = PlanRecord(
                            learner_id=learner_id,
                            task_type=task_type,
                            guidance_mode=mode,
                            round_index=1,
                            tutoring_plan=adaptive_plan,
                            recommended_task_ids=[task.task_id for task in recommended_tasks],
                        )
                        plans.append(plan_record)
                        append_jsonl(run_dir / "plans.jsonl", plan_record)
                        for record in pretest_records:
                            task = self.tasks[record.task_id]
                            feedback_record = generate_feedback_record(
                                backend=self.backend,
                                model=self.config.models.tutor_model,
                                learner_id=learner_id,
                                guidance_mode=mode,
                                task=task,
                                learner_answer=record.response_text,
                                evaluation=pretest_evaluations[task.task_id],
                                plan=adaptive_plan,
                                recommended_task_ids=[task.task_id for task in recommended_tasks],
                                seed=self.config.seed if self.config.generation.use_seed else None,
                                temperature=self.config.generation.feedback_temperature,
                            )
                            feedback_records.append(feedback_record)
                            append_jsonl(run_dir / "feedback.jsonl", feedback_record)
                            phase_feedback.append(feedback_record)
                        guidance_text = build_adaptive_guidance(task_type, adaptive_plan)
                    elif mode == "generic_guidance":
                        guidance_text = build_generic_guidance(task_type)
                        for record in pretest_records:
                            feedback_record = FeedbackRecord(
                                learner_id=learner_id,
                                task_id=record.task_id,
                                task_type=task_type,
                                guidance_mode=mode,
                                round_index=1,
                                feedback_style="generic_guidance",
                                feedback_text=guidance_text,
                                next_task_recommendation=[],
                                focus_skill=None,
                            )
                            feedback_records.append(feedback_record)
                            append_jsonl(run_dir / "feedback.jsonl", feedback_record)
                            phase_feedback.append(feedback_record)

                    practice_tasks: list[Task] = []
                    if self.config.practice.enabled and self.config.practice.batch_size > 0:
                        excluded_ids = set(pre_ids) | set(post_ids)
                        if mode == "adaptive_guidance" and adaptive_plan:
                            practice_tasks = recommended_tasks[: self.config.practice.batch_size]
                        elif mode == "generic_guidance":
                            practice_tasks = self._select_generic_practice_tasks(
                                task_type,
                                excluded_ids,
                                self.config.practice.batch_size,
                            )

                    for task in practice_tasks:
                        answer = self._answer_task(
                            learner,
                            task,
                            mode,
                            phase="practice",
                            guidance_text=guidance_text,
                            focus_skill=adaptive_plan.focus_skill if adaptive_plan else None,
                        )
                        evaluation = self._score_answer(task, answer)
                        training_row = self._triage_training_row(
                            learner_id, mode, "practice", task, answer, evaluation
                        )
                        if training_row:
                            triage_training_rows.append(training_row)
                            append_jsonl(run_dir / "triage_training.jsonl", training_row)
                        tracker.update(task, evaluation)
                        record = InteractionRecord(
                            interaction_id=f"{learner_id}-{mode}-{task.task_id}-practice",
                            learner_id=learner_id,
                            task_id=task.task_id,
                            task_type=task.task_type,
                            difficulty=task.difficulty,
                            response_text=answer,
                            score=evaluation.score,
                            error_tags=evaluation.error_tags,
                            guidance_mode=mode,
                            round_index=1,
                            phase="practice",
                            evaluator_note=evaluation.evaluator_note,
                            **self._scoring_fields(evaluation),
                        )
                        interactions.append(record)
                        append_jsonl(run_dir / "interactions.jsonl", record)
                        practice_records.append(record)
                        if mode == "adaptive_guidance" and adaptive_plan:
                            feedback_record = generate_feedback_record(
                                backend=self.backend,
                                model=self.config.models.tutor_model,
                                learner_id=learner_id,
                                guidance_mode=mode,
                                task=task,
                                learner_answer=answer,
                                evaluation=evaluation,
                                plan=adaptive_plan,
                                recommended_task_ids=[item.task_id for item in recommended_tasks],
                                seed=self.config.seed if self.config.generation.use_seed else None,
                                temperature=self.config.generation.feedback_temperature,
                            )
                        else:
                            feedback_record = FeedbackRecord(
                                learner_id=learner_id,
                                task_id=task.task_id,
                                task_type=task_type,
                                guidance_mode=mode,
                                round_index=1,
                                feedback_style="generic_guidance",
                                feedback_text=guidance_text,
                                next_task_recommendation=[],
                                focus_skill=None,
                            )
                        feedback_records.append(feedback_record)
                        append_jsonl(run_dir / "feedback.jsonl", feedback_record)
                        phase_feedback.append(feedback_record)
                        practice_feedback_texts.append(feedback_record.feedback_text)

                    guidance_text = self._compose_post_guidance(
                        mode,
                        task_type,
                        guidance_text,
                        practice_feedback_texts,
                    )

                    posttest_records: list[InteractionRecord] = []
                    for task_id in post_ids:
                        task = self.tasks[task_id]
                        answer = self._answer_task(
                            learner,
                            task,
                            mode,
                            phase="posttest",
                            guidance_text=guidance_text,
                            focus_skill=adaptive_plan.focus_skill if adaptive_plan else None,
                        )
                        evaluation = self._score_answer(task, answer)
                        training_row = self._triage_training_row(
                            learner_id, mode, "posttest", task, answer, evaluation
                        )
                        if training_row:
                            triage_training_rows.append(training_row)
                            append_jsonl(run_dir / "triage_training.jsonl", training_row)
                        tracker.update(task, evaluation)
                        record = InteractionRecord(
                            interaction_id=f"{learner_id}-{mode}-{task_id}-posttest",
                            learner_id=learner_id,
                            task_id=task.task_id,
                            task_type=task.task_type,
                            difficulty=task.difficulty,
                            response_text=answer,
                            score=evaluation.score,
                            error_tags=evaluation.error_tags,
                            guidance_mode=mode,
                            round_index=2,
                            phase="posttest",
                            evaluator_note=evaluation.evaluator_note,
                            **self._scoring_fields(evaluation),
                        )
                        interactions.append(record)
                        append_jsonl(run_dir / "interactions.jsonl", record)
                        posttest_records.append(record)

                    final_state = tracker.snapshot()
                    state_record = StateRecord(
                        learner_id=learner_id,
                        task_type=task_type,
                        guidance_mode=mode,
                        round_index=2,
                        learner_state=final_state,
                    )
                    states.append(state_record)
                    append_jsonl(run_dir / "states.jsonl", state_record)
                    round1_score = round(average(record.score for record in pretest_records), 3)
                    round2_score = round(average(record.score for record in posttest_records), 3)
                    metric = ExperimentMetric(
                        learner_id=learner_id,
                        mode=mode,
                        task_type=task_type,
                        round1_score=round1_score,
                        round2_score=round2_score,
                        score_delta=round(round2_score - round1_score, 3),
                    )
                    metrics.append(metric)
                    if mode == "adaptive_guidance" and adaptive_plan and phase_feedback:
                        case_payloads.append(
                            {
                                "learner_id": learner_id,
                                "mode": mode,
                                "task_type": task_type,
                                "round1_score": round1_score,
                                "round2_score": round2_score,
                                "score_delta": metric.score_delta,
                                "learner_state": pretest_state.model_dump(),
                                "tutoring_plan": adaptive_plan.model_dump(),
                                "recommended_task_ids": [task.task_id for task in recommended_tasks],
                                "feedback_excerpt": phase_feedback[0].feedback_text,
                                "pretest_examples": [record.model_dump() for record in pretest_records],
                                "practice_examples": [
                                    record.model_dump() for record in practice_records
                                ],
                                "posttest_examples": [record.model_dump() for record in posttest_records],
                            }
                        )

        selected_cases = self._select_cases(case_payloads)
        artifacts = RunArtifacts(
            interactions=interactions,
            states=states,
            plans=plans,
            feedback=feedback_records,
            metrics=metrics,
            cases=selected_cases,
        )
        self._write_artifacts(run_dir, artifacts, triage_training_rows)
        return run_dir

    @staticmethod
    def _case_sort_key(case: dict) -> tuple[float, float, float, str, str]:
        return (
            -float(case["score_delta"]),
            -float(case["round2_score"]),
            float(case["round1_score"]),
            str(case["learner_id"]),
            str(case["task_type"]),
        )

    @classmethod
    def _select_cases(cls, case_payloads: list[dict]) -> list[dict]:
        return sorted(case_payloads, key=cls._case_sort_key)[:3]

    @staticmethod
    def _initialize_incremental_artifacts(run_dir: Path) -> None:
        for filename in [
            "interactions.jsonl",
            "states.jsonl",
            "plans.jsonl",
            "feedback.jsonl",
            "triage_training.jsonl",
        ]:
            (run_dir / filename).write_text("", encoding="utf-8")

    @staticmethod
    def _build_efficiency_summary(artifacts: RunArtifacts) -> dict:
        records = artifacts.interactions
        triage_candidates = sum(1 for record in records if record.triage_candidate)
        triage_skips = sum(1 for record in records if record.scoring_source == "triage")
        judge_calls = sum(1 for record in records if record.used_judge)
        triage_predictions = sum(1 for record in records if record.used_triage)
        baseline_judge_calls = judge_calls + triage_skips
        skip_rate = triage_skips / triage_candidates if triage_candidates else 0.0
        reduction_rate = triage_skips / baseline_judge_calls if baseline_judge_calls else 0.0
        return {
            "judge_calls": judge_calls,
            "baseline_judge_calls": baseline_judge_calls,
            "triage_candidates": triage_candidates,
            "triage_predictions": triage_predictions,
            "triage_skips": triage_skips,
            "skip_rate": round(skip_rate, 4),
            "judge_call_reduction_rate": round(reduction_rate, 4),
            "estimated_saved_api_calls": triage_skips,
        }

    def _write_artifacts(
        self,
        run_dir: Path,
        artifacts: RunArtifacts,
        triage_training_rows: list[dict],
    ) -> None:
        write_jsonl(run_dir / "interactions.jsonl", artifacts.interactions)
        write_jsonl(run_dir / "states.jsonl", artifacts.states)
        write_jsonl(run_dir / "plans.jsonl", artifacts.plans)
        write_jsonl(run_dir / "feedback.jsonl", artifacts.feedback)
        write_jsonl(run_dir / "triage_training.jsonl", triage_training_rows)
        write_csv(run_dir / "metrics.csv", artifacts.metrics)
        write_json(run_dir / "cases.json", artifacts.cases)
        write_json(run_dir / "efficiency.json", self._build_efficiency_summary(artifacts))
        report_text = build_report_text(artifacts)
        (run_dir / "report.md").write_text(report_text, encoding="utf-8")


def run_experiment(config_path: str) -> Path:
    config = load_config(config_path)
    runner = ExperimentRunner(config)
    return runner.run()
