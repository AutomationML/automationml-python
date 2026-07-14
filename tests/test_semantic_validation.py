import json
from copy import deepcopy
from pathlib import Path

from automationml import (
    CAEXFile,
    InstanceHierarchy,
    InterfaceClass,
    InternalElement,
    InternalLink,
    SystemUnitClassLib,
    SystemUnitFamily,
)


FIXTURE = Path(__file__).parent / "fixtures" / "minimal_caex.json"


def _load_fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_valid_fixture_has_no_semantic_issues_and_resolves_paths():
    document = CAEXFile.model_validate(_load_fixture())

    assert document.caex_validation_issues() == []

    index = document.reference_index()
    assert (
        index.resolve_system_unit_class("ExampleSystemUnitClassLib/Motor").name
        == "Motor"
    )
    assert index.resolve_role_class("ExampleRoleClassLib/Drive").name == "Drive"


def test_unresolved_references_include_codes_paths_and_targets():
    data = deepcopy(_load_fixture())
    element = data["InstanceHierarchy"][0]["InternalElement"][0]
    element["RefBaseSystemUnitPath"] = "MissingSystemUnits/Motor"
    element["RoleRequirements"][0]["RefBaseRoleClassPath"] = "MissingRoles/Drive"
    element["ExternalInterface"] = [
        {
            "ID": "if-power",
            "Name": "Power",
            "RefBaseClassPath": "MissingInterfaces/Port",
        }
    ]
    element["Attribute"][0]["RefAttributeType"] = "MissingAttributeTypes/Speed"

    issues = CAEXFile.model_validate(data).caex_validation_issues()

    by_code = {issue.code: issue for issue in issues}
    assert by_code["unresolved-system-unit-class-reference"].path == (
        "$.InstanceHierarchy[0].InternalElement[0].RefBaseSystemUnitPath"
    )
    assert by_code["unresolved-system-unit-class-reference"].target == (
        "MissingSystemUnits/Motor"
    )
    assert by_code["unresolved-role-class-reference"].path == (
        "$.InstanceHierarchy[0].InternalElement[0]"
        ".RoleRequirements[0].RefBaseRoleClassPath"
    )
    assert by_code["unresolved-interface-class-reference"].target == (
        "MissingInterfaces/Port"
    )
    assert by_code["unresolved-attribute-type-reference"].target == (
        "MissingAttributeTypes/Speed"
    )


def test_duplicate_ids_and_internal_link_partner_ids_are_reported():
    document = CAEXFile(
        file_name="links.aml",
        system_unit_class_libs=[
            SystemUnitClassLib(
                name="ExampleSystemUnitClassLib",
                system_unit_classes=[
                    SystemUnitFamily(
                        name="Cell",
                        external_interfaces=[
                            InterfaceClass(id="if-duplicate", name="In"),
                            InterfaceClass(id="if-duplicate", name="Out"),
                        ],
                        internal_links=[
                            InternalLink(
                                name="MaterialFlow",
                                ref_partner_side_a="if-duplicate",
                                ref_partner_side_b="missing-interface",
                            )
                        ],
                    )
                ],
            )
        ],
    )

    issues = document.caex_validation_issues()
    duplicate_id_issues = [
        issue for issue in issues if issue.code == "duplicate-id"
    ]

    assert len(duplicate_id_issues) == 2
    assert any(
        issue.code == "unresolved-internal-link-partner"
        and issue.path.endswith(".InternalLink[0].RefPartnerSideB")
        and issue.target == "missing-interface"
        for issue in issues
    )


def test_internal_links_resolve_element_id_and_interface_name_partners():
    document = CAEXFile(
        file_name="links.aml",
        instance_hierarchies=[
            InstanceHierarchy(
                name="Plant",
                internal_elements=[
                    InternalElement(
                        id="project",
                        name="Project",
                        internal_elements=[
                            InternalElement(
                                id="source",
                                name="Source",
                                external_interfaces=[
                                    InterfaceClass(id="source-interface", name="Output")
                                ],
                            ),
                            InternalElement(
                                id="target",
                                name="Target",
                                external_interfaces=[
                                    InterfaceClass(id="target-interface", name="Input")
                                ],
                            ),
                        ],
                        internal_links=[
                            InternalLink(
                                name="MaterialFlow",
                                ref_partner_side_a="source:Output",
                                ref_partner_side_b="target:Input",
                            )
                        ],
                    )
                ],
            )
        ],
    )

    assert not any(
        issue.code == "unresolved-internal-link-partner"
        for issue in document.caex_validation_issues()
    )
