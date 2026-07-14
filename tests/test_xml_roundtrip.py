import json
from pathlib import Path

import xmlschema

from automationml import CAEXFile


FIXTURE = Path(__file__).parent / "fixtures" / "minimal_caex.json"
XSD = Path(__file__).parents[1] / "schemas" / "caex" / "CAEX_ClassModel_V.3.0.xsd"


def test_xml_roundtrip_preserves_core_caex_structure():
    document = CAEXFile.model_validate_json(FIXTURE.read_text(encoding="utf-8"))

    xml_text = document.to_aml_xml(pretty=False)
    parsed = CAEXFile.from_aml_xml(xml_text)

    assert parsed.file_name == "minimal.aml"
    assert parsed.schema_version == "3.0"
    assert parsed.instance_hierarchies[0].internal_elements[0].attributes[0].unit == "rpm"
    assert parsed.to_aml_dict()["SourceDocumentInformation"][0]["OriginID"] == (
        "automationml-python"
    )


def test_json_xml_json_is_stable_for_minimal_fixture():
    original = json.loads(FIXTURE.read_text(encoding="utf-8"))
    document = CAEXFile.model_validate(original)

    parsed = CAEXFile.from_aml_xml(document.to_aml_xml(pretty=False))

    assert parsed.to_aml_dict() == document.to_aml_dict()


def test_xml_json_xml_keeps_semantic_references_valid():
    original = CAEXFile.model_validate_json(FIXTURE.read_text(encoding="utf-8"))
    from_xml = CAEXFile.from_aml_xml(original.to_aml_xml(pretty=False))
    from_json = CAEXFile.model_validate(from_xml.to_aml_dict())
    from_xml_again = CAEXFile.from_aml_xml(from_json.to_aml_xml(pretty=False))

    assert from_xml.caex_validation_issues() == []
    assert from_json.caex_validation_issues() == []
    assert from_xml_again.caex_validation_issues() == []
    assert from_xml_again.to_aml_dict() == from_xml.to_aml_dict()


def test_generated_xml_is_valid_caex_3_against_xsd():
    document = CAEXFile.model_validate_json(FIXTURE.read_text(encoding="utf-8"))
    schema = xmlschema.XMLSchema(str(XSD))

    schema.validate(document.to_aml_xml(pretty=False))
