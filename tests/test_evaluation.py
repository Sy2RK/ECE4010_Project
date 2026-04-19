from __future__ import annotations

from adaptive_tutor.evaluation import score_grammar_answer, score_reading_answer
from adaptive_tutor.schemas import JudgeDecision, Task


def test_grammar_partial_score_and_tags() -> None:
    task = Task.model_validate(
        {
            "task_id": "g-test",
            "task_type": "grammar_correction",
            "difficulty": 1,
            "prompt": "Correct the sentence.",
            "input_text": "She go to school every day.",
            "reference_answer": "She goes to school every day.",
            "skill_tags": ["grammar", "tense", "sva"],
        }
    )
    result = score_grammar_answer(task, "She go to school every day.")
    assert 0 < result.score < 1
    assert "tense_error" in result.error_tags or "sva_error" in result.error_tags


def test_grammar_accepts_common_contractions() -> None:
    task = Task.model_validate(
        {
            "task_id": "g-test-contraction",
            "task_type": "grammar_correction",
            "difficulty": 2,
            "prompt": "Correct the sentence.",
            "input_text": "She don't wanted to stop.",
            "reference_answer": "She did not want to stop.",
            "skill_tags": ["grammar", "tense"],
        }
    )
    result = score_grammar_answer(task, "She didn't want to stop.")
    assert result.score == 1.0
    assert result.error_tags == []


def test_reading_uses_judge_in_gray_zone() -> None:
    task = Task.model_validate(
        {
            "task_id": "r-test",
            "task_type": "reading_qa",
            "difficulty": 2,
            "passage": "Nina emailed her teacher and borrowed paper from a classmate after she lost her notebook.",
            "question": "What two actions did Nina take?",
            "reference_answer": "She emailed her teacher and borrowed paper from a classmate.",
            "skill_tags": ["reading", "detail_location", "evidence_selection"],
        }
    )

    def judge(_task: Task, _answer: str, _rule_score: float) -> JudgeDecision:
        return JudgeDecision(score=0.5, note="Partial evidence.")

    result = score_reading_answer(task, "She emailed her teacher.", (0.25, 0.75), judge)
    assert result.used_judge is True
    assert result.score == 0.5
    assert "missing_key_evidence" in result.error_tags


def test_reading_clears_error_tags_for_high_quality_answer() -> None:
    task = Task.model_validate(
        {
            "task_id": "r-test-full",
            "task_type": "reading_qa",
            "difficulty": 2,
            "passage": "The event was moved because the guest was free and the room was available.",
            "question": "Why was the event moved?",
            "reference_answer": "Because the guest was free and the room was available.",
            "skill_tags": ["reading", "evidence_selection"],
        }
    )

    result = score_reading_answer(task, "The guest was free and the room was available.", (0.25, 0.75), None)
    assert result.used_judge is False
    assert result.score >= 0.85
    assert result.error_tags == []


def test_reading_falls_back_when_no_judge() -> None:
    task = Task.model_validate(
        {
            "task_id": "r-test-2",
            "task_type": "reading_qa",
            "difficulty": 2,
            "passage": "Nina emailed her teacher and borrowed paper from a classmate after she lost her notebook.",
            "question": "What two actions did Nina take?",
            "reference_answer": "She emailed her teacher and borrowed paper from a classmate.",
            "skill_tags": ["reading", "detail_location", "evidence_selection"],
        }
    )
    result = score_reading_answer(task, "She emailed her teacher.", (0.25, 0.75), None)
    assert result.used_judge is False
    assert "judge_skipped" in result.error_tags


def test_reading_shadow_triage_still_uses_judge() -> None:
    task = Task.model_validate(
        {
            "task_id": "r-shadow",
            "task_type": "reading_qa",
            "difficulty": 2,
            "passage": "Nina emailed her teacher and borrowed paper from a classmate.",
            "question": "What two actions did Nina take?",
            "reference_answer": "She emailed her teacher and borrowed paper from a classmate.",
            "skill_tags": ["reading", "detail_location"],
        }
    )
    judge_calls = 0

    def judge(_task: Task, _answer: str, _rule_score: float) -> JudgeDecision:
        nonlocal judge_calls
        judge_calls += 1
        return JudgeDecision(score=0.5, note="Judge label.")

    def triage(_task: Task, _answer: str, _rule_score: float) -> dict:
        return {
            "candidate": True,
            "available": True,
            "prediction": 1.0,
            "confidence": 0.99,
            "would_skip": False,
            "features": [[0.1] * 8],
        }

    result = score_reading_answer(task, "She emailed her teacher.", (0.25, 0.75), judge, triage)
    assert judge_calls == 1
    assert result.used_judge is True
    assert result.used_triage is True
    assert result.scoring_source == "judge"
    assert result.triage_prediction == 1.0


def test_reading_enforce_triage_skips_judge_when_confident() -> None:
    task = Task.model_validate(
        {
            "task_id": "r-enforce",
            "task_type": "reading_qa",
            "difficulty": 2,
            "passage": "Nina emailed her teacher and borrowed paper from a classmate.",
            "question": "What two actions did Nina take?",
            "reference_answer": "She emailed her teacher and borrowed paper from a classmate.",
            "skill_tags": ["reading", "detail_location"],
        }
    )
    judge_calls = 0

    def judge(_task: Task, _answer: str, _rule_score: float) -> JudgeDecision:
        nonlocal judge_calls
        judge_calls += 1
        return JudgeDecision(score=0.0, note="Should not be used.")

    def triage(_task: Task, _answer: str, _rule_score: float) -> dict:
        return {
            "candidate": True,
            "available": True,
            "prediction": 0.5,
            "confidence": 0.95,
            "would_skip": True,
            "features": [[0.1] * 8],
        }

    result = score_reading_answer(task, "She emailed her teacher.", (0.25, 0.75), judge, triage)
    assert judge_calls == 0
    assert result.used_judge is False
    assert result.used_triage is True
    assert result.scoring_source == "triage"
    assert result.score == 0.5
