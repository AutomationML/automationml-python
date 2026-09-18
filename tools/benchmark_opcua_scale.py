"""Reproducible large-graph gates for the AutomationML/OPC UA mappers."""

from __future__ import annotations

import argparse
import gc
import json
import platform
import sys
import threading
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import median
from time import perf_counter
from typing import Callable

from lxml import etree
import psutil

from automationml import CAEXFile
from automationml.opcua import UA_NODESET_NS, nodeset_to_document

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evaluation"))

from opcua_evaluation import ComparisonEngine, ComparisonRunner


PUBLICATION_DATE = "2026-08-17"
NS = {"ua": UA_NODESET_NS}


@dataclass(frozen=True, slots=True)
class ScaleCase:
    id: str
    requested_nodes: int
    requested_references: int
    element_count: int = 0
    depth: int = 0


@dataclass(frozen=True, slots=True)
class ScaleResult:
    case_id: str
    engine: str
    status: str
    cold_ms: float | None
    warm_median_ms: float | None
    reverse_ms: float | None
    peak_rss_bytes: int | None
    output_bytes: int | None
    actual_nodes: int | None
    actual_references: int | None
    deterministic: bool
    roundtrip_equivalent: bool
    diagnostic: str | None = None


DEFAULT_CASES = (
    ScaleCase("flat-1k-5k", 990, 4_900, element_count=490),
    ScaleCase("flat-10k-50k", 9_900, 49_000, element_count=4_990),
    ScaleCase("depth-64", 125, 250, depth=64),
)

QUICK_CASES = (
    ScaleCase("flat-100-smoke", 100, 500, element_count=40),
    ScaleCase("depth-32-smoke", 60, 120, depth=32),
)


def _flat_document(element_count: int) -> CAEXFile:
    roles = [f"Role{position}" for position in range(1, 7)]
    role_requirements = [
        {"RefBaseRoleClassPath": f"Roles/{role}"} for role in roles
    ]
    return CAEXFile.model_validate(
        {
            "FileName": f"scale-flat-{element_count}.aml",
            "SchemaVersion": "3.0",
            "InstanceHierarchy": [
                {
                    "Name": "Scale",
                    "InternalElement": [
                        {
                            "Name": f"Element{position:05d}",
                            "ID": f"scale-element-{position:05d}",
                            "RoleRequirements": role_requirements,
                        }
                        for position in range(element_count)
                    ],
                }
            ],
            "RoleClassLib": [
                {
                    "Name": "Roles",
                    "ID": "scale-role-library",
                    "RoleClass": [
                        {"Name": role, "ID": f"scale-{role.lower()}"}
                        for role in roles
                    ],
                }
            ],
        }
    )


def _deep_document(depth: int) -> CAEXFile:
    child: dict[str, object] | None = None
    for position in reversed(range(depth)):
        current: dict[str, object] = {
            "Name": f"Level{position:03d}",
            "ID": f"scale-depth-{position:03d}",
        }
        if child is not None:
            current["InternalElement"] = [child]
        child = current
    return CAEXFile.model_validate(
        {
            "FileName": f"scale-depth-{depth}.aml",
            "SchemaVersion": "3.0",
            "InstanceHierarchy": [
                {"Name": "Deep", "InternalElement": [child] if child else []}
            ],
        }
    )


def _document(case: ScaleCase) -> CAEXFile:
    return (
        _deep_document(case.depth)
        if case.depth
        else _flat_document(case.element_count)
    )


def _measure(call: Callable[[], str]) -> tuple[float, int, str]:
    gc.collect()
    process = psutil.Process()
    peak = process.memory_info().rss
    stop = threading.Event()

    def sample() -> None:
        nonlocal peak
        while not stop.wait(0.01):
            peak = max(peak, process.memory_info().rss)

    sampler = threading.Thread(target=sample, daemon=True)
    sampler.start()
    started = perf_counter()
    try:
        output = call()
        elapsed_ms = (perf_counter() - started) * 1_000
    finally:
        stop.set()
        sampler.join()
        peak = max(peak, process.memory_info().rss)
    return elapsed_ms, peak, output


def _counts(xml: str) -> tuple[int, int]:
    root = etree.fromstring(
        xml.encode("utf-8"),
        parser=etree.XMLParser(
            resolve_entities=False,
            load_dtd=False,
            no_network=True,
        ),
    )
    return (
        int(root.xpath("count(./ua:*[@NodeId])", namespaces=NS)),
        int(root.xpath("count(.//ua:Reference)", namespaces=NS)),
    )


def _run_case(
    repo_root: Path,
    case: ScaleCase,
    engine: ComparisonEngine,
    repeats: int,
) -> ScaleResult:
    try:
        document = _document(case)
        aml = document.to_aml_xml(
            pretty=False,
            include_default_change_mode=True,
        ).encode("utf-8")
        expected = document.to_aml_dict(include_change_mode=True)

        cold_runner = ComparisonRunner(repo_root=repo_root)
        cold_ms, cold_peak, cold_output = _measure(
            lambda: cold_runner._forward(engine, aml, PUBLICATION_DATE)
        )
        warm_runner = ComparisonRunner(repo_root=repo_root)
        warm_samples: list[float] = []
        warm_peaks: list[int] = []
        warm_outputs: list[str] = []
        for _ in range(repeats):
            elapsed, peak, output = _measure(
                lambda: warm_runner._forward(engine, aml, PUBLICATION_DATE)
            )
            warm_samples.append(elapsed)
            warm_peaks.append(peak)
            warm_outputs.append(output)
        output = warm_outputs[-1]
        actual_nodes, actual_references = _counts(output)
        deterministic = all(item == cold_output for item in warm_outputs)

        reverse_started = perf_counter()
        roundtrip_equivalent = False
        try:
            recovered_xml = warm_runner._reverse(engine, output.encode("utf-8"))
            recovered = CAEXFile.from_aml_xml(recovered_xml).to_aml_dict(
                include_change_mode=True
            )
            roundtrip_equivalent = recovered == expected
            reverse_ms = (perf_counter() - reverse_started) * 1_000
        except Exception:
            reverse_ms = (perf_counter() - reverse_started) * 1_000

        status = (
            "pass"
            if engine == ComparisonEngine.PYTHON_STRICT
            else "measured"
        )
        failures: list[str] = []
        if actual_nodes < case.requested_nodes:
            failures.append(
                f"{actual_nodes} nodes is below requested {case.requested_nodes}"
            )
        if actual_references < case.requested_references:
            failures.append(
                f"{actual_references} references is below requested "
                f"{case.requested_references}"
            )
        if not deterministic:
            failures.append("fixed input was not byte deterministic")
        if engine == ComparisonEngine.PYTHON_STRICT and not roundtrip_equivalent:
            failures.append("Python AML semantic roundtrip changed")
        if failures and engine == ComparisonEngine.PYTHON_STRICT:
            status = "fail"
        return ScaleResult(
            case_id=case.id,
            engine=engine.value,
            status=status,
            cold_ms=round(cold_ms, 3),
            warm_median_ms=round(median(warm_samples), 3),
            reverse_ms=round(reverse_ms, 3),
            peak_rss_bytes=max([cold_peak, *warm_peaks]),
            output_bytes=len(output.encode("utf-8")),
            actual_nodes=actual_nodes,
            actual_references=actual_references,
            deterministic=deterministic,
            roundtrip_equivalent=roundtrip_equivalent,
            diagnostic=(
                "; ".join(failures)
                if engine == ComparisonEngine.PYTHON_STRICT and failures
                else None
            ),
        )
    except Exception as exc:
        return ScaleResult(
            case_id=case.id,
            engine=engine.value,
            status="error",
            cold_ms=None,
            warm_median_ms=None,
            reverse_ms=None,
            peak_rss_bytes=None,
            output_bytes=None,
            actual_nodes=None,
            actual_references=None,
            deterministic=False,
            roundtrip_equivalent=False,
            diagnostic=f"{type(exc).__name__}: {exc}",
        )


def _markdown(payload: dict[str, object]) -> str:
    lines = [
        "# OPC UA scale report",
        "",
        f"Generated: {payload['generated']}",
        "",
        "Peak memory is process resident-set size sampled every 10 ms and includes "
        "native mapper/runtime allocations.",
        "",
        "| Case | Engine | Status | Nodes | References | Cold ms | Warm median ms | "
        "Reverse ms | Peak RSS MiB | Bytes | Deterministic | Roundtrip |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | "
        "--- | --- |",
    ]
    for item in payload["results"]:  # type: ignore[index]
        result = item  # type: ignore[assignment]
        peak = result["peak_rss_bytes"]
        lines.append(
            "| "
            + " | ".join(
                (
                    str(result["case_id"]),
                    str(result["engine"]),
                    str(result["status"]),
                    str(result["actual_nodes"] or "—"),
                    str(result["actual_references"] or "—"),
                    str(result["cold_ms"] or "—"),
                    str(result["warm_median_ms"] or "—"),
                    str(result["reverse_ms"] or "—"),
                    f"{peak / 1024 / 1024:.2f}" if peak else "—",
                    str(result["output_bytes"] or "—"),
                    "yes" if result["deterministic"] else "no",
                    "yes" if result["roundtrip_equivalent"] else "no",
                )
            )
            + " |"
        )
        if result["diagnostic"]:
            lines.extend(("", f"- `{result['case_id']}` / `{result['engine']}`: {result['diagnostic']}"))
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("build/opcua-scale"))
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--quick", action="store_true")
    parser.add_argument(
        "--engine",
        action="append",
        choices=(ComparisonEngine.PYTHON_STRICT.value, ComparisonEngine.XSLT_RAW.value),
    )
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("--repeats must be at least 1")

    repo_root = Path(__file__).resolve().parents[1]
    output_dir = args.output_dir
    if not output_dir.is_absolute():
        output_dir = repo_root / output_dir
    engines = tuple(
        ComparisonEngine(value)
        for value in (
            args.engine
            or [ComparisonEngine.PYTHON_STRICT.value, ComparisonEngine.XSLT_RAW.value]
        )
    )
    cases = QUICK_CASES if args.quick else DEFAULT_CASES
    results = [
        _run_case(repo_root, case, engine, args.repeats)
        for engine in engines
        for case in cases
    ]
    payload: dict[str, object] = {
        "generated": PUBLICATION_DATE,
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
        "repeats": args.repeats,
        "cases": [asdict(case) for case in cases],
        "results": [asdict(result) for result in results],
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "report.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "report.md").write_text(_markdown(payload), encoding="utf-8")
    for result in results:
        print(
            f"{result.case_id} {result.engine}: {result.status}; "
            f"nodes={result.actual_nodes}, refs={result.actual_references}, "
            f"warm={result.warm_median_ms} ms"
        )
    print(f"Evidence written to {output_dir}")
    return int(
        any(result.status in {"fail", "error"} for result in results)
    )


if __name__ == "__main__":
    raise SystemExit(main())
