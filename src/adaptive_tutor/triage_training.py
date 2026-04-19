from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from adaptive_tutor.triage import (
    TRIAGE_FEATURE_DIM,
    ReadingTriageGRU,
    score_to_label_index,
)


def _load_training_rows(run_dirs: list[str | Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for run_dir in run_dirs:
        path = Path(run_dir) / "triage_training.jsonl"
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(json.loads(line))
    return rows


def _split_bucket(row: dict[str, Any]) -> int:
    key = "|".join(
        str(row.get(field, ""))
        for field in ["learner_id", "mode", "phase", "task_id", "learner_answer"]
    )
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % 5


def _pad_batch(rows: list[dict[str, Any]]):
    import torch

    max_len = max(len(row["features"]) for row in rows)
    features = torch.zeros((len(rows), max_len, TRIAGE_FEATURE_DIM), dtype=torch.float32)
    lengths = torch.zeros((len(rows),), dtype=torch.long)
    labels = torch.zeros((len(rows),), dtype=torch.long)
    for index, row in enumerate(rows):
        feature_rows = row["features"]
        lengths[index] = len(feature_rows)
        labels[index] = score_to_label_index(float(row["label_score"]))
        features[index, : len(feature_rows), :] = torch.tensor(feature_rows, dtype=torch.float32)
    return features, lengths, labels


def _macro_f1(predictions: list[int], labels: list[int]) -> float:
    scores: list[float] = []
    for label in [0, 1, 2]:
        true_positive = sum(1 for pred, gold in zip(predictions, labels) if pred == gold == label)
        false_positive = sum(1 for pred, gold in zip(predictions, labels) if pred == label and gold != label)
        false_negative = sum(1 for pred, gold in zip(predictions, labels) if pred != label and gold == label)
        precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
        recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
        scores.append(2 * precision * recall / (precision + recall) if precision + recall else 0.0)
    return sum(scores) / len(scores)


def train_reading_triage(
    run_dirs: list[str | Path],
    model_path: str | Path,
    epochs: int = 80,
    hidden_size: int = 16,
    confidence_threshold: float = 0.90,
    seed: int = 42,
) -> dict[str, Any]:
    try:
        import torch
        import torch.nn.functional as F
    except ImportError as exc:
        raise ImportError("PyTorch is required. Install with `pip install -e .[ml]`.") from exc

    rows = _load_training_rows(run_dirs)
    if not rows:
        raise ValueError("No triage_training.jsonl rows found in the provided run directories.")

    torch.manual_seed(seed)
    train_rows = [row for row in rows if _split_bucket(row) != 0]
    val_rows = [row for row in rows if _split_bucket(row) == 0]
    if not train_rows:
        train_rows = rows
    if not val_rows:
        val_rows = rows

    train_features, train_lengths, train_labels = _pad_batch(train_rows)
    val_features, val_lengths, val_labels = _pad_batch(val_rows)

    model = ReadingTriageGRU(input_size=TRIAGE_FEATURE_DIM, hidden_size=hidden_size)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
    model.train()
    for _ in range(epochs):
        optimizer.zero_grad()
        logits = model(train_features, train_lengths)
        loss = F.cross_entropy(logits, train_labels)
        loss.backward()
        optimizer.step()

    model.eval()
    with torch.no_grad():
        logits = model(val_features, val_lengths)
        probabilities = torch.softmax(logits, dim=-1)
        confidences, predictions = torch.max(probabilities, dim=-1)
    predicted_labels = [int(item) for item in predictions.tolist()]
    gold_labels = [int(item) for item in val_labels.tolist()]
    high_confidence = [
        (pred, gold)
        for pred, gold, confidence in zip(predicted_labels, gold_labels, confidences.tolist())
        if float(confidence) >= confidence_threshold
    ]
    disagreements = sum(1 for pred, gold in high_confidence if pred != gold)
    metrics = {
        "train_size": len(train_rows),
        "validation_size": len(val_rows),
        "accuracy": round(
            sum(1 for pred, gold in zip(predicted_labels, gold_labels) if pred == gold)
            / len(gold_labels),
            4,
        ),
        "macro_f1": round(_macro_f1(predicted_labels, gold_labels), 4),
        "high_confidence_coverage": round(len(high_confidence) / len(gold_labels), 4),
        "high_confidence_disagreement_rate": round(
            disagreements / len(high_confidence) if high_confidence else 0.0,
            4,
        ),
        "confidence_threshold": confidence_threshold,
    }

    target = Path(model_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "state_dict": model.state_dict(),
            "input_size": TRIAGE_FEATURE_DIM,
            "hidden_size": hidden_size,
            "labels": [0.0, 0.5, 1.0],
            "metrics": metrics,
        },
        target,
    )
    metrics_path = target.with_suffix(".metrics.json")
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics


def train_reading_triage_from_args(args: argparse.Namespace) -> dict[str, Any]:
    return train_reading_triage(
        run_dirs=args.runs,
        model_path=args.model_path,
        epochs=args.epochs,
        hidden_size=args.hidden_size,
        confidence_threshold=args.confidence_threshold,
        seed=args.seed,
    )
