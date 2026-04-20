from __future__ import annotations

from pathlib import Path
import json

import pytest
import yaml

import adaptive_tutor.runner as runner_module
from adaptive_tutor.reporting import load_run_artifacts
from adaptive_tutor.runner import ExperimentRunner
from adaptive_tutor.runner import run_experiment
from adaptive_tutor.planning import heuristic_tutoring_plan
from adaptive_tutor.prompts import build_compact_adaptive_post_guidance
from adaptive_tutor.schemas import InteractionRecord, LearnerState, RecentErrorSummary, StateVector

ROOT = Path(__file__).resolve().parents[1]


def test_mock_runner_creates_reproducible_artifacts(tmp_path: Path) -> None:
    sample_config_path = ROOT / "data" / "config.mock.yaml"
    with sample_config_path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    payload["learners_path"] = str((ROOT / "data" / "learners.json").resolve())
    payload["tasks_path"] = str((ROOT / "data" / "tasks.jsonl").resolve())
    payload["bundles_path"] = str((ROOT / "data" / "bundles.json").resolve())
    payload["output_root"] = str(tmp_path)
    payload["run_name"] = "test_run"
    temp_config = tmp_path / "config.yaml"
    with temp_config.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(payload, handle, sort_keys=False)

    run_dir = run_experiment(str(temp_config))
    artifacts = load_run_artifacts(run_dir)

    assert (run_dir / "interactions.jsonl").exists()
    assert (run_dir / "states.jsonl").exists()
    assert (run_dir / "plans.jsonl").exists()
    assert (run_dir / "feedback.jsonl").exists()
    assert (run_dir / "triage_training.jsonl").exists()
    assert (run_dir / "efficiency.json").exists()
    assert (run_dir / "metrics.csv").exists()
    assert (run_dir / "cases.json").exists()
    assert (run_dir / "report.md").exists()

    assert len(artifacts.metrics) == 18
    assert len(artifacts.plans) == 12
    assert len(artifacts.cases) >= 2
    round1_plans = [plan for plan in artifacts.plans if plan.round_index == 1]
    round2_plans = [plan for plan in artifacts.plans if plan.round_index == 2]
    assert len(round1_plans) == 6
    assert len(round2_plans) == 6
    assert all(plan.recommended_task_ids for plan in round1_plans)

    grouped_pre = {}
    grouped_post = {}
    grouped_practice = {}
    pretest_by_item = {}
    for record in artifacts.interactions:
        key = (record.learner_id, record.task_type, record.guidance_mode)
        if record.phase == "pretest":
            target = grouped_pre
            pretest_by_item.setdefault(
                (record.learner_id, record.task_type, record.task_id),
                [],
            ).append(record)
        elif record.phase == "posttest":
            target = grouped_post
        else:
            target = grouped_practice
        target.setdefault(key, []).append(record.task_id)

    for learner_id in {"learner_a", "learner_b", "learner_c"}:
        for task_type in {"grammar_correction", "reading_qa"}:
            pre_sets = {
                tuple(sorted(grouped_pre[(learner_id, task_type, mode)]))
                for mode in {"no_guidance", "generic_guidance", "adaptive_guidance"}
            }
            post_sets = {
                tuple(sorted(grouped_post[(learner_id, task_type, mode)]))
                for mode in {"no_guidance", "generic_guidance", "adaptive_guidance"}
            }
            assert len(pre_sets) == 1
            assert len(post_sets) == 1
            assert (learner_id, task_type, "no_guidance") not in grouped_practice
            assert grouped_practice[(learner_id, task_type, "generic_guidance")]
            assert grouped_practice[(learner_id, task_type, "adaptive_guidance")]
    for records in pretest_by_item.values():
        assert len({record.response_text for record in records}) == 1
        assert len({record.score for record in records}) == 1


def test_adaptive_post_guidance_uses_sanitized_practice_outcome() -> None:
    state = LearnerState(
        learner_id="learner_c",
        state_vector=StateVector(grammar=0.6, vocabulary=0.5, reading=0.4, confidence=0.5),
        recent_error_summary=RecentErrorSummary(
            top_errors=["missing_key_evidence"],
            weakest_skill="reading",
        ),
    )
    practice_record = InteractionRecord(
        interaction_id="learner_c-adaptive_guidance-r9-practice",
        learner_id="learner_c",
        task_id="r9",
        task_type="reading_qa",
        difficulty=2,
        response_text="Survey answer",
        score=0.5,
        error_tags=["missing_key_evidence"],
        guidance_mode="adaptive_guidance",
        round_index=1,
        phase="practice",
    )

    guidance = ExperimentRunner._compose_post_guidance(
        "adaptive_guidance",
        "reading_qa",
        "Adaptive post-practice guidance:\nUse only the current passage.",
        [practice_record],
        state,
    )

    assert "Practice outcome: avg_score=0.50" in guidance
    assert "missing_key_evidence" in guidance
    assert "weakest_skill_after_practice=reading" in guidance
    assert "Use only the current passage" in guidance
    assert "Survey answer" not in guidance


def test_compact_adaptive_post_guidance_uses_updated_state() -> None:
    state = LearnerState(
        learner_id="learner_a",
        state_vector=StateVector(grammar=0.4, vocabulary=0.4, reading=0.3, confidence=0.5),
        recent_error_summary=RecentErrorSummary(
            top_errors=["low_keyword_overlap", "missing_key_evidence"],
            weakest_skill="reading",
        ),
    )
    plan = heuristic_tutoring_plan(state, "reading_qa")

    guidance = build_compact_adaptive_post_guidance("reading_qa", plan, state)

    assert "Adaptive post-practice guidance:" in guidance
    assert "Updated focus: reading" in guidance
    assert "weakest_skill=reading" in guidance
    assert "Use only the current passage" in guidance


def test_case_selection_is_deterministic_and_score_first() -> None:
    cases = [
        {
            "learner_id": "learner_b",
            "task_type": "grammar_correction",
            "score_delta": 0.092,
            "round2_score": 0.70,
            "round1_score": 0.608,
        },
        {
            "learner_id": "learner_a",
            "task_type": "reading_qa",
            "score_delta": 0.300,
            "round2_score": 0.85,
            "round1_score": 0.55,
        },
        {
            "learner_id": "learner_c",
            "task_type": "reading_qa",
            "score_delta": 0.300,
            "round2_score": 0.80,
            "round1_score": 0.50,
        },
        {
            "learner_id": "learner_b",
            "task_type": "reading_qa",
            "score_delta": 0.300,
            "round2_score": 0.80,
            "round1_score": 0.50,
        },
        {
            "learner_id": "learner_c",
            "task_type": "grammar_correction",
            "score_delta": 0.250,
            "round2_score": 0.90,
            "round1_score": 0.65,
        },
    ]

    selected = ExperimentRunner._select_cases(cases)

    assert [(case["learner_id"], case["task_type"]) for case in selected] == [
        ("learner_a", "reading_qa"),
        ("learner_b", "reading_qa"),
        ("learner_c", "reading_qa"),
    ]


def test_adaptive_feedback_reuses_pretest_evaluation(
    tmp_path: Path,
    monkeypatch,
) -> None:
    sample_config_path = ROOT / "data" / "config.mock.yaml"
    with sample_config_path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    payload["learners_path"] = str((ROOT / "data" / "learners.json").resolve())
    payload["tasks_path"] = str((ROOT / "data" / "tasks.jsonl").resolve())
    payload["bundles_path"] = str((ROOT / "data" / "bundles.json").resolve())
    payload["output_root"] = str(tmp_path)
    payload["run_name"] = "reuse_eval_run"
    temp_config = tmp_path / "config.yaml"
    with temp_config.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(payload, handle, sort_keys=False)

    original_score_task = runner_module.score_task
    call_count = 0

    def counting_score_task(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return original_score_task(*args, **kwargs)

    monkeypatch.setattr(runner_module, "score_task", counting_score_task)

    run_dir = run_experiment(str(temp_config))
    artifacts = load_run_artifacts(run_dir)

    assert call_count == len(artifacts.interactions)


def test_mock_runner_collects_triage_training_rows_in_shadow_mode(tmp_path: Path) -> None:
    sample_config_path = ROOT / "data" / "config.mock.yaml"
    with sample_config_path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    payload["learners_path"] = str((ROOT / "data" / "learners.json").resolve())
    payload["tasks_path"] = str((ROOT / "data" / "tasks.jsonl").resolve())
    payload["bundles_path"] = str((ROOT / "data" / "bundles.json").resolve())
    payload["output_root"] = str(tmp_path)
    payload["run_name"] = "triage_shadow_run"
    payload["reading_judge_triage"] = {
        "enabled": True,
        "mode": "shadow",
        "model_path": str(tmp_path / "missing.pt"),
        "confidence_threshold": 0.90,
        "collect_training_data": True,
    }
    temp_config = tmp_path / "config.yaml"
    with temp_config.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(payload, handle, sort_keys=False)

    run_dir = run_experiment(str(temp_config))
    artifacts = load_run_artifacts(run_dir)
    training_rows = (run_dir / "triage_training.jsonl").read_text(encoding="utf-8").splitlines()

    assert any(record.triage_candidate for record in artifacts.interactions)
    assert any(record.used_judge for record in artifacts.interactions)
    assert training_rows


def _write_temp_config(tmp_path: Path, payload: dict) -> Path:
    temp_config = tmp_path / "config.yaml"
    with temp_config.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(payload, handle, sort_keys=False)
    return temp_config


def test_runner_rejects_bundle_task_type_mismatch(tmp_path: Path) -> None:
    sample_config_path = ROOT / "data" / "config.mock.yaml"
    with sample_config_path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    payload["learners_path"] = str((ROOT / "data" / "learners.json").resolve())
    payload["tasks_path"] = str((ROOT / "data" / "tasks.jsonl").resolve())
    payload["output_root"] = str(tmp_path)
    bundles_path = tmp_path / "bundles.json"
    bundles = json.loads((ROOT / "data" / "bundles.json").read_text(encoding="utf-8"))
    bundles["bundle_definitions"]["reading_pre"] = ["g1"]
    bundles_path.write_text(json.dumps(bundles), encoding="utf-8")
    payload["bundles_path"] = str(bundles_path)

    with pytest.raises(ValueError, match="contains grammar_correction task"):
        ExperimentRunner(runner_module.load_config(_write_temp_config(tmp_path, payload)))


def test_runner_rejects_missing_assignment(tmp_path: Path) -> None:
    sample_config_path = ROOT / "data" / "config.mock.yaml"
    with sample_config_path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    payload["learners_path"] = str((ROOT / "data" / "learners.json").resolve())
    payload["tasks_path"] = str((ROOT / "data" / "tasks.jsonl").resolve())
    payload["output_root"] = str(tmp_path)
    bundles_path = tmp_path / "bundles.json"
    bundles = json.loads((ROOT / "data" / "bundles.json").read_text(encoding="utf-8"))
    bundles["assignments"].pop("learner_c")
    bundles_path.write_text(json.dumps(bundles), encoding="utf-8")
    payload["bundles_path"] = str(bundles_path)

    with pytest.raises(ValueError, match="missing learners"):
        ExperimentRunner(runner_module.load_config(_write_temp_config(tmp_path, payload)))


def test_runner_flushes_interactions_incrementally_on_failure(
    tmp_path: Path,
    monkeypatch,
) -> None:
    sample_config_path = ROOT / "data" / "config.mock.yaml"
    with sample_config_path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    payload["learners_path"] = str((ROOT / "data" / "learners.json").resolve())
    payload["tasks_path"] = str((ROOT / "data" / "tasks.jsonl").resolve())
    payload["bundles_path"] = str((ROOT / "data" / "bundles.json").resolve())
    payload["output_root"] = str(tmp_path)
    payload["run_name"] = "partial_run"
    runner = ExperimentRunner(runner_module.load_config(_write_temp_config(tmp_path, payload)))
    original_answer_task = runner._answer_task
    call_count = 0

    def flaky_answer_task(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise RuntimeError("forced failure")
        return original_answer_task(*args, **kwargs)

    monkeypatch.setattr(runner, "_answer_task", flaky_answer_task)

    with pytest.raises(RuntimeError, match="forced failure"):
        runner.run()

    interactions_path = tmp_path / "partial_run" / "interactions.jsonl"
    assert interactions_path.exists()
    assert len(interactions_path.read_text(encoding="utf-8").splitlines()) == 1


def test_runner_passes_role_specific_generation_settings(tmp_path: Path) -> None:
    sample_config_path = ROOT / "data" / "config.mock.yaml"
    with sample_config_path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    payload["learners_path"] = str((ROOT / "data" / "learners.json").resolve())
    payload["tasks_path"] = str((ROOT / "data" / "tasks.jsonl").resolve())
    payload["bundles_path"] = str((ROOT / "data" / "bundles.json").resolve())
    payload["output_root"] = str(tmp_path)
    payload["run_name"] = "generation_settings"
    payload["generation"] = {
        "learner_temperature": 0.7,
        "tutor_temperature": 0.2,
        "feedback_temperature": 0.3,
        "judge_temperature": 0.0,
        "use_seed": True,
        "vary_learner_seed": True,
    }
    runner = ExperimentRunner(runner_module.load_config(_write_temp_config(tmp_path, payload)))
    calls = []

    def fake_generate(messages, model, response_format=None, seed=None, temperature=None, metadata=None):
        calls.append(
            {
                "role": (metadata or {}).get("role"),
                "seed": seed,
                "temperature": temperature,
                "response_format": response_format,
            }
        )
        role = (metadata or {}).get("role")
        if role == "learner":
            task = metadata["task"]
            if task["task_type"] == "reading_qa":
                return "partial answer"
            return task["reference_answer"]
        if role == "judge":
            return '{"score": 1.0, "note": "ok"}'
        if role == "tutor_planner":
            return (
                '{"focus_skill":"grammar","focus_subskills":["tense"],'
                '"recommended_difficulty":2,'
                '"feedback_style":"concise_correction",'
                '"hint_level":"low",'
                '"next_task_type":"grammar_correction",'
                '"next_batch_size":1,'
                '"adaptation_rationale":"test"}'
            )
        if role == "feedback":
            return "Short feedback."
        return ""

    runner.backend.generate = fake_generate

    runner.run()

    learner_calls = [call for call in calls if call["role"] == "learner"]
    judge_calls = [call for call in calls if call["role"] == "judge"]
    assert learner_calls
    assert all(call["temperature"] == 0.7 for call in learner_calls)
    assert len({call["seed"] for call in learner_calls[:4]}) > 1
    assert all(0 <= call["seed"] < 2_147_483_647 for call in learner_calls)
    assert judge_calls
    assert all(call["temperature"] == 0.0 for call in judge_calls)
    assert all(call["seed"] == 42 for call in judge_calls)
