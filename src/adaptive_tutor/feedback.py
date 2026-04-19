from __future__ import annotations

from adaptive_tutor.backends.base import LLMBackend
from adaptive_tutor.prompts import build_feedback_messages
from adaptive_tutor.schemas import EvaluationResult, FeedbackRecord, GuidanceMode, Task, TutoringPlan


def fallback_feedback(task: Task, evaluation: EvaluationResult, plan: TutoringPlan) -> str:
    if task.task_type == "grammar_correction":
        return (
            f"Main issue: {', '.join(evaluation.error_tags) or 'minor grammar issue'}. "
            f"Check the corrected sentence and focus on {plan.focus_skill} next."
        )
    return (
        f"Main issue: {', '.join(evaluation.error_tags) or 'missing evidence'}. "
        f"Use the passage evidence more directly and focus on {plan.focus_skill} next."
    )


def generate_feedback_record(
    backend: LLMBackend,
    model: str,
    learner_id: str,
    guidance_mode: GuidanceMode,
    task: Task,
    learner_answer: str,
    evaluation: EvaluationResult,
    plan: TutoringPlan,
    recommended_task_ids: list[str],
    seed: int,
) -> FeedbackRecord:
    messages = build_feedback_messages(
        task=task,
        learner_answer=learner_answer,
        reference_answer=task.reference_answer,
        tutoring_plan=plan,
        error_tags=evaluation.error_tags,
    )
    raw_text = backend.generate(
        messages=messages,
        model=model,
        response_format=None,
        seed=seed,
        metadata={
            "role": "feedback",
            "plan": plan.model_dump(),
            "task_type": task.task_type,
            "reference_answer": task.reference_answer,
            "learner_answer": learner_answer,
            "error_tags": evaluation.error_tags,
        },
    ).strip()
    feedback_text = raw_text or fallback_feedback(task, evaluation, plan)
    return FeedbackRecord(
        learner_id=learner_id,
        task_id=task.task_id,
        task_type=task.task_type,
        guidance_mode=guidance_mode,
        round_index=1,
        feedback_style=plan.feedback_style,
        feedback_text=feedback_text,
        next_task_recommendation=recommended_task_ids,
        focus_skill=plan.focus_skill,
    )
