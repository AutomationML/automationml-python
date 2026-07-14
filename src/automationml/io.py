"""File IO helpers for AutomationML JSON and XML."""

from __future__ import annotations

import json
from pathlib import Path

from .models import CAEXFile
from .xml import dump as dump_xml
from .xml import load as load_xml


def load_json(path: str | Path) -> CAEXFile:
    """Load a CAEX document from AML JSON."""

    with open(path, encoding="utf-8") as handle:
        return CAEXFile.model_validate(json.load(handle))


def dump_json(
    document: CAEXFile,
    path: str | Path,
    *,
    indent: int = 2,
    include_change_mode: bool = False,
) -> None:
    """Write a CAEX document as AML JSON."""

    with open(path, "w", encoding="utf-8") as handle:
        handle.write(
            document.to_aml_json(
                indent=indent,
                include_change_mode=include_change_mode,
            )
        )
        handle.write("\n")


__all__ = ["dump_json", "dump_xml", "load_json", "load_xml"]
