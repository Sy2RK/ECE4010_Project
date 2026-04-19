from __future__ import annotations

import re
from collections.abc import Callable
from difflib import SequenceMatcher
from typing import Any

from adaptive_tutor.schemas import EvaluationResult, JudgeDecision, Task

ARTICLES = {"a", "an", "the"}
PREPOSITIONS = {"in", "on", "at", "to", "for", "with", "from", "about"}
STOPWORDS = {
    "a",
    "an",
    "the",
    "and",
    "or",
    "to",
    "of",
    "for",
    "in",
    "on",
    "at",
    "is",
    "are",
    "was",
    "were",
    "be",
    "he",
    "she",
    "it",
    "they",
    "because",
    "after",
    "before",
    "could",
    "would",
    "should",
    "did",
    "do",
    "does",
}
CONTRACTIONS = {
    "aren't": "are not",
    "can't": "can not",
    "couldn't": "could not",
    "didn't": "did not",
    "doesn't": "does not",
    "don't": "do not",
    "hadn't": "had not",
    "hasn't": "has not",
    "haven't": "have not",
    "he's": "he is",
    "i'm": "i am",
    "isn't": "is not",
    "it's": "it is",
    "she's": "she is",
    "shouldn't": "should not",
    "that's": "that is",
    "there's": "there is",
    "they're": "they are",
    "wasn't": "was not",
    "weren't": "were not",
    "won't": "will not",
    "wouldn't": "would not",
}


def normalize_text(text: str) -> str:
    for contraction, expanded in CONTRACTIONS.items():
        text = re.sub(rf"\b{re.escape(contraction)}\b", expanded, text, flags=re.IGNORECASE)
    normalized = re.sub(r"[^a-z0-9\s']", " ", text.lower())
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def tokenize(text: str) -> list[str]:
    normalized = normalize_text(text)
    return normalized.split() if normalized else []


def keyword_tokens(text: str) -> list[str]:
    return [token for token in tokenize(text) if token not in STOPWORDS]


def _token_overlap_ratio(reference_tokens: list[str], response_tokens: list[str]) -> float:
    if not reference_tokens:
        return 0.0
    intersection = set(reference_tokens) & set(response_tokens)
    return len(intersection) / len(set(reference_tokens))


def _reference_components(text: str) -> list[list[str]]:
    normalized = normalize_text(text)
    pieces = re.split(r"\s*(?:,\s*and\s+|,\s*but\s+|\sand\s|\sbut\s|;)\s*", normalized)
    components = [keyword_tokens(piece) for piece in pieces]
    return [component for component in components if component]


def _evidence_coverage(reference: str, response: str) -> tuple[float, int]:
    components = _reference_components(reference)
    if not components:
        return 0.0, 0
    response_keywords = set(keyword_tokens(response))
    covered = 0
    for component in components:
        overlap = len(set(component) & response_keywords) / len(set(component))
        if overlap >= 0.5:
            covered += 1
    return covered / len(components), len(components)


def _detect_grammar_error_tags(reference: str, response: str) -> list[str]:
    if normalize_text(reference) == normalize_text(response):
        return []
    ref_tokens = tokenize(reference)
    resp_tokens = tokenize(response)
    tags: list[str] = []
    if (set(ref_tokens) & ARTICLES) != (set(resp_tokens) & ARTICLES):
        tags.append("article_error")
    if any(token in ref_tokens for token in {"went", "called", "studied", "finished", "was"}) and any(
        token in resp_tokens for token in {"go", "call", "study", "finish", "is"}
    ):
        tags.append("tense_error")
    if any(
        (token.endswith("ed") and token[:-2] in resp_tokens)
        or (token.endswith("es") and token[:-2] in resp_tokens)
        or (token.endswith("s") and token[:-1] in resp_tokens)
        for token in ref_tokens
    ):
        tags.append("sva_error")
    if any(token in ref_tokens for token in {"is", "are", "has", "have", "likes", "like"}) and any(
        token in resp_tokens for token in {"is", "are", "has", "have", "likes", "like"}
    ):
        if ref_tokens != resp_tokens:
            tags.append("sva_error")
    if (set(ref_tokens) & PREPOSITIONS) != (set(resp_tokens) & PREPOSITIONS):
        tags.append("preposition_error")
    if any(
        (token.endswith("s") and token[:-1] in resp_tokens) or (token + "s" in resp_tokens)
        for token in ref_tokens
    ):
        tags.append("plural_error")
    if sorted(ref_tokens) == sorted(resp_tokens) and ref_tokens != resp_tokens:
        tags.append("word_order_error")
    if not tags:
        tags.append("grammar_mismatch")
    return list(dict.fromkeys(tags))


def score_grammar_answer(task: Task, learner_answer: str) -> EvaluationResult:
    reference = task.reference_answer
    normalized_reference = normalize_text(reference)
    normalized_answer = normalize_text(learner_answer)
    if not normalized_answer:
        return EvaluationResult(
            score=0.0,
            error_tags=["empty_answer"],
            evaluator_note="Empty answer.",
            scoring_source="grammar_rule",
        )
    if normalized_reference == normalized_answer:
        return EvaluationResult(
            score=1.0,
            evaluator_note="Normalized exact match.",
            scoring_source="grammar_exact",
            rule_score=1.0,
        )
    reference_tokens = tokenize(reference)
    answer_tokens = tokenize(learner_answer)
    sequence_ratio = SequenceMatcher(None, normalized_reference, normalized_answer).ratio()
    overlap_ratio = _token_overlap_ratio(reference_tokens, answer_tokens)
    error_tags = _detect_grammar_error_tags(reference, learner_answer)
    score = min(0.95, 0.55 * sequence_ratio + 0.45 * overlap_ratio)
    score = round(max(0.0, score - 0.15 * min(3, len(error_tags))), 2)
    return EvaluationResult(
        score=score,
        error_tags=error_tags,
        evaluator_note="Partial grammar score from normalized similarity.",
        scoring_source="grammar_rule",
        rule_score=score,
    )


JudgeCallback = Callable[[Task, str, float], JudgeDecision]
TriageCallback = Callable[[Task, str, float], dict[str, Any]]


def _score_adjusted_reading_tags(score: float, error_tags: list[str]) -> list[str]:
    if score == 1.0:
        return []
    if score == 0.0 and "answer_mismatch" not in error_tags:
        return [*error_tags, "answer_mismatch"]
    return error_tags if error_tags else ["partial_reading_answer"]


def score_reading_answer(
    task: Task,
    learner_answer: str,
    gray_zone: tuple[float, float],
    judge_callback: JudgeCallback | None = None,
    triage_callback: TriageCallback | None = None,
) -> EvaluationResult:
    normalized_reference = normalize_text(task.reference_answer)
    normalized_answer = normalize_text(learner_answer)
    if not normalized_answer:
        return EvaluationResult(
            score=0.0,
            error_tags=["empty_answer", "answer_mismatch"],
            evaluator_note="Empty answer.",
            scoring_source="reading_rule",
            rule_score=0.0,
        )
    if normalized_reference == normalized_answer:
        return EvaluationResult(
            score=1.0,
            evaluator_note="Normalized exact match.",
            scoring_source="reading_exact",
            rule_score=1.0,
        )
    reference_keywords = keyword_tokens(task.reference_answer)
    answer_keywords = keyword_tokens(learner_answer)
    keyword_ratio = _token_overlap_ratio(reference_keywords, answer_keywords)
    evidence_ratio, component_count = _evidence_coverage(task.reference_answer, learner_answer)
    reference_tokens = tokenize(task.reference_answer)
    answer_tokens = tokenize(learner_answer)
    length_ratio = min(len(answer_tokens), len(reference_tokens)) / max(len(reference_tokens), 1)
    overlap_ratio = round(0.30 * keyword_ratio + 0.45 * evidence_ratio + 0.25 * length_ratio, 2)
    error_tags: list[str] = []
    if keyword_ratio < 0.6:
        error_tags.append("low_keyword_overlap")
    if component_count > 1 and evidence_ratio < 1.0:
        error_tags.append("missing_key_evidence")
    if component_count > 1 and evidence_ratio <= 0.5:
        error_tags.append("incomplete_support")
    if overlap_ratio == 0:
        error_tags.append("answer_mismatch")
    low, high = gray_zone
    should_use_judge = (
        judge_callback is not None
        and (
            low <= overlap_ratio <= high
            or (component_count > 1 and evidence_ratio < 1.0)
        )
    )
    triage_result: dict[str, Any] | None = None
    if should_use_judge and triage_callback is not None:
        triage_result = triage_callback(task, learner_answer, overlap_ratio)
        if triage_result.get("would_skip") and triage_result.get("prediction") is not None:
            triage_score = float(triage_result["prediction"])
            return EvaluationResult(
                score=triage_score,
                error_tags=_score_adjusted_reading_tags(triage_score, error_tags),
                evaluator_note=(
                    "Reading triage prediction used; judge skipped."
                    if not triage_result.get("note")
                    else f"Reading triage prediction used; {triage_result['note']}"
                ),
                used_judge=False,
                scoring_source="triage",
                rule_score=overlap_ratio,
                used_triage=True,
                triage_candidate=True,
                triage_would_skip=True,
                triage_confidence=triage_result.get("confidence"),
                triage_prediction=triage_score,
                triage_features=triage_result.get("features"),
            )
    if should_use_judge:
        decision = judge_callback(task, learner_answer, overlap_ratio)
        if decision.score == 1.0:
            error_tags = []
        elif decision.score == 0.0 and "answer_mismatch" not in error_tags:
            error_tags.append("answer_mismatch")
        return EvaluationResult(
            score=decision.score,
            error_tags=error_tags if error_tags or decision.score == 1.0 else ["partial_reading_answer"],
            evaluator_note=decision.note,
            used_judge=True,
            scoring_source="judge",
            rule_score=overlap_ratio,
            used_triage=bool(triage_result and triage_result.get("available")),
            triage_candidate=triage_result is not None,
            triage_would_skip=bool(triage_result and triage_result.get("would_skip")),
            triage_confidence=triage_result.get("confidence") if triage_result else None,
            triage_prediction=triage_result.get("prediction") if triage_result else None,
            triage_features=triage_result.get("features") if triage_result else None,
        )
    if low <= overlap_ratio <= high:
        error_tags.append("judge_skipped")
    if overlap_ratio >= 0.85 and evidence_ratio == 1.0:
        error_tags = []
    return EvaluationResult(
        score=overlap_ratio,
        error_tags=error_tags if error_tags or (overlap_ratio >= 0.85 and evidence_ratio == 1.0) else ["partial_reading_answer"],
        evaluator_note="Keyword overlap score.",
        scoring_source="reading_rule",
        rule_score=overlap_ratio,
    )


def score_task(
    task: Task,
    learner_answer: str,
    gray_zone: tuple[float, float],
    judge_callback: JudgeCallback | None = None,
    triage_callback: TriageCallback | None = None,
) -> EvaluationResult:
    if task.task_type == "grammar_correction":
        return score_grammar_answer(task, learner_answer)
    return score_reading_answer(task, learner_answer, gray_zone, judge_callback, triage_callback)
