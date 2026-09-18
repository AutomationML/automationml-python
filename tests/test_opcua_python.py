from pathlib import Path

from lxml import etree
import pytest
from pydantic import ValidationError

from automationml import CAEXFile
from automationml.opcua import (
    OPCUAConversionError,
    ROUNDTRIP_NS,
    UA_NODESET_NS,
    aml_xml_to_nodeset,
    compare_aml_semantics,
)
from automationml.opcua_mapping import (
    DEFAULT_MAPPING_PROFILE,
    UnsupportedDataTypeError,
    canonical_internal_link_identity,
)
from automationml.opcua_nodeset import (
    UANode,
    UANodeSet,
    UANodeSetBuilder,
    UAReference,
)


FIXTURES = Path(__file__).parent / "fixtures" / "opcua_reverse"
NS = {"ua": UA_NODESET_NS, "amlrt": ROUNDTRIP_NS}


def test_typed_nodeset_model_rejects_duplicate_node_ids():
    node = UANode(
        node_class="UAObject",
        node_id="ns=1;s=duplicate",
        browse_name="1:Duplicate",
        display_name="Duplicate",
    )

    with pytest.raises(ValidationError, match="Duplicate OPC UA NodeIds"):
        UANodeSet(nodes=[node, node.model_copy(deep=True)])


def test_typed_nodeset_is_immutable_and_builder_is_explicit_mutation_boundary():
    node = UANode(
        node_class="UAObject",
        node_id="ns=1;s=motor",
        browse_name="1:Motor",
        display_name="Motor",
    )
    builder = UANodeSetBuilder(
        namespace_uris=["urn:example:model"],
        aliases={"HasComponent": "i=47"},
    )
    builder.add_node(node)
    builder.add_reference(
        node,
        UAReference(reference_type="HasComponent", target="ns=1;s=child"),
    )
    nodeset = builder.build()

    assert nodeset.outgoing("ns=1;s=motor", "HasComponent")[0].target == (
        "ns=1;s=child"
    )
    with pytest.raises(ValidationError, match="frozen"):
        nodeset.nodes[0].display_name = "Changed"
    with pytest.raises(TypeError, match="immutable"):
        nodeset.aliases["HasProperty"] = "i=46"


def test_shared_datatype_profile_has_one_canonical_inverse():
    registry = DEFAULT_MAPPING_PROFILE.data_types

    assert registry.from_aml("xs:integer").ua_node_id == "i=6"
    assert registry.from_ua("i=6").canonical_aml_type == "xs:int"
    assert registry.from_aml("xs:token").ua_node_id == "i=12"
    assert registry.from_ua("i=12").canonical_aml_type == "xs:string"
    with pytest.raises(UnsupportedDataTypeError):
        registry.from_ua("i=14")  # OPC UA Guid, not XML Schema token.


@pytest.mark.parametrize(
    "fixture_name",
    [
        "0_EmptyFile_V2.1.aml",
        "2_IE.aml",
        "3_IE_Attribute.aml",
        "4_IH.aml",
        "5_SUC.aml",
    ],
)
def test_python_mvp_round_trips_simple_fixtures_without_embedded_aml(fixture_name):
    source = (FIXTURES / fixture_name).read_bytes()
    expected = CAEXFile.from_aml_xml(source)

    nodeset = aml_xml_to_nodeset(
        source,
        include_roundtrip=False,
        publication_date="2026-08-17",
    )
    recovered = CAEXFile.from_opcua_nodeset_xml(nodeset)

    assert recovered.to_aml_dict() == expected.to_aml_dict()
    root = etree.fromstring(nodeset.encode())
    metadata = root.xpath(
        "./ua:Extensions/ua:Extension/amlrt:AutomationMLExport",
        namespaces=NS,
    )[0]
    assert metadata.get("mapping") == "automationml-python"
    assert metadata.get("mappingVersion") == "automationml-python-bidirectional-v1"
    assert metadata.get("roundTrip") == "none"
    assert not root.xpath(".//amlrt:OriginalAutomationML", namespaces=NS)


def test_public_roundtrip_result_is_inspectable_and_uses_no_source_payload():
    document = CAEXFile.from_aml_xml(
        (FIXTURES / "3_IE_Attribute.aml").read_bytes()
    )

    result = document.round_trip_opcua(publication_date="2026-08-17")

    assert result.semantically_equivalent is True
    assert result.mapping_profile == "strict-implicit-v1"
    assert result.assert_equivalent().to_aml_dict() == document.to_aml_dict()
    assert result.nodeset.node("ns=1;s=CAEXFile").display_name == (
        document.file_name
    )
    assert not etree.fromstring(result.nodeset_xml.encode()).xpath(
        ".//amlrt:OriginalAutomationML", namespaces=NS
    )


def test_semantic_comparison_returns_pydantic_json_pointer_differences():
    source = CAEXFile.from_aml_xml((FIXTURES / "2_IE.aml").read_bytes())
    recovered = source.model_copy(update={"file_name": "renamed.aml"})

    differences = compare_aml_semantics(source, recovered)

    assert len(differences) == 1
    assert differences[0].path == "/FileName"
    assert differences[0].kind == "changed"
    assert differences[0].source_value == source.file_name
    assert differences[0].recovered_value == "renamed.aml"


def test_opcua_authored_node_ids_round_trip_without_generated_id_assumptions():
    document = CAEXFile.from_aml_xml(
        (FIXTURES / "3_IE_Attribute.aml").read_bytes()
    )
    generated = document.to_opcua_nodeset(publication_date="2026-08-17")
    remapped_ids = {
        node.node_id: f"ns=1;s=authored:{position}"
        for position, node in enumerate(generated.nodes, start=1)
        if node.node_id.startswith("ns=1;")
    }
    authored_nodes = []
    for node in generated.nodes:
        payload = node.model_dump()
        payload["node_id"] = remapped_ids.get(node.node_id, node.node_id)
        if node.parent_node_id is not None:
            payload["parent_node_id"] = remapped_ids.get(
                node.parent_node_id,
                node.parent_node_id,
            )
        payload["references"] = [
            {
                **reference.model_dump(),
                "target": remapped_ids.get(reference.target, reference.target),
            }
            for reference in node.references
        ]
        authored_nodes.append(UANode.model_validate(payload))
    authored = UANodeSet(
        namespace_uris=generated.namespace_uris,
        models=generated.models,
        aliases=dict(generated.aliases),
        nodes=authored_nodes,
    )

    recovered = authored.to_automationml()
    result = authored.round_trip_automationml(publication_date="2026-08-17")

    assert recovered.to_aml_dict() == document.to_aml_dict()
    assert CAEXFile.from_opcua_nodeset(authored).to_aml_dict() == (
        document.to_aml_dict()
    )
    assert result.semantically_equivalent is True
    assert result.differences == ()
    assert result.assert_equivalent() == result.regenerated_nodeset
    assert result.source_nodeset != result.regenerated_nodeset


def test_generated_xml_parses_back_into_the_typed_nodeset_graph():
    document = CAEXFile.from_aml_xml((FIXTURES / "2_IE.aml").read_bytes())
    native_graph = document.to_opcua_nodeset(publication_date="2026-08-17")
    xml = document.to_opcua_nodeset_xml(
        publication_date="2026-08-17",
        include_roundtrip=False,
    )

    parsed = UANodeSet.from_xml(xml)
    reparsed = UANodeSet.from_xml(parsed.to_xml())

    assert reparsed == parsed
    assert parsed == native_graph
    assert parsed.models[0].model_uri.endswith("2_IE.aml")


def test_python_mvp_uses_plain_typed_default_value_and_unit_properties():
    source = (FIXTURES / "3_IE_Attribute.aml").read_bytes()
    root = etree.fromstring(
        aml_xml_to_nodeset(
            source,
            include_roundtrip=False,
            publication_date="2026-08-17",
        ).encode()
    )
    attribute = root.xpath(
        "./ua:UAVariable[ua:DisplayName='New Attribute']",
        namespaces=NS,
    )[0]
    default_value = root.xpath(
        "./ua:UAVariable[ua:DisplayName='DefaultValue']",
        namespaces=NS,
    )[0]
    unit = root.xpath(
        "./ua:UAVariable[ua:DisplayName='Unit']",
        namespaces=NS,
    )[0]

    assert attribute.get("DataType") == "String"
    assert "".join(attribute.xpath("ua:Value/*/text()", namespaces=NS)) == "ValueTest"
    assert default_value.get("DataType") == attribute.get("DataType")
    assert "".join(default_value.xpath("ua:Value/*/text()", namespaces=NS)) == (
        "DefaultValueTest"
    )
    assert "".join(unit.xpath("ua:Value/*/text()", namespaces=NS)) == "m"
    assert not root.xpath(
        "./ua:UAVariable[ua:DisplayName='AMLDefaultValue' or "
        "ua:DisplayName='AMLUnit']",
        namespaces=NS,
    )


def test_python_mapper_materializes_part19_dictionary_entry_objects():
    document = CAEXFile.model_validate(
        {
            "FileName": "semantics.aml",
            "SchemaVersion": "3.0",
            "InstanceHierarchy": [
                {
                    "Name": "Plant",
                    "InternalElement": [
                        {
                            "Name": "Device",
                            "ID": "device-1",
                            "Attribute": [
                                {
                                    "Name": "semantic",
                                    "AttributeDataType": "xs:string",
                                    "RefSemantic": [
                                        {
                                            "CorrespondingAttributePath": (
                                                "0173/1///#02-TEST#001"
                                            )
                                        },
                                        {"CorrespondingAttributePath": "local/path"},
                                        {
                                            "CorrespondingAttributePath": (
                                                "urn:example:temperature"
                                            )
                                        },
                                    ],
                                }
                            ],
                        }
                    ],
                }
            ],
        }
    )

    xml = document.to_opcua_nodeset_xml(
        include_roundtrip=False,
        publication_date="2026-08-17",
    )
    root = etree.fromstring(xml.encode())
    attribute = root.xpath(
        "./ua:UAVariable[ua:DisplayName='semantic']",
        namespaces=NS,
    )[0]
    targets = attribute.xpath(
        "ua:References/ua:Reference[@ReferenceType='HasDictionaryEntry']/text()",
        namespaces=NS,
    )

    assert len(targets) == 2
    for target, expected_type in zip(
        targets,
        ("IrdiDictionaryEntryType", "UriDictionaryEntryType"),
        strict=True,
    ):
        entry = root.xpath(
            "./ua:UAObject[@NodeId=$target]",
            namespaces=NS,
            target=target,
        )[0]
        assert entry.get("ParentNodeId") == "i=17594"
        assert entry.xpath(
            "ua:References/ua:Reference[@ReferenceType='HasTypeDefinition' "
            "and text()=$expected]",
            namespaces=NS,
            expected=expected_type,
        )
        assert entry.xpath(
            "ua:References/ua:Reference[@ReferenceType='HasComponent' "
            "and @IsForward='false' and text()='i=17594']",
            namespaces=NS,
        )
        assert not root.xpath(
            "./ua:UAVariable[ua:DisplayName='RefSemantic_1' or "
            "ua:DisplayName='RefSemantic_3']",
            namespaces=NS,
        )
        assert root.xpath(
            "./ua:UAVariable[ua:DisplayName='RefSemantic_2']",
            namespaces=NS,
        )
    assert CAEXFile.from_opcua_nodeset_xml(xml).to_aml_dict() == (
        document.to_aml_dict()
    )
    references = attribute.find(f"{{{UA_NODESET_NS}}}References")
    assert references is not None
    references[:] = reversed(references)
    assert CAEXFile.from_opcua_nodeset_xml(
        etree.tostring(root, encoding="unicode")
    ).to_aml_dict() == document.to_aml_dict()


def test_python_mvp_uses_native_role_edge_with_contextual_reverse_rule():
    document = CAEXFile.model_validate(
        {
            "FileName": "roles.aml",
            "SchemaVersion": "3.0",
            "InstanceHierarchy": [
                {
                    "Name": "Plant",
                    "InternalElement": [
                        {
                            "Name": "Motor",
                            "ID": "motor-1",
                            "RoleRequirements": [
                                {"RefBaseRoleClassPath": "Roles/Drive"}
                            ],
                        }
                    ],
                }
            ],
            "RoleClassLib": [
                {"Name": "Roles", "RoleClass": [{"Name": "Drive"}]}
            ],
        }
    )

    nodeset = document.to_opcua_nodeset_xml(
        include_roundtrip=False,
        publication_date="2026-08-17",
    )
    root = etree.fromstring(nodeset.encode())
    motor = root.xpath(
        "./ua:UAObject[ua:DisplayName='Motor']",
        namespaces=NS,
    )[0]

    assert motor.xpath(
        "ua:References/ua:Reference[@ReferenceType='HasAMLRoleReference']",
        namespaces=NS,
    )
    assert not root.xpath(
        "./ua:UAObject[starts-with(ua:DisplayName, 'AMLRoleRequirements_')]",
        namespaces=NS,
    )
    assert CAEXFile.from_opcua_nodeset_xml(nodeset).to_aml_dict() == (
        document.to_aml_dict()
    )


def test_python_mapper_uses_typed_native_constraints_without_embedded_caex():
    document = CAEXFile.model_validate(
        {
            "FileName": "constraints.aml",
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
                                    "Name": "mode",
                                    "AttributeDataType": "xs:string",
                                    "Constraint": [
                                        {
                                            "Name": "Allowed modes",
                                            "NominalScaledType": {
                                                "RequiredValue": [
                                                    "Out",
                                                    "In",
                                                    "InOut",
                                                ]
                                            },
                                        }
                                    ],
                                },
                                {
                                    "Name": "temperature",
                                    "AttributeDataType": "xs:int",
                                    "Constraint": [
                                        {
                                            "Name": "Operating range",
                                            "OrdinalScaledType": {
                                                "RequiredMinValue": "-20",
                                                "RequiredValue": "20",
                                                "RequiredMaxValue": "80",
                                            },
                                        }
                                    ],
                                },
                                {
                                    "Name": "note",
                                    "AttributeDataType": "xs:string",
                                    "Constraint": [
                                        {
                                            "Name": "Human rule",
                                            "UnknownType": {
                                                "Requirements": "approved by operator"
                                            },
                                        }
                                    ],
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
        publication_date="2026-08-17",
    )
    root = etree.fromstring(nodeset.encode())
    constraints = {
        node.findtext(f"{{{UA_NODESET_NS}}}DisplayName"): node
        for node in root.xpath(
            "./ua:UAVariable[ua:References/ua:Reference["
            "@ReferenceType='HasTypeDefinition' and "
            "(text()='NominalScaledConstraint' or "
            "text()='OrdinalScaledConstraint' or text()='UnknownConstraint')]]",
            namespaces=NS,
        )
    }

    assert set(constraints) == {
        "Allowed modes",
        "Operating range",
        "Human rule",
    }
    assert not root.xpath(
        ".//ua:Value/*[starts-with(normalize-space(text()), '<Constraint')]",
        namespaces=NS,
    )
    assert not root.xpath(
        ".//ua:Reference[@ReferenceType='HasConstraint']",
        namespaces=NS,
    )
    temperature_components = root.xpath(
        "./ua:UAVariable[ua:DisplayName='RequiredMinValue' or "
        "ua:DisplayName='RequiredMaxValue'][@DataType='Int32']",
        namespaces=NS,
    )
    assert len(temperature_components) == 2
    assert all(
        component.xpath(
            "ua:References/ua:Reference["
            "@ReferenceType='HasTypeDefinition' and "
            "text()='BaseDataVariableType']",
            namespaces=NS,
        )
        for component in temperature_components
    )

    recovered = CAEXFile.from_opcua_nodeset_xml(nodeset)
    recovered_attributes = recovered.instance_hierarchies[0].internal_elements[0].attributes
    nominal_values = recovered_attributes[0].constraint[0].nominal_scaled_type.required_values
    assert nominal_values == ["In", "InOut", "Out"]
    assert recovered_attributes[1].constraint[0].ordinal_scaled_type.required_min_value == "-20"
    assert recovered_attributes[2].constraint[0].unknown_type.requirements == (
        "approved by operator"
    )


def test_python_mapper_reifies_only_role_relationships_with_real_payload():
    document = CAEXFile.model_validate(
        {
            "FileName": "role-payload.aml",
            "SchemaVersion": "3.0",
            "InstanceHierarchy": [
                {
                    "Name": "Plant",
                    "InternalElement": [
                        {
                            "Name": "Motor",
                            "ID": "motor-1",
                            "RoleRequirements": [
                                {
                                    "RefBaseRoleClassPath": "Roles/Drive",
                                    "Description": {"value": "Configured drive"},
                                    "Version": {"value": "1.0"},
                                    "Attribute": [
                                        {
                                            "Name": "setpoint",
                                            "AttributeDataType": "xs:int",
                                            "Value": "1500",
                                        }
                                    ],
                                    "MappingObject": {
                                        "AttributeNameMapping": [
                                            {
                                                "SystemUnitAttributeName": "speed",
                                                "RoleAttributeName": "setpoint",
                                            }
                                        ],
                                        "InterfaceIDMapping": [
                                            {
                                                "SystemUnitInterfaceID": "motor-port",
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
            "RoleClassLib": [
                {"Name": "Roles", "RoleClass": [{"Name": "Drive"}]}
            ],
        }
    )

    nodeset = document.to_opcua_nodeset_xml(
        include_roundtrip=False,
        publication_date="2026-08-17",
    )
    root = etree.fromstring(nodeset.encode())
    relationship = root.xpath(
        "./ua:UAObject[ua:DisplayName='RoleRequirements']",
        namespaces=NS,
    )[0]
    assert relationship.xpath(
        "ua:References/ua:Reference[@ReferenceType='HasAMLRoleReference']",
        namespaces=NS,
    )
    assert root.xpath(
        "./ua:UAObject[ua:DisplayName='MappingObject']",
        namespaces=NS,
    )
    assert not root.xpath(
        "./ua:UAVariable[ua:DisplayName='AMLMappingObjectPresent' or "
        "ua:DisplayName='AMLRefBaseRoleClassPath']",
        namespaces=NS,
    )

    recovered = CAEXFile.from_opcua_nodeset_xml(nodeset)
    assert recovered.to_aml_dict() == document.to_aml_dict()


def test_python_mapper_uses_partner_a_directed_native_internal_link():
    document = CAEXFile.model_validate(
        {
            "FileName": "link.aml",
            "SchemaVersion": "3.0",
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
                                    "Name": "L1",
                                    "ID": "legacy-link-id",
                                    "RefPartnerSideA": "assembly-1:A",
                                    "RefPartnerSideB": "assembly-1:PortB",
                                }
                            ],
                        }
                    ],
                }
            ],
            "InterfaceClassLib": [
                {
                    "Name": "ConnectorLib",
                    "InterfaceClass": [{"Name": "Port"}],
                }
            ],
        }
    )

    # The deliberately broken PartnerA spelling must fail before XML emission.
    with pytest.raises(OPCUAConversionError, match="unknown partner 'assembly-1:A'"):
        document.to_opcua_nodeset_xml(publication_date="2026-08-17")

    payload = document.to_aml_dict()
    payload["InstanceHierarchy"][0]["InternalElement"][0]["InternalLink"][0][
        "RefPartnerSideA"
    ] = "assembly-1:PortA"
    document = CAEXFile.model_validate(payload)
    nodeset = document.to_opcua_nodeset_xml(
        include_roundtrip=False,
        publication_date="2026-08-17",
    )
    root = etree.fromstring(nodeset.encode())
    port_a = root.xpath(
        "./ua:UAObject[ua:DisplayName='PortA']",
        namespaces=NS,
    )[0]
    port_b = root.xpath(
        "./ua:UAObject[ua:DisplayName='PortB']",
        namespaces=NS,
    )[0]
    assert port_a.xpath(
        "ua:References/ua:Reference[@ReferenceType='HasAMLInternalLink' "
        "and text()=$target]",
        namespaces=NS,
        target=port_b.get("NodeId"),
    )
    assert not root.xpath(
        "./ua:UAObject[starts-with(ua:DisplayName, 'InternalLink_')]",
        namespaces=NS,
    )

    recovered = CAEXFile.from_opcua_nodeset_xml(nodeset)
    link = recovered.instance_hierarchies[0].internal_elements[0].internal_links[0]
    expected_name, expected_id = canonical_internal_link_identity(
        "assembly-1:PortA",
        "assembly-1:PortB",
    )
    assert (link.name, link.id) == (expected_name, expected_id)
    assert link.ref_partner_side_a == "assembly-1:PortA"
    assert link.ref_partner_side_b == "assembly-1:PortB"
