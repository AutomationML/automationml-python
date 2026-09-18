"""Generate the readable AutomationML JSON Schema."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .models import CAEXFile


SCHEMA_ID = "https://schemas.automationml.org/json/caex-3.0.schema.json"


def caex_json_schema() -> dict[str, Any]:
    """Return a readable JSON Schema for the JSON-first CAEX model."""

    schema = CAEXFile.model_json_schema(by_alias=True, mode="validation")
    schema = _strip_generated_titles(schema)
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = SCHEMA_ID
    schema["title"] = "AutomationML CAEX 3.0 JSON"
    schema["description"] = (
        "JSON-first serialization for AutomationML CAEX 3.0. Field names use "
        "the canonical AML element and attribute names while SDK models expose "
        "readable snake_case Python attributes."
    )
    return _ordered(schema)


def write_schema(path: str | Path) -> None:
    """Write the AutomationML JSON Schema to disk."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(
        (json.dumps(caex_json_schema(), indent=2, ensure_ascii=False) + "\n").encode(
            "utf-8"
        )
    )


def _strip_generated_titles(value: Any) -> Any:
    if isinstance(value, list):
        return [_strip_generated_titles(item) for item in value]
    if isinstance(value, dict):
        cleaned = {
            key: _strip_generated_titles(item)
            for key, item in value.items()
            if key != "title"
        }
        return cleaned
    return value


def _ordered(schema: dict[str, Any]) -> dict[str, Any]:
    preferred = ["$schema", "$id", "title", "description", "type", "properties"]
    result: dict[str, Any] = {}
    for key in preferred:
        if key in schema:
            result[key] = schema[key]
    for key, value in schema.items():
        if key not in result and key != "$defs":
            result[key] = value
    if "$defs" in schema:
        result["$defs"] = schema["$defs"]
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        default="schemas/automationml.caex3.schema.json",
        help="Target JSON Schema path.",
    )
    args = parser.parse_args()
    write_schema(args.output)


if __name__ == "__main__":
    main()
