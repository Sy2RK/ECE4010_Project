from __future__ import annotations

import hashlib
import json
from typing import Iterable


def clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def average(values: Iterable[float]) -> float:
    items = list(values)
    if not items:
        return 0.0
    return sum(items) / len(items)


def deterministic_seed(base_seed: int, *parts: object) -> int:
    joined = "|".join(str(part) for part in parts)
    digest = hashlib.sha256(f"{base_seed}|{joined}".encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def extract_json_object(text: str) -> str:
    decoder = json.JSONDecoder()
    for start, char in enumerate(text):
        if char != "{":
            continue
        try:
            payload, end = decoder.raw_decode(text, idx=start)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return text[start:end]
    raise ValueError("No JSON object found in text")


def parse_json_object(text: str) -> dict:
    return json.loads(extract_json_object(text))
