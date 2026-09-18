from __future__ import annotations

import json
from itertools import count
from pathlib import Path

import pytest
import xmlschema

from automationml import (
    CAEXFile,
    ChangeSetError,
    ConflictAction,
    ExternalReference,
    FileSystemResolver,
    InstanceHierarchy,
    InterfaceClass,
    InternalElement,
    InternalLink,
    LegacyConversionError,
    LegacyConversionWarning,
    MergePolicy,
    SourceDocumentInformation,
    SystemUnitClassLib,
    SystemUnitFamily,
    XmlExtensionNode,
    attribute,
    merge_documents,
    resolve_external_references,
)


def _source() -> SourceDocumentInformation:
    return SourceDocumentInformation(
        origin_name="tests",
        origin_id="tests",
        origin_version="1",
        last_writing_date_time="2026-01-01T00:00:00Z",
    )


def test_additional_information_preserves_mixed_namespaced_xml_and_json():
    xml = """<CAEXFile xmlns="http://www.dke.de/CAEX" xmlns:v="urn:vendor"
        FileName="extension.aml" SchemaVersion="3.0">
      <SourceDocumentInformation OriginName="tests" OriginID="tests"
        OriginVersion="1" LastWritingDateTime="2026-01-01T00:00:00Z" />
      <AdditionalInformation v:code="A">before<v:Item n="1">inside</v:Item>after</AdditionalInformation>
    </CAEXFile>"""

    document = CAEXFile.from_aml_xml(xml)
    payload = document.to_aml_dict()
    info = payload["AdditionalInformation"][0]
    assert info["$xml"]["Attributes"]["{urn:vendor}code"] == "A"
    assert info["$xml"]["Children"][0]["Name"] == "{urn:vendor}Item"

    from_json = CAEXFile.from_aml_json(document.to_aml_json())
    reparsed = CAEXFile.from_aml_xml(from_json.to_aml_xml(pretty=False))
    assert reparsed.to_aml_dict() == document.to_aml_dict()


def test_xml_rejects_unknown_caex_structure_and_doctype():
    with pytest.raises(ValueError, match="only allowed inside AdditionalInformation"):
        CAEXFile.from_aml_xml(
            '<CAEXFile xmlns="http://www.dke.de/CAEX" FileName="x" SchemaVersion="3.0"><Mystery/></CAEXFile>'
        )
    with pytest.raises(ValueError, match="Unknown CAEX attribute"):
        CAEXFile.from_aml_xml(
            '<CAEXFile xmlns="http://www.dke.de/CAEX" FileName="x" '
            'SchemaVersion="3.0" vendorFlag="true"/>'
        )


def test_generated_json_schema_describes_structured_extension_xml():
    schema = json.loads(Path("schemas/automationml.caex3.schema.json").read_text("utf-8"))
    additional = schema["$defs"]["AdditionalInformation"]
    assert additional["properties"]["$xml"]["anyOf"][0]["$ref"].endswith(
        "/XmlExtensionPayload"
    )
    assert "Children" in schema["$defs"]["XmlExtensionPayload"]["properties"]


def test_opcua_roundtrip_retains_structured_additional_information():
    document = CAEXFile.from_aml_xml(
        """<CAEXFile xmlns="http://www.dke.de/CAEX" xmlns:v="urn:vendor"
        FileName="extension.aml" SchemaVersion="3.0">
        <SourceDocumentInformation OriginName="tests" OriginID="tests"
          OriginVersion="1" LastWritingDateTime="2026-01-01T00:00:00Z"/>
        <AdditionalInformation v:code="A">before<v:Item>inside</v:Item>after</AdditionalInformation>
        </CAEXFile>"""
    )
    recovered = CAEXFile.from_opcua_nodeset_xml(document.to_opcua_nodeset_xml())
    assert (
        recovered.additional_information[0].to_aml_dict(prune_empty=False)
        == document.additional_information[0].to_aml_dict(prune_empty=False)
    )
    with pytest.raises(ValueError, match="DTD"):
        CAEXFile.from_aml_xml(
            '<!DOCTYPE x [<!ENTITY y "z">]><CAEXFile FileName="x" SchemaVersion="3.0"/>'
        )


def _class_document() -> CAEXFile:
    return CAEXFile(
        file_name="classes.aml",
        source_document_information=[_source()],
        system_unit_class_libs=[
            SystemUnitClassLib(
                name="Equipment",
                system_unit_classes=[
                    SystemUnitFamily(
                        name="BaseMotor",
                        attributes=[attribute("speed", "1000")],
                        external_interfaces=[InterfaceClass(id="power-old", name="Power")],
                        internal_links=[
                            InternalLink(
                                id="link-old",
                                name="Loop",
                                ref_partner_side_a="power-old",
                                ref_partner_side_b="power-old",
                            )
                        ],
                    ),
                    SystemUnitFamily(
                        name="ServoMotor",
                        ref_base_class_path="Equipment/BaseMotor",
                        attributes=[attribute("speed", "2000"), attribute("torque", "5")],
                    ),
                ],
            )
        ],
        instance_hierarchies=[
            InstanceHierarchy(
                name="Plant",
                internal_elements=[
                    InternalElement(
                        id="motor-1",
                        name="M1",
                        ref_base_system_unit_path="Equipment/ServoMotor",
                    )
                ],
            )
        ],
    )


def test_query_reverse_relations_and_materialized_instantiation():
    document = _class_document()
    query = document.query()
    base = query.find_by_path("Equipment/BaseMotor")
    assert [item.name for item in query.derived_classes(base.aml_path)] == ["ServoMotor"]
    assert [item.name for item in query.instances_of(base.aml_path)] == ["M1"]
    assert any(edge.relation == "base-class" for edge in query.references_to(base))

    sequence = count(1)
    instance = document.instantiate_system_unit_class(
        "Equipment/ServoMotor",
        name="M2",
        id="root-new",
        id_factory=lambda: f"generated-{next(sequence)}",
    )
    assert instance.id == "root-new"
    assert {item.name: item.value for item in instance.attributes} == {
        "speed": "2000",
        "torque": "5",
    }
    assert instance.external_interfaces[0].id.startswith("generated-")
    assert instance.internal_links[0].ref_partner_side_a == instance.external_interfaces[0].id


def test_query_is_a_snapshot_and_descendants_accept_source_objects():
    document = _class_document()
    source_class = document.system_unit_class_libs[0].system_unit_classes[0]
    query = document.query()
    source_class.name = "MutatedAfterSnapshot"
    document.system_unit_class_libs[0].system_unit_classes[1].ref_base_class_path = None

    assert query.find_by_path("Equipment/BaseMotor").name == "BaseMotor"
    assert [item.name for item in query.derived_classes("Equipment/BaseMotor")] == [
        "ServoMotor"
    ]
    assert {item.name for item in query.descendants(source_class)} >= {"speed", "Power"}


def test_legacy_import_upgrades_metadata_roles_and_link_partners():
    legacy = """<CAEXFile xmlns:v="urn:vendor" FileName="legacy.aml" SchemaVersion="2.15">
      <AdditionalInformation><WriterHeader><WriterName>Tool</WriterName><WriterID>tool</WriterID>
      <WriterVersion>1</WriterVersion><LastWritingDateTime>2020-01-01T00:00:00Z</LastWritingDateTime>
      </WriterHeader><v:Other keep="yes"/></AdditionalInformation>
      <InstanceHierarchy Name="Plant"><InternalElement Name="A" ID="a">
        <ExternalInterface Name="P" ID="p"/>
        <SupportedRoleClass RefRoleClassPath="Roles/Asset"/>
        <InternalLink Name="L" RefPartnerSideA="a:P" RefPartnerSideB="a:P"/>
      </InternalElement></InstanceHierarchy><RoleClassLib Name="Roles"><RoleClass Name="Asset"/></RoleClassLib>
    </CAEXFile>"""

    result = CAEXFile.import_aml_xml(legacy)
    assert result.converted and result.source_schema_version == "2.15"
    assert result.document.schema_version == "3.0"
    element = result.document.instance_hierarchies[0].internal_elements[0]
    assert element.role_requirements[0].ref_base_role_class_path == "Roles/Asset"
    assert element.internal_links[0].ref_partner_side_a == "p"
    assert result.document.source_document_information[0].origin_name == "Tool"
    assert result.document.additional_information[0].xml.children[0].name == "{urn:vendor}Other"
    with pytest.warns(LegacyConversionWarning):
        assert CAEXFile.from_aml_xml(legacy).schema_version == "3.0"


def test_legacy_import_rejects_input_invalid_against_pinned_schema():
    with pytest.raises(LegacyConversionError, match="pinned schema"):
        CAEXFile.import_aml_xml(
            '<CAEXFile FileName="invalid.aml" SchemaVersion="2.15" Bogus="x"/>'
        )


def test_legacy_import_normalizes_mirror_content_like_csharp_upgrader():
    legacy = """<CAEXFile FileName="mirror.aml" SchemaVersion="2.15">
      <InstanceHierarchy Name="Plant">
        <InternalElement Name="Master" ID="master"><Attribute Name="same"/></InternalElement>
        <InternalElement Name="Mirror" ID="mirror" RefBaseSystemUnitPath="master">
          <Attribute Name="same"/><Attribute Name="moved"/>
          <ExternalInterface Name="Port" ID="port"/>
          <InternalElement Name="Child" ID="child"/>
        </InternalElement>
      </InstanceHierarchy>
    </CAEXFile>"""
    result = CAEXFile.import_aml_xml(legacy)
    master, mirror = result.document.instance_hierarchies[0].internal_elements
    assert [item.name for item in master.attributes] == ["same", "moved"]
    assert [item.name for item in master.external_interfaces] == ["Port"]
    assert [item.name for item in master.internal_elements] == ["Child"]
    assert not mirror.attributes and not mirror.external_interfaces and not mirror.internal_elements
    assert any(issue.code == "mirror-content-normalized" for issue in result.issues)


def test_legacy_import_materializes_role_interfaces_and_converts_name_mappings():
    legacy = """<CAEXFile FileName="mapping.aml" SchemaVersion="2.15">
      <InstanceHierarchy Name="Plant"><InternalElement Name="A" ID="a">
        <ExternalInterface Name="SystemPort"/>
        <SupportedRoleClass RefRoleClassPath="Roles/Asset"><MappingObject>
          <AttributeNameMapping SystemUnitAttributeName="group.value"
            RoleAttributeName="role.value"/>
          <InterfaceNameMapping SystemUnitInterfaceName="SystemPort"
            RoleInterfaceName="RolePort"/>
        </MappingObject></SupportedRoleClass>
      </InternalElement></InstanceHierarchy>
      <RoleClassLib Name="Roles"><RoleClass Name="Asset">
        <Attribute Name="roleValue"/>
        <ExternalInterface Name="RolePort" ID="role-class-port"/>
      </RoleClass></RoleClassLib>
    </CAEXFile>"""
    result = CAEXFile.import_aml_xml(legacy)
    element = result.document.instance_hierarchies[0].internal_elements[0]
    requirement = element.role_requirements[0]
    assert [item.name for item in requirement.attributes] == ["roleValue"]
    assert requirement.external_interfaces[0].id != "role-class-port"
    mapping = requirement.mapping_object
    assert mapping.attribute_name_mapping[0].system_unit_attribute_name == "group/value"
    assert mapping.interface_id_mapping[0].system_unit_interface_id == element.external_interfaces[0].id
    assert mapping.interface_id_mapping[0].role_interface_id == requirement.external_interfaces[0].id



def test_legacy_import_reports_unresolved_base_role_class_without_raising():
    """A 2.15 document may derive from a standard library it does not carry.

    Migration stays non-destructive: the resolvable part of the inheritance
    chain is still materialized, the gap is reported as a warning issue, and
    the document remains loadable and inspectable.
    """

    legacy = """<CAEXFile FileName="external-base.aml" SchemaVersion="2.15">
      <InstanceHierarchy Name="Plant"><InternalElement Name="A" ID="a">
        <SupportedRoleClass RefRoleClassPath="Roles/Robot"/>
      </InternalElement></InstanceHierarchy>
      <RoleClassLib Name="Roles">
        <RoleClass Name="Robot" RefBaseClassPath="AutomationMLBaseRole">
          <Attribute Name="localValue"/>
        </RoleClass>
      </RoleClassLib>
    </CAEXFile>"""
    result = CAEXFile.import_aml_xml(legacy)

    codes = [issue.code for issue in result.issues]
    assert "unresolved-base-role-class" in codes
    issue = next(item for item in result.issues if item.code == "unresolved-base-role-class")
    assert issue.severity == "warning"
    assert "AutomationMLBaseRole" in issue.message

    requirement = result.document.instance_hierarchies[0].internal_elements[0].role_requirements[0]
    assert [item.name for item in requirement.attributes] == ["localValue"]


@pytest.mark.parametrize(
    "fixture_name",
    [
        "0_EmptyFile_V2.0.aml",
        "2_IE.aml",
        "3_IE_Attribute.aml",
        "4_IH.aml",
        "6_RCL.aml",
        "7_ICL.aml",
        "9_ExtInt_IntLink.aml",
    ],
)
def test_official_legacy_fixtures_upgrade_to_xsd_valid_caex3(fixture_name):
    repository = Path(__file__).parents[1]
    fixture = (
        repository
        / "tests/vendor/aml-ua-xslt-e38653c/UnitTests/AML"
        / fixture_name
    )
    legacy_schema = xmlschema.XMLSchema(
        repository
        / "tests/vendor/aml-ua-xslt-e38653c/UnitTests/AML/CAEX_ClassModel_V2.15.xsd"
    )
    legacy_schema.validate(fixture)
    result = CAEXFile.import_aml_xml(fixture.read_bytes())
    schema = xmlschema.XMLSchema(
        repository / "schemas/caex/CAEX_ClassModel_V.3.0.xsd"
    )
    assert result.converted
    schema.validate(result.document.to_aml_xml(pretty=False))


def test_changes_apply_inverse_and_transaction_rollback():
    original = _class_document()
    edit = original.edit()
    with edit as working:
        working.file_name = "changed.aml"
        working.instance_hierarchies[0].internal_elements[0].name = "Changed"
    result = edit.result
    assert original.file_name == "classes.aml"
    assert result.document.file_name == "changed.aml"
    assert result.inverse.apply(result.document).to_aml_dict() == original.to_aml_dict()
    with pytest.raises(ChangeSetError):
        result.changes.apply(result.document)

    failed = original.edit()
    with pytest.raises(RuntimeError):
        with failed as working:
            working.file_name = "never-committed.aml"
            raise RuntimeError("stop")
    with pytest.raises(ChangeSetError):
        _ = failed.result


def test_merge_is_atomic_reports_conflicts_and_can_remap_ids():
    target = CAEXFile(
        file_name="target.aml",
        source_document_information=[_source()],
        system_unit_class_libs=[
            SystemUnitClassLib(name="A", system_unit_classes=[SystemUnitFamily(name="One")])
        ],
        instance_hierarchies=[
            InstanceHierarchy(name="Target", internal_elements=[InternalElement(id="same", name="A")])
        ],
    )
    source = CAEXFile(
        file_name="source.aml",
        source_document_information=[_source()],
        system_unit_class_libs=[
            SystemUnitClassLib(name="A", system_unit_classes=[SystemUnitFamily(name="Two")])
        ],
        instance_hierarchies=[
            InstanceHierarchy(name="Source", internal_elements=[InternalElement(id="same", name="B")])
        ],
    )

    failed = merge_documents(target, source)
    assert not failed.succeeded and failed.conflicts[0].code == "duplicate-id"
    assert target.instance_hierarchies[0].name == "Target"

    merged = merge_documents(
        target,
        source,
        policy=MergePolicy(ids=ConflictAction.REMAP_SOURCE_IDS),
    )
    assert merged.succeeded
    assert {lib.system_unit_classes[0].name for lib in merged.document.system_unit_class_libs} == {"One"}
    assert {item.name for item in merged.document.system_unit_class_libs[0].system_unit_classes} == {"One", "Two"}
    assert len(merged.document.reference_index().ids) == 2


def test_merge_rename_policy_rewrites_copied_class_references():
    target = CAEXFile(
        file_name="target.aml",
        source_document_information=[_source()],
        system_unit_class_libs=[
            SystemUnitClassLib(
                name="A",
                system_unit_classes=[SystemUnitFamily(name="Base")],
            )
        ],
    )
    source = CAEXFile(
        file_name="source.aml",
        source_document_information=[_source()],
        system_unit_class_libs=[
            SystemUnitClassLib(
                name="A",
                system_unit_classes=[
                    SystemUnitFamily(name="Base", attributes=[attribute("source", "1")]),
                    SystemUnitFamily(name="Derived", ref_base_class_path="A/Base"),
                ],
            )
        ],
        instance_hierarchies=[
            InstanceHierarchy(
                name="Source",
                internal_elements=[
                    InternalElement(
                        id="source-instance",
                        name="I",
                        ref_base_system_unit_path="A/Base",
                    )
                ],
            )
        ],
    )
    result = merge_documents(
        target,
        source,
        policy=MergePolicy(definitions=ConflictAction.RENAME_SOURCE),
    )
    assert result.succeeded
    query = result.document.query()
    assert query.find_by_path("A/Base_2") is not None
    assert query.find_by_path("A/Derived").obj.ref_base_class_path == "A/Base_2"
    assert (
        result.document.instance_hierarchies[0]
        .internal_elements[0]
        .ref_base_system_unit_path
        == "A/Base_2"
    )


def test_filesystem_resolution_blocks_escape_and_supports_external_queries(tmp_path):
    external = CAEXFile(
        file_name="library.aml",
        source_document_information=[_source()],
        system_unit_class_libs=[
            SystemUnitClassLib(name="External", system_unit_classes=[SystemUnitFamily(name="Motor")])
        ],
    )
    (tmp_path / "library.aml").write_text(external.to_aml_xml(), encoding="utf-8")
    root = CAEXFile(
        file_name="root.aml",
        source_document_information=[_source()],
        external_references=[ExternalReference(path="library.aml", file_alias="Lib")],
    )
    result = resolve_external_references(root, FileSystemResolver(tmp_path))
    assert result.succeeded
    assert root.query(externals=result.documents).find_by_path(
        "[Lib]External/Motor", kind="SystemUnitClass"
    ).name == "Motor"

    escaped = root.model_copy(deep=True)
    escaped.external_references[0].path = "../outside.aml"
    result = resolve_external_references(escaped, FileSystemResolver(tmp_path))
    assert result.issues[0].code == "resolution-failed"


def test_recursive_filesystem_resolution_reports_cycles(tmp_path):
    first = CAEXFile(
        file_name="first.aml",
        source_document_information=[_source()],
        external_references=[ExternalReference(path="second.aml", file_alias="Second")],
    )
    second = CAEXFile(
        file_name="second.aml",
        source_document_information=[_source()],
        external_references=[ExternalReference(path="first.aml", file_alias="First")],
    )
    (tmp_path / "first.aml").write_text(first.to_aml_xml(), encoding="utf-8")
    (tmp_path / "second.aml").write_text(second.to_aml_xml(), encoding="utf-8")
    result = resolve_external_references(
        first,
        FileSystemResolver(tmp_path),
        recursive=True,
    )
    assert any(issue.code == "reference-cycle" for issue in result.issues)
