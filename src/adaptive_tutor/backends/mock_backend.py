from __future__ import annotations

import json
import random
import re
from typing import Any

from adaptive_tutor.backends.base import LLMBackend
from adaptive_tutor.evaluation import keyword_tokens
from adaptive_tutor.schemas import LearnerProfile, LearnerState, Task, TutoringPlan
from adaptive_tutor.utils import clamp, deterministic_seed

MODE_BONUS = {
    "no_guidance": 0.02,
    "generic_guidance": 0.08,
    "adaptive_guidance": 0.25,
}


class MockBackend(LLMBackend):
    def generate(
        self,
        messages: list[dict[str, str]],
        model: str,
        response_format: dict[str, Any] | None = None,
        seed: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        meta = metadata or {}
        role = meta.get("role")
        if role == "learner":
            return self._generate_learner_answer(seed or 0, meta)
        if role == "tutor_planner":
            return self._generate_tutoring_plan(meta)
        if role == "feedback":
            return self._generate_feedback(meta)
        if role == "judge":
            return self._generate_judge(meta)
        return ""

    def _generate_learner_answer(self, seed: int, meta: dict[str, Any]) -> str:
        task = Task.model_validate(meta["task"])
        learner = LearnerProfile.model_validate(meta["learner"])
        mode = meta["mode"]
        phase = meta["phase"]
        focus_skill = meta.get("focus_skill")
        guidance_text = meta.get("guidance_text", "")
        seed_key = mode if phase == "posttest" else "shared_pretest"
        rng = random.Random(
            deterministic_seed(seed, learner.learner_id, task.task_id, seed_key, phase)
        )
        primary_skill = "grammar" if task.task_type == "grammar_correction" else "reading"
        base_level = self._skill_level(learner, primary_skill)
        difficulty_penalty = 0.08 * (task.difficulty - 1)
        mode_bonus = 0.0
        if phase == "posttest":
            mode_bonus += MODE_BONUS.get(mode, 0.0)
            if focus_skill == primary_skill:
                mode_bonus += 0.12
            elif focus_skill == "vocabulary":
                mode_bonus += 0.05
            if guidance_text:
                mode_bonus += 0.03
        effective_skill = clamp(base_level + mode_bonus - difficulty_penalty, 0.05, 0.95)
        if task.task_type == "grammar_correction":
            return self._answer_grammar(task.reference_answer, learner, effective_skill, rng)
        return self._answer_reading(task, effective_skill, rng)

    def _generate_tutoring_plan(self, meta: dict[str, Any]) -> str:
        learner_state = LearnerState.model_validate(meta["learner_state"])
        task_type = meta["task_type"]
        weakest_skill = learner_state.recent_error_summary.weakest_skill
        focus_skill = "grammar" if task_type == "grammar_correction" else "reading"
        if weakest_skill == "vocabulary":
            focus_skill = "vocabulary"
        primary_value = getattr(learner_state.state_vector, focus_skill)
        recommended_difficulty = 1 if primary_value < 0.45 else 2 if primary_value < 0.7 else 3
        if primary_value < 0.40:
            feedback_style = "step_by_step_hint"
            hint_level = "high"
        elif primary_value < 0.65:
            feedback_style = "correction_brief_explanation"
            hint_level = "medium"
        else:
            feedback_style = "concise_correction"
            hint_level = "low"
        top_errors = learner_state.recent_error_summary.top_errors or (
            ["tense_error"] if task_type == "grammar_correction" else ["detail_missing"]
        )
        payload = {
            "focus_skill": focus_skill,
            "focus_subskills": [error.replace("_error", "") for error in top_errors[:2]],
            "recommended_difficulty": recommended_difficulty,
            "feedback_style": feedback_style,
            "hint_level": hint_level,
            "next_task_type": task_type,
            "next_batch_size": 3,
            "adaptation_rationale": (
                f"The learner needs more support on {focus_skill} because of recent mistakes."
            ),
        }
        return json.dumps(payload)

    def _generate_feedback(self, meta: dict[str, Any]) -> str:
        plan = TutoringPlan.model_validate(meta["plan"])
        reference_answer = meta["reference_answer"]
        error_tags = meta.get("error_tags", [])
        task_type = meta["task_type"]
        if task_type == "grammar_correction":
            opening = (
                f"Your sentence needs revision: {', '.join(error_tags) or 'minor grammar issue'}."
            )
            correction = f"Correct form: {reference_answer}"
            explanation = "Check verb form and sentence structure before you answer again."
        else:
            opening = (
                f"Your answer is incomplete: {', '.join(error_tags) or 'missing evidence'}."
            )
            correction = f"Key answer: {reference_answer}"
            explanation = "Use the exact evidence from the passage to support the answer."
        next_tip = f"Next tip: focus on {plan.focus_skill} with {plan.hint_level} hints."
        if plan.feedback_style == "concise_correction":
            return f"{opening} {correction} {next_tip}"
        if plan.feedback_style == "step_by_step_hint":
            return (
                f"{opening} Compare your answer with the key evidence. "
                f"{correction} {explanation} {next_tip}"
            )
        return f"{opening} {correction} {explanation} {next_tip}"

    def _generate_judge(self, meta: dict[str, Any]) -> str:
        rule_score = float(meta["rule_score"])
        learner_answer = str(meta["learner_answer"]).strip()
        if not learner_answer:
            payload = {"score": 0.0, "note": "The answer is empty."}
        elif rule_score >= 0.66:
            payload = {"score": 1.0, "note": "The answer covers the key information."}
        elif rule_score >= 0.35:
            payload = {"score": 0.5, "note": "The answer is partially correct but incomplete."}
        else:
            payload = {"score": 0.0, "note": "The answer misses the required evidence."}
        return json.dumps(payload)

    def _skill_level(self, learner: LearnerProfile, skill: str) -> float:
        if skill in learner.strong_skills:
            return 0.80
        if skill in learner.weak_skills:
            return 0.35
        if skill in learner.mid_skills:
            return 0.60
        return 0.60

    def _answer_grammar(
        self,
        reference_answer: str,
        learner: LearnerProfile,
        effective_skill: float,
        rng: random.Random,
    ) -> str:
        if effective_skill >= 0.65:
            return reference_answer
        error_count = 1 if effective_skill >= 0.45 else 2
        response = reference_answer
        grammar_errors = [
            error for error in learner.typical_errors if error.endswith("_error")
        ] or ["tense_error", "article_error"]
        chosen = grammar_errors[:]
        rng.shuffle(chosen)
        for error in chosen[:error_count]:
            mutated = self._apply_error(response, error)
            if mutated != response:
                response = mutated
        if effective_skill < 0.35:
            response = self._apply_error(response, "word_order_error")
        if response == reference_answer:
            response = self._apply_error(reference_answer, "word_order_error")
        return response

    def _answer_reading(self, task: Task, effective_skill: float, rng: random.Random) -> str:
        reference_answer = task.reference_answer
        if effective_skill >= 0.80:
            return reference_answer
        ref_keywords = keyword_tokens(reference_answer)
        if effective_skill >= 0.60:
            keep = max(2, len(ref_keywords) - 1)
            return " ".join(ref_keywords[:keep])
        if effective_skill >= 0.40:
            keep = max(1, len(ref_keywords) // 2)
            return " ".join(ref_keywords[:keep])
        passage_tokens = re.findall(r"[A-Za-z']+", task.passage or "")
        if passage_tokens:
            start = rng.randint(0, max(len(passage_tokens) - 3, 0))
            return " ".join(passage_tokens[start : start + 3])
        return "I do not know."

    def _apply_error(self, text: str, error_type: str) -> str:
        if error_type == "article_error":
            updated = re.sub(r"\b(a|an|the)\b\s+", "", text, count=1, flags=re.IGNORECASE)
            if updated != text:
                return re.sub(r"\s+", " ", updated).strip()
            return "the " + text
        if error_type == "tense_error":
            for source, target in [
                ("goes", "go"),
                ("called", "call"),
                ("studied", "study"),
                ("was", "is"),
                ("went", "go"),
            ]:
                updated = re.sub(rf"\b{source}\b", target, text, count=1, flags=re.IGNORECASE)
                if updated != text:
                    return updated
        if error_type == "sva_error":
            for source, target in [
                ("are", "is"),
                ("is", "are"),
                ("has", "have"),
                ("likes", "like"),
            ]:
                updated = re.sub(rf"\b{source}\b", target, text, count=1, flags=re.IGNORECASE)
                if updated != text:
                    return updated
        if error_type == "preposition_error":
            for source, target in [("at", "on"), ("on", "in"), ("to", "for"), ("with", "to")]:
                updated = re.sub(rf"\b{source}\b", target, text, count=1, flags=re.IGNORECASE)
                if updated != text:
                    return updated
        if error_type == "plural_error":
            for source, target in [("children", "child"), ("books", "book"), ("apples", "apple")]:
                updated = re.sub(rf"\b{source}\b", target, text, count=1, flags=re.IGNORECASE)
                if updated != text:
                    return updated
        if error_type == "word_order_error":
            tokens = text.split()
            if len(tokens) >= 2:
                tokens[0], tokens[1] = tokens[1], tokens[0]
                return " ".join(tokens)
        return text
