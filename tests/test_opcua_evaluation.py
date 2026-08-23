from collections import Counter
from pathlib import Path

from lxml import etree
import pytest

from automationml.opcua import aml_xml_to_nodeset
from automationml.opcua_evaluation import (
    CaseOutcome,
    ComparisonEngine,
    ComparisonManifest,
    ComparisonRunner,
    OracleName,
    UPSTREAM_COMMIT,
    UPSTREAM_SOURCE_HASHES,
    _OracleFailure,
    _assert_expected_graph,
)


REPO = Path(__file__).parents[1]
MANIFEST_PATH = REPO / "tests" / "opcua-comparison" / "phase1-manifest.json"
RELEASE_MANIFEST_PATH = (
    REPO / "tests" / "opcua-comparison" / "release-manifest.json"
)
UA_NS = "http://opcfoundation.org/UA/2011/03/UANodeSet.xsd"
NS = {"ua": UA_NS}


def _manifest() -> ComparisonManifest:
    return ComparisonManifest.from_json_file(MANIFEST_PATH)


def _case(case_id: str):
    return next(case for case in _manifest().cases if case.id == case_id)


def _aliases(root: etree._Element) -> dict[str, str]:
    return {
        alias.get("Alias", ""): (alias.text or "").strip()
        for alias in root.xpath("./ua:Aliases/ua:Alias", namespaces=NS)
    }


def _display_node(root: etree._Element, display_name: str) -> etree._Element:
    return next(
        node
        for node in root.xpath("./ua:*[@NodeId]", namespaces=NS)
        if node.findtext(f"{{{UA_NS}}}DisplayName") == display_name
    )


def _candidate_root(case_id: str, mapper: str = "python") -> etree._Element:
    case = _case(case_id)
    source = (REPO / case.source).read_bytes()
    xml = aml_xml_to_nodeset(
        source,
        include_roundtrip=False,
        publication_date="2026-08-17",
        mapper=mapper,
    )
    return etree.fromstring(xml.encode("utf-8"))


def test_phase1_manifest_freezes_complete_upstream_and_defect_corpus():
    manifest = _manifest()

    assert manifest.baseline_commit == UPSTREAM_COMMIT
    assert len(manifest.cases) == 49
    assert len({case.id for case in manifest.cases}) == 49
    assert sum(case.id.startswith("UP-UNIT-") for case in manifest.cases) == 15
    assert sum(case.id.startswith("UP-APP-") for case in manifest.cases) == 15
    assert sum(case.id.startswith("UP-OPC-") for case in manifest.cases) == 7
    assert sum(case.id.startswith("REG-") for case in manifest.cases) == 12


def test_release_manifest_has_predeclared_121_case_headline_corpus():
    manifest = ComparisonManifest.from_json_file(RELEASE_MANIFEST_PATH)

    assert len(manifest.cases) == 145
    assert len({case.id for case in manifest.cases}) == 145
    assert sum(
        ComparisonEngine.PYTHON_STRICT in case.score_engines
        and case.severity.value != "observation"
        for case in manifest.cases
    ) == 121
    assert sum(
        ComparisonEngine.PYTHON_STRICT in case.score_engines
        and case.severity.value == "critical"
        for case in manifest.cases
    ) == 30
    assert Counter(case.family for case in manifest.cases) == {
        "attribute-semantics": 11,
        "constraints-mirror-facet": 6,
        "datatype-matrix": 21,
        "document-header": 6,
        "hierarchy-class": 10,
        "interfaces-links": 7,
        "known-defect": 12,
        "negative-security": 12,
        "roles-mapping": 7,
        "ua-origin": 16,
        "upstream-application": 5,
        "upstream-application-legacy": 10,
        "upstream-opc-observation": 7,
        "upstream-unit": 8,
        "upstream-unit-legacy": 7,
    }


def test_vendored_upstream_executable_sources_match_frozen_hashes():
    runner = ComparisonRunner(repo_root=REPO)

    assert runner._verify_vendor() == UPSTREAM_SOURCE_HASHES


def test_independent_semantic_oracle_distinguishes_python_from_raw_xslt():
    manifest = ComparisonManifest(
        name="oracle smoke test",
        cases=(_case("UP-UNIT-001"),),
    )

    report = ComparisonRunner(repo_root=REPO).run(
        manifest,
        engines=(ComparisonEngine.PYTHON_STRICT, ComparisonEngine.XSLT_RAW),
    )
    outcomes = {result.engine: result for result in report.results}

    assert outcomes[ComparisonEngine.PYTHON_STRICT].outcome == CaseOutcome.PASS
    raw = outcomes[ComparisonEngine.XSLT_RAW]
    assert raw.outcome == CaseOutcome.FAIL
    assert "ns=2;ns=2;i=2004" in (raw.diagnostic or "")


def _mutate_nodeid(root: etree._Element) -> None:
    alias = root.xpath(
        "./ua:Aliases/ua:Alias[@Alias='String']",
        namespaces=NS,
    )[0]
    alias.text = "ns=2;ns=2;i=12"


def _mutate_reference_type(root: etree._Element) -> None:
    reference = root.xpath(
        ".//ua:Reference[@ReferenceType='HasComponent']",
        namespaces=NS,
    )[0]
    reference.set("ReferenceType", "HasComponnent")


def _mutate_model_version(root: etree._Element) -> None:
    root.xpath("./ua:Models/ua:Model", namespaces=NS)[0].set("Version", "")


def _mutate_publication_date(root: etree._Element) -> None:
    root.xpath("./ua:Models/ua:Model", namespaces=NS)[0].set(
        "PublicationDate", "1999-01-01T00:00:00Z"
    )


def _mutate_data_type(root: etree._Element, display_name: str, value: str) -> None:
    _display_node(root, display_name).set("DataType", value)


def _mutate_class_path(root: etree._Element) -> None:
    port = _display_node(root, "Port")
    reference = port.xpath(
        "./ua:References/ua:Reference[@ReferenceType='HasTypeDefinition']",
        namespaces=NS,
    )[0]
    reference.text = "ConnectorLib/BaseConnector/PortConnector"


def _mutate_source_identity(root: etree._Element) -> None:
    second = _display_node(root, "SourceDocumentInformation_2")
    second.find(f"{{{UA_NS}}}DisplayName").text = "SourceDocumentInformation_1"


def _mutate_nested_class(root: etree._Element) -> None:
    cartoner = _display_node(root, "Cartoner")
    reference = cartoner.xpath(
        "./ua:References/ua:Reference[@ReferenceType='HasSubtype']",
        namespaces=NS,
    )[0]
    reference.getparent().remove(reference)


def _mutate_default_value(root: etree._Element) -> None:
    default = _display_node(root, "DefaultValue")
    default.getparent().remove(default)


def _mutate_documentation(root: etree._Element) -> None:
    state = _display_node(root, "state")
    documentation = state.find(f"{{{UA_NS}}}Documentation")
    assert documentation is not None
    state.remove(documentation)


MUTANTS = (
    ("REG-NODEID-001", "python", _mutate_nodeid),
    ("REG-REF-001", "xslt", _mutate_reference_type),
    ("REG-MODEL-001", "python", _mutate_model_version),
    ("REG-DETERMINISM-001", "python", _mutate_publication_date),
    ("REG-DTYPE-001", "python", lambda root: _mutate_data_type(root, "identifier", "id")),
    ("REG-DTYPE-002", "python", lambda root: _mutate_data_type(root, "timestamp", "datetime")),
    ("REG-DTYPE-003", "python", lambda root: _mutate_data_type(root, "token", "Guid")),
    ("REG-CLASS-001", "xslt", _mutate_class_path),
    ("REG-IDENTITY-001", "python", _mutate_source_identity),
    ("REG-CLASS-002", "python", _mutate_nested_class),
    ("REG-ATTR-001", "python", _mutate_default_value),
    ("REG-ATTR-002", "python", _mutate_documentation),
)


@pytest.mark.parametrize("case_id,mapper,mutate", MUTANTS, ids=[item[0] for item in MUTANTS])
def test_every_known_defect_oracle_rejects_its_mutant(case_id, mapper, mutate):
    case = _case(case_id)
    assert OracleName.EXPECTED_GRAPH in case.oracles
    root = _candidate_root(case_id, mapper=mapper)

    _assert_expected_graph(root, _aliases(root), case.expected)
    mutate(root)

    with pytest.raises(_OracleFailure, match="expected_graph"):
        _assert_expected_graph(root, _aliases(root), case.expected)
