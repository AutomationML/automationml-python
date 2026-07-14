import json
from pathlib import Path

from automationml import CAEXFile, attribute, caex_file, instance_hierarchy, internal_element


FIXTURE = Path(__file__).parent / "fixtures" / "minimal_caex.json"


def test_loads_minimal_aml_json_and_emits_canonical_aliases():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))

    document = CAEXFile.model_validate(data)

    assert document.file_name == "minimal.aml"
    assert document.instance_hierarchies[0].internal_elements[0].name == "Motor"
    assert document.to_aml_dict()["InstanceHierarchy"][0]["Name"] == "Plant"


def test_builder_api_keeps_python_clean_and_json_canonical():
    document = caex_file("builder.aml")
    motor = internal_element(
        "Motor",
        id="ie-1",
        attributes=[attribute("speed", 1500, unit="rpm")],
        role_paths=["ExampleRoleClassLib/Drive"],
    )
    document.instance_hierarchies.append(
        instance_hierarchy("Plant", internal_elements=[motor])
    )

    payload = document.to_aml_dict()

    assert payload["FileName"] == "builder.aml"
    assert payload["InstanceHierarchy"][0]["InternalElement"][0]["Attribute"][0][
        "Value"
    ] == "1500"
    assert "ChangeMode" not in json.dumps(payload)
