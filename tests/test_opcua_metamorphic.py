from __future__ import annotations

import os
import random
from pathlib import Path

from hypothesis import HealthCheck, given, settings, strategies as st
from lxml import etree

from automationml import CAEXFile
from automationml.opcua import aml_xml_to_nodeset, nodeset_to_document
from automationml.opcua_evaluation import (
    SourceMutationName,
    UA_NODESET_NS,
    _apply_source_mutations,
)


REPO = Path(__file__).parents[1]
ORIGIN = (
    REPO / "tests" / "opcua-comparison" / "fixtures" / "ua-origin-base.xml"
).read_bytes()
ORIGIN_EXPECTED = CAEXFile.from_aml_xml(
    (
        REPO
        / "tests"
        / "opcua-comparison"
        / "fixtures"
        / "ua-origin-expected.aml"
    ).read_bytes()
).to_aml_dict(include_change_mode=True)
NS = {"ua": UA_NODESET_NS}
EXAMPLES = int(os.environ.get("AML_HYPOTHESIS_EXAMPLES", "200"))
PROFILE = settings(
    max_examples=EXAMPLES,
    derandomize=True,
    deadline=None,
    database=None,
    suppress_health_check=(HealthCheck.too_slow,),
)


def _parse(data: bytes) -> etree._Element:
    return etree.fromstring(
        data,
        parser=etree.XMLParser(
            resolve_entities=False,
            load_dtd=False,
            no_network=True,
            remove_blank_text=True,
        ),
    )


def _render(root: etree._Element, *, pretty: bool = False) -> bytes:
    return etree.tostring(
        root,
        encoding="utf-8",
        xml_declaration=True,
        pretty_print=pretty,
    )


def _assert_origin_projection(data: bytes) -> None:
    actual = nodeset_to_document(
        data,
        prefer_embedded_source=False,
    ).to_aml_dict(include_change_mode=True)
    assert actual == ORIGIN_EXPECTED


@PROFILE
@given(st.integers(min_value=0, max_value=2**32 - 1))
def test_metamorphic_1_node_and_reference_order(seed: int):
    root = _parse(ORIGIN)
    rng = random.Random(seed)
    nodes = [child for child in root if child.get("NodeId") is not None]
    rng.shuffle(nodes)
    for child in nodes:
        root.remove(child)
    root.extend(nodes)
    for references in root.xpath(".//ua:References", namespaces=NS):
        edges = list(references)
        rng.shuffle(edges)
        references[:] = edges
    _assert_origin_projection(_render(root))


@PROFILE
@given(st.integers(min_value=1, max_value=3), st.booleans())
def test_metamorphic_2_namespace_prefix_and_index(
    dummy_namespace_count: int,
    explicit_prefix: bool,
):
    data = _apply_source_mutations(
        ORIGIN,
        (SourceMutationName.REMAP_NAMESPACE_INDEXES,) * dummy_namespace_count,
    )
    if explicit_prefix:
        source = _parse(data)
        root = etree.Element(
            source.tag,
            nsmap={
                "ua": UA_NODESET_NS,
                "uax": "http://opcfoundation.org/UA/2008/02/Types.xsd",
            },
        )
        root.attrib.update(source.attrib)
        root.extend(source)
        data = _render(root)
    _assert_origin_projection(data)


@PROFILE
@given(st.integers(min_value=0, max_value=2**32 - 1))
def test_metamorphic_3_alias_and_expanded_nodeid_substitution(seed: int):
    root = _parse(ORIGIN)
    aliases = {
        alias.get("Alias", ""): (alias.text or "").strip()
        for alias in root.xpath("./ua:Aliases/ua:Alias", namespaces=NS)
    }
    selected = {
        name
        for position, name in enumerate(sorted(aliases))
        if (seed >> (position % 31)) & 1
    }
    for node in root.xpath("./ua:*[@NodeId]", namespaces=NS):
        data_type = node.get("DataType")
        if data_type in selected:
            node.set("DataType", aliases[data_type])
    for reference in root.xpath(".//ua:Reference", namespaces=NS):
        reference_type = reference.get("ReferenceType", "")
        if reference_type in selected:
            reference.set("ReferenceType", aliases[reference_type])
        target = (reference.text or "").strip()
        if target in selected:
            reference.text = aliases[target]
    alias_container = root.find(f"{{{UA_NODESET_NS}}}Aliases")
    assert alias_container is not None
    for alias in list(alias_container):
        if alias.get("Alias") in selected:
            alias_container.remove(alias)
    _assert_origin_projection(_render(root))


@PROFILE
@given(st.integers(min_value=1, max_value=2**31 - 1))
def test_metamorphic_4_arbitrary_document_nodeids(seed: int):
    root = _parse(ORIGIN)
    node_ids = [
        node.get("NodeId", "")
        for node in root.xpath("./ua:*[@NodeId]", namespaces=NS)
        if node.get("NodeId", "").startswith("ns=1;")
    ]
    rng = random.Random(seed)
    replacements = list(range(1, len(node_ids) + 1))
    rng.shuffle(replacements)
    mapping = {
        old: f"ns=1;s=external-author:{seed:x}:{replacement}"
        for old, replacement in zip(node_ids, replacements, strict=True)
    }
    for node in root.xpath("./ua:*[@NodeId]", namespaces=NS):
        old = node.get("NodeId", "")
        node.set("NodeId", mapping.get(old, old))
        parent = node.get("ParentNodeId")
        if parent in mapping:
            node.set("ParentNodeId", mapping[parent])
    for reference in root.xpath(".//ua:Reference", namespaces=NS):
        target = (reference.text or "").strip()
        if target in mapping:
            reference.text = mapping[target]
    _assert_origin_projection(_render(root))


@PROFILE
@given(st.sampled_from(("", "\n", "\r\n", "\n  ", "\r\n\t")))
def test_metamorphic_5_irrelevant_xml_whitespace(separator: str):
    compact = _render(_parse(ORIGIN)).decode("utf-8")
    data = compact.replace("><", f">{separator}<").encode("utf-8")
    _assert_origin_projection(data)


_CANONICAL_SCALARS = st.sampled_from(
    (
        ("xs:boolean", "true"),
        ("xs:int", "-42"),
        ("xs:unsignedInt", "42"),
        ("xs:long", "-9000000000"),
        ("xs:double", "1.5"),
        ("xs:string", "generated"),
        ("xs:dateTime", "2026-08-17T12:30:00Z"),
        ("xs:base64Binary", "AQID"),
    )
)


@st.composite
def _documents(draw: st.DrawFn) -> CAEXFile:
    attributes = draw(
        st.dictionaries(
            keys=st.from_regex(r"attr_[a-z]{1,8}", fullmatch=True),
            values=_CANONICAL_SCALARS,
            min_size=1,
            max_size=5,
        )
    )
    return CAEXFile.model_validate(
        {
            "FileName": "generated-profile.aml",
            "SchemaVersion": "3.0",
            "InstanceHierarchy": [
                {
                    "Name": "Generated",
                    "InternalElement": [
                        {
                            "Name": "Device",
                            "ID": "generated-device",
                            "Attribute": [
                                {
                                    "Name": name,
                                    "AttributeDataType": data_type,
                                    "Value": value,
                                }
                                for name, (data_type, value) in sorted(
                                    attributes.items()
                                )
                            ],
                        }
                    ],
                }
            ],
        }
    )


@PROFILE
@given(_documents())
def test_metamorphic_6_repeated_conversion_is_deterministic(document: CAEXFile):
    first = document.to_opcua_nodeset_xml(
        pretty=False,
        include_roundtrip=False,
        publication_date="2026-08-17",
    )
    second = document.to_opcua_nodeset_xml(
        pretty=False,
        include_roundtrip=False,
        publication_date="2026-08-17",
    )
    assert first == second


@PROFILE
@given(_documents())
def test_metamorphic_7_aml_origin_idempotence(document: CAEXFile):
    first_ua = document.to_opcua_nodeset_xml(
        include_roundtrip=False,
        publication_date="2026-08-17",
    )
    first_aml = nodeset_to_document(first_ua, prefer_embedded_source=False)
    second_ua = first_aml.to_opcua_nodeset_xml(
        include_roundtrip=False,
        publication_date="2026-08-17",
    )
    second_aml = nodeset_to_document(second_ua, prefer_embedded_source=False)
    assert first_aml.to_aml_dict() == document.to_aml_dict()
    assert second_aml.to_aml_dict() == first_aml.to_aml_dict()


@PROFILE
@given(
    st.lists(
        st.sampled_from(
            (
                SourceMutationName.REMAP_NODE_IDS,
                SourceMutationName.EXPAND_ALIAS_USES,
                SourceMutationName.REMAP_NAMESPACE_INDEXES,
                SourceMutationName.REVERSE_NODE_ORDER,
                SourceMutationName.REVERSE_REFERENCE_ORDER,
                SourceMutationName.DIFFERENT_DISPLAY_NAME,
                SourceMutationName.COMPACT_XML,
            )
        ),
        unique=True,
        max_size=7,
    )
)
def test_metamorphic_8_ua_origin_idempotence(
    mutations: list[SourceMutationName],
):
    source = _apply_source_mutations(ORIGIN, tuple(mutations))
    first_aml = nodeset_to_document(source, prefer_embedded_source=False)
    regenerated = aml_xml_to_nodeset(
        first_aml.to_aml_xml(),
        mapper="python",
        include_roundtrip=False,
        publication_date="2026-08-17",
    )
    second_aml = nodeset_to_document(regenerated, prefer_embedded_source=False)
    assert first_aml.to_aml_dict(include_change_mode=True) == ORIGIN_EXPECTED
    assert second_aml.to_aml_dict() == first_aml.to_aml_dict()
