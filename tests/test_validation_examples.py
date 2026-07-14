import json
from collections import Counter
from pathlib import Path

import pytest
import xmlschema

from automationml import CAEXFile


SUITE = Path(__file__).parents[1] / "examples" / "validation-suite"
MANIFEST = SUITE / "manifest.json"
XSD = Path(__file__).parents[1] / "schemas" / "caex" / "CAEX_ClassModel_V.3.0.xsd"


def _cases() -> list[dict]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))["cases"]


def _case_id(case: dict) -> str:
    return case["name"]


def test_validation_example_catalog_covers_sizes_and_polarities():
    cases = _cases()
    by_size: dict[str, set[str]] = {}
    for case in cases:
        by_size.setdefault(case["size"], set()).add(case["polarity"])

    assert set(by_size) == {"small", "medium", "big"}
    assert by_size == {
        "small": {"positive", "negative", "warning"},
        "medium": {"positive", "negative", "warning"},
        "big": {"positive", "negative"},
    }


def test_small_motor_examples_both_exercise_instance_interfaces():
    cases = {case["name"]: case for case in _cases()}
    valid_document = CAEXFile.model_validate_json(
        (SUITE / cases["small-valid-motor"]["json"]).read_text(encoding="utf-8")
    )
    invalid_document = CAEXFile.model_validate_json(
        (SUITE / cases["small-invalid-unresolved-references"]["json"]).read_text(
            encoding="utf-8"
        )
    )

    valid_motor = valid_document.instance_hierarchies[0].internal_elements[0]
    invalid_motor = invalid_document.instance_hierarchies[0].internal_elements[0]

    assert len(valid_motor.external_interfaces) == 1
    assert len(invalid_motor.external_interfaces) == 1
    assert valid_motor.external_interfaces[0].name == invalid_motor.external_interfaces[0].name
    assert valid_motor.external_interfaces[0].ref_base_class_path == (
        "ExampleInterfaceClassLib/PowerPort"
    )
    assert valid_document.reference_index().resolve_interface_class(
        "ExampleInterfaceClassLib/PowerPort"
    )


def test_warning_example_names_are_catalog_parseable():
    warning_cases = [case for case in _cases() if case["polarity"] == "warning"]

    assert warning_cases
    for case in warning_cases:
        parts = case["name"].split("_")

        assert parts[0] == case["size"]
        assert len(parts) == 4
        assert parts[1] == "robot-cell"
        assert parts[2] == "warning"
        assert parts[3]
        assert case["json"] == f"json/{case['name']}.json"
        assert case["xml"] == f"xml/{case['name']}.aml"


@pytest.mark.parametrize("case", _cases(), ids=_case_id)
def test_validation_examples_have_json_and_xml_serializations(case: dict):
    json_path = SUITE / case["json"]
    xml_path = SUITE / case["xml"]

    assert json_path.exists()
    assert xml_path.exists()
    assert json_path.suffix == ".json"
    assert xml_path.suffix == ".aml"


@pytest.mark.parametrize("case", _cases(), ids=_case_id)
def test_validation_examples_match_expected_sdk_issues(case: dict):
    json_document = CAEXFile.model_validate_json(
        (SUITE / case["json"]).read_text(encoding="utf-8")
    )
    xml_document = CAEXFile.from_aml_xml(
        (SUITE / case["xml"]).read_text(encoding="utf-8")
    )

    assert xml_document.to_aml_dict() == json_document.to_aml_dict()

    for document in (json_document, xml_document):
        issues = document.caex_validation_issues()
        issue_counts = Counter(issue.code for issue in issues)
        severity_counts = Counter(issue.severity for issue in issues)
        assert (severity_counts.get("error", 0) == 0) is case["expected_valid"]
        assert len(issues) == case["expected_issue_count"]
        assert severity_counts.get("error", 0) == case["expected_error_count"]
        assert severity_counts.get("warning", 0) == case["expected_warning_count"]
        assert issue_counts == Counter(case["expected_issue_counts"])
        assert severity_counts == Counter(case["expected_severity_counts"])


def test_medium_robot_cell_materializes_deep_inheritance_without_warnings():
    cases = {case["name"]: case for case in _cases()}
    document = CAEXFile.model_validate_json(
        (SUITE / cases["medium-valid-robot-cell"]["json"]).read_text(
            encoding="utf-8"
        )
    )

    issues = document.caex_validation_issues()
    assert issues == []

    system_units = document.system_unit_class_libs[0].system_unit_classes
    asset_class = system_units[0]
    cell_class = system_units[1]
    robot_class = system_units[3]
    interface_classes = document.interface_class_libs[0].interface_classes
    robot_cell = document.instance_hierarchies[0].internal_elements[0]
    robot_arm = robot_cell.internal_elements[1]

    assert {interface.name for interface in interface_classes} == {
        "Port",
        "DataPort",
        "MaterialPort",
    }
    assert asset_class.name == "Asset"
    assert cell_class.ref_base_class_path == "SystemUnitClassLib/Asset"
    assert robot_class.ref_base_class_path == "SystemUnitClassLib/Cell"
    assert {attribute.name for attribute in robot_arm.attributes} == {
        "assetTag",
        "cycleTime",
        "payload",
    }
    assert {interface.name for interface in robot_arm.external_interfaces} == {
        "Data",
        "MaterialIn",
    }


def test_explicit_inheritance_warning_examples_are_valid_warning_cases():
    cases = {case["name"]: case for case in _cases()}
    expectations = {
        "small_robot-cell_warning_missing-inherited-attribute": Counter(
            {"missing-inherited-attribute": 1}
        ),
        "medium_robot-cell_warning_missing-inherited-attribute-and-class-interface": Counter(
            {
                "missing-inherited-attribute": 2,
                "missing-class-interface": 3,
            }
        ),
    }

    for case_name, expected_counts in expectations.items():
        document = CAEXFile.model_validate_json(
            (SUITE / cases[case_name]["json"]).read_text(encoding="utf-8")
        )
        issues = document.caex_validation_issues()
        severity_counts = Counter(issue.severity for issue in issues)

        assert cases[case_name]["polarity"] == "warning"
        assert severity_counts.get("error", 0) == 0
        assert severity_counts == Counter({"warning": sum(expected_counts.values())})
        assert Counter(issue.code for issue in issues) == expected_counts


@pytest.mark.parametrize("case", _cases(), ids=_case_id)
def test_validation_example_xml_is_caex_xsd_valid(case: dict):
    schema = xmlschema.XMLSchema(str(XSD))

    schema.validate(str(SUITE / case["xml"]))
