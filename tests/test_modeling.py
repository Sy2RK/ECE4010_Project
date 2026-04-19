from __future__ import annotations

from adaptive_tutor.modeling import LearnerModeler
from adaptive_tutor.schemas import EvaluationResult, LearnerProfile, Task


def test_modeler_tracks_weakest_skill_and_recent_errors() -> None:
    learner = LearnerProfile.model_validate(
        {
            "learner_id": "learner_b",
            "weak_skills": ["grammar"],
            "mid_skills": ["reading", "vocabulary"],
            "strong_skills": [],
            "typical_errors": ["tense_error", "article_error"],
            "answer_style": "short",
        }
    )
    grammar_task = Task.model_validate(
        {
            "task_id": "g-test",
            "task_type": "grammar_correction",
            "difficulty": 1,
            "prompt": "Correct the sentence.",
            "input_text": "I saw cat.",
            "reference_answer": "I saw a cat.",
            "skill_tags": ["grammar", "articles"],
        }
    )
    modeler = LearnerModeler(learner)
    modeler.update(
        grammar_task,
        EvaluationResult(score=0.3, error_tags=["article_error"], evaluator_note="partial"),
    )
    state = modeler.update(
        grammar_task,
        EvaluationResult(score=0.2, error_tags=["article_error"], evaluator_note="partial"),
    )
    assert state.recent_error_summary.weakest_skill == "grammar"
    assert "article_error" in state.recent_error_summary.top_errors
    assert state.state_vector.confidence < 0.5
