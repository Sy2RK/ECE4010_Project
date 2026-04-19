from __future__ import annotations

from collections import Counter, deque

from adaptive_tutor.schemas import EvaluationResult, LearnerProfile, LearnerState, RecentErrorSummary, StateVector, Task
from adaptive_tutor.utils import clamp

ERROR_SKILL_MAP = {
    "tense_error": ["grammar"],
    "article_error": ["grammar", "vocabulary"],
    "sva_error": ["grammar"],
    "preposition_error": ["grammar", "vocabulary"],
    "plural_error": ["grammar"],
    "word_order_error": ["grammar"],
    "grammar_mismatch": ["grammar"],
    "low_keyword_overlap": ["reading", "vocabulary"],
    "answer_mismatch": ["reading"],
    "detail_missing": ["reading"],
    "empty_answer": ["reading", "grammar", "confidence"],
}


def initial_skill_value(profile: LearnerProfile, skill: str) -> float:
    if skill in profile.weak_skills:
        return 0.35
    if skill in profile.strong_skills:
        return 0.80
    if skill in profile.mid_skills:
        return 0.60
    return 0.60


def task_skill_roles(task: Task) -> tuple[str, list[str]]:
    if task.task_type == "grammar_correction":
        return "grammar", ["vocabulary"]
    return "reading", ["vocabulary"]


class LearnerModeler:
    def __init__(self, profile: LearnerProfile) -> None:
        self.profile = profile
        self.skill_scores = {
            "grammar": initial_skill_value(profile, "grammar"),
            "vocabulary": initial_skill_value(profile, "vocabulary"),
            "reading": initial_skill_value(profile, "reading"),
        }
        self.confidence = 0.50
        self.error_counts: Counter[str] = Counter()
        self.recent_errors: deque[list[str]] = deque(maxlen=2)

    def update(self, task: Task, evaluation: EvaluationResult) -> LearnerState:
        primary_skill, secondary_skills = task_skill_roles(task)
        item_score = evaluation.score
        self.skill_scores[primary_skill] = clamp(
            0.75 * self.skill_scores[primary_skill] + 0.25 * item_score
        )
        for skill in secondary_skills:
            self.skill_scores[skill] = clamp(0.90 * self.skill_scores[skill] + 0.10 * item_score)
        repeat_error_penalty = 0.0
        for error in evaluation.error_tags:
            if self.error_counts[error] > 0:
                repeat_error_penalty += 0.05
                for skill in ERROR_SKILL_MAP.get(error, [primary_skill]):
                    if skill == "confidence":
                        continue
                    self.skill_scores[skill] = clamp(self.skill_scores[skill] - 0.05)
            self.error_counts[error] += 1
        self.confidence = clamp(0.80 * self.confidence + 0.20 * (item_score - repeat_error_penalty))
        self.recent_errors.append(list(evaluation.error_tags))
        return self.snapshot()

    def snapshot(self) -> LearnerState:
        flattened = [error for group in self.recent_errors for error in group]
        counts = Counter(flattened)
        top_errors = [item for item, _ in counts.most_common(2)]
        weakest_skill = min(self.skill_scores, key=self.skill_scores.get)
        return LearnerState(
            learner_id=self.profile.learner_id,
            state_vector=StateVector(
                grammar=round(self.skill_scores["grammar"], 3),
                vocabulary=round(self.skill_scores["vocabulary"], 3),
                reading=round(self.skill_scores["reading"], 3),
                confidence=round(self.confidence, 3),
            ),
            recent_error_summary=RecentErrorSummary(
                top_errors=top_errors,
                weakest_skill=weakest_skill,
            ),
        )
