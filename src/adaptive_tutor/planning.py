from __future__ import annotations

from pydantic import ValidationError

from adaptive_tutor.backends.base import LLMBackend
from adaptive_tutor.prompts import build_tutor_plan_messages
from adaptive_tutor.schemas import LearnerState, TaskType, TutoringPlan
from adaptive_tutor.utils import parse_json_object

ERROR_TO_SUBSKILL = {
    "tense_error": "tense",
    "article_error": "articles",
    "sva_error": "subject_verb_agreement",
    "preposition_error": "prepositions",
    "plural_error": "plural_forms",
    "word_order_error": "word_order",
    "low_keyword_overlap": "evidence_selection",
    "answer_mismatch": "answer_accuracy",
    "detail_missing": "detail_location",
    "grammar_mismatch": "sentence_form",
}


def validate_tutoring_plan_payload(payload: dict) -> TutoringPlan:
    return TutoringPlan.model_validate(payload)


def heuristic_tutoring_plan(learner_state: LearnerState, task_type: TaskType) -> TutoringPlan:
    if task_type == "grammar_correction":
        focus_skill = "grammar"
        primary_value = learner_state.state_vector.grammar
        fallback_subskills = ["tense", "articles"]
    else:
        focus_skill = "reading"
        primary_value = learner_state.state_vector.reading
        fallback_subskills = ["detail_location", "evidence_selection"]
    if learner_state.recent_error_summary.weakest_skill == "vocabulary":
        focus_skill = "vocabulary"
        primary_value = learner_state.state_vector.vocabulary
    recommended_difficulty = 1 if primary_value < 0.45 else 2 if primary_value < 0.70 else 3
    if primary_value < 0.40:
        feedback_style = "step_by_step_hint"
        hint_level = "high"
    elif primary_value < 0.65:
        feedback_style = "correction_brief_explanation"
        hint_level = "medium"
    else:
        feedback_style = "concise_correction"
        hint_level = "low"
    top_errors = learner_state.recent_error_summary.top_errors
    subskills = [
        ERROR_TO_SUBSKILL.get(error, error.replace("_error", ""))
        for error in top_errors[:2]
    ] or fallback_subskills
    return TutoringPlan(
        focus_skill=focus_skill,
        focus_subskills=subskills,
        recommended_difficulty=recommended_difficulty,
        feedback_style=feedback_style,
        hint_level=hint_level,
        next_task_type=task_type,
        next_batch_size=3,
        adaptation_rationale=(
            f"The learner shows recurring weaknesses in {focus_skill} and needs targeted practice."
        ),
    )


def generate_tutoring_plan(
    backend: LLMBackend,
    model: str,
    learner_state: LearnerState,
    task_type: TaskType,
    seed: int,
) -> TutoringPlan:
    messages = build_tutor_plan_messages(learner_state, task_type, ["grammar_correction", "reading_qa"])
    raw_text = backend.generate(
        messages=messages,
        model=model,
        response_format={"type": "json_object"},
        seed=seed,
        metadata={
            "role": "tutor_planner",
            "learner_state": learner_state.model_dump(),
            "task_type": task_type,
        },
    )
    try:
        return validate_tutoring_plan_payload(parse_json_object(raw_text))
    except (ValueError, ValidationError):
        return heuristic_tutoring_plan(learner_state, task_type)
