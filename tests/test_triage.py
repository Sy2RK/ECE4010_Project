from __future__ import annotations

import json
from pathlib import Path

import pytest

from adaptive_tutor.triage import (
    TRIAGE_FEATURE_DIM,
    ReadingTriageGRU,
    TriagePredictor,
    extract_reading_triage_features,
)
from adaptive_tutor.triage_training import train_reading_triage
from adaptive_tutor.schemas import ReadingJudgeTriageConfig, Task


def _reading_task() -> Task:
    return Task.model_validate(
        {
            "task_id": "r-triage",
            "task_type": "reading_qa",
            "difficulty": 3,
            "passage": "Nina emailed her teacher and borrowed paper from a classmate.",
            "question": "What two actions did Nina take?",
            "reference_answer": "She emailed her teacher and borrowed paper from a classmate.",
            "skill_tags": ["reading", "detail_location", "evidence_selection"],
        }
    )


def test_triage_feature_extraction_has_stable_shape_and_range() -> None:
    features = extract_reading_triage_features(_reading_task(), "She emailed her teacher.")

    assert features
    assert all(len(row) == TRIAGE_FEATURE_DIM for row in features)
    assert all(0.0 <= value <= 1.0 for row in features for value in row)


def test_gru_forward_supports_variable_length_sequences() -> None:
    torch = pytest.importorskip("torch")
    model = ReadingTriageGRU(input_size=TRIAGE_FEATURE_DIM, hidden_size=8)
    features = torch.zeros((2, 3, TRIAGE_FEATURE_DIM), dtype=torch.float32)
    lengths = torch.tensor([1, 3], dtype=torch.long)

    logits = model(features, lengths)

    assert tuple(logits.shape) == (2, 3)


def test_synthetic_training_data_creates_checkpoint(tmp_path: Path) -> None:
    pytest.importorskip("torch")
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    rows = [
        {"features": [[0.0] * TRIAGE_FEATURE_DIM], "label_score": 0.0, "task_id": "r1"},
        {"features": [[0.5] * TRIAGE_FEATURE_DIM], "label_score": 0.5, "task_id": "r2"},
        {"features": [[1.0] * TRIAGE_FEATURE_DIM], "label_score": 1.0, "task_id": "r3"},
    ]
    with (run_dir / "triage_training.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")

    model_path = tmp_path / "reading_judge_triage.pt"
    metrics = train_reading_triage([run_dir], model_path, epochs=2, hidden_size=4)

    assert model_path.exists()
    assert model_path.with_suffix(".metrics.json").exists()
    assert metrics["train_size"] >= 1


def test_triage_checkpoint_schema_is_validated(tmp_path: Path) -> None:
    torch = pytest.importorskip("torch")
    checkpoint = tmp_path / "bad.pt"
    torch.save({"input_size": TRIAGE_FEATURE_DIM}, checkpoint)

    predictor = TriagePredictor.load(
        ReadingJudgeTriageConfig(enabled=True, model_path=str(checkpoint))
    )

    assert predictor.available is False
    assert "state_dict" in (predictor.reason or "")
