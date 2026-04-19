from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from adaptive_tutor.io_utils import load_bundle_catalog, load_config, load_learners, load_tasks
from adaptive_tutor.planning import validate_tutoring_plan_payload
from adaptive_tutor.schemas import AppConfig

ROOT = Path(__file__).resolve().parents[1]


def test_sample_config_and_data_load() -> None:
    config = load_config(ROOT / "data" / "config.mock.yaml")
    assert config.backend.type == "mock"
    assert Path(config.tasks_path).name == "tasks.jsonl"
    tasks = load_tasks(config.tasks_path)
    learners = load_learners(config.learners_path)
    bundles = load_bundle_catalog(config.bundles_path)
    assert len(tasks) == 20
    assert len(learners) == 3
    assert bundles.assignments["learner_a"]["grammar_correction"].pretest_bundle == "grammar_pre"


def test_api_sample_config_resolves_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    monkeypatch.setenv("SHARED_LEARNER_MODEL", "learner-model")
    monkeypatch.setenv("TUTOR_MODEL", "tutor-model")
    monkeypatch.setenv("JUDGE_MODEL", "judge-model")
    monkeypatch.setenv("LEARNER_A_MODEL", "learner-a-model")
    monkeypatch.setenv("LEARNER_B_MODEL", "learner-b-model")
    monkeypatch.setenv("LEARNER_C_MODEL", "")
    temp_config = ROOT / "data" / "_test_config_env.yaml"
    temp_config.write_text(
        "\n".join(
            [
                "backend:",
                "  type: openai_compatible",
                "  base_url: https://dashscope.aliyuncs.com/compatible-mode/v1",
                "  api_key: ${DASHSCOPE_API_KEY}",
                "  timeout_seconds: 30",
                "models:",
                "  shared_learner_model: ${SHARED_LEARNER_MODEL}",
                "  tutor_model: ${TUTOR_MODEL}",
                "  judge_model: ${JUDGE_MODEL}",
                "  learner_model_overrides:",
                "    learner_a: ${LEARNER_A_MODEL:-}",
                "    learner_b: ${LEARNER_B_MODEL:-}",
                "    learner_c: ${LEARNER_C_MODEL:-}",
                "learners_path: ../data/learners.json",
                "tasks_path: ../data/tasks.jsonl",
                "bundles_path: ../data/bundles.json",
            ]
        ),
        encoding="utf-8",
    )
    try:
        config = load_config(temp_config)
    finally:
        temp_config.unlink(missing_ok=True)
    assert config.backend.type == "openai_compatible"
    assert config.backend.base_url == "https://dashscope.aliyuncs.com/compatible-mode/v1"
    assert config.backend.api_key == "test-key"
    assert config.models.shared_learner_model == "learner-model"
    assert config.models.learner_model_overrides["learner_a"] == "learner-a-model"
    assert config.models.learner_model_overrides["learner_b"] == "learner-b-model"
    assert config.models.learner_model_overrides["learner_c"] == ""


def test_api_sample_config_keeps_secret_as_env_placeholder() -> None:
    sample_config_text = (ROOT / "data" / "config.sample.yaml").read_text(encoding="utf-8")
    assert "${DASHSCOPE_API_KEY}" in sample_config_text
    assert "sk-" not in sample_config_text


def test_invalid_tutoring_plan_is_rejected() -> None:
    with pytest.raises(ValidationError):
        validate_tutoring_plan_payload(
            {
                "focus_skill": "grammar",
                "focus_subskills": [],
                "recommended_difficulty": 4,
                "feedback_style": "generic_guidance",
                "hint_level": "medium",
                "next_task_type": "grammar_correction",
                "next_batch_size": 3,
                "adaptation_rationale": "invalid",
            }
        )


def test_required_model_names_must_not_be_empty() -> None:
    with pytest.raises(ValidationError):
        AppConfig.model_validate(
            {
                "backend": {"type": "mock"},
                "models": {
                    "shared_learner_model": "",
                    "tutor_model": "mock-tutor",
                    "judge_model": "mock-judge",
                },
                "learners_path": "learners.json",
                "tasks_path": "tasks.jsonl",
                "bundles_path": "bundles.json",
            }
        )
