from automationml import (
    RoleFamily,
    SystemUnitFamily,
    attribute,
    attribute_type,
    attribute_type_lib,
    caex_file,
    external_interface,
    instance_hierarchy,
    interface_class,
    interface_class_lib,
    role_class,
    role_class_lib,
    role_requirement,
    system_unit_class,
    system_unit_class_lib,
)


def _plant():
    document = caex_file("builders.aml")
    document.attribute_type_libs.append(
        attribute_type_lib(
            "Types",
            attribute_types=[
                attribute_type("Speed", data_type="xs:double", unit="rpm")
            ],
        )
    )
    document.interface_class_libs.append(
        interface_class_lib(
            "Interfaces",
            classes=[interface_class("Port", classes=[interface_class("PowerPort")])],
        )
    )
    document.role_class_libs.append(
        role_class_lib("Roles", classes=[role_class("Drive")])
    )
    document.system_unit_class_libs.append(
        system_unit_class_lib(
            "Components",
            classes=[
                system_unit_class(
                    "Motor",
                    attributes=[attribute("speed", ref_attribute_type="Types/Speed")],
                    role_paths=["Roles/Drive"],
                    external_interfaces=[
                        external_interface(
                            "Power", ref_base_class_path="Interfaces/Port/PowerPort"
                        )
                    ],
                    classes=[
                        system_unit_class(
                            "ServoMotor",
                            ref_base_class_path="Components/Motor",
                            attributes={"torque": 4},
                        )
                    ],
                )
            ],
        )
    )
    motor = document.instantiate_system_unit_class("Components/Motor", name="Motor-1")
    motor.role_requirements.append(role_requirement("Roles/Drive"))
    document.instance_hierarchies.append(
        instance_hierarchy("Plant", internal_elements=[motor])
    )
    return document


def test_class_library_builders_produce_resolvable_libraries():
    document = _plant()

    assert document.caex_validation_issues() == []
    motor_class = document.system_unit_class_libs[0].system_unit_classes[0]
    assert isinstance(motor_class, SystemUnitFamily)
    assert isinstance(document.role_class_libs[0].role_classes[0], RoleFamily)
    assert document.query().find_by_path(
        "Components/Motor/ServoMotor", kind="SystemUnitClass"
    ) is not None


def test_nested_class_inherits_from_its_base_when_instantiated():
    document = _plant()

    servo = document.instantiate_system_unit_class(
        "Components/Motor/ServoMotor", name="Servo-1"
    )

    assert [item.name for item in servo.attributes] == ["speed", "torque"]
    assert [item.name for item in servo.external_interfaces] == ["Power"]


def test_class_library_builders_emit_canonical_aml_json():
    library = _plant().to_aml_dict()["SystemUnitClassLib"][0]

    assert library == {
        "Name": "Components",
        "SystemUnitClass": [
            {
                "Name": "Motor",
                "Attribute": [{"Name": "speed", "RefAttributeType": "Types/Speed"}],
                "ExternalInterface": [
                    {"Name": "Power", "RefBaseClassPath": "Interfaces/Port/PowerPort"}
                ],
                "SupportedRoleClass": [{"RefRoleClassPath": "Roles/Drive"}],
                "SystemUnitClass": [
                    {
                        "Name": "ServoMotor",
                        "Attribute": [{"Name": "torque", "Value": "4"}],
                        "RefBaseClassPath": "Components/Motor",
                    }
                ],
            }
        ],
    }
