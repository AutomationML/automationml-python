"""AML <-> RDF/Turtle round-trip tests.

Reuses the AML-UA-XSLT unit-test corpus already vendored for the OPC UA
mapper (``tests/fixtures/opcua_reverse/``), plus the SDK's own
validation-suite examples, as the AML side of the corpus: it is the same
"basic building blocks" set (empty file, a lone InternalElement, an
InternalElement with an Attribute, an empty InstanceHierarchy, class
hierarchies, an attribute-type library, ExternalInterfaces + InternalLinks,
RefSemantic, Constraints) the OPC UA mapper was scored against, so a
regression here is directly comparable to a regression there.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from rdflib import Graph

from automationml import CAEXFile
from automationml.rdf import RDFMappingUnsupported, document_to_ttl

REPO = Path(__file__).parents[1]
REVERSE_FIXTURES = REPO / "tests" / "fixtures" / "opcua_reverse"
VALIDATION_SUITE_XML = REPO / "examples" / "validation-suite" / "xml"

BASIC_FIXTURES = [
    "0_EmptyFile_V2.1.aml",
    "2_IE.aml",
    "3_IE_Attribute.aml",
    "4_IH.aml",
    "5_SUC.aml",
    "8_AMLAttributeLibrary.aml",
    "9_ExtInt_IntLink.aml",
    "10_RefSemantic.aml",
    "11_Constraints.aml",
]

VALIDATION_SUITE_FIXTURES = [
    "small-valid-motor.aml",
    "medium-valid-robot-cell.aml",
    "medium_robot-cell_warning_missing-inherited-attribute-and-class-interface.aml",
    "big-valid-packaging-line.aml",
]


def _load(path: Path) -> CAEXFile:
    return CAEXFile.from_aml_xml(path.read_bytes())


@pytest.mark.parametrize("name", BASIC_FIXTURES)
def test_round_trip_basic_aml_ua_xslt_corpus(name: str) -> None:
    document = _load(REVERSE_FIXTURES / name)
    result = document.round_trip_ttl()

    assert result.semantically_equivalent, result.differences


@pytest.mark.parametrize("name", VALIDATION_SUITE_FIXTURES)
def test_round_trip_validation_suite_examples(name: str) -> None:
    document = _load(VALIDATION_SUITE_XML / name)
    result = document.round_trip_ttl()
    assert result.semantically_equivalent, result.differences


def test_ttl_output_is_parseable_turtle() -> None:
    document = _load(REVERSE_FIXTURES / "9_ExtInt_IntLink.aml")
    ttl = document_to_ttl(document)
    graph = Graph()
    graph.parse(data=ttl, format="turtle")
    assert len(graph) > 0


def test_typed_attribute_values_survive_the_legacy_lossy_lexical_form_trap() -> None:
    # rdflib re-renders a numeric literal's lexical form on serialize/parse
    # (e.g. an xsd:double "36" comes back as "36.0"). The authoritative
    # hasAttributeValue/hasDefaultValue literals are deliberately untyped
    # strings for exactly this reason -- this test pins that decision.
    document = _load(VALIDATION_SUITE_XML / "small-valid-motor.aml")
    result = document.round_trip_ttl()
    assert result.semantically_equivalent, result.differences


def test_unresolvable_internal_link_partner_fails_explicitly() -> None:
    # An InternalLink whose partner reference names an ID that does not
    # exist anywhere in the document. The legacy XSLT's "Hack for wrong
    # format" comment (see docs/rdf-mapping-audit.md) papers over exactly
    # this kind of malformed reference; this profile fails closed instead.
    from automationml.models import InternalLink

    document = _load(REVERSE_FIXTURES / "9_ExtInt_IntLink.aml")
    element = document.instance_hierarchies[0].internal_elements[0]
    element.internal_links.append(
        InternalLink(
            name="BadLink",
            ref_partner_side_a="not-a-real-id:EnergySupply",
            ref_partner_side_b="19dcf818-4716-4fc1-a85f-28e1938c4c3a:EnergySupply",
        )
    )

    with pytest.raises(RDFMappingUnsupported):
        document.to_ttl()


def test_external_base_library_reference_becomes_a_stable_proxy() -> None:
    # "AutomationMLBaseInterface" and friends are AutomationML's own
    # standard base types: real-world files reference them without ever
    # embedding them, and without the alias@library/path syntax. The profile
    # must not treat that as a hard failure.
    document = _load(REVERSE_FIXTURES / "11_Constraints.aml")
    graph = document.to_rdf_graph()
    from automationml.rdf_mapping import DEFAULT_MAPPING_PROFILE
    from rdflib import Namespace, RDF

    ns = Namespace(DEFAULT_MAPPING_PROFILE.base_uri)
    proxies = list(graph.subjects(RDF.type, ns.ExternalClassProxy))
    assert proxies, "expected at least one ExternalClassProxy node"
    paths = {str(value) for uri in proxies for value in graph.objects(uri, ns.hasExternalClassPath)}
    assert "AutomationMLBaseInterface" in paths


def _metadata(label: str) -> dict:
    """Every CAEXBasicObject header field, populated."""

    from automationml.models import (
        AdditionalInformation,
        Revision,
        SourceObjectInformation,
        TextElement,
        XmlExtensionNode,
        XmlExtensionPayload,
    )

    return {
        "description": TextElement(value=f"{label} description"),
        "version": TextElement(value="", change_mode="change"),
        "copyright": TextElement(value=f"(c) {label}"),
        "revision": [
            Revision(
                revision_date="2026-08-17T10:30:00+02:00",
                old_version="1.0",
                new_version="1.1",
                author_name="Tester",
                comment=f"{label} revision",
                change_mode="create",
            )
        ],
        "additional_information": [
            AdditionalInformation(
                value="note",
                xml=XmlExtensionPayload(
                    children=[
                        XmlExtensionNode(
                            name="{urn:vendor}Hint",
                            attributes={"level": "2"},
                            text="keep",
                            tail=" ",
                        )
                    ]
                ),
            )
        ],
        "source_object_information": [
            SourceObjectInformation(origin_id="origin-1", source_obj_id=f"{label}-src", value="x")
        ],
    }


def test_header_metadata_on_every_object_kind_round_trips() -> None:
    # Description/Version/Copyright/Revision/AdditionalInformation/
    # SourceObjectInformation exist on every CAEX object; none of them may
    # be dropped silently by the RDF mapping.
    from automationml.models import (
        AttributeNameMapping,
        ExternalReference,
        InterfaceIDMapping,
        MappingObject,
        RefSemantic,
        RoleRequirements,
        SupportedRoleClass,
    )

    document = _load(REVERSE_FIXTURES / "9_ExtInt_IntLink.aml")
    for key, value in _metadata("file").items():
        setattr(document, key, value)
    document.external_references.append(
        ExternalReference(path="lib.aml", file_alias="Lib", **_metadata("extref"))
    )
    hierarchy = document.instance_hierarchies[0]
    for key, value in _metadata("hierarchy").items():
        setattr(hierarchy, key, value)
    element = hierarchy.internal_elements[0]
    for key, value in _metadata("element").items():
        setattr(element, key, value)
    element.internal_links[0].description = _metadata("link")["description"]
    interface = element.external_interfaces[0]
    for key, value in _metadata("interface").items():
        setattr(interface, key, value)
    from automationml.builders import attribute

    attr = attribute("Speed", "36", data_type="xs:integer", unit="rpm")
    for key, value in _metadata("attribute").items():
        setattr(attr, key, value)
    attr.ref_semantic.append(RefSemantic(corresponding_attribute_path="ECLASS:0173-1#02-AAA", **_metadata("sem")))
    element.attributes.append(attr)
    element.role_requirements.append(
        RoleRequirements(
            ref_base_role_class_path="AutomationMLBaseRoleClassLib/AutomationMLBaseRole",
            mapping_object=MappingObject(
                attribute_name_mapping=[
                    AttributeNameMapping(
                        system_unit_attribute_name="Speed",
                        role_attribute_name="RoleSpeed",
                        **_metadata("name-pair"),
                    )
                ],
                interface_id_mapping=[
                    InterfaceIDMapping(
                        system_unit_interface_id="a",
                        role_interface_id="b",
                        **_metadata("id-pair"),
                    )
                ],
                **_metadata("mapping"),
            ),
            **_metadata("role-req"),
        )
    )
    element.supported_role_classes.append(
        SupportedRoleClass(
            ref_role_class_path="AutomationMLBaseRoleClassLib/AutomationMLBaseRole",
            **_metadata("supported"),
        )
    )

    result = document.round_trip_ttl()
    assert result.semantically_equivalent, result.differences


@pytest.mark.parametrize(
    "data_type",
    ["xs:integer", "xs:positiveInteger", "xs:ID", "xs:token", "xs:decimal", "xs:duration"],
)
def test_authored_attribute_data_type_is_preserved(data_type: str) -> None:
    from automationml.builders import attribute

    document = _load(REVERSE_FIXTURES / "3_IE_Attribute.aml")
    element = document.instance_hierarchies[0].internal_elements[0]
    element.attributes.append(attribute("Typed", "1", data_type=data_type))
    result = document.round_trip_ttl()
    assert result.semantically_equivalent, result.differences


def test_omitted_attribute_data_type_stays_omitted() -> None:
    from automationml.builders import attribute
    from rdflib import Namespace
    from automationml.rdf_mapping import DEFAULT_MAPPING_PROFILE

    document = _load(REVERSE_FIXTURES / "3_IE_Attribute.aml")
    element = document.instance_hierarchies[0].internal_elements[0]
    element.attributes.append(attribute("Untyped", "x"))
    result = document.round_trip_ttl()
    assert result.semantically_equivalent, result.differences

    ns = Namespace(DEFAULT_MAPPING_PROFILE.base_uri)
    graph = document.to_rdf_graph()
    # Consumers still get the effective default type.
    assert any(str(v) == "xs:string" for v in graph.objects(None, ns.hasDataType))


@pytest.mark.parametrize(
    ("interface_id", "partner"),
    [
        ("{5f535d4c-dd46-4c1c-898c-4e58419048b6}", "5f535d4c-dd46-4c1c-898c-4e58419048b6"),
        ("5f535d4c-dd46-4c1c-898c-4e58419048b6", "{5f535d4c-dd46-4c1c-898c-4e58419048b6}"),
    ],
)
def test_internal_link_partner_ids_match_with_or_without_braces(interface_id: str, partner: str) -> None:
    # IDs stay exactly as authored; lookups ignore optional GUID braces.
    from automationml import external_interface, internal_element, instance_hierarchy, caex_file
    from automationml.models import InternalLink

    left = internal_element("Left", id="11111111-1111-1111-1111-111111111111")
    left.external_interfaces.append(external_interface("Out", id=interface_id))
    right = internal_element("Right", id="{22222222-2222-2222-2222-222222222222}")
    right.external_interfaces.append(external_interface("In", id="33333333-3333-3333-3333-333333333333"))
    parent = internal_element("Cell", id="44444444-4444-4444-4444-444444444444")
    parent.internal_elements.extend([left, right])
    parent.internal_links.append(
        InternalLink(
            name="Link",
            ref_partner_side_a=partner,
            ref_partner_side_b="{33333333-3333-3333-3333-333333333333}",
        )
    )
    hierarchy = instance_hierarchy("Plant")
    hierarchy.internal_elements.append(parent)
    document = caex_file("braces.aml")
    document.instance_hierarchies.append(hierarchy)

    assert not [
        issue for issue in document.caex_validation_issues() if issue.code == "unresolved-internal-link-partner"
    ]
    result = document.round_trip_ttl()
    assert result.semantically_equivalent, result.differences
    # Authored spelling is kept.
    assert result.recovered_document.instance_hierarchies[0].internal_elements[0].internal_elements[0].external_interfaces[0].id == interface_id
    assert document.query().find_by_id(partner) is not None
