from __future__ import annotations

from adaptive_tutor.utils import parse_json_object


def test_parse_json_object_handles_braces_inside_strings() -> None:
    payload = parse_json_object('prefix {"note": "Use {braces} literally", "score": 1} suffix')

    assert payload == {"note": "Use {braces} literally", "score": 1}
