"""Generate the self-guided AutomationML learning notebooks."""

from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
LEARNING = ROOT / "learning"


def markdown(source: str, cell_id: str) -> dict[str, Any]:
    return {
        "cell_type": "markdown",
        "id": cell_id,
        "metadata": {},
        "source": dedent(source).strip() + "\n",
    }


def code(source: str, cell_id: str) -> dict[str, Any]:
    return {
        "cell_type": "code",
        "execution_count": None,
        "id": cell_id,
        "metadata": {},
        "outputs": [],
        "source": dedent(source).strip() + "\n",
    }


def notebook(title: str, cells: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3.11"},
            "automationml_learning": {
                "title": title,
                "format_version": 2,
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


NOTEBOOK_ONE = notebook(
    "Build a small drive station",
    [
        markdown(
            """
            # Build a small drive station

            **Lesson 1 of 3 | Beginner | About 50 minutes**

            ## Learning scenario

            A training workshop is building a small mixer. The mixer needs an
            electric motor and a power supply. During commissioning, equipment
            names and operating values may change, but other tools must still
            understand what each object *is* and how the objects are connected.

            We will begin with concrete equipment only. Classes appear later,
            after the model itself shows us why they are useful.
            """,
            "build-title",
        ),
        markdown(
            """
            ## 1. Create a document and an InstanceHierarchy

            A `CAEXFile` is the AutomationML document. An
            `InstanceHierarchy` holds the equipment occurrences in one system.
            We name ours `TrainingWorkshop`.
            """,
            "build-document-intro",
        ),
        code(
            """
            from automationml import caex_file, instance_hierarchy

            document = caex_file("training-drive-station.aml")
            workshop = instance_hierarchy("TrainingWorkshop")
            document.instance_hierarchies.append(workshop)
            """,
            "build-document",
        ),
        markdown(
            """
            ## 2. Add the motor

            An `InternalElement` represents an object occurrence. Its `Name` is
            readable for people. Its `ID` gives this occurrence a stable
            identity inside the document.
            """,
            "build-motor-intro",
        ),
        code(
            """
            from automationml import internal_element

            motor = internal_element("Motor 1", id="motor-1")
            workshop.internal_elements.append(motor)
            """,
            "build-motor",
        ),
        markdown(
            """
            ## 3. Describe this particular motor

            Attributes hold information about an object. At commissioning time
            we know that this motor runs at 1500 rpm and expects 48 V.
            """,
            "build-motor-attributes-intro",
        ),
        code(
            """
            from automationml import attribute

            motor.attributes.append(
                attribute("ratedSpeed", 1500, unit="rpm", data_type="xs:double")
            )
            motor.attributes.append(
                attribute("ratedVoltage", 48, unit="V", data_type="xs:double")
            )
            """,
            "build-motor-attributes",
        ),
        markdown(
            """
            ### First inspection

            We now have enough information to make inspecting the element
            worthwhile. Read the output as an object, not as an exchange format:
            one identity, one human name, and two properties.
            """,
            "build-first-inspection-intro",
        ),
        code(
            """
            print(f"{motor.name}  [ID: {motor.id}]")
            for item in motor.attributes:
                print(f"  {item.name}: {item.value} {item.unit or ''}".rstrip())
            """,
            "build-first-inspection",
        ),
        markdown(
            """
            ## 4. The motor needs a power supply

            The supply is another independent equipment occurrence. Its output
            voltage matches the motor, and its rated power is 500 W.
            """,
            "build-supply-intro",
        ),
        code(
            """
            power_supply = internal_element("Power Supply 1", id="power-supply-1")
            workshop.internal_elements.append(power_supply)
            """,
            "build-supply",
        ),
        code(
            """
            power_supply.attributes.append(
                attribute("outputVoltage", 48, unit="V", data_type="xs:double")
            )
            power_supply.attributes.append(
                attribute("ratedPower", 500, unit="W", data_type="xs:double")
            )
            """,
            "build-supply-attributes",
        ),
        markdown(
            """
            ## 5. Give both elements a connection point

            An `ExternalInterface` is a connection point on an element. The
            motor receives power through `PowerIn`; the supply provides it
            through `PowerOut`.
            """,
            "build-interfaces-intro",
        ),
        code(
            """
            from automationml import external_interface

            motor_power = external_interface("PowerIn", id="motor-1-power-in")
            motor.external_interfaces.append(motor_power)
            """,
            "build-motor-interface",
        ),
        code(
            """
            supply_power = external_interface(
                "PowerOut", id="power-supply-1-power-out"
            )
            power_supply.external_interfaces.append(supply_power)
            """,
            "build-supply-interface",
        ),
        markdown(
            """
            ## 6. Put the equipment under one connection owner

            A CAEX `InternalLink` belongs to the element that contains both
            partners. Therefore the motor and supply become children of a
            common `Drive Station 1` element. This is our first actual equipment
            hierarchy.
            """,
            "build-parent-intro",
        ),
        code(
            """
            drive_station = internal_element(
                "Drive Station 1",
                id="drive-station-1",
                children=[motor, power_supply],
            )
            workshop.internal_elements = [drive_station]
            """,
            "build-parent",
        ),
        markdown(
            """
            The partner syntax below combines a stable element ID with the name
            of one of its interfaces. For this learning scenario, read Partner A
            as the source and Partner B as the target.
            """,
            "build-link-intro",
        ),
        code(
            """
            from automationml import InternalLink

            power_link = InternalLink(
                name="MotorPower",
                ref_partner_side_a="power-supply-1:PowerOut",
                ref_partner_side_b="motor-1:PowerIn",
            )
            drive_station.internal_links.append(power_link)
            """,
            "build-link",
        ),
        markdown(
            """
            ### Inspect the connected station

            The tree shows containment. The final line shows a relationship
            between interfaces; that relationship is not the same thing as
            parent-child containment.
            """,
            "build-connected-inspection-intro",
        ),
        code(
            """
            print(drive_station.name)
            for child in drive_station.internal_elements:
                interfaces = ", ".join(item.name for item in child.external_interfaces)
                print(f"  +-- {child.name}  [{interfaces}]")
            print(
                f"  link: {power_link.ref_partner_side_a}"
                f" -> {power_link.ref_partner_side_b}"
            )
            """,
            "build-connected-inspection",
        ),
        markdown(
            """
            ## 7. A valid structure can still have weak meaning

            At this point the validator can confirm that the link partners
            exist. But `Motor 1` is only a name we chose. Nothing in the model
            formally says that the element is an electric motor rather than a
            label that happens to contain the word "Motor".

            This distinction matters: **validation can confirm claims that the
            model makes, but it cannot invent semantic claims that are absent.**
            """,
            "build-semantic-gap-intro",
        ),
        code(
            """
            issues_without_classes = document.caex_validation_issues(strict_xsd=True)

            print("Validation issues:", len(issues_without_classes))
            assert issues_without_classes == []
            """,
            "build-semantic-gap",
        ),
        markdown(
            """
            Zero issues means the claims currently present are consistent. It
            does **not** mean that the document already carries strong type
            semantics.

            ## 8. Commissioning changes human-facing data

            The workshop decides on clearer names, and testing produces a new
            motor speed. The IDs and link do not change when element names
            change.
            """,
            "build-renaming-intro",
        ),
        code(
            """
            motor.name = "Mixer Drive Motor"
            motor.attributes[0].value = "1800"
            power_supply.name = "Control Cabinet Power Supply"

            print(motor.name, "at", motor.attributes[0].value, "rpm")
            print(power_supply.name)
            print(power_link.ref_partner_side_a, "->", power_link.ref_partner_side_b)
            """,
            "build-renaming",
        ),
        markdown(
            """
            Names and values should be editable. The stable meaning should not
            depend on the current display name. Now we have a concrete reason
            to introduce classes.

            ## 9. Classify the interface meaning

            `ElectricalPower` describes the kind of connection independently
            from the local names `PowerIn` and `PowerOut`.
            """,
            "build-interface-class-intro",
        ),
        code(
            """
            from automationml import InterfaceClassLib, InterfaceFamily

            connection_types = InterfaceClassLib(
                name="ConnectionTypes",
                interface_classes=[InterfaceFamily(name="ElectricalPower")],
            )
            document.interface_class_libs.append(connection_types)
            """,
            "build-interface-class",
        ),
        code(
            """
            POWER_INTERFACE_PATH = "ConnectionTypes/ElectricalPower"

            motor_power.ref_base_class_path = POWER_INTERFACE_PATH
            supply_power.ref_base_class_path = POWER_INTERFACE_PATH
            """,
            "build-apply-interface-class",
        ),
        markdown(
            """
            ## 10. Classify important attribute meaning

            Attribute types give shared meaning to values even when different
            classes use local attribute names such as `ratedVoltage` and
            `outputVoltage`.
            """,
            "build-attribute-types-intro",
        ),
        code(
            """
            from automationml import AttributeType, AttributeTypeLib

            value_types = AttributeTypeLib(name="ValueTypes")
            document.attribute_type_libs.append(value_types)
            """,
            "build-attribute-library",
        ),
        markdown(
            """
            First, define the meaning and unit of rotational speed.
            """,
            "build-speed-type-intro",
        ),
        code(
            """
            speed_type = AttributeType(
                name="RotationalSpeed",
                unit="rpm",
                attribute_data_type="xs:double",
            )
            value_types.attribute_types.append(speed_type)
            """,
            "build-speed-type",
        ),
        markdown(
            """
            Voltage is a second shared meaning used by both pieces of equipment.
            """,
            "build-voltage-type-intro",
        ),
        code(
            """
            voltage_type = AttributeType(
                name="Voltage",
                unit="V",
                attribute_data_type="xs:double",
            )
            value_types.attribute_types.append(voltage_type)
            """,
            "build-voltage-type",
        ),
        code(
            """
            motor.attributes[0].ref_attribute_type = "ValueTypes/RotationalSpeed"
            motor.attributes[1].ref_attribute_type = "ValueTypes/Voltage"
            power_supply.attributes[0].ref_attribute_type = "ValueTypes/Voltage"
            """,
            "build-apply-attribute-types",
        ),
        markdown(
            """
            ## 11. Define the motor class

            A `SystemUnitClass` describes reusable equipment shape. The class
            below says what attributes and interfaces an electric motor is
            expected to materialize.
            """,
            "build-motor-class-intro",
        ),
        code(
            """
            from automationml import SystemUnitFamily

            motor_class = SystemUnitFamily(name="ElectricMotor")
            """,
            "build-motor-class",
        ),
        markdown(
            """
            Add the expected motor attributes one at a time. These define shape,
            so they do not need occurrence-specific values.
            """,
            "build-motor-class-attributes-intro",
        ),
        code(
            """
            motor_class.attributes.append(
                attribute(
                    "ratedSpeed", unit="rpm", data_type="xs:double",
                    ref_attribute_type="ValueTypes/RotationalSpeed",
                )
            )
            """,
            "build-motor-class-speed",
        ),
        code(
            """
            motor_class.attributes.append(
                attribute(
                    "ratedVoltage", unit="V", data_type="xs:double",
                    ref_attribute_type="ValueTypes/Voltage",
                )
            )
            """,
            "build-motor-class-voltage",
        ),
        markdown(
            """
            Finally, make `PowerIn` part of the expected motor interface set.
            """,
            "build-motor-class-interface-intro",
        ),
        code(
            """
            motor_class.external_interfaces.append(
                external_interface(
                    "PowerIn", id="class-motor-power-in",
                    ref_base_class_path=POWER_INTERFACE_PATH,
                )
            )
            """,
            "build-motor-class-interface",
        ),
        markdown(
            """
            ## 12. Define the power-supply class

            The same pattern gives the supply a stable type. Its two attributes
            and power output become the expected class shape.
            """,
            "build-supply-class-intro",
        ),
        code(
            """
            supply_class = SystemUnitFamily(name="PowerSupply")
            """,
            "build-supply-class",
        ),
        code(
            """
            supply_class.attributes.append(
                attribute(
                    "outputVoltage", unit="V", data_type="xs:double",
                    ref_attribute_type="ValueTypes/Voltage",
                )
            )
            """,
            "build-supply-class-voltage",
        ),
        code(
            """
            supply_class.attributes.append(
                attribute("ratedPower", unit="W", data_type="xs:double")
            )
            """,
            "build-supply-class-power",
        ),
        code(
            """
            supply_class.external_interfaces.append(
                external_interface(
                    "PowerOut", id="class-supply-power-out",
                    ref_base_class_path=POWER_INTERFACE_PATH,
                )
            )
            """,
            "build-supply-class-interface",
        ),
        markdown(
            """
            ## 13. Put the classes in a library and reference them

            Library name plus class name forms a stable AML path. Instance names
            may continue to change without changing that type reference.
            """,
            "build-class-library-intro",
        ),
        code(
            """
            from automationml import SystemUnitClassLib

            equipment_types = SystemUnitClassLib(
                name="EquipmentTypes",
                system_unit_classes=[motor_class, supply_class],
            )
            document.system_unit_class_libs.append(equipment_types)
            """,
            "build-class-library",
        ),
        code(
            """
            motor.ref_base_system_unit_path = "EquipmentTypes/ElectricMotor"
            power_supply.ref_base_system_unit_path = "EquipmentTypes/PowerSupply"

            print(motor.name, "is a", motor.ref_base_system_unit_path)
            print(power_supply.name, "is a", power_supply.ref_base_system_unit_path)
            """,
            "build-apply-system-classes",
        ),
        markdown(
            """
            ## 14. Validate the semantic claims

            The validator can now resolve the type paths and compare each
            instance with its class shape. That is much stronger than checking
            only whether the object tree is internally consistent.
            """,
            "build-final-validation-intro",
        ),
        code(
            """
            issues = document.caex_validation_issues(strict_xsd=True)

            for issue in issues:
                print(issue.severity, issue.code, issue.path)

            assert issues == []
            print("The classified motor and supply validate without issues.")
            """,
            "build-final-validation",
        ),
        markdown(
            """
            ## 15. Your turn: classify the containing station

            `Drive Station 1` is also an InternalElement, but it does not yet
            reference a SystemUnitClass. Complete the hierarchy by:

            1. creating a `SystemUnitFamily` named `DriveStation`;
            2. adding it to `equipment_types.system_unit_classes`;
            3. setting the station's path to `EquipmentTypes/DriveStation`.

            Use the empty cell below. Keep the existing motor and supply classes.
            """,
            "build-challenge-intro",
        ),
        code(
            """
            # Your code here:



            """,
            "build-challenge",
        ),
        code(
            """
            if drive_station.ref_base_system_unit_path is None:
                print("Challenge ready: Drive Station 1 still needs its class.")
            else:
                target = document.reference_index().resolve_system_unit_class(
                    drive_station.ref_base_system_unit_path
                )
                assert target is not None
                assert document.caex_validation_issues(strict_xsd=True) == []
                print("Complete:", drive_station.name, "is a", target.aml_path)
            """,
            "build-challenge-check",
        ),
        markdown(
            """
            <details>
            <summary><strong>Reveal one solution</strong></summary>

            ```python
            drive_station_class = SystemUnitFamily(name="DriveStation")
            equipment_types.system_unit_classes.append(drive_station_class)
            drive_station.ref_base_system_unit_path = "EquipmentTypes/DriveStation"
            ```

            Run the check cell again after adding the solution.
            </details>

            ## What you built

            - an InstanceHierarchy containing a small equipment hierarchy;
            - instance attributes and external interfaces;
            - an InternalLink between two interface partners;
            - interface, attribute, and equipment semantics that survive renaming;
            - a final class-design task for the containing element.

            Lesson 2 will take a completed AutomationML model and focus only on
            JSON and XML exchange.
            """,
            "build-summary",
        ),
    ],
)


NOTEBOOK_TWO = notebook(
    "One model, two exchange formats",
    [
        markdown(
            """
            # One model, two exchange formats

            **Lesson 2 of 3 | Beginner | About 30 minutes**

            ## Learning scenario

            The engineering model is ready to leave our Python session. A web
            application wants AML JSON; an established AutomationML tool wants
            an `.aml` XML file. We should not build two models. We should expose
            the same validated model through two exchange formats.

            This notebook starts from a provided valid motor example so it can
            run independently from Lesson 1.
            """,
            "exchange-title",
        ),
        markdown(
            """
            ## 1. Load the starting model

            `load_json` parses canonical AML JSON into the same `CAEXFile` model
            that the Python builders create.
            """,
            "exchange-load-intro",
        ),
        code(
            """
            from automationml import load_json
            from pathlib import Path

            repo_root = Path.cwd()
            if not (repo_root / "examples").exists():
                repo_root = repo_root.parent

            source_path = repo_root / "examples/validation-suite/json/small-valid-motor.json"
            document = load_json(source_path)
            """,
            "exchange-load",
        ),
        code(
            """
            motor = document.instance_hierarchies[0].internal_elements[0]

            print("Document:", document.file_name)
            print("Element:", motor.name)
            print("Class:", motor.ref_base_system_unit_path)
            """,
            "exchange-inspect",
        ),
        markdown(
            """
            ## 2. Validate before exchange

            Serialization can faithfully preserve an invalid reference. It
            cannot decide whether that reference is correct. Validation is a
            separate step and should happen before trusted export.
            """,
            "exchange-validation-intro",
        ),
        code(
            """
            issues = document.caex_validation_issues(strict_xsd=True)

            assert issues == []
            print("Ready for exchange: no validation issues.")
            """,
            "exchange-validation",
        ),
        markdown(
            """
            ## 3. Create canonical AML JSON

            `to_aml_json` uses AutomationML/CAEX names such as
            `InstanceHierarchy` and `RefBaseSystemUnitPath`. Python's
            `snake_case` field names remain an implementation convenience.
            """,
            "exchange-json-intro",
        ),
        code(
            """
            json_text = document.to_aml_json(indent=2)

            print("\\n".join(json_text.splitlines()[:24]))
            print("... preview shortened")
            """,
            "exchange-json",
        ),
        code(
            """
            assert '"InstanceHierarchy"' in json_text
            assert '"RefBaseSystemUnitPath"' in json_text
            assert '"instance_hierarchies"' not in json_text

            print("Canonical CAEX property names confirmed.")
            """,
            "exchange-json-check",
        ),
        markdown(
            """
            ## 4. Parse the JSON back into a model

            Parsing is the first half of a round trip. The result is a new
            `CAEXFile` object with the same model content.
            """,
            "exchange-json-parse-intro",
        ),
        code(
            """
            from automationml import CAEXFile

            from_json = CAEXFile.from_aml_json(json_text)

            assert from_json.to_aml_dict() == document.to_aml_dict()
            print("AML JSON round trip passed.")
            """,
            "exchange-json-parse",
        ),
        markdown(
            """
            ## 5. Create AML XML from the same object

            No JSON-to-XML mapping is written in this notebook. The XML adapter
            reads the same Pydantic model that produced the JSON string.
            """,
            "exchange-xml-intro",
        ),
        code(
            """
            xml_text = document.to_aml_xml(pretty=True)

            print("\\n".join(xml_text.splitlines()[:18]))
            print("... preview shortened")
            """,
            "exchange-xml",
        ),
        markdown(
            """
            ## 6. Parse the XML and compare model content

            Whitespace and text ordering conventions differ between formats.
            Canonical AML dictionaries give us a format-neutral comparison.
            """,
            "exchange-xml-parse-intro",
        ),
        code(
            """
            from_xml = CAEXFile.from_aml_xml(xml_text)
            canonical = document.to_aml_dict()

            assert from_json.to_aml_dict() == canonical
            assert from_xml.to_aml_dict() == canonical
            print("JSON and XML reconstruct the same AutomationML model.")
            """,
            "exchange-xml-parse",
        ),
        markdown(
            """
            ## 7. Write both exchange files

            We use a temporary folder in the lesson so repeated runs do not
            leave generated files in the repository. Real applications can
            pass any target `Path` to the same functions.
            """,
            "exchange-files-intro",
        ),
        code(
            """
            from tempfile import TemporaryDirectory
            from automationml import dump_json, dump_xml

            temporary_directory = TemporaryDirectory()
            output_directory = Path(temporary_directory.name)

            json_path = output_directory / "motor.json"
            xml_path = output_directory / "motor.aml"
            """,
            "exchange-files-setup",
        ),
        code(
            """
            dump_json(document, json_path)
            dump_xml(document, xml_path)

            print(json_path.name, json_path.stat().st_size, "bytes")
            print(xml_path.name, xml_path.stat().st_size, "bytes")
            """,
            "exchange-files-write",
        ),
        markdown(
            """
            ## 8. Load both files through the public IO API

            This is the full file-level round trip an application would use.
            """,
            "exchange-files-load-intro",
        ),
        code(
            """
            from automationml import load_xml

            json_document = load_json(json_path)
            xml_document = load_xml(xml_path)

            assert json_document.to_aml_dict() == canonical
            assert xml_document.to_aml_dict() == canonical
            print("Both files loaded with identical canonical content.")
            """,
            "exchange-files-load",
        ),
        markdown(
            """
            ## 9. One edit, two updated representations

            Model changes happen before serialization. We rename a copy of the
            instance and then observe the new name in both outputs.
            """,
            "exchange-edit-intro",
        ),
        code(
            """
            edited = document.model_copy(deep=True)
            edited_motor = edited.instance_hierarchies[0].internal_elements[0]
            edited_motor.name = "Mixer Motor"

            assert '"Name": "Mixer Motor"' in edited.to_aml_json()
            assert 'Name="Mixer Motor"' in edited.to_aml_xml()
            print("One model edit reached both exchange formats.")
            """,
            "exchange-edit",
        ),
        markdown(
            """
            ## Your turn

            Change the motor speed on `edited_motor`. Then generate both strings
            again and search for the new value. Finally, break its
            `RefBaseSystemUnitPath` and compare successful serialization with
            the validator's semantic result.

            ## Takeaways

            - The Pydantic `CAEXFile` is the source of truth.
            - AML JSON is the primary readable exchange representation.
            - AML XML is produced from the same model for existing toolchains.
            - Round trips compare model content, not text formatting.
            - Validation and serialization answer different questions.
            """,
            "exchange-summary",
        ),
    ],
)


NOTEBOOK_THREE = notebook(
    "Inheritance, interfaces, and useful warnings",
    [
        markdown(
            """
            # Inheritance, interfaces, and useful warnings

            **Lesson 3 of 3 | Intermediate | About 45 minutes**

            ## Learning scenario

            A robot-cell document is structurally valid and all of its class
            paths resolve. Yet two instances do not carry the complete shape
            expected from their SystemUnitClasses. We will determine whether
            this is intentional 150% modeling or an omission, then repair it.
            """,
            "inheritance-title",
        ),
        markdown(
            """
            ## 1. Load the warning-focused example

            The catalog file name tells us its size, subject, polarity, and the
            warning types it is designed to demonstrate.
            """,
            "inheritance-load-intro",
        ),
        code(
            """
            from automationml import load_json
            from pathlib import Path

            repo_root = Path.cwd()
            if not (repo_root / "examples").exists():
                repo_root = repo_root.parent

            example_path = repo_root / (
                "examples/validation-suite/json/"
                "medium_robot-cell_warning_missing-inherited-attribute-and-class-interface.json"
            )
            document = load_json(example_path)
            """,
            "inheritance-load",
        ),
        code(
            """
            cell = document.instance_hierarchies[0].internal_elements[0]
            robot, vision_gate = cell.internal_elements

            print(cell.name)
            print("  +--", robot.name, "->", robot.ref_base_system_unit_path)
            print("  +--", vision_gate.name, "->", vision_gate.ref_base_system_unit_path)
            """,
            "inheritance-instance-tree",
        ),
        markdown(
            """
            ## 2. Follow the robot's class path

            `RobotArm` references `RobotModule`. That class inherits from
            `Cell`, so its effective shape combines knowledge from both classes.
            """,
            "inheritance-lineage-intro",
        ),
        code(
            """
            library = document.system_unit_class_libs[0]
            classes = {item.name: item for item in library.system_unit_classes}

            cell_class = classes["Cell"]
            robot_class = classes["RobotModule"]
            quality_class = classes["QualityGateModule"]

            print("RobotModule inherits from", robot_class.ref_base_class_path)
            """,
            "inheritance-lineage",
        ),
        markdown(
            """
            ## 3. Compare declared and materialized members

            `cycleTime` comes from the base `Cell` class. `payload` and the four
            robot interfaces are declared directly on `RobotModule`.
            """,
            "inheritance-compare-intro",
        ),
        code(
            """
            print("Cell attributes:", [item.name for item in cell_class.attributes])
            print("RobotModule attributes:", [item.name for item in robot_class.attributes])
            print("RobotArm attributes:", [item.name for item in robot.attributes])
            """,
            "inheritance-compare-attributes",
        ),
        code(
            """
            print(
                "RobotModule interfaces:",
                [item.name for item in robot_class.external_interfaces],
            )
            print(
                "RobotArm interfaces:",
                [item.name for item in robot.external_interfaces],
            )
            """,
            "inheritance-compare-interfaces",
        ),
        markdown(
            """
            <details>
            <summary><strong>Predict the warning profile before running validation</strong></summary>

            Both child instances omit inherited `cycleTime`: two
            `missing-inherited-attribute` warnings. RobotArm omits `Power` and
            `MaterialOut`; VisionGate omits `MaterialOut`: three
            `missing-class-interface` warnings.
            </details>

            ## 4. Validate the prediction
            """,
            "inheritance-prediction",
        ),
        code(
            """
            from collections import Counter

            issues = document.caex_validation_issues(strict_xsd=True)
            counts = Counter(issue.code for issue in issues)

            print(counts)
            for issue in issues:
                print(f"{issue.severity.upper():7} {issue.code}: {issue.target}")
            """,
            "inheritance-validate",
        ),
        code(
            """
            expected = Counter({
                "missing-inherited-attribute": 2,
                "missing-class-interface": 3,
            })

            assert counts == expected
            assert all(issue.severity == "warning" for issue in issues)
            print("Prediction confirmed: five warnings and no errors.")
            """,
            "inheritance-validate-check",
        ),
        markdown(
            """
            ## 5. Why these are warnings

            A class can deliberately describe a 150% set of possible members;
            an occurrence may use only part of it. The SDK therefore reports
            missing materialization as reviewable warnings. Unresolved class
            paths, by contrast, are errors because their meaning cannot be found.

            We will assume this project expects full materialization.
            """,
            "inheritance-warning-meaning",
        ),
        markdown(
            """
            ## 6. Repair the inherited attributes

            We work on a deep copy so the warning example remains available for
            comparison.
            """,
            "inheritance-repair-attributes-intro",
        ),
        code(
            """
            from automationml import attribute

            repaired = document.model_copy(deep=True)
            repaired_cell = repaired.instance_hierarchies[0].internal_elements[0]
            repaired_robot, repaired_vision = repaired_cell.internal_elements
            """,
            "inheritance-repair-copy",
        ),
        code(
            """
            repaired_robot.attributes.append(
                attribute(
                    "cycleTime", 12, unit="s", data_type="xs:double",
                    ref_attribute_type="LineAttributeTypes/CycleTime",
                )
            )
            """,
            "inheritance-repair-robot-attribute",
        ),
        code(
            """
            repaired_vision.attributes.append(
                attribute(
                    "cycleTime", 6, unit="s", data_type="xs:double",
                    ref_attribute_type="LineAttributeTypes/CycleTime",
                )
            )

            remaining = repaired.caex_validation_issues()
            assert Counter(issue.code for issue in remaining) == Counter(
                {"missing-class-interface": 3}
            )
            print("Attribute warnings repaired; three interface warnings remain.")
            """,
            "inheritance-repair-vision-attribute",
        ),
        markdown(
            """
            ## 7. Repair RobotArm's class interfaces

            Interface IDs belong to occurrences. Their class paths preserve the
            shared interface meaning.
            """,
            "inheritance-repair-robot-interfaces-intro",
        ),
        code(
            """
            from automationml import external_interface

            repaired_robot.external_interfaces.append(
                external_interface(
                    "Power", id="medium-robot-power",
                    ref_base_class_path="AutomationMLInterfaceClassLib/PowerPort",
                )
            )
            """,
            "inheritance-repair-robot-power",
        ),
        code(
            """
            repaired_robot.external_interfaces.append(
                external_interface(
                    "MaterialOut", id="medium-robot-material-out",
                    ref_base_class_path="AutomationMLInterfaceClassLib/MaterialPort",
                )
            )
            """,
            "inheritance-repair-robot-material",
        ),
        markdown(
            """
            ## 8. Repair VisionGate's remaining interface
            """,
            "inheritance-repair-vision-interface-intro",
        ),
        code(
            """
            repaired_vision.external_interfaces.append(
                external_interface(
                    "MaterialOut", id="medium-quality-material-out",
                    ref_base_class_path="AutomationMLInterfaceClassLib/MaterialPort",
                )
            )

            repaired_issues = repaired.caex_validation_issues(strict_xsd=True)
            assert repaired_issues == []
            print("The intended class shape is now fully materialized.")
            """,
            "inheritance-repair-vision-interface",
        ),
        markdown(
            """
            ## 9. Add a link between repaired interfaces

            The cell owns both children, so it also owns their InternalLink.
            """,
            "inheritance-link-intro",
        ),
        code(
            """
            from automationml import InternalLink

            repaired_cell.internal_links.append(
                InternalLink(
                    name="RobotToVision",
                    ref_partner_side_a="medium-cell-robot:MaterialOut",
                    ref_partner_side_b="medium-cell-quality:MaterialIn",
                )
            )

            assert repaired.caex_validation_issues(strict_xsd=True) == []
            print("RobotToVision resolves both interface partners.")
            """,
            "inheritance-link",
        ),
        markdown(
            """
            ## 10. Compare a real error

            We break a copy of the link. Unlike an intentionally omitted class
            member, a missing partner cannot describe a usable connection.
            """,
            "inheritance-error-intro",
        ),
        code(
            """
            broken = repaired.model_copy(deep=True)
            broken_link = broken.instance_hierarchies[0].internal_elements[0].internal_links[-1]
            broken_link.ref_partner_side_b = "medium-cell-quality:MissingPort"

            broken_issues = broken.caex_validation_issues()
            for issue in broken_issues:
                print(issue.severity.upper(), issue.code, issue.target)
            """,
            "inheritance-error",
        ),
        code(
            """
            assert Counter(issue.code for issue in broken_issues) == Counter(
                {"unresolved-internal-link-partner": 1}
            )
            assert broken_issues[0].severity == "error"
            print("The unresolved partner is correctly classified as an error.")
            """,
            "inheritance-error-check",
        ),
        markdown(
            """
            ## Your turn

            Remove one different member from a copy of `repaired`. Predict the
            issue code before validating. Then decide whether your own project
            would accept that warning or require full materialization.

            ## Takeaways

            - Effective class shape combines local and inherited members.
            - Missing materialization is a warning because 150% classes can be intentional.
            - Structured issue codes make expectations testable and navigable.
            - Unresolved class paths and link partners are errors.
            - The policy decision belongs to the project; the validator supplies evidence.
            """,
            "inheritance-summary",
        ),
    ],
)


def write_notebook(file_name: str, content: dict[str, Any]) -> None:
    LEARNING.mkdir(parents=True, exist_ok=True)
    path = LEARNING / file_name
    path.write_text(
        json.dumps(content, indent=1, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    legacy_files = (
        "01_first-automationml-model.ipynb",
        "02_inheritance-interfaces-and-validation.ipynb",
    )
    for file_name in legacy_files:
        legacy_path = LEARNING / file_name
        if legacy_path.exists():
            legacy_path.unlink()

    write_notebook("01_build-a-drive-station.ipynb", NOTEBOOK_ONE)
    write_notebook("02_json-and-xml-exchange.ipynb", NOTEBOOK_TWO)
    write_notebook("03_inheritance-interfaces-and-validation.ipynb", NOTEBOOK_THREE)
