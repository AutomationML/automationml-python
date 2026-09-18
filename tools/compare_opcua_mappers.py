"""Run the published AutomationML / OPC UA mapper comparison manifest."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evaluation"))

from opcua_evaluation import (
    PASS_OUTCOMES,
    CaseOutcome,
    ComparisonEngine,
    ComparisonManifest,
    ComparisonRunner,
    report_junit_xml,
    report_markdown,
)


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare Python and frozen upstream AML/OPC UA mappers."
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("tests/opcua-comparison/phase1-manifest.json"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("build/opcua-comparison"),
    )
    parser.add_argument(
        "--engine",
        action="append",
        choices=[engine.value for engine in ComparisonEngine],
        help="Engine to run; repeat the option. The default runs all systems.",
    )
    parser.add_argument(
        "--require-all",
        action="store_true",
        help="Exit non-zero when any scored result is not a pass.",
    )
    parser.add_argument(
        "--artifacts",
        action="store_true",
        help="Retain every generated XML output below the report directory.",
    )
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    repo_root = Path(__file__).resolve().parents[1]
    manifest_path = (
        args.manifest if args.manifest.is_absolute() else repo_root / args.manifest
    ).resolve()
    output_dir = (
        args.output_dir if args.output_dir.is_absolute() else repo_root / args.output_dir
    ).resolve()
    manifest = ComparisonManifest.from_json_file(manifest_path)
    engines = (
        tuple(ComparisonEngine(name) for name in args.engine)
        if args.engine
        else tuple(ComparisonEngine)
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    report = ComparisonRunner(
        repo_root=repo_root,
        artifact_root=output_dir if args.artifacts else None,
    ).run(manifest, engines=engines)
    (output_dir / "report.json").write_text(
        report.model_dump_json(indent=2),
        encoding="utf-8",
    )
    (output_dir / "report.md").write_text(
        report_markdown(report),
        encoding="utf-8",
    )
    (output_dir / "junit.xml").write_text(
        report_junit_xml(report),
        encoding="utf-8",
    )

    for score in report.scores:
        print(
            f"{score.engine.value}: {score.passed}/{score.total} "
            f"({score.percent:.2f}%), critical "
            f"{score.critical_passed}/{score.critical_total}"
        )
    print(f"Evidence written to {output_dir}")

    if args.require_all and any(
        result.scored and result.outcome not in PASS_OUTCOMES
        for result in report.results
    ):
        return 1
    if any(result.outcome == CaseOutcome.CRASH for result in report.results):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
