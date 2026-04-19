from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from adaptive_tutor.io_utils import load_json, read_csv_dicts, read_jsonl_models, write_json
from adaptive_tutor.schemas import (
    ExperimentMetric,
    FeedbackRecord,
    InteractionRecord,
    PlanRecord,
    RunArtifacts,
    StateRecord,
)
from adaptive_tutor.utils import average


def _markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    header_row = "| " + " | ".join(headers) + " |"
    separator = "| " + " | ".join(["---"] * len(headers)) + " |"
    body = ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join([header_row, separator, *body])


def _format_float(value: float) -> str:
    return f"{value:.2f}"


def load_run_artifacts(run_dir: str | Path) -> RunArtifacts:
    run_path = Path(run_dir)
    interactions = read_jsonl_models(run_path / "interactions.jsonl", InteractionRecord)
    states = read_jsonl_models(run_path / "states.jsonl", StateRecord)
    plans = read_jsonl_models(run_path / "plans.jsonl", PlanRecord)
    feedback = read_jsonl_models(run_path / "feedback.jsonl", FeedbackRecord)
    metrics = [
        ExperimentMetric.model_validate(
            {
                **row,
                "round1_score": float(row["round1_score"]),
                "round2_score": float(row["round2_score"]),
                "score_delta": float(row["score_delta"]),
            }
        )
        for row in read_csv_dicts(run_path / "metrics.csv")
    ]
    cases = load_json(run_path / "cases.json")
    return RunArtifacts(
        interactions=interactions,
        states=states,
        plans=plans,
        feedback=feedback,
        metrics=metrics,
        cases=cases,
    )


def build_report_text(artifacts: RunArtifacts) -> str:
    metrics = artifacts.metrics
    by_mode: dict[str, list[ExperimentMetric]] = defaultdict(list)
    by_task_mode: dict[tuple[str, str], list[ExperimentMetric]] = defaultdict(list)
    learner_mode_map: dict[tuple[str, str], list[ExperimentMetric]] = defaultdict(list)
    for metric in metrics:
        by_mode[metric.mode].append(metric)
        by_task_mode[(metric.task_type, metric.mode)].append(metric)
        learner_mode_map[(metric.learner_id, metric.mode)].append(metric)
    triage_candidates = sum(1 for record in artifacts.interactions if record.triage_candidate)
    triage_skips = sum(1 for record in artifacts.interactions if record.scoring_source == "triage")
    judge_calls = sum(1 for record in artifacts.interactions if record.used_judge)
    baseline_judge_calls = judge_calls + triage_skips
    skip_rate = triage_skips / triage_candidates if triage_candidates else 0.0
    reduction_rate = triage_skips / baseline_judge_calls if baseline_judge_calls else 0.0

    modes = sorted(by_mode)
    learner_ids = sorted({metric.learner_id for metric in metrics})
    task_types = sorted({metric.task_type for metric in metrics})

    overall_rows = [
        [
            mode,
            _format_float(average(item.round1_score for item in items)),
            _format_float(average(item.round2_score for item in items)),
            _format_float(average(item.score_delta for item in items)),
        ]
        for mode, items in sorted(by_mode.items())
    ]
    learner_rows = [
        [
            learner_id,
            *[
                _format_float(
                    average(item.score_delta for item in learner_mode_map.get((learner_id, mode), []))
                )
                for mode in modes
            ],
        ]
        for learner_id in learner_ids
    ]
    task_rows = []
    for task_type in task_types:
        for mode in modes:
            items = by_task_mode.get((task_type, mode), [])
            task_rows.append(
                [
                    task_type,
                    mode,
                    _format_float(average(item.round1_score for item in items)),
                    _format_float(average(item.round2_score for item in items)),
                    _format_float(average(item.score_delta for item in items)),
                ]
            )

    case_lines: list[str] = []
    for index, case in enumerate(artifacts.cases, start=1):
        practice_examples = case.get("practice_examples", [])
        practice_task_ids = [record["task_id"] for record in practice_examples]
        case_lines.extend(
            [
                f"### Case {index}: {case['learner_id']} / {case['task_type']}",
                f"- Mode: {case['mode']}",
                f"- Score: {case['round1_score']:.2f} -> {case['round2_score']:.2f} (delta {case['score_delta']:.2f})",
                (
                    f"- Weakest skill before tutoring: "
                    f"{case['learner_state']['recent_error_summary']['weakest_skill']}"
                ),
                f"- Tutor focus: {case['tutoring_plan']['focus_skill']}",
                f"- Recommended tasks: {', '.join(case['recommended_task_ids']) or 'none'}",
                f"- Practice tasks used before posttest: {', '.join(practice_task_ids) or 'none'}",
                f"- Feedback excerpt: {case['feedback_excerpt']}",
                "",
            ]
        )

    total_runs = len(metrics)
    report = [
        "# Adaptive English AI Tutor Experiment Report",
        "",
        "## Overall Summary",
        f"本次运行共完成 {total_runs} 个子实验，覆盖 {len(learner_ids)} 个 learners、{len(modes)} 种 guidance modes、{len(task_types)} 种 task types。",
        "pretest/posttest 仍使用固定题组；generic/adaptive guidance 在中间增加非计分 practice phase，practice 结果只用于后续提示和 learner state 更新，不进入 score_delta。",
        "",
        _markdown_table(["mode", "avg_round1", "avg_round2", "avg_delta"], overall_rows),
        "",
        "## By Learner",
        _markdown_table(["learner_id", *modes], learner_rows),
        "",
        "## By Task Type",
        _markdown_table(["task_type", "mode", "avg_round1", "avg_round2", "avg_delta"], task_rows),
        "",
        "## Efficiency",
        _markdown_table(
            [
                "judge_calls",
                "baseline_judge_calls",
                "triage_candidates",
                "triage_skips",
                "skip_rate",
                "judge_call_reduction",
                "estimated_saved_api_calls",
            ],
            [
                [
                    str(judge_calls),
                    str(baseline_judge_calls),
                    str(triage_candidates),
                    str(triage_skips),
                    _format_float(skip_rate),
                    _format_float(reduction_rate),
                    str(triage_skips),
                ]
            ],
        ),
        "",
        "## Typical Cases",
        *case_lines,
    ]
    return "\n".join(report).strip() + "\n"


def generate_report(run_dir: str | Path) -> str:
    artifacts = load_run_artifacts(run_dir)
    report_text = build_report_text(artifacts)
    run_path = Path(run_dir)
    (run_path / "report.md").write_text(report_text, encoding="utf-8")
    write_json(run_path / "report_preview.json", {"case_count": len(artifacts.cases)})
    return report_text
