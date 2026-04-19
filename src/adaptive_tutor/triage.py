from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from adaptive_tutor.evaluation import (
    _evidence_coverage,
    _reference_components,
    _token_overlap_ratio,
    keyword_tokens,
    tokenize,
)
from adaptive_tutor.schemas import ReadingJudgeTriageConfig, Task

TRIAGE_SCORE_LABELS = (0.0, 0.5, 1.0)
TRIAGE_FEATURE_DIM = 8


def extract_reading_triage_features(task: Task, learner_answer: str) -> list[list[float]]:
    reference_keywords = keyword_tokens(task.reference_answer)
    answer_keywords = keyword_tokens(learner_answer)
    keyword_ratio = _token_overlap_ratio(reference_keywords, answer_keywords)
    evidence_ratio, component_count = _evidence_coverage(task.reference_answer, learner_answer)
    reference_tokens = tokenize(task.reference_answer)
    answer_tokens = tokenize(learner_answer)
    length_ratio = min(len(answer_tokens), len(reference_tokens)) / max(len(reference_tokens), 1)
    difficulty_scaled = task.difficulty / 3.0
    answer_len_scaled = min(len(answer_tokens) / 20.0, 1.0)

    components = _reference_components(task.reference_answer) or [reference_keywords]
    rows: list[list[float]] = []
    denominator = max(len(components) - 1, 1)
    answer_keyword_set = set(answer_keywords)
    for index, component in enumerate(components):
        component_set = set(component)
        component_overlap = (
            len(component_set & answer_keyword_set) / len(component_set)
            if component_set
            else 0.0
        )
        component_len_scaled = min(len(component) / 10.0, 1.0)
        rows.append(
            [
                round(component_overlap, 4),
                round(keyword_ratio, 4),
                round(evidence_ratio, 4),
                round(length_ratio, 4),
                round(difficulty_scaled, 4),
                round(answer_len_scaled, 4),
                round(component_len_scaled, 4),
                round(index / denominator, 4),
            ]
        )
    return rows or [[0.0] * TRIAGE_FEATURE_DIM]


def score_to_label_index(score: float) -> int:
    if score <= 0.25:
        return 0
    if score < 0.75:
        return 1
    return 2


def label_index_to_score(index: int) -> float:
    return TRIAGE_SCORE_LABELS[index]


class ReadingTriageGRU:
    def __new__(cls, *args: Any, **kwargs: Any):
        try:
            import torch.nn as nn
        except ImportError as exc:
            raise ImportError("PyTorch is required for ReadingTriageGRU.") from exc

        class _ReadingTriageGRU(nn.Module):
            def __init__(self, input_size: int = TRIAGE_FEATURE_DIM, hidden_size: int = 16) -> None:
                super().__init__()
                self.input_size = input_size
                self.hidden_size = hidden_size
                self.gru = nn.GRU(input_size=input_size, hidden_size=hidden_size, batch_first=True)
                self.head = nn.Linear(hidden_size, len(TRIAGE_SCORE_LABELS))

            def forward(self, features, lengths):
                import torch.nn.utils.rnn as rnn_utils

                packed = rnn_utils.pack_padded_sequence(
                    features,
                    lengths.cpu(),
                    batch_first=True,
                    enforce_sorted=False,
                )
                _, hidden = self.gru(packed)
                return self.head(hidden[-1])

        return _ReadingTriageGRU(*args, **kwargs)


@dataclass
class TriagePredictor:
    model_path: Path
    confidence_threshold: float
    mode: str
    available: bool
    reason: str | None = None
    model: Any | None = None

    @classmethod
    def load(cls, config: ReadingJudgeTriageConfig) -> "TriagePredictor":
        model_path = Path(config.model_path)
        if not model_path.exists():
            return cls(
                model_path=model_path,
                confidence_threshold=config.confidence_threshold,
                mode=config.mode,
                available=False,
                reason=f"Model file not found: {model_path}",
            )
        try:
            import torch
        except ImportError:
            return cls(
                model_path=model_path,
                confidence_threshold=config.confidence_threshold,
                mode=config.mode,
                available=False,
                reason="PyTorch is not installed.",
            )
        try:
            try:
                checkpoint = torch.load(model_path, map_location="cpu", weights_only=True)
            except TypeError:
                checkpoint = torch.load(model_path, map_location="cpu")
            if not isinstance(checkpoint, Mapping):
                raise ValueError("checkpoint must be a mapping")
            if not isinstance(checkpoint.get("state_dict"), Mapping):
                raise ValueError("checkpoint missing state_dict mapping")
            input_size = int(checkpoint.get("input_size", TRIAGE_FEATURE_DIM))
            hidden_size = int(checkpoint.get("hidden_size", 16))
            if input_size != TRIAGE_FEATURE_DIM:
                raise ValueError(f"unexpected input_size: {input_size}")
            labels = checkpoint.get("labels", list(TRIAGE_SCORE_LABELS))
            if [float(item) for item in labels] != list(TRIAGE_SCORE_LABELS):
                raise ValueError("checkpoint labels do not match expected triage labels")
            model = ReadingTriageGRU(
                input_size=input_size,
                hidden_size=hidden_size,
            )
            model.load_state_dict(checkpoint["state_dict"])
            model.eval()
        except Exception as exc:
            return cls(
                model_path=model_path,
                confidence_threshold=config.confidence_threshold,
                mode=config.mode,
                available=False,
                reason=f"Could not load triage model: {exc}",
            )
        return cls(
            model_path=model_path,
            confidence_threshold=config.confidence_threshold,
            mode=config.mode,
            available=True,
            model=model,
        )

    def predict(self, features: list[list[float]]) -> dict[str, Any]:
        if not self.available or self.model is None:
            return {
                "available": False,
                "prediction": None,
                "confidence": None,
                "would_skip": False,
                "note": self.reason,
            }
        import torch

        with torch.no_grad():
            tensor = torch.tensor([features], dtype=torch.float32)
            lengths = torch.tensor([len(features)], dtype=torch.long)
            logits = self.model(tensor, lengths)
            probabilities = torch.softmax(logits, dim=-1)[0]
            confidence, index = torch.max(probabilities, dim=0)
        confidence_value = round(float(confidence.item()), 4)
        prediction = label_index_to_score(int(index.item()))
        would_skip = self.mode == "enforce" and confidence_value >= self.confidence_threshold
        return {
            "available": True,
            "prediction": prediction,
            "confidence": confidence_value,
            "would_skip": would_skip,
            "note": None,
        }


class ReadingJudgeTriageRuntime:
    def __init__(self, config: ReadingJudgeTriageConfig) -> None:
        self.config = config
        self.predictor = TriagePredictor.load(config) if config.enabled else None

    @property
    def enabled(self) -> bool:
        return self.config.enabled

    def predict(self, task: Task, learner_answer: str, rule_score: float) -> dict[str, Any]:
        features = extract_reading_triage_features(task, learner_answer)
        if not self.predictor:
            return {
                "candidate": True,
                "features": features,
                "available": False,
                "prediction": None,
                "confidence": None,
                "would_skip": False,
                "note": "Triage is disabled.",
            }
        prediction = self.predictor.predict(features)
        return {
            "candidate": True,
            "features": features,
            "available": prediction["available"],
            "prediction": prediction["prediction"],
            "confidence": prediction["confidence"],
            "would_skip": bool(prediction["would_skip"]),
            "note": prediction["note"],
            "rule_score": rule_score,
        }
