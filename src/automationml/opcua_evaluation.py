"""Manifest-driven evidence harness for AutomationML / OPC UA mappers.

This module deliberately sits beside, rather than inside, the mapping code. It
uses its own XML parsing, schema validation, NodeId checks, and graph-fact
oracles so a candidate mapper cannot validate itself. The public runtime does
not import this module.
"""

from __future__ import annotations

import hashlib
import json
import platform
import re
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from lxml import etree
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .models import CAEXFile
from .opcua import (
    OPCUAConversionError,
    aml_xml_to_nodeset,
    nodeset_to_document,
)


UA_NODESET_NS = "http://opcfoundation.org/UA/2011/03/UANodeSet.xsd"
CAEX_NS = "http://www.dke.de/CAEX"
ROUNDTRIP_NS = "urn:automationml:opcua:nodeset-roundtrip:1"
FIXED_PUBLICATION_DATE = "2026-08-17"
UPSTREAM_COMMIT = "e38653c1bc58ffc658595093e0a2d163a7ecebf7"

_UA = {"ua": UA_NODESET_NS}
_UNSAFE_XML = re.compile(br"<!\s*(?:DOCTYPE|ENTITY)\b", re.IGNORECASE)
_NODE_ID = re.compile(
    r"^(?:ns=\d+;)?(?:i=\d+|s=.+|g=[0-9A-Fa-f-]{36}|b=[A-Za-z0-9+/=]+)$"
)
_BROWSE_NAME = re.compile(r"^(?:\d+:)?.+")
_SHADOW_NAMES = {
    "AMLAttributeDataType",
    "AMLDefaultValue",
    "AMLUnit",
    "AMLRefSemantic",
    "AMLMappingObjectPresent",
}

UPSTREAM_SOURCE_HASHES = {
    "AML2Nodeset.xslt": "17331d1d923187be278e3343ce56bff4fef7127a8e8e3dbe9bef394ac19446d5",
    "DatatypeTranslation.xslt": "bc48502fcc39c8c6614e74ca009fbdf022a2ee076c3c1bfeed4629458bc1bdac",
    "LibraryParsing.xslt": "296378e3c842e97a4f18f955c5c2c403a07c9ee95a5814dea60fa5fec3b6875a",
    "LibraryTranslation.xslt": "6783eb34b820b7a03b7a6115b8fdcee891c306072e0406b55a77b85bcc71c98e",
    "Nodeset2AML.xslt": "646231ee52bc0bfc941b1228a7c1f754bd0e2180aa3022e44e3e5bd8fe2d5083",
    "Nodeset2AML_V2.xslt": "492392dcb40894a6c81c49873d4847ca3ec12503621535c2f90726829a7f244a",
    "License.txt": "5e7dcaed9c919e408039d268a1835dc6758545bd9f96269112917864712f69c0",
}


class ComparisonEngine(StrEnum):
    PYTHON_STRICT = "PY-STRICT"
    XSLT_RAW = "XSLT-RAW"
    XSLT_RUNNER = "XSLT-RUNNER"
    XSLT_PATCHED = "XSLT-PATCHED"


HEADLINE_ENGINES = (
    ComparisonEngine.PYTHON_STRICT,
    ComparisonEngine.XSLT_RAW,
)


class CaseDirection(StrEnum):
    AML_TO_UA = "aml_to_ua"
    AML_TO_UA_TO_AML = "aml_to_ua_to_aml"
    UA_TO_AML = "ua_to_aml"
    UA_TO_AML_TO_UA_TO_AML = "ua_to_aml_to_ua_to_aml"


class CaseSeverity(StrEnum):
    CRITICAL = "critical"
    MUST = "must"
    OBSERVATION = "observation"


class CaseOutcome(StrEnum):
    PASS = "PASS"
    CANONICAL_PASS = "CANONICAL_PASS"
    EXPECTED_REJECTION = "EXPECTED_REJECTION"
    FAIL = "FAIL"
    UNSUPPORTED = "UNSUPPORTED"
    CRASH = "CRASH"
    INVALID_FIXTURE = "INVALID_FIXTURE"


PASS_OUTCOMES = {
    CaseOutcome.PASS,
    CaseOutcome.CANONICAL_PASS,
    CaseOutcome.EXPECTED_REJECTION,
}


class OracleName(StrEnum):
    SECURE_XML = "secure_xml"
    CAEX_XSD = "caex_xsd"
    NODESET_XSD = "nodeset_xsd"
    NODESET_SEMANTICS = "nodeset_semantics"
    EXPECTED_GRAPH = "expected_graph"
    CANONICAL_AML = "canonical_aml"
    DETERMINISTIC = "deterministic"
    NO_ROUNDTRIP_METADATA = "no_roundtrip_metadata"


class CanonicalizationName(StrEnum):
    DATATYPE_ALIASES = "datatype_aliases"
    NOMINAL_CONSTRAINT_SET = "nominal_constraint_set"
    UUID_BRACES = "uuid_braces"
    XML_ATTRIBUTE_WHITESPACE = "xml_attribute_whitespace"
    RELATIONSHIP_SETS = "relationship_sets"


class SourceMutationName(StrEnum):
    REMAP_NODE_IDS = "remap_node_ids"
    EXPAND_ALIAS_USES = "expand_alias_uses"
    REMAP_NAMESPACE_INDEXES = "remap_namespace_indexes"
    REVERSE_NODE_ORDER = "reverse_node_order"
    REVERSE_REFERENCE_ORDER = "reverse_reference_order"
    DIFFERENT_DISPLAY_NAME = "different_display_name"
    COMPACT_XML = "compact_xml"
    ADD_UNKNOWN_COMPONENT = "add_unknown_component"
    DUPLICATE_NODE_ID = "duplicate_node_id"
    INVALID_NODE_ID = "invalid_node_id"
    MISSING_LOCAL_TARGET = "missing_local_target"
    MULTIPLE_TYPE_DEFINITIONS = "multiple_type_definitions"
    CLASS_ANCESTRY_CYCLE = "class_ancestry_cycle"
    MULTIPLE_COMPONENT_OWNERS = "multiple_component_owners"
    OBJECT_VARIABLE_FIELDS = "object_variable_fields"
    DEFAULT_DATATYPE_MISMATCH = "default_datatype_mismatch"
    UNKNOWN_DATATYPE = "unknown_datatype"


class ReferenceExpectation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    reference_type: str
    target: str | None = None
    target_endswith: str | None = None
    is_forward: bool = True

    @model_validator(mode="after")
    def one_target_selector(self) -> ReferenceExpectation:
        if self.target is not None and self.target_endswith is not None:
            raise ValueError("reference expectation has two target selectors")
        return self


class NodeExpectation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    node_class: str
    display_name: str
    count: int = Field(default=1, ge=0)
    browse_name: str | None = None
    attributes: dict[str, str] = Field(default_factory=dict)
    documentation: str | None = None
    value: str | None = None
    references: tuple[ReferenceExpectation, ...] = ()


class GraphExpectation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    nodes: tuple[NodeExpectation, ...] = ()
    forbidden_reference_types: tuple[str, ...] = ()
    forbidden_node_id_patterns: tuple[str, ...] = ()
    require_nonempty_model_version: bool = False
    required_model_version: str | None = None
    required_publication_date: str | None = None
    forbid_shadow_names: bool = False


class ComparisonCase(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(pattern=r"^[A-Z0-9][A-Z0-9-]+$")
    title: str
    family: str
    source: str
    expected_aml: str | None = None
    direction: CaseDirection
    severity: CaseSeverity = CaseSeverity.MUST
    profile: str = "strict-implicit-v1"
    equivalence: str = "exact"
    canonicalizations: tuple[CanonicalizationName, ...] = ()
    source_mutations: tuple[SourceMutationName, ...] = ()
    oracles: tuple[OracleName, ...]
    score_engines: tuple[ComparisonEngine, ...] = HEADLINE_ENGINES
    expected: GraphExpectation = Field(default_factory=GraphExpectation)
    expected_rejection_category: str | None = None
    standard_references: tuple[str, ...] = ()

    @model_validator(mode="after")
    def oracle_contract(self) -> ComparisonCase:
        if (
            OracleName.EXPECTED_GRAPH in self.oracles
            and self.expected == GraphExpectation()
        ):
            raise ValueError("expected_graph requires at least one graph expectation")
        if self.expected_rejection_category and self.severity == CaseSeverity.OBSERVATION:
            raise ValueError("expected rejection cases must be scored")
        if (
            self.direction
            in {
                CaseDirection.UA_TO_AML,
                CaseDirection.UA_TO_AML_TO_UA_TO_AML,
            }
            and OracleName.CANONICAL_AML in self.oracles
            and self.expected_aml is None
        ):
            raise ValueError(
                "a UA-origin canonical_aml oracle requires expected_aml"
            )
        return self


class ComparisonManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0"
    name: str
    baseline_commit: str = UPSTREAM_COMMIT
    publication_date: str = FIXED_PUBLICATION_DATE
    include_manifests: tuple[str, ...] = ()
    cases: tuple[ComparisonCase, ...]

    @model_validator(mode="after")
    def unique_case_ids(self) -> ComparisonManifest:
        ids = [case.id for case in self.cases]
        duplicates = sorted(name for name, count in Counter(ids).items() if count > 1)
        if duplicates:
            raise ValueError(f"duplicate comparison case IDs: {duplicates}")
        if self.baseline_commit != UPSTREAM_COMMIT:
            raise ValueError("manifest baseline commit differs from the frozen profile")
        return self

    @classmethod
    def from_json_file(cls, path: Path) -> ComparisonManifest:
        return cls._from_json_file(path.resolve(), seen=set())

    @classmethod
    def _from_json_file(
        cls,
        path: Path,
        *,
        seen: set[Path],
    ) -> ComparisonManifest:
        if path in seen:
            raise ValueError(f"comparison manifest include cycle at {path}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        includes = tuple(payload.get("include_manifests", ()))
        inherited: list[ComparisonCase] = []
        next_seen = {*seen, path}
        for relative in includes:
            include_path = (path.parent / relative).resolve()
            if not include_path.is_relative_to(path.parent.resolve()):
                raise ValueError(
                    f"comparison manifest include escapes its directory: {relative}"
                )
            inherited.extend(
                cls._from_json_file(include_path, seen=next_seen).cases
            )
        payload["cases"] = [
            *(case.model_dump(mode="json", by_alias=True) for case in inherited),
            *payload.get("cases", ()),
        ]
        return cls.model_validate(payload)


class OracleEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    oracle: str
    passed: bool
    detail: str


class CaseResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: str
    engine: ComparisonEngine
    family: str
    severity: CaseSeverity
    scored: bool
    outcome: CaseOutcome
    duration_ms: float = Field(ge=0)
    evidence: tuple[OracleEvidence, ...]
    diagnostic_category: str | None = None
    diagnostic: str | None = None
    output_sha256: str | None = None
    artifact: str | None = None


class EngineScore(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    engine: ComparisonEngine
    passed: int
    total: int
    percent: float
    critical_passed: int
    critical_total: int
    outcomes: dict[str, int]


class ComparisonEnvironment(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    generated_at: datetime
    platform: str
    python: str
    pydantic: str
    lxml: str
    saxonche: str | None


class ComparisonReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    manifest_name: str
    manifest_schema_version: str
    baseline_commit: str
    baseline_hashes: dict[str, str]
    environment: ComparisonEnvironment
    results: tuple[CaseResult, ...]
    scores: tuple[EngineScore, ...]


class _InvalidFixture(ValueError):
    pass


class _OracleFailure(ValueError):
    pass


class _TransformFailure(ValueError):
    pass


class _SaxonSession:
    """Own one Saxon processor so the exact stylesheets compile once per run."""

    def __init__(self, vendor_root: Path) -> None:
        try:
            from saxonche import PySaxonProcessor
        except ImportError as exc:  # pragma: no cover - dependency profile test
            raise _TransformFailure("saxonche is not installed") from exc
        self._processor = PySaxonProcessor(license=False)
        self._xslt = self._processor.new_xslt30_processor()
        self._vendor_root = vendor_root
        self._forward: Any | None = None
        self._reverse: Any | None = None

    @property
    def version(self) -> str:
        return str(self._processor.version)

    def close(self) -> None:
        self._processor.__exit__(None, None, None)

    def forward(self, source: bytes) -> str:
        try:
            if self._forward is None:
                self._forward = self._xslt.compile_stylesheet(
                    stylesheet_file=str(self._vendor_root / "AML2Nodeset.xslt")
                )
            node = self._processor.parse_xml(xml_text=source.decode("utf-8-sig"))
            result = self._forward.transform_to_string(xdm_node=node)
        except Exception as exc:
            raise _TransformFailure(f"upstream forward XSLT failed: {exc}") from exc
        if not result:
            raise _TransformFailure("upstream forward XSLT returned no XML")
        return result

    def reverse(self, source: bytes) -> str:
        try:
            if self._reverse is None:
                self._reverse = self._xslt.compile_stylesheet(
                    stylesheet_file=str(self._vendor_root / "Nodeset2AML.xslt")
                )
            node = self._processor.parse_xml(xml_text=source.decode("utf-8-sig"))
            result = self._reverse.transform_to_string(xdm_node=node)
        except Exception as exc:
            raise _TransformFailure(f"upstream reverse XSLT failed: {exc}") from exc
        if not result:
            raise _TransformFailure("upstream reverse XSLT returned no XML")
        return result


class ComparisonRunner:
    """Execute one manifest against explicitly named mapper systems."""

    def __init__(
        self,
        *,
        repo_root: Path,
        artifact_root: Path | None = None,
    ) -> None:
        self.repo_root = repo_root.resolve()
        self.vendor_root = (
            self.repo_root / "tests" / "vendor" / "aml-ua-xslt-e38653c"
        )
        self.artifact_root = artifact_root.resolve() if artifact_root else None
        self._saxon: _SaxonSession | None = None
        self._nodeset_schema: etree.XMLSchema | None = None
        self._caex_schemas: dict[str, etree.XMLSchema] = {}

    def close(self) -> None:
        if self._saxon is not None:
            self._saxon.close()
            self._saxon = None

    def run(
        self,
        manifest: ComparisonManifest,
        *,
        engines: tuple[ComparisonEngine, ...] = tuple(ComparisonEngine),
    ) -> ComparisonReport:
        hashes = self._verify_vendor()
        results: list[CaseResult] = []
        try:
            for case in manifest.cases:
                results.extend(self._run_case(case, manifest, engines))
        finally:
            self.close()
        return ComparisonReport(
            manifest_name=manifest.name,
            manifest_schema_version=manifest.schema_version,
            baseline_commit=manifest.baseline_commit,
            baseline_hashes=hashes,
            environment=_environment(),
            results=tuple(results),
            scores=_score_results(results, engines),
        )

    def _run_case(
        self,
        case: ComparisonCase,
        manifest: ComparisonManifest,
        engines: tuple[ComparisonEngine, ...],
    ) -> list[CaseResult]:
        source_path = (self.repo_root / case.source).resolve()
        if not source_path.is_relative_to(self.repo_root):
            raise ValueError(f"case {case.id} source escapes the repository")
        try:
            source = source_path.read_bytes()
        except OSError as exc:
            invalid = f"source file unavailable: {exc}"
            return [self._invalid_result(case, engine, invalid) for engine in engines]

        try:
            source = _apply_source_mutations(source, case.source_mutations)
            self._validate_source(case, source)
        except (_InvalidFixture, ValueError) as exc:
            return [self._invalid_result(case, engine, str(exc)) for engine in engines]

        return [
            self._run_engine(case, manifest, engine, source)
            for engine in engines
        ]

    def _run_engine(
        self,
        case: ComparisonCase,
        manifest: ComparisonManifest,
        engine: ComparisonEngine,
        source: bytes,
    ) -> CaseResult:
        start = time.perf_counter()
        evidence: list[OracleEvidence] = []
        output: str | None = None
        try:
            if case.direction in {
                CaseDirection.AML_TO_UA,
                CaseDirection.AML_TO_UA_TO_AML,
            }:
                output = self._forward(engine, source, manifest.publication_date)
                self._evaluate_nodeset_oracles(case, output, evidence)
                if OracleName.DETERMINISTIC in case.oracles:
                    repeated = self._forward(engine, source, manifest.publication_date)
                    if _semantic_xml_bytes(output) != _semantic_xml_bytes(repeated):
                        raise _OracleFailure("deterministic: repeated XML differs")
                    evidence.append(
                        OracleEvidence(
                            oracle=OracleName.DETERMINISTIC,
                            passed=True,
                            detail="two transformations are byte-equivalent after XML C14N",
                        )
                    )
                if case.direction == CaseDirection.AML_TO_UA_TO_AML:
                    recovered = self._reverse(engine, output.encode("utf-8"))
                    self._assert_canonical_aml(
                        source,
                        recovered.encode("utf-8"),
                        case.canonicalizations,
                    )
                    evidence.append(
                        OracleEvidence(
                            oracle=OracleName.CANONICAL_AML,
                            passed=True,
                            detail="source and recovered canonical CAEX models are equal",
                        )
                    )
            else:
                self._evaluate_nodeset_oracles(
                    case,
                    source.decode("utf-8-sig"),
                    evidence,
                )
                output = self._reverse(engine, source)
                recovered = output.encode("utf-8")
                self._validate_aml_bytes(
                    recovered,
                    require_schema=OracleName.CAEX_XSD in case.oracles,
                )
                evidence.append(
                    OracleEvidence(
                        oracle=OracleName.CAEX_XSD,
                        passed=True,
                        detail="reverse result is well-formed CAEX",
                    )
                )
                if case.expected_aml is not None:
                    expected_path = (self.repo_root / case.expected_aml).resolve()
                    if not expected_path.is_relative_to(self.repo_root):
                        raise _OracleFailure(
                            "canonical_aml: expected AML path escapes the repository"
                        )
                    try:
                        expected_aml = expected_path.read_bytes()
                    except OSError as exc:
                        raise _OracleFailure(
                            f"canonical_aml: expected AML is unavailable: {exc}"
                        ) from exc
                    self._assert_canonical_aml(
                        expected_aml,
                        recovered,
                        case.canonicalizations,
                    )
                    evidence.append(
                        OracleEvidence(
                            oracle=OracleName.CANONICAL_AML,
                            passed=True,
                            detail=(
                                "reverse result equals the independently stored "
                                "canonical AML projection"
                            ),
                        )
                    )
                if case.direction == CaseDirection.UA_TO_AML_TO_UA_TO_AML:
                    regenerated = self._forward(
                        engine, recovered, manifest.publication_date
                    )
                    verification = self._reverse(
                        engine, regenerated.encode("utf-8")
                    )
                    self._assert_canonical_aml(
                        recovered,
                        verification.encode("utf-8"),
                        case.canonicalizations,
                    )
                    evidence.append(
                        OracleEvidence(
                            oracle=OracleName.CANONICAL_AML,
                            passed=True,
                            detail="UA-origin AML projection is stable",
                        )
                    )

            if case.expected_rejection_category:
                raise _OracleFailure(
                    "expected_rejection: mapper accepted input that must be rejected"
                )
            outcome = (
                CaseOutcome.CANONICAL_PASS
                if case.equivalence != "exact" or case.canonicalizations
                else CaseOutcome.PASS
            )
            diagnostic_category = None
            diagnostic = None
        except Exception as exc:  # all engine errors become report evidence
            category, outcome = _classify_error(exc)
            if case.expected_rejection_category and category == case.expected_rejection_category:
                outcome = CaseOutcome.EXPECTED_REJECTION
                evidence.append(
                    OracleEvidence(
                        oracle="expected_rejection",
                        passed=True,
                        detail=f"rejected with category {category}",
                    )
                )
            else:
                evidence.append(
                    OracleEvidence(
                        oracle=_oracle_from_exception(exc),
                        passed=False,
                        detail=str(exc),
                    )
                )
            diagnostic_category = category
            diagnostic = str(exc)

        artifact = self._write_artifact(case, engine, output)
        return CaseResult(
            case_id=case.id,
            engine=engine,
            family=case.family,
            severity=case.severity,
            scored=(
                engine in case.score_engines
                and case.severity != CaseSeverity.OBSERVATION
            ),
            outcome=outcome,
            duration_ms=(time.perf_counter() - start) * 1000,
            evidence=tuple(evidence),
            diagnostic_category=diagnostic_category,
            diagnostic=diagnostic,
            output_sha256=(
                hashlib.sha256(output.encode("utf-8")).hexdigest()
                if output is not None
                else None
            ),
            artifact=artifact,
        )

    def _validate_source(self, case: ComparisonCase, source: bytes) -> None:
        if _UNSAFE_XML.search(source):
            if case.expected_rejection_category == "UNSAFE_XML":
                return
            raise _InvalidFixture("input contains a forbidden DTD/entity declaration")
        if case.expected_rejection_category:
            # Negative fixtures intentionally violate a semantic precondition.
            # They must remain parseable XML (except the explicit DTD/entity
            # attack above), but are passed to each mapper so a typed rejection
            # can be scored rather than being hidden as INVALID_FIXTURE.
            try:
                root = _parse_xml(source)
            except etree.XMLSyntaxError as exc:
                raise _InvalidFixture(
                    f"negative fixture is not well-formed XML: {exc}"
                ) from exc
            expected_root = (
                "CAEXFile"
                if case.direction
                in {CaseDirection.AML_TO_UA, CaseDirection.AML_TO_UA_TO_AML}
                else "UANodeSet"
            )
            if etree.QName(root).localname != expected_root:
                raise _InvalidFixture(
                    f"negative fixture root is not {expected_root}"
                )
            return
        if case.direction in {
            CaseDirection.AML_TO_UA,
            CaseDirection.AML_TO_UA_TO_AML,
        }:
            require_schema = OracleName.CAEX_XSD in case.oracles
            self._validate_aml_bytes(source, require_schema=require_schema)
        else:
            try:
                root = _parse_xml(source)
            except etree.XMLSyntaxError as exc:
                raise _InvalidFixture(f"invalid NodeSet XML: {exc}") from exc
            if etree.QName(root).localname != "UANodeSet":
                raise _InvalidFixture("OPC UA input does not have a UANodeSet root")
            try:
                self._evaluate_nodeset_oracles(case, source.decode("utf-8-sig"), [])
            except (_OracleFailure, UnicodeError) as exc:
                raise _InvalidFixture(f"invalid NodeSet fixture: {exc}") from exc

    def _validate_aml_bytes(self, source: bytes, *, require_schema: bool) -> None:
        try:
            root = _parse_xml(source)
        except etree.XMLSyntaxError as exc:
            raise _InvalidFixture(f"invalid AutomationML XML: {exc}") from exc
        name = etree.QName(root)
        if name.localname != "CAEXFile" or name.namespace not in {None, "", CAEX_NS}:
            raise _InvalidFixture("input does not have a CAEXFile root")
        if not require_schema:
            return
        version = root.get("SchemaVersion", "")
        schema_key = "3.0" if version.startswith("3") else "2.15"
        schema = self._caex_schema(schema_key)
        if not schema.validate(root):
            error = schema.error_log.last_error
            raise _InvalidFixture(f"CAEX {schema_key} XSD failure: {error}")

    def _evaluate_nodeset_oracles(
        self,
        case: ComparisonCase,
        xml: str,
        evidence: list[OracleEvidence],
    ) -> None:
        data = xml.encode("utf-8")
        if _UNSAFE_XML.search(data):
            raise _OracleFailure("secure_xml: generated XML contains DTD/entity markup")
        try:
            root = _parse_xml(data)
        except etree.XMLSyntaxError as exc:
            raise _OracleFailure(f"nodeset_xsd: output is not well-formed XML: {exc}") from exc
        if etree.QName(root) != etree.QName(UA_NODESET_NS, "UANodeSet"):
            raise _OracleFailure("nodeset_xsd: output root is not ua:UANodeSet")
        if OracleName.SECURE_XML in case.oracles:
            evidence.append(
                OracleEvidence(
                    oracle=OracleName.SECURE_XML,
                    passed=True,
                    detail="DTD/entity markup absent and no-network parser succeeded",
                )
            )
        if OracleName.NODESET_XSD in case.oracles:
            schema = self._get_nodeset_schema()
            if not schema.validate(root):
                error = schema.error_log.last_error
                raise _OracleFailure(f"nodeset_xsd: {error}")
            evidence.append(
                OracleEvidence(
                    oracle=OracleName.NODESET_XSD,
                    passed=True,
                    detail="official vendored UANodeSet XSD accepts the output",
                )
            )
        if OracleName.NODESET_SEMANTICS in case.oracles:
            aliases = _semantic_nodeset_validation(root)
            evidence.append(
                OracleEvidence(
                    oracle=OracleName.NODESET_SEMANTICS,
                    passed=True,
                    detail="NodeIds, aliases, BrowseNames, and references are resolvable",
                )
            )
        else:
            aliases = {
                alias.get("Alias", ""): (alias.text or "").strip()
                for alias in root.xpath("./ua:Aliases/ua:Alias", namespaces=_UA)
            }
        if OracleName.NO_ROUNDTRIP_METADATA in case.oracles:
            _assert_no_roundtrip_metadata(root, case.expected.forbid_shadow_names)
            evidence.append(
                OracleEvidence(
                    oracle=OracleName.NO_ROUNDTRIP_METADATA,
                    passed=True,
                    detail="no embedded AML or forbidden mapper-private shadow nodes",
                )
            )
        if OracleName.EXPECTED_GRAPH in case.oracles:
            _assert_expected_graph(root, aliases, case.expected)
            evidence.append(
                OracleEvidence(
                    oracle=OracleName.EXPECTED_GRAPH,
                    passed=True,
                    detail="all independently declared graph facts hold",
                )
            )

    def _forward(
        self,
        engine: ComparisonEngine,
        source: bytes,
        publication_date: str,
    ) -> str:
        if engine == ComparisonEngine.PYTHON_STRICT:
            return aml_xml_to_nodeset(
                source,
                include_roundtrip=False,
                publication_date=publication_date,
                mapper="python",
            )
        if engine == ComparisonEngine.XSLT_PATCHED:
            return aml_xml_to_nodeset(
                source,
                include_roundtrip=False,
                publication_date=publication_date,
                mapper="xslt",
            )
        raw = self._saxon_session().forward(source)
        if engine == ComparisonEngine.XSLT_RUNNER:
            return _apply_upstream_runner_postprocessing(raw)
        return raw

    def _reverse(self, engine: ComparisonEngine, source: bytes) -> str:
        if engine in {
            ComparisonEngine.PYTHON_STRICT,
            ComparisonEngine.XSLT_PATCHED,
        }:
            document = nodeset_to_document(source, prefer_embedded_source=False)
            return document.to_aml_xml(pretty=True)
        return self._saxon_session().reverse(source)

    def _assert_canonical_aml(
        self,
        source: bytes,
        recovered: bytes,
        canonicalizations: tuple[CanonicalizationName, ...],
    ) -> None:
        try:
            expected = CAEXFile.from_aml_xml(source).to_aml_dict(
                include_change_mode=True
            )
            actual = CAEXFile.from_aml_xml(recovered).to_aml_dict(
                include_change_mode=True
            )
        except (ValueError, OPCUAConversionError) as exc:
            raise _OracleFailure(f"canonical_aml: CAEX model load failed: {exc}") from exc
        if CanonicalizationName.DATATYPE_ALIASES in canonicalizations:
            expected = _canonicalize_datatype_aliases(expected)
        if CanonicalizationName.NOMINAL_CONSTRAINT_SET in canonicalizations:
            expected = _canonicalize_nominal_constraint_sets(expected)
            actual = _canonicalize_nominal_constraint_sets(actual)
        if CanonicalizationName.UUID_BRACES in canonicalizations:
            expected = _canonicalize_uuid_braces(expected)
            actual = _canonicalize_uuid_braces(actual)
        if CanonicalizationName.XML_ATTRIBUTE_WHITESPACE in canonicalizations:
            expected = _canonicalize_xml_attribute_whitespace(expected)
            actual = _canonicalize_xml_attribute_whitespace(actual)
        if CanonicalizationName.RELATIONSHIP_SETS in canonicalizations:
            expected = _canonicalize_relationship_sets(expected)
            actual = _canonicalize_relationship_sets(actual)
        if expected != actual:
            path = _first_difference(expected, actual)
            raise _OracleFailure(f"canonical_aml: first difference at {path}")

    def _invalid_result(
        self,
        case: ComparisonCase,
        engine: ComparisonEngine,
        detail: str,
    ) -> CaseResult:
        return CaseResult(
            case_id=case.id,
            engine=engine,
            family=case.family,
            severity=case.severity,
            scored=False,
            outcome=CaseOutcome.INVALID_FIXTURE,
            duration_ms=0,
            evidence=(
                OracleEvidence(oracle="input", passed=False, detail=detail),
            ),
            diagnostic_category="INVALID_FIXTURE",
            diagnostic=detail,
        )

    def _write_artifact(
        self,
        case: ComparisonCase,
        engine: ComparisonEngine,
        output: str | None,
    ) -> str | None:
        if self.artifact_root is None or output is None:
            return None
        relative = Path("artifacts") / engine.value / f"{case.id}.xml"
        target = self.artifact_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(output, encoding="utf-8")
        return relative.as_posix()

    def _saxon_session(self) -> _SaxonSession:
        if self._saxon is None:
            self._saxon = _SaxonSession(self.vendor_root)
        return self._saxon

    def _get_nodeset_schema(self) -> etree.XMLSchema:
        if self._nodeset_schema is None:
            path = self.vendor_root / "TestData_OPC" / "UANodeSet.xsd"
            self._nodeset_schema = etree.XMLSchema(etree.parse(str(path)))
        return self._nodeset_schema

    def _caex_schema(self, version: str) -> etree.XMLSchema:
        if version not in self._caex_schemas:
            name = (
                "CAEX_ClassModel_V.3.0.xsd"
                if version == "3.0"
                else "CAEX_ClassModel_V2.15.xsd"
            )
            path = self.vendor_root / "UnitTests" / "AML" / name
            self._caex_schemas[version] = etree.XMLSchema(etree.parse(str(path)))
        return self._caex_schemas[version]

    def _verify_vendor(self) -> dict[str, str]:
        if not self.vendor_root.is_dir():
            raise FileNotFoundError(f"vendored upstream baseline missing: {self.vendor_root}")
        actual: dict[str, str] = {}
        for name, expected in UPSTREAM_SOURCE_HASHES.items():
            path = self.vendor_root / name
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest != expected:
                raise ValueError(
                    f"vendored upstream hash mismatch for {name}: {digest} != {expected}"
                )
            actual[name] = digest
        return actual


def _parse_xml(source: bytes) -> etree._Element:
    parser = etree.XMLParser(
        resolve_entities=False,
        load_dtd=False,
        no_network=True,
        remove_blank_text=True,
        strip_cdata=False,
    )
    return etree.fromstring(source, parser=parser)


def _apply_source_mutations(
    source: bytes,
    mutations: tuple[SourceMutationName, ...],
) -> bytes:
    """Apply declared graph-preserving or deliberate-negative UA mutations."""

    if not mutations:
        return source
    root = _parse_xml(source)
    if etree.QName(root) != etree.QName(UA_NODESET_NS, "UANodeSet"):
        raise ValueError("source mutations currently require a UANodeSet fixture")
    for mutation in mutations:
        if mutation == SourceMutationName.REMAP_NODE_IDS:
            _remap_document_node_ids(root)
        elif mutation == SourceMutationName.EXPAND_ALIAS_USES:
            _expand_alias_uses(root)
        elif mutation == SourceMutationName.REMAP_NAMESPACE_INDEXES:
            _remap_namespace_indexes(root)
        elif mutation == SourceMutationName.REVERSE_NODE_ORDER:
            nodes = [child for child in root if child.get("NodeId") is not None]
            for child in nodes:
                root.remove(child)
            root.extend(reversed(nodes))
        elif mutation == SourceMutationName.REVERSE_REFERENCE_ORDER:
            for references in root.xpath(".//ua:References", namespaces=_UA):
                references[:] = list(reversed(references[:]))
        elif mutation == SourceMutationName.DIFFERENT_DISPLAY_NAME:
            candidates = root.xpath(
                "./ua:*[@BrowseName='1:Motor']/ua:DisplayName",
                namespaces=_UA,
            )
            if len(candidates) != 1:
                raise ValueError("display-name mutation requires one 1:Motor node")
            candidates[0].text = "Localized motor label"
        elif mutation == SourceMutationName.COMPACT_XML:
            pass
        elif mutation == SourceMutationName.ADD_UNKNOWN_COMPONENT:
            _add_unknown_component(root)
        elif mutation == SourceMutationName.DUPLICATE_NODE_ID:
            temperature = _one_browse_node(root, "1:temperature")
            root.append(etree.fromstring(etree.tostring(temperature)))
        elif mutation == SourceMutationName.INVALID_NODE_ID:
            temperature = _one_browse_node(root, "1:temperature")
            temperature.set("NodeId", "not-a-node-id")
        elif mutation == SourceMutationName.MISSING_LOCAL_TARGET:
            motor = _one_browse_node(root, "1:Motor")
            edge = motor.xpath(
                "./ua:References/ua:Reference[@ReferenceType='HasComponent'][1]",
                namespaces=_UA,
            )
            if not edge:
                raise ValueError("missing-target mutation requires a component")
            edge[0].text = "ns=1;s=authored:missing-target"
        elif mutation == SourceMutationName.MULTIPLE_TYPE_DEFINITIONS:
            _append_reference(
                _one_browse_node(root, "1:PortA"),
                "HasTypeDefinition",
                "BaseObjectType",
            )
        elif mutation == SourceMutationName.CLASS_ANCESTRY_CYCLE:
            port = _one_browse_node(root, "1:Port")
            motor_type = _one_browse_node(root, "1:MotorType")
            for source_node, target_node in (
                (port, motor_type),
                (motor_type, port),
            ):
                inverse = source_node.xpath(
                    "./ua:References/ua:Reference[@ReferenceType='HasSubtype' "
                    "and @IsForward='false']",
                    namespaces=_UA,
                )
                if len(inverse) != 1:
                    raise ValueError(
                        "class-cycle mutation requires one base edge per class"
                    )
                inverse[0].text = target_node.get("NodeId")
        elif mutation == SourceMutationName.MULTIPLE_COMPONENT_OWNERS:
            _append_reference(
                _one_browse_node(root, "1:Device"),
                "HasComponent",
                _one_browse_node(root, "1:PortA").get("NodeId", ""),
            )
        elif mutation == SourceMutationName.OBJECT_VARIABLE_FIELDS:
            device = _one_browse_node(root, "1:Device")
            device.set("DataType", "Int32")
            value = etree.SubElement(device, f"{{{UA_NODESET_NS}}}Value")
            scalar = etree.SubElement(
                value,
                "{http://opcfoundation.org/UA/2008/02/Types.xsd}Int32",
            )
            scalar.text = "1"
        elif mutation == SourceMutationName.DEFAULT_DATATYPE_MISMATCH:
            _one_browse_node(root, "1:DefaultValue").set("DataType", "String")
        elif mutation == SourceMutationName.UNKNOWN_DATATYPE:
            _one_browse_node(root, "1:temperature").set("DataType", "i=22")
            _one_browse_node(root, "1:DefaultValue").set("DataType", "i=22")
    return etree.tostring(
        root,
        encoding="utf-8",
        xml_declaration=True,
        pretty_print=SourceMutationName.COMPACT_XML not in mutations,
    )


def _remap_document_node_ids(root: etree._Element) -> None:
    node_ids = [
        node.get("NodeId", "")
        for node in root.xpath("./ua:*[@NodeId]", namespaces=_UA)
    ]
    mapping = {
        node_id: f"ns=1;s=authored:{position}"
        for position, node_id in enumerate(node_ids, start=1)
        if node_id.startswith("ns=1;")
    }
    for node in root.xpath("./ua:*[@NodeId]", namespaces=_UA):
        node.set("NodeId", mapping.get(node.get("NodeId", ""), node.get("NodeId", "")))
        parent = node.get("ParentNodeId")
        if parent in mapping:
            node.set("ParentNodeId", mapping[parent])
    for reference in root.xpath(".//ua:Reference", namespaces=_UA):
        target = (reference.text or "").strip()
        if target in mapping:
            reference.text = mapping[target]


def _expand_alias_uses(root: etree._Element) -> None:
    aliases = {
        alias.get("Alias", ""): (alias.text or "").strip()
        for alias in root.xpath("./ua:Aliases/ua:Alias", namespaces=_UA)
    }
    for node in root.xpath("./ua:*[@NodeId]", namespaces=_UA):
        for attribute in ("ParentNodeId", "DataType"):
            value = node.get(attribute)
            if value in aliases:
                node.set(attribute, aliases[value])
    for reference in root.xpath(".//ua:Reference", namespaces=_UA):
        reference_type = reference.get("ReferenceType", "")
        if reference_type in aliases:
            reference.set("ReferenceType", aliases[reference_type])
        target = (reference.text or "").strip()
        if target in aliases:
            reference.text = aliases[target]
    container = root.find(f"{{{UA_NODESET_NS}}}Aliases")
    if container is not None:
        root.remove(container)


_NAMESPACE_NODE_ID = re.compile(r"\bns=(\d+);")


def _remap_namespace_indexes(root: etree._Element) -> None:
    namespace_uris = root.find(f"{{{UA_NODESET_NS}}}NamespaceUris")
    if namespace_uris is None:
        raise ValueError("namespace mutation requires NamespaceUris")
    dummy = etree.Element(f"{{{UA_NODESET_NS}}}Uri")
    dummy.text = "urn:automationml:test:unrelated"
    namespace_uris.insert(0, dummy)

    def remap(value: str) -> str:
        return _NAMESPACE_NODE_ID.sub(
            lambda match: f"ns={int(match.group(1)) + 1};",
            value,
        )

    for element in root.iter():
        for attribute in ("NodeId", "ParentNodeId", "DataType", "ReferenceType"):
            value = element.get(attribute)
            if value:
                element.set(attribute, remap(value))
        if etree.QName(element).localname in {"Alias", "Reference"} and element.text:
            element.text = remap(element.text)


def _add_unknown_component(root: etree._Element) -> None:
    owner = root.xpath("./ua:*[@BrowseName='1:Motor']", namespaces=_UA)
    if len(owner) != 1:
        raise ValueError("unknown-component mutation requires one 1:Motor node")
    references = owner[0].find(f"{{{UA_NODESET_NS}}}References")
    if references is None:
        references = etree.SubElement(
            owner[0],
            f"{{{UA_NODESET_NS}}}References",
        )
    edge = etree.SubElement(references, f"{{{UA_NODESET_NS}}}Reference")
    edge.set("ReferenceType", "HasComponent")
    edge.text = "ns=1;s=authored:unknown-component"
    unknown = etree.SubElement(root, f"{{{UA_NODESET_NS}}}UAObject")
    unknown.set("NodeId", "ns=1;s=authored:unknown-component")
    unknown.set("BrowseName", "1:Mystery")
    etree.SubElement(unknown, f"{{{UA_NODESET_NS}}}DisplayName").text = "Mystery"
    unknown_references = etree.SubElement(
        unknown,
        f"{{{UA_NODESET_NS}}}References",
    )
    type_edge = etree.SubElement(
        unknown_references,
        f"{{{UA_NODESET_NS}}}Reference",
    )
    type_edge.set("ReferenceType", "HasTypeDefinition")
    type_edge.text = "BaseObjectType"


def _one_browse_node(root: etree._Element, browse_name: str) -> etree._Element:
    nodes = root.xpath("./ua:*[@BrowseName=$name]", namespaces=_UA, name=browse_name)
    if len(nodes) != 1:
        raise ValueError(f"mutation requires one {browse_name!r} node, got {len(nodes)}")
    return nodes[0]


def _append_reference(
    node: etree._Element,
    reference_type: str,
    target: str,
    *,
    is_forward: bool = True,
) -> None:
    references = node.find(f"{{{UA_NODESET_NS}}}References")
    if references is None:
        references = etree.SubElement(node, f"{{{UA_NODESET_NS}}}References")
    edge = etree.SubElement(references, f"{{{UA_NODESET_NS}}}Reference")
    edge.set("ReferenceType", reference_type)
    if not is_forward:
        edge.set("IsForward", "false")
    edge.text = target


def _semantic_xml_bytes(xml: str) -> bytes:
    return etree.tostring(_parse_xml(xml.encode("utf-8")), method="c14n")


def _apply_upstream_runner_postprocessing(xml: str) -> str:
    root = _parse_xml(xml.encode("utf-8"))
    etree.cleanup_namespaces(root)
    for node in root.xpath(
        "//uax:String",
        namespaces={"uax": "http://opcfoundation.org/UA/2008/02/Types.xsd"},
    ):
        if node.text and node.text.lstrip().startswith("<"):
            node.text = etree.CDATA(node.text)
    rendered = etree.tostring(
        root,
        encoding="utf-8",
        xml_declaration=True,
        pretty_print=True,
    ).decode("utf-8")
    return re.sub(
        r'PublicationDate="(\d{4}-\d{2}-\d{2})T[\d:]+Z',
        r'PublicationDate="\1T00:00:00Z',
        rendered,
    )


def _semantic_nodeset_validation(root: etree._Element) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for alias in root.xpath("./ua:Aliases/ua:Alias", namespaces=_UA):
        name = alias.get("Alias", "")
        value = (alias.text or "").strip()
        if not name or name in aliases:
            raise _OracleFailure(f"nodeset_semantics: duplicate/empty alias {name!r}")
        _require_node_id(value, f"alias {name!r}")
        aliases[name] = value

    node_ids: set[str] = set()
    for node in root.xpath("./ua:*[@NodeId]", namespaces=_UA):
        node_id = node.get("NodeId", "")
        _require_node_id(node_id, "NodeId")
        if node_id in node_ids:
            raise _OracleFailure(f"nodeset_semantics: duplicate NodeId {node_id!r}")
        node_ids.add(node_id)
        browse_name = node.get("BrowseName")
        if browse_name is not None and not _BROWSE_NAME.fullmatch(browse_name):
            raise _OracleFailure(
                f"nodeset_semantics: invalid BrowseName {browse_name!r} on {node_id}"
            )
        for attribute in ("ParentNodeId", "DataType"):
            value = node.get(attribute)
            if value:
                _require_node_id_or_alias(value, aliases, attribute)

    for reference in root.xpath(".//ua:Reference", namespaces=_UA):
        _require_node_id_or_alias(
            reference.get("ReferenceType", ""), aliases, "ReferenceType"
        )
        _require_node_id_or_alias(
            (reference.text or "").strip(), aliases, "reference target"
        )
    return aliases


def _require_node_id(value: str, label: str) -> None:
    if not _NODE_ID.fullmatch(value):
        raise _OracleFailure(f"nodeset_semantics: invalid {label} {value!r}")


def _require_node_id_or_alias(
    value: str,
    aliases: dict[str, str],
    label: str,
) -> None:
    if value not in aliases and not _NODE_ID.fullmatch(value):
        raise _OracleFailure(f"nodeset_semantics: unresolved {label} {value!r}")


def _assert_no_roundtrip_metadata(root: etree._Element, forbid_shadows: bool) -> None:
    payload = root.xpath(
        ".//*[local-name()='OriginalAutomationML' and namespace-uri()=$namespace]",
        namespace=ROUNDTRIP_NS,
    )
    if payload:
        raise _OracleFailure("no_roundtrip_metadata: embedded AutomationML found")
    if forbid_shadows:
        names = {
            (node.text or "").strip()
            for node in root.xpath("./ua:*/ua:DisplayName", namespaces=_UA)
        }
        shadows = sorted(names & _SHADOW_NAMES)
        if shadows:
            raise _OracleFailure(
                "no_roundtrip_metadata: forbidden shadow nodes " + ", ".join(shadows)
            )


def _assert_expected_graph(
    root: etree._Element,
    aliases: dict[str, str],
    expected: GraphExpectation,
) -> None:
    if expected.require_nonempty_model_version:
        models = root.xpath("./ua:Models/ua:Model", namespaces=_UA)
        if not models or any(not model.get("Version", "").strip() for model in models):
            raise _OracleFailure("expected_graph: a Model Version is absent or empty")
    if expected.required_model_version is not None:
        versions = root.xpath("./ua:Models/ua:Model/@Version", namespaces=_UA)
        if expected.required_model_version not in versions:
            raise _OracleFailure(
                "expected_graph: required Model Version "
                f"{expected.required_model_version!r} is absent; got {versions}"
            )
    if expected.required_publication_date is not None:
        publication_dates = root.xpath(
            "./ua:Models/ua:Model/@PublicationDate",
            namespaces=_UA,
        )
        if expected.required_publication_date not in publication_dates:
            raise _OracleFailure(
                "expected_graph: required PublicationDate "
                f"{expected.required_publication_date!r} is absent; got "
                f"{publication_dates}"
            )
    reference_types = {
        reference.get("ReferenceType", "")
        for reference in root.xpath(".//ua:Reference", namespaces=_UA)
    }
    forbidden = sorted(reference_types & set(expected.forbidden_reference_types))
    if forbidden:
        raise _OracleFailure(
            "expected_graph: forbidden reference types " + ", ".join(forbidden)
        )
    node_ids = root.xpath(
        "./ua:*[@NodeId]/@NodeId | ./ua:Aliases/ua:Alias/text() | "
        "./ua:*[@ParentNodeId]/@ParentNodeId | ./ua:*[@DataType]/@DataType | "
        ".//ua:Reference/text()",
        namespaces=_UA,
    )
    for pattern in expected.forbidden_node_id_patterns:
        matches = [value for value in node_ids if re.search(pattern, value)]
        if matches:
            raise _OracleFailure(
                f"expected_graph: NodeIds match forbidden {pattern!r}: {matches[:3]}"
            )
    for fact in expected.nodes:
        candidates = [
            node
            for node in root.xpath(f"./ua:{fact.node_class}", namespaces=_UA)
            if node.findtext(f"{{{UA_NODESET_NS}}}DisplayName") == fact.display_name
        ]
        nodes = [
            node
            for node in candidates
            if (fact.browse_name is None or node.get("BrowseName") == fact.browse_name)
            and all(node.get(name) == value for name, value in fact.attributes.items())
            and (
                fact.documentation is None
                or node.findtext(f"{{{UA_NODESET_NS}}}Documentation")
                == fact.documentation
            )
            and (
                fact.value is None
                or _nodeset_scalar_text(node) == fact.value
            )
        ]
        if len(nodes) != fact.count:
            raise _OracleFailure(
                f"expected_graph: {fact.node_class} {fact.display_name!r} count "
                f"is {len(nodes)}, expected {fact.count}"
            )
        for node in nodes:
            if fact.browse_name is not None and node.get("BrowseName") != fact.browse_name:
                raise _OracleFailure(
                    f"expected_graph: {fact.display_name!r} BrowseName is "
                    f"{node.get('BrowseName')!r}, expected {fact.browse_name!r}"
                )
            for name, value in fact.attributes.items():
                if node.get(name) != value:
                    raise _OracleFailure(
                        f"expected_graph: {fact.display_name!r} @{name} is "
                        f"{node.get(name)!r}, expected {value!r}"
                    )
            if fact.documentation is not None:
                actual = node.findtext(f"{{{UA_NODESET_NS}}}Documentation")
                if actual != fact.documentation:
                    raise _OracleFailure(
                        f"expected_graph: {fact.display_name!r} documentation is "
                        f"{actual!r}, expected {fact.documentation!r}"
                    )
            if fact.value is not None:
                actual = _nodeset_scalar_text(node)
                if actual != fact.value:
                    raise _OracleFailure(
                        f"expected_graph: {fact.display_name!r} value is "
                        f"{actual!r}, expected {fact.value!r}"
                    )
            for reference in fact.references:
                _assert_reference(node, aliases, fact.display_name, reference)


def _nodeset_scalar_text(node: etree._Element) -> str:
    value_node = node.find(f"{{{UA_NODESET_NS}}}Value")
    return (
        ""
        if value_node is None
        else "".join(
            value_node[0].itertext()
            if len(value_node)
            else value_node.itertext()
        )
    )


def _assert_reference(
    node: etree._Element,
    aliases: dict[str, str],
    display_name: str,
    expected: ReferenceExpectation,
) -> None:
    expected_type = aliases.get(expected.reference_type, expected.reference_type)
    candidates = []
    for reference in node.xpath("./ua:References/ua:Reference", namespaces=_UA):
        actual_type = reference.get("ReferenceType", "")
        resolved_type = aliases.get(actual_type, actual_type)
        actual_forward = reference.get("IsForward", "true").lower() != "false"
        if resolved_type == expected_type and actual_forward == expected.is_forward:
            candidates.append((reference.text or "").strip())
    if expected.target is not None:
        expected_target = aliases.get(expected.target, expected.target)
        candidates = [value for value in candidates if aliases.get(value, value) == expected_target]
    if expected.target_endswith is not None:
        candidates = [value for value in candidates if value.endswith(expected.target_endswith)]
    if not candidates:
        raise _OracleFailure(
            f"expected_graph: {display_name!r} lacks expected "
            f"{expected.reference_type} reference"
        )


def _first_difference(left: Any, right: Any, path: str = "") -> str:
    if isinstance(left, dict) and isinstance(right, dict):
        for key in sorted(left.keys() | right.keys()):
            child = f"{path}/{key}"
            if key not in left or key not in right:
                return child
            difference = _first_difference(left[key], right[key], child)
            if difference:
                return difference
        return ""
    if isinstance(left, list) and isinstance(right, list):
        for index in range(max(len(left), len(right))):
            child = f"{path}/{index}"
            if index >= len(left) or index >= len(right):
                return child
            difference = _first_difference(left[index], right[index], child)
            if difference:
                return difference
        return ""
    return path or "/" if type(left) is not type(right) or left != right else ""


_CANONICAL_DATATYPE_ALIASES = {
    "xs:integer": "xs:int",
    "xs:positiveInteger": "xs:unsignedLong",
    "xs:ID": "xs:string",
    "xs:token": "xs:string",
    "xs:anyURI": "xs:string",
    "xs:date": "xs:dateTime",
}


def _canonicalize_datatype_aliases(
    value: Any,
    element_kind: str | None = None,
) -> Any:
    """Apply only the many-to-one datatype choices declared by the manifest."""

    if isinstance(value, dict):
        normalized = {
            key: _canonicalize_datatype_aliases(
                item,
                key if key in {"Attribute", "AttributeType"} else None,
            )
            for key, item in value.items()
        }
        data_type = normalized.get("AttributeDataType")
        if isinstance(data_type, str):
            normalized["AttributeDataType"] = _CANONICAL_DATATYPE_ALIASES.get(
                data_type,
                data_type,
            )
        elif element_kind in {"Attribute", "AttributeType"}:
            normalized["AttributeDataType"] = "xs:string"
        return normalized
    if isinstance(value, list):
        return [_canonicalize_datatype_aliases(item, element_kind) for item in value]
    return value


def _canonicalize_nominal_constraint_sets(value: Any) -> Any:
    if isinstance(value, dict):
        normalized = {
            key: _canonicalize_nominal_constraint_sets(item)
            for key, item in value.items()
        }
        nominal = normalized.get("NominalScaledType")
        if isinstance(nominal, dict) and isinstance(
            nominal.get("RequiredValue"),
            list,
        ):
            nominal["RequiredValue"] = sorted(nominal["RequiredValue"])
        return normalized
    if isinstance(value, list):
        return [_canonicalize_nominal_constraint_sets(item) for item in value]
    return value


def _canonicalize_uuid_braces(value: Any) -> Any:
    if isinstance(value, dict):
        normalized = {
            key: _canonicalize_uuid_braces(item)
            for key, item in value.items()
        }
        identifier = normalized.get("ID")
        if (
            isinstance(identifier, str)
            and identifier.startswith("{")
            and identifier.endswith("}")
        ):
            normalized["ID"] = identifier[1:-1]
        return normalized
    if isinstance(value, list):
        return [_canonicalize_uuid_braces(item) for item in value]
    return value


def _canonicalize_xml_attribute_whitespace(
    value: Any,
    element_kind: str | None = None,
) -> Any:
    if isinstance(value, dict):
        return {
            key: _canonicalize_xml_attribute_whitespace(
                item,
                "SourceDocumentInformation"
                if key == "SourceDocumentInformation"
                else element_kind,
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [
            _canonicalize_xml_attribute_whitespace(item, element_kind)
            for item in value
        ]
    if isinstance(value, str) and element_kind == "SourceDocumentInformation":
        return value.replace("\r", " ").replace("\n", " ").replace("\t", " ")
    return value


def _canonicalize_relationship_sets(value: Any) -> Any:
    """Sort only relationship collections declared as semantic sets."""

    if isinstance(value, dict):
        normalized = {
            key: _canonicalize_relationship_sets(item)
            for key, item in value.items()
        }
        sort_fields = {
            "RoleRequirements": "RefBaseRoleClassPath",
            "SupportedRoleClass": "RefRoleClassPath",
            "AttributeNameMapping": (
                "SystemUnitAttributeName",
                "RoleAttributeName",
            ),
            "InterfaceIDMapping": (
                "SystemUnitInterfaceID",
                "RoleInterfaceID",
            ),
            "RefSemantic": "CorrespondingAttributePath",
        }
        for name, fields in sort_fields.items():
            items = normalized.get(name)
            if not isinstance(items, list):
                continue
            keys = (fields,) if isinstance(fields, str) else fields
            normalized[name] = sorted(
                items,
                key=lambda item: tuple(
                    str(item.get(field, "")) if isinstance(item, dict) else ""
                    for field in keys
                ),
            )
        return normalized
    if isinstance(value, list):
        return [_canonicalize_relationship_sets(item) for item in value]
    return value


def _classify_error(exc: Exception) -> tuple[str, CaseOutcome]:
    message = str(exc)
    if isinstance(exc, _OracleFailure):
        prefix = message.split(":", 1)[0].upper()
        return prefix, CaseOutcome.FAIL
    if isinstance(exc, _TransformFailure):
        return "TRANSFORM_ERROR", CaseOutcome.FAIL
    if isinstance(exc, OPCUAConversionError):
        normalized = message.lower()
        diagnostic_patterns = (
            ("UNSAFE_XML", ("dtd and entity", "doctype", "entity declaration")),
            ("DUPLICATE_NODE_ID", ("duplicate opc ua nodeid", "duplicate nodeid")),
            (
                "INVALID_NODE_ID",
                (
                    "invalid opc ua nodeid",
                    "expected an opc ua nodeid",
                    "invalid nodeid value",
                ),
            ),
            (
                "UNRESOLVED_REFERENCE",
                ("unresolved alias", "points to missing node", "missing node"),
            ),
            (
                "MULTIPLE_TYPE_DEFINITIONS",
                (
                    "more than one typedefinition",
                    "must have one typedefinition",
                    "competing typedefinition",
                ),
            ),
            (
                "CLASS_ANCESTRY_CYCLE",
                ("class ancestry contains a cycle", "class ancestry cycle"),
            ),
            (
                "NON_TREE_COMPONENT",
                (
                    "component owners; exactly one",
                    "component graph",
                    "ownership contains a cycle",
                ),
            ),
            (
                "NODE_CLASS_SHAPE",
                (
                    "cannot carry variable fields",
                    "requires a datatype",
                    "missing datatype",
                    "attribute 'datatype' is not allowed",
                    "element '{http://opcfoundation.org/ua/2011/03/uanodeset.xsd}value'",
                ),
            ),
            (
                "DEFAULT_DATATYPE_MISMATCH",
                ("defaultvalue", "datatype differs"),
            ),
            (
                "AMBIGUOUS_ROLE",
                ("ambiguous in the implicit role profile", "ambiguous role"),
            ),
            (
                "PARALLEL_INTERNAL_LINK",
                ("parallel aml internallinks", "parallel native internallink"),
            ),
            (
                "BROKEN_INTERNAL_LINK",
                ("internallink", "references unknown partner"),
            ),
            (
                "UNSUPPORTED_DATATYPE",
                (
                    "no strict opc ua mapping exists for aml datatype",
                    "no strict automationml mapping exists for opc ua datatype",
                    "cannot safely translate aml attributedatatype",
                    "does not yet support opc ua datatype",
                ),
            ),
            (
                "INVALID_SCALAR",
                ("invalid scalar", "invalid opc ua scalar", "lexical value"),
            ),
        )
        for category, fragments in diagnostic_patterns:
            if any(fragment in normalized for fragment in fragments):
                return category, CaseOutcome.FAIL
        if "does not yet support" in message or "not yet support" in message:
            return "UNSUPPORTED_FEATURE", CaseOutcome.UNSUPPORTED
        return "CONVERSION_ERROR", CaseOutcome.FAIL
    return type(exc).__name__.upper(), CaseOutcome.CRASH


def _oracle_from_exception(exc: Exception) -> str:
    if isinstance(exc, _OracleFailure):
        return str(exc).split(":", 1)[0]
    if isinstance(exc, OPCUAConversionError):
        return "mapping"
    return "engine"


def _score_results(
    results: list[CaseResult],
    engines: tuple[ComparisonEngine, ...],
) -> tuple[EngineScore, ...]:
    scores: list[EngineScore] = []
    for engine in engines:
        selected = [item for item in results if item.engine == engine]
        scored = [item for item in selected if item.scored]
        passed = sum(item.outcome in PASS_OUTCOMES for item in scored)
        critical = [item for item in scored if item.severity == CaseSeverity.CRITICAL]
        critical_passed = sum(item.outcome in PASS_OUTCOMES for item in critical)
        counts = Counter(item.outcome.value for item in selected)
        scores.append(
            EngineScore(
                engine=engine,
                passed=passed,
                total=len(scored),
                percent=round((100 * passed / len(scored)) if scored else 0.0, 2),
                critical_passed=critical_passed,
                critical_total=len(critical),
                outcomes=dict(sorted(counts.items())),
            )
        )
    return tuple(scores)


def _environment() -> ComparisonEnvironment:
    import lxml
    import pydantic

    try:
        import saxonche

        saxon_version: str | None = saxonche.__version__
    except ImportError:  # pragma: no cover - dependency profile test
        saxon_version = None
    return ComparisonEnvironment(
        generated_at=datetime.now(UTC),
        platform=platform.platform(),
        python=sys.version,
        pydantic=pydantic.__version__,
        lxml=lxml.__version__,
        saxonche=saxon_version,
    )


def report_markdown(report: ComparisonReport) -> str:
    """Render a compact, transparent capability matrix."""

    lines = [
        f"# {report.manifest_name}",
        "",
        f"Baseline commit: `{report.baseline_commit}`  ",
        f"Generated: `{report.environment.generated_at.isoformat()}`  ",
        f"Platform: `{report.environment.platform}`",
        "",
        "## Score",
        "",
        "| System | Passed | Scored | Percent | Critical |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for score in report.scores:
        lines.append(
            f"| `{score.engine.value}` | {score.passed} | {score.total} | "
            f"{score.percent:.2f}% | {score.critical_passed}/{score.critical_total} |"
        )
    lines.extend(
        [
            "",
            "Scores count conformance outcomes, not independent root causes. A single "
            "global NodeSet defect can correctly fail many cases which all require a "
            "valid NodeSet.",
        ]
    )
    unscored_engines = [score.engine for score in report.scores if score.total == 0]
    if unscored_engines:
        lines.extend(
            [
                "",
                "## Unscored engine outcomes",
                "",
                "These are diagnostic appendix counts over non-observation cases. They "
                "are not headline scores and cannot improve or reduce either candidate.",
                "",
                "| System | Passing outcomes | Applicable mandatory cases |",
                "| --- | ---: | ---: |",
            ]
        )
        for engine in unscored_engines:
            applicable = [
                result
                for result in report.results
                if result.engine == engine
                and result.severity != CaseSeverity.OBSERVATION
            ]
            passing = sum(
                result.outcome in PASS_OUTCOMES for result in applicable
            )
            lines.append(
                f"| `{engine.value}` | {passing} | {len(applicable)} |"
            )
    lines.extend(
        [
            "",
            "## Full result matrix",
            "",
            "| Case | Family | Severity | System | Scored | Outcome | Diagnostic |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for result in report.results:
        diagnostic = (result.diagnostic or "").replace("|", "\\|").replace("\n", " ")
        if len(diagnostic) > 180:
            diagnostic = diagnostic[:177] + "..."
        lines.append(
            f"| `{result.case_id}` | {result.family} | {result.severity.value} | "
            f"`{result.engine.value}` | {'yes' if result.scored else 'no'} | "
            f"**{result.outcome.value}** | {diagnostic} |"
        )
    lines.extend(
        [
            "",
            "`INVALID_FIXTURE` and observation rows are visible but excluded from scores. "
            "`UNSUPPORTED` is not a pass.",
            "",
        ]
    )
    return "\n".join(lines)


def report_junit_xml(report: ComparisonReport) -> str:
    """Render results as JUnit without turning honest unsupported rows green."""

    suite = etree.Element(
        "testsuite",
        name=report.manifest_name,
        tests=str(len(report.results)),
        failures=str(
            sum(
                result.scored and result.outcome not in PASS_OUTCOMES
                for result in report.results
            )
        ),
        skipped=str(sum(not result.scored for result in report.results)),
    )
    for result in report.results:
        case = etree.SubElement(
            suite,
            "testcase",
            classname=f"opcua-comparison.{result.engine.value}.{result.family}",
            name=result.case_id,
            time=f"{result.duration_ms / 1000:.6f}",
        )
        if not result.scored:
            etree.SubElement(case, "skipped", message=result.outcome.value)
        elif result.outcome not in PASS_OUTCOMES:
            failure = etree.SubElement(
                case,
                "failure",
                type=result.diagnostic_category or result.outcome.value,
                message=result.diagnostic or result.outcome.value,
            )
            failure.text = "\n".join(
                f"{item.oracle}: {'PASS' if item.passed else 'FAIL'} — {item.detail}"
                for item in result.evidence
            )
    return etree.tostring(
        suite,
        encoding="utf-8",
        xml_declaration=True,
        pretty_print=True,
    ).decode("utf-8")
