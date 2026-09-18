import base64
from copy import deepcopy
from pathlib import Path

from lxml import etree
import pytest

from automationml import CAEXFile
from automationml.opcua import (
    OPCUAConversionError,
    ROUNDTRIP_NS,
    UA_NODESET_NS,
    _validate_nodeset,
    aml_xml_to_nodeset,
    nodeset_to_aml_xml,
)

# The patched working-group stylesheet is comparison material rather than SDK
# API, so it is produced by the evaluation harness. These tests use it as an
# independent NodeSet producer to exercise the SDK's semantic reverse mapping.
from opcua_evaluation import (
    patched_xslt_nodeset_element,
    patched_xslt_nodeset_xml,
)


FIXTURE = Path(__file__).parent / "fixtures" / "minimal_caex.json"
REVERSE_FIXTURES = Path(__file__).parent / "fixtures" / "opcua_reverse"
NODESET_XSD = (
    Path(__file__).parents[1]
    / "src"
    / "automationml"
    / "resources"
    / "opcua"
    / "UANodeSet.xsd"
)
NS = {"ua": UA_NODESET_NS, "amlrt": ROUNDTRIP_NS}


def _document() -> CAEXFile:
    return CAEXFile.model_validate_json(FIXTURE.read_text(encoding="utf-8"))


def _raw_nodeset(document: CAEXFile, publication_date: str = "2026-08-16"):
    aml_xml = document.to_aml_xml(
        pretty=False,
        include_default_change_mode=True,
    )
    return patched_xslt_nodeset_element(
        aml_xml.encode(),
        publication_date=publication_date,
    )


def _xslt_nodeset(document: CAEXFile, publication_date: str = "2026-08-16") -> str:
    """The annotated patched-XSLT NodeSet the SDK used to expose as mapper='xslt'."""

    aml_xml = document.to_aml_xml(
        pretty=False,
        include_default_change_mode=True,
    )
    return patched_xslt_nodeset_xml(
        aml_xml.encode(),
        publication_date=publication_date,
    )


def test_forward_stylesheet_is_schema_valid_without_output_repairs():
    root = _raw_nodeset(_document())
    schema = etree.XMLSchema(etree.parse(str(NODESET_XSD)))

    schema.assertValid(root)
    _validate_nodeset(root)
    assert root.tag == f"{{{UA_NODESET_NS}}}UANodeSet"
    assert root.xpath("count(./ua:UAObject)", namespaces=NS) > 0
    assert not root.xpath(
        "./ua:Aliases/ua:Alias[contains(text(), ';ns=')]", namespaces=NS
    )
    assert not root.xpath("./ua:Models/*[@Version='']", namespaces=NS)
    assert set(
        root.xpath("./ua:Models//@PublicationDate", namespaces=NS)
    ) >= {"2026-08-16T00:00:00Z", "2019-09-09T00:00:00Z"}
    assert not root.xpath(
        ".//ua:Reference[@ReferenceType='HasComponnent']", namespaces=NS
    )


def test_forward_stylesheet_is_deterministic_for_a_fixed_publication_date():
    first = etree.tostring(_raw_nodeset(_document()))
    second = etree.tostring(_raw_nodeset(_document()))

    assert first == second


def test_xslt_wrapper_adds_metadata_without_rewriting_xslt_mapping():
    raw = _raw_nodeset(_document())
    wrapped = etree.fromstring(
        _xslt_nodeset(_document()).encode(),
        parser=etree.XMLParser(remove_blank_text=True),
    )
    metadata = wrapped.xpath(
        "./ua:Extensions/ua:Extension/amlrt:AutomationMLExport",
        namespaces=NS,
    )[0]
    assert metadata.get("mappingPatch") == "automationml-xslt-v3"
    assert metadata.get("reverseMapping") == "automationml-python-semantic-v3"
    assert metadata.get("validation") == "automationml-python-v1"
    assert metadata.get("hardening") is None

    extensions = wrapped.find(f"{{{UA_NODESET_NS}}}Extensions")
    assert extensions is not None
    wrapped.remove(extensions)
    etree.cleanup_namespaces(raw)
    etree.cleanup_namespaces(wrapped)

    assert etree.tostring(raw, method="c14n") == etree.tostring(wrapped, method="c14n")


def test_app_generated_nodeset_round_trips_losslessly():
    document = _document()

    nodeset = document.to_opcua_nodeset_xml()
    recovered = CAEXFile.from_opcua_nodeset_xml(nodeset)

    assert recovered.to_aml_dict() == document.to_aml_dict()


def test_semantic_reverse_round_trips_supported_libraries_without_source_payload():
    document = _document()
    nodeset = _document().to_opcua_nodeset_xml(include_roundtrip=False)

    recovered = CAEXFile.from_opcua_nodeset_xml(nodeset)

    assert recovered.to_aml_dict() == document.to_aml_dict()


def test_semantic_enrichment_uses_part19_and_canonicalizes_ref_semantics():
    semantic_values = [
        "ECLASS:0173-1#02-AAB977#007",
        "0112/2///61987#ABA565#009",
        "https://example.org/semantic/temperature",
        "AMLID:4f8aa42d-8495-4e15-a960-8e36da028ceb",
        "IEC81346:plain-local-reference",
        "plain-local-reference",
    ]
    document = CAEXFile.model_validate(
        {
            "FileName": "semantic-references.aml",
            "SchemaVersion": "3.0",
            "InstanceHierarchy": [
                {
                    "Name": "Plant",
                    "InternalElement": [
                        {
                            "Name": "Machine",
                            "ID": "machine-1",
                            "Attribute": [
                                {
                                    "Name": "temperature",
                                    "AttributeDataType": "xs:double",
                                    "RefSemantic": [
                                        {"CorrespondingAttributePath": value}
                                        for value in semantic_values
                                    ],
                                }
                            ],
                        }
                    ],
                }
            ],
        }
    )

    nodeset = _xslt_nodeset(document, "2026-08-16")
    root = etree.fromstring(nodeset.encode())
    attribute = root.xpath(
        "./ua:UAVariable[ua:DisplayName='temperature']",
        namespaces=NS,
    )[0]
    semantic_properties = root.xpath(
        "./ua:UAVariable[starts-with(ua:DisplayName, 'AMLRefSemantic_')]",
        namespaces=NS,
    )
    dictionary_targets = attribute.xpath(
        "ua:References/ua:Reference[@ReferenceType='HasDictionaryEntry']/text()",
        namespaces=NS,
    )

    assert [
        "".join(node.xpath("ua:Value/*/text()", namespaces=NS))
        for node in semantic_properties
    ] == semantic_values
    assert len(dictionary_targets) == 5
    assert root.xpath(
        "./ua:Aliases/ua:Alias[@Alias='HasDictionaryEntry' and text()='i=17597']",
        namespaces=NS,
    )
    assert not root.xpath(
        "./ua:Aliases/ua:Alias[@Alias='HasReferenceType'] | "
        "./ua:*[ua:DisplayName='RefSematic']",
        namespaces=NS,
    )
    expected = document.to_aml_dict()
    expected["InstanceHierarchy"][0]["InternalElement"][0]["Attribute"][0][
        "RefSemantic"
    ] = [
        {"CorrespondingAttributePath": value} for value in sorted(semantic_values)
    ]
    recovered = CAEXFile.from_opcua_nodeset_xml(nodeset).to_aml_dict()
    assert recovered == expected

    references = attribute.find(f"{{{NS['ua']}}}References")
    assert references is not None
    references[:] = list(reversed(references))
    reordered_nodeset = etree.tostring(root, encoding="unicode")
    assert CAEXFile.from_opcua_nodeset_xml(reordered_nodeset).to_aml_dict() == expected


def test_semantic_reverse_accepts_native_only_part19_dictionary_reference():
    document = CAEXFile.model_validate(
        {
            "FileName": "native-part19.aml",
            "SchemaVersion": "3.0",
            "InstanceHierarchy": [
                {
                    "Name": "Plant",
                    "InternalElement": [
                        {
                            "Name": "Machine",
                            "ID": "machine-1",
                            "Attribute": [
                                {
                                    "Name": "temperature",
                                    "RefSemantic": [
                                        {
                                            "CorrespondingAttributePath": (
                                                "https://example.org/semantic/temperature"
                                            )
                                        }
                                    ],
                                }
                            ],
                        }
                    ],
                }
            ],
        }
    )
    root = etree.fromstring(
        _xslt_nodeset(document, "2026-08-16").encode()
    )
    attribute = root.xpath(
        "./ua:UAVariable[ua:DisplayName='temperature']",
        namespaces=NS,
    )[0]
    exact_property = root.xpath(
        "./ua:UAVariable[ua:DisplayName='AMLRefSemantic_1']",
        namespaces=NS,
    )[0]
    property_node_id = exact_property.get("NodeId")
    for reference in attribute.xpath(
        "ua:References/ua:Reference[@ReferenceType='HasProperty']",
        namespaces=NS,
    ):
        if (reference.text or "").strip() == property_node_id:
            reference.getparent().remove(reference)
    root.remove(exact_property)

    recovered = CAEXFile.from_opcua_nodeset_xml(etree.tostring(root))

    assert recovered.instance_hierarchies[0].internal_elements[0].attributes[
        0
    ].ref_semantic[0].corresponding_attribute_path == (
        "https://example.org/semantic/temperature"
    )


def test_semantic_reverse_round_trips_internal_links_role_mappings_and_external_refs():
    document = CAEXFile.model_validate(
        {
            "FileName": "semantic-relations.aml",
            "SchemaVersion": "3.0",
            "ExternalReference": [
                {"Alias": "Vendor", "Path": "vendor-library.aml"}
            ],
            "InstanceHierarchy": [
                {
                    "Name": "Plant",
                    "InternalElement": [
                        {
                            "Name": "Assembly",
                            "ID": "assembly-1",
                            "ExternalInterface": [
                                {
                                    "Name": "PortA",
                                    "ID": "port-a",
                                    "RefBaseClassPath": "ConnectorLib/Port",
                                },
                                {
                                    "Name": "PortB",
                                    "ID": "port-b",
                                    "RefBaseClassPath": "ConnectorLib/Port",
                                },
                            ],
                            "InternalLink": [
                                {
                                    "Name": "Signal cable",
                                    "ID": "link-1",
                                    "Description": {"value": "Exact CAEX link"},
                                    "RefPartnerSideA": "assembly-1:PortA",
                                    "RefPartnerSideB": "assembly-1:PortB",
                                }
                            ],
                            "RoleRequirements": [
                                {
                                    "RefBaseRoleClassPath": "RoleLib/Controller",
                                    "MappingObject": {
                                        "AttributeNameMapping": [
                                            {
                                                "SystemUnitAttributeName": "speed",
                                                "RoleAttributeName": "setpoint",
                                            }
                                        ],
                                        "InterfaceIDMapping": [
                                            {
                                                "SystemUnitInterfaceID": "port-a",
                                                "RoleInterfaceID": "role-port",
                                            }
                                        ],
                                    },
                                }
                            ],
                        }
                    ],
                }
            ],
            "InterfaceClassLib": [
                {"Name": "ConnectorLib", "InterfaceClass": [{"Name": "Port"}]}
            ],
            "RoleClassLib": [
                {"Name": "RoleLib", "RoleClass": [{"Name": "Controller"}]}
            ],
        }
    )

    nodeset = _xslt_nodeset(document, "2026-08-16")
    root = etree.fromstring(nodeset.encode())

    assert root.xpath(
        "count(./ua:UAObject[ua:DisplayName='PortA']/ua:References/"
        "ua:Reference[@ReferenceType='HasAMLInternalLink'])",
        namespaces=NS,
    ) == 1.0
    assert root.xpath(
        "./ua:UAObject[ua:DisplayName='Signal cable']/ua:References/"
        "ua:Reference[@ReferenceType='HasProperty']",
        namespaces=NS,
    )
    assert root.xpath(
        "./ua:UAVariable[ua:DisplayName='AMLMappingObjectPresent']",
        namespaces=NS,
    )
    assert CAEXFile.from_opcua_nodeset_xml(nodeset).to_aml_dict() == (
        document.to_aml_dict()
    )


def test_semantic_reverse_round_trips_official_internal_link_fixture():
    aml = (REVERSE_FIXTURES / "9_ExtInt_IntLink.aml").read_bytes()
    expected = CAEXFile.from_aml_xml(aml).to_aml_dict()
    nodeset = patched_xslt_nodeset_xml(
        aml, publication_date="2026-08-16"
    )

    recovered = CAEXFile.from_opcua_nodeset_xml(nodeset).to_aml_dict()

    # Indentation-only text around nested legacy AdditionalInformation is not
    # part of its semantic content.
    for document in (expected, recovered):
        for information in document.get("AdditionalInformation", []):
            if information.get("value", "").strip() == "":
                information.pop("value", None)
    assert recovered == expected


def test_semantic_reverse_preserves_lexical_ids_and_change_modes():
    payload = deepcopy(_document().to_aml_dict())
    payload["InstanceHierarchy"][0]["ID"] = (
        "{3f827140-a771-4051-8559-a14d728a9421}"
    )
    payload["InstanceHierarchy"][0]["ChangeMode"] = "change"
    attribute = payload["InstanceHierarchy"][0]["InternalElement"][0][
        "Attribute"
    ][0]
    attribute["ID"] = "{9d237d43-e14a-4218-9826-15be984afb4e}"
    attribute["ChangeMode"] = "create"
    payload["RoleClassLib"][0]["ChangeMode"] = "change"
    document = CAEXFile.model_validate(payload)

    nodeset = _xslt_nodeset(document, "2026-08-16")

    assert CAEXFile.from_opcua_nodeset_xml(nodeset).to_aml_dict() == (
        document.to_aml_dict()
    )


@pytest.mark.parametrize(
    "fixture_name",
    [
        "0_EmptyFile_V2.1.aml",
        "2_IE.aml",
        "4_IH.aml",
        "5_SUC.aml",
        "8_AMLAttributeLibrary.aml",
        "10_RefSemantic.aml",
        "11_Constraints.aml",
    ],
)
def test_semantic_reverse_matches_easier_upstream_fixtures(fixture_name: str):
    aml = (REVERSE_FIXTURES / fixture_name).read_bytes()
    expected = CAEXFile.from_aml_xml(aml)
    nodeset = patched_xslt_nodeset_xml(
        aml, publication_date="2026-08-16"
    )

    recovered = CAEXFile.from_opcua_nodeset_xml(nodeset)

    assert recovered.to_aml_dict() == expected.to_aml_dict()


def test_semantic_reverse_serializes_reconstructed_aml_xml():
    aml = (REVERSE_FIXTURES / "2_IE.aml").read_bytes()
    nodeset = aml_xml_to_nodeset(
        aml,
        include_roundtrip=False,
        publication_date="2026-08-16",
    )

    reconstructed_xml = nodeset_to_aml_xml(nodeset)
    recovered = CAEXFile.from_aml_xml(reconstructed_xml)

    assert recovered.to_aml_dict() == CAEXFile.from_aml_xml(aml).to_aml_dict()


def test_forward_stylesheet_preserves_reversible_attribute_metadata():
    aml = (REVERSE_FIXTURES / "3_IE_Attribute.aml").read_bytes()
    root = patched_xslt_nodeset_element(aml, publication_date="2026-08-16")
    _validate_nodeset(root)

    attribute = root.xpath(
        "./ua:UAVariable[ua:DisplayName='New Attribute']",
        namespaces=NS,
    )[0]
    assert attribute.findtext(f"{{{UA_NODESET_NS}}}Documentation") == (
        "thisisthedescription"
    )

    expected_properties = {
        "AMLAttributeDataType": "xs:string",
        "AMLDefaultValue": "DefaultValueTest",
        "AMLUnit": "m",
    }
    property_nodes = {
        node.findtext(f"{{{UA_NODESET_NS}}}DisplayName"): node
        for node in root.xpath("./ua:UAVariable", namespaces=NS)
        if node.findtext(f"{{{UA_NODESET_NS}}}DisplayName")
        in expected_properties
    }
    assert set(property_nodes) == set(expected_properties)
    for property_name, expected_value in expected_properties.items():
        property_node = property_nodes[property_name]
        assert property_node.get("ParentNodeId") == attribute.get("NodeId")
        assert property_node.get("DataType") == "String"
        assert property_node.xpath(
            "ua:References/ua:Reference"
            "[@ReferenceType='HasTypeDefinition' and text()='PropertyType']",
            namespaces=NS,
        )
        assert "".join(property_node.xpath("ua:Value/*/text()", namespaces=NS)) == (
            expected_value
        )


def test_semantic_reverse_round_trips_upstream_attribute_fixture():
    aml = (REVERSE_FIXTURES / "3_IE_Attribute.aml").read_bytes()
    expected = CAEXFile.from_aml_xml(aml).to_aml_dict()
    nodeset = aml_xml_to_nodeset(
        aml,
        include_roundtrip=False,
        publication_date="2026-08-16",
    )

    recovered = CAEXFile.from_opcua_nodeset_xml(nodeset)

    assert recovered.to_aml_dict() == expected


def test_semantic_reverse_can_be_forced_when_embedded_source_exists():
    aml = (REVERSE_FIXTURES / "3_IE_Attribute.aml").read_bytes()
    nodeset = aml_xml_to_nodeset(
        aml,
        include_roundtrip=True,
        publication_date="2026-08-16",
    )

    source_recovered = CAEXFile.from_opcua_nodeset_xml(nodeset)
    semantic_recovered = CAEXFile.from_opcua_nodeset_xml(
        nodeset,
        prefer_embedded_source=False,
    )

    source_attribute = source_recovered.instance_hierarchies[0].internal_elements[0].attributes[0]
    semantic_attribute = semantic_recovered.instance_hierarchies[0].internal_elements[0].attributes[0]
    assert source_attribute.unit == "m"
    assert source_attribute.default_value == "DefaultValueTest"
    assert semantic_attribute == source_attribute


def test_semantic_reverse_preserves_exact_datatype_and_default_value_semantics():
    document = CAEXFile.model_validate(
        {
            "FileName": "reversible-attribute-metadata.aml",
            "SchemaVersion": "3.0",
            "InstanceHierarchy": [
                {
                    "Name": "Plant",
                    "InternalElement": [
                        {
                            "Name": "Machine",
                            "ID": "machine-1",
                            "Attribute": [
                                {
                                    "Name": "identifier",
                                    "Description": {"value": "Fallback identifier"},
                                    "AttributeDataType": "xs:ID",
                                    "DefaultValue": "unknown",
                                    "Unit": "asset-code",
                                },
                                {
                                    "Name": "integer",
                                    "AttributeDataType": "xs:integer",
                                },
                                {
                                    "Name": "date",
                                    "AttributeDataType": "xs:date",
                                },
                            ],
                        }
                    ],
                }
            ],
        }
    )
    nodeset = _xslt_nodeset(document, "2026-08-16")
    root = etree.fromstring(nodeset.encode())
    identifier = root.xpath(
        "./ua:UAVariable[ua:DisplayName='identifier']",
        namespaces=NS,
    )[0]

    assert identifier.find(f"{{{UA_NODESET_NS}}}Value") is None
    recovered = CAEXFile.from_opcua_nodeset_xml(nodeset)
    assert recovered.to_aml_dict() == document.to_aml_dict()


def test_semantic_reverse_recovers_canonical_scalar_and_nested_attributes():
    document = CAEXFile.model_validate(
        {
            "FileName": "scalar-attributes.aml",
            "SchemaVersion": "3.0",
            "InstanceHierarchy": [
                {
                    "Name": "Plant",
                    "InternalElement": [
                        {
                            "Name": "Machine",
                            "ID": "machine-1",
                            "Attribute": [
                                {
                                    "Name": "label",
                                    "AttributeDataType": "xs:string",
                                    "Value": "Mixer",
                                    "Attribute": [
                                        {
                                            "Name": "enabled",
                                            "AttributeDataType": "xs:boolean",
                                            "Value": "true",
                                        }
                                    ],
                                },
                                {
                                    "Name": "count",
                                    "AttributeDataType": "xs:int",
                                    "Value": "4",
                                },
                                {
                                    "Name": "ratio",
                                    "AttributeDataType": "xs:double",
                                    "Value": "1.5",
                                },
                            ],
                        }
                    ],
                }
            ],
        }
    )
    nodeset = document.to_opcua_nodeset_xml(
        include_roundtrip=False,
        publication_date="2026-08-16",
    )

    recovered = CAEXFile.from_opcua_nodeset_xml(nodeset)

    assert recovered.to_aml_dict() == document.to_aml_dict()


def test_round_trip_payload_integrity_is_verified():
    root = etree.fromstring(
        _document().to_opcua_nodeset_xml(include_roundtrip=True).encode()
    )
    payload = root.xpath(
        "./ua:Extensions/ua:Extension/amlrt:AutomationMLExport/"
        "amlrt:OriginalAutomationML",
        namespaces=NS,
    )[0]
    decoded = base64.b64decode(payload.text)
    payload.text = base64.b64encode(decoded + b" ").decode()

    with pytest.raises(OPCUAConversionError, match="integrity check"):
        CAEXFile.from_opcua_nodeset_xml(etree.tostring(root))


def test_constraint_reference_type_is_generated_correctly_by_stylesheet():
    payload = deepcopy(_document().to_aml_dict())
    payload["InstanceHierarchy"][0]["InternalElement"][0]["Attribute"][0][
        "Constraint"
    ] = [
        {
            "Name": "Allowed speeds",
            "NominalScaledType": {"RequiredValue": ["1500", "1600"]},
        }
    ]

    document = CAEXFile.model_validate(payload)
    root = _raw_nodeset(document)

    _validate_nodeset(root)
    assert not root.xpath(
        ".//ua:Reference[@ReferenceType='HasComponnent']", namespaces=NS
    )
    assert root.xpath(
        ".//ua:Reference[@ReferenceType='HasComponent']", namespaces=NS
    )
    assert CAEXFile.from_opcua_nodeset_xml(
        etree.tostring(root)
    ).to_aml_dict() == document.to_aml_dict()


def test_datatype_and_source_metadata_ids_are_generated_correctly_by_stylesheet():
    payload = deepcopy(_document().to_aml_dict())
    payload["InstanceHierarchy"][0]["InternalElement"][0]["Attribute"][0][
        "AttributeDataType"
    ] = "xs:ID"
    payload["SourceDocumentInformation"].append(
        {"OriginName": "Second tool", "OriginID": "second-tool"}
    )

    root = _raw_nodeset(CAEXFile.model_validate(payload))
    _validate_nodeset(root)
    node_ids = root.xpath("./ua:*[@NodeId]/@NodeId", namespaces=NS)

    assert len(node_ids) == len(set(node_ids))
    assert root.xpath(
        "./ua:UAVariable[ua:DisplayName='speed']/@DataType", namespaces=NS
    ) == ["String"]


def test_semantic_reverse_merges_numbered_source_document_properties():
    payload = deepcopy(_document().to_aml_dict())
    payload["InstanceHierarchy"] = []
    payload["RoleClassLib"] = []
    payload["SystemUnitClassLib"] = []
    payload["SourceDocumentInformation"].append(
        {"OriginName": "Second tool", "OriginID": "second-tool"}
    )
    document = CAEXFile.model_validate(payload)
    nodeset = document.to_opcua_nodeset_xml(
        include_roundtrip=False,
        publication_date="2026-08-16",
    )

    recovered = CAEXFile.from_opcua_nodeset_xml(nodeset)

    assert recovered.to_aml_dict() == document.to_aml_dict()


def test_aliased_class_path_is_resolved_by_stylesheet():
    aml = b"""<?xml version="1.0" encoding="UTF-8"?>
    <CAEXFile xmlns="http://www.dke.de/CAEX" FileName="external.aml" SchemaVersion="3.0">
      <InstanceHierarchy Name="Plant">
        <InternalElement Name="Machine" ID="machine-1">
          <ExternalInterface Name="Port" ID="port-1"
            RefBaseClassPath="ExternalAlias@ConnectorLib/BaseConnector/PortConnector"/>
        </InternalElement>
      </InstanceHierarchy>
      <InterfaceClassLib Name="ConnectorLib">
        <InterfaceClass Name="BaseConnector">
          <InterfaceClass Name="PortConnector"/>
        </InterfaceClass>
      </InterfaceClassLib>
    </CAEXFile>
    """

    root = patched_xslt_nodeset_element(aml, publication_date="2026-08-16")
    _validate_nodeset(root)
    targets = root.xpath(
        ".//ua:UAObject[ua:DisplayName='Port']/ua:References/"
        "ua:Reference[@ReferenceType='HasTypeDefinition']/text()",
        namespaces=NS,
    )

    assert len(targets) == 1
    assert targets[0].endswith(";s=PortConnector")
    assert "/" not in targets[0]


def test_unknown_attribute_datatype_is_rejected_instead_of_repaired():
    payload = deepcopy(_document().to_aml_dict())
    payload["InstanceHierarchy"][0]["InternalElement"][0]["Attribute"][0][
        "AttributeDataType"
    ] = "xs:notAType"

    root = _raw_nodeset(CAEXFile.model_validate(payload))

    with pytest.raises(OPCUAConversionError, match="unresolved DataType"):
        _validate_nodeset(root)


def test_xslt_baseline_maps_xml_token_to_string_not_opcua_guid():
    payload = deepcopy(_document().to_aml_dict())
    payload["InstanceHierarchy"][0]["InternalElement"][0]["Attribute"][0][
        "AttributeDataType"
    ] = "xs:token"

    root = _raw_nodeset(CAEXFile.model_validate(payload))
    data_types = root.xpath(
        ".//ua:UAVariable[ua:DisplayName='speed']/@DataType",
        namespaces=NS,
    )

    assert data_types == ["String"]


def test_dtd_and_entity_input_is_rejected():
    malicious = """<!DOCTYPE CAEXFile [<!ENTITY xxe SYSTEM 'file:///secret'>]>
    <CAEXFile xmlns="http://www.dke.de/CAEX" FileName="x.aml" SchemaVersion="3.0"/>
    """

    from automationml.opcua import aml_xml_to_nodeset

    with pytest.raises(OPCUAConversionError, match="DTD and entity"):
        aml_xml_to_nodeset(malicious)
