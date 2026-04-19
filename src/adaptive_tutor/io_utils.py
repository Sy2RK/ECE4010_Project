from __future__ import annotations

import csv
import json
import os
import re
from pathlib import Path
from typing import Any, Iterable, TypeVar

import yaml
from pydantic import BaseModel

from adaptive_tutor.schemas import AppConfig, BundleCatalog, LearnerProfile, Task

T = TypeVar("T", bound=BaseModel)
ENV_VAR_PATTERN = re.compile(r"\$\{([A-Z0-9_]+)(?::-(.*?))?\}")


def resolve_path(base: Path, raw_path: str) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return (base / path).resolve()


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def load_dotenv_chain(config_path: Path) -> dict[str, str]:
    dotenv_values: dict[str, str] = {}
    candidate_dirs: list[Path] = []
    for directory in reversed(config_path.parents):
        if directory not in candidate_dirs:
            candidate_dirs.append(directory)
    for directory in candidate_dirs:
        dotenv_path = directory / ".env"
        if not dotenv_path.exists():
            continue
        for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            dotenv_values[key.strip()] = value.strip().strip("'\"")
    return dotenv_values


def expand_env_placeholders(value: Any, env_map: dict[str, str]) -> Any:
    if isinstance(value, dict):
        return {key: expand_env_placeholders(item, env_map) for key, item in value.items()}
    if isinstance(value, list):
        return [expand_env_placeholders(item, env_map) for item in value]
    if isinstance(value, str):
        def replace(match: re.Match[str]) -> str:
            env_key = match.group(1)
            default = match.group(2)
            if env_key in env_map:
                return env_map[env_key]
            if default is not None:
                return default
            raise ValueError(f"Missing environment variable: {env_key}")

        return ENV_VAR_PATTERN.sub(replace, value)
    return value


def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path).resolve()
    payload = load_yaml(config_path)
    env_map = {
        **load_dotenv_chain(config_path),
        **os.environ,
    }
    payload = expand_env_placeholders(payload, env_map)
    config = AppConfig.model_validate(payload)
    base_dir = config_path.parent
    return config.model_copy(
        update={
            "learners_path": str(resolve_path(base_dir, config.learners_path)),
            "tasks_path": str(resolve_path(base_dir, config.tasks_path)),
            "bundles_path": str(resolve_path(base_dir, config.bundles_path)),
            "output_root": str(resolve_path(base_dir, config.output_root)),
            "reading_judge_triage": config.reading_judge_triage.model_copy(
                update={
                    "model_path": str(
                        resolve_path(base_dir, config.reading_judge_triage.model_path)
                    )
                }
            ),
        }
    )


def load_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_tasks(path: str | Path) -> dict[str, Task]:
    tasks: dict[str, Task] = {}
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            task = Task.model_validate_json(line)
            tasks[task.task_id] = task
    return tasks


def load_learners(path: str | Path) -> dict[str, LearnerProfile]:
    payload = load_json(path)
    learners = [LearnerProfile.model_validate(item) for item in payload]
    return {learner.learner_id: learner for learner in learners}


def load_bundle_catalog(path: str | Path) -> BundleCatalog:
    payload = load_json(path)
    return BundleCatalog.model_validate(payload)


def ensure_dir(path: str | Path) -> Path:
    target = Path(path)
    target.mkdir(parents=True, exist_ok=True)
    return target


def write_json(path: str | Path, payload: Any) -> None:
    with Path(path).open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)


def write_jsonl(path: str | Path, rows: Iterable[BaseModel | dict[str, Any]]) -> None:
    with Path(path).open("w", encoding="utf-8") as handle:
        for row in rows:
            if isinstance(row, BaseModel):
                payload = row.model_dump()
            else:
                payload = row
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def append_jsonl(path: str | Path, row: BaseModel | dict[str, Any]) -> None:
    if isinstance(row, BaseModel):
        payload = row.model_dump()
    else:
        payload = row
    with Path(path).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
        handle.flush()


def write_csv(path: str | Path, rows: Iterable[BaseModel | dict[str, Any]]) -> None:
    serialized: list[dict[str, Any]] = []
    for row in rows:
        if isinstance(row, BaseModel):
            serialized.append(row.model_dump())
        else:
            serialized.append(dict(row))
    if not serialized:
        return
    with Path(path).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(serialized[0].keys()))
        writer.writeheader()
        writer.writerows(serialized)


def read_jsonl_models(path: str | Path, model_cls: type[T]) -> list[T]:
    rows: list[T] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(model_cls.model_validate_json(line))
    return rows


def read_csv_dicts(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))
