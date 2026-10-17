# AutomationML Python SDK

[![CI](https://github.com/AutomationML/automationml-python/actions/workflows/ci.yml/badge.svg)](https://github.com/AutomationML/automationml-python/actions/workflows/ci.yml)

Create, read, check, and convert [AutomationML](https://www.automationml.org/)
files from Python.

```python
from automationml import attribute, caex_file, instance_hierarchy, internal_element

doc = caex_file("plant.aml")
motor = internal_element("Motor-1", attributes=[attribute("speed", 1500, unit="rpm")])
doc.instance_hierarchies.append(instance_hierarchy("Plant", internal_elements=[motor]))

doc.to_aml_json()  # AML JSON, for web apps and scripts
doc.to_aml_xml()   # CAEX XML, for AutomationML tools such as the AutomationML Editor
```

> **Project status: alpha.** The core model, JSON/XML conversion, and
> validation work and are tested, but the Python API may still change before
> the first stable release.

## Contents

- [What is AutomationML?](#what-is-automationml)
- [Installation](#installation)
- [Tutorial: your first plant model](#tutorial-your-first-plant-model)
- [Validation](#validation)
- [Python names and file names](#python-names-and-file-names)
- [What else can it do?](#what-else-can-it-do)
- [Learn more](#learn-more)
- [Development](#development)

## What is AutomationML?

AutomationML (IEC 62714) is an open, XML-based format for exchanging
engineering data between the tools used to plan a production plant:
mechanical design, electrical design, PLC programming, simulation, and so on.
Instead of re-typing the same motor in five tools, each tool reads and writes
one shared AutomationML file.

An AutomationML file (`.aml`) is a *CAEX* document (IEC 62424). It has two
halves: the **plant you are describing**, and **libraries of reusable
definitions** that the plant refers to.

```text
plant.aml                        CAEXFile             the whole document
├── Plant                        InstanceHierarchy    the real plant, as a tree
│   └── Motor-1                  InternalElement      one object in the plant
│       ├── speed = 1500 rpm     Attribute            a property of the object
│       └── Power                ExternalInterface    a connection point
└── MyComponents                 SystemUnitClassLib   a library of templates
    └── Motor                    SystemUnitClass      "what a motor looks like"
```

The main building blocks:

| Term | What it means |
| --- | --- |
| **InstanceHierarchy** | The plant itself: a tree of objects such as lines, cells, robots, and motors. |
| **InternalElement** | One object in that tree. It can contain other InternalElements. |
| **Attribute** | A named property of an object, with an optional unit and data type, such as `speed = 1500 rpm`. |
| **ExternalInterface** | A connection point on an object, such as a power port or a signal. |
| **InternalLink** | Connects two interfaces, such as a cable from a power supply to a motor. |
| **SystemUnitClass** | A reusable template for objects ("a Motor has a speed and a power port"). Objects point to it with `RefBaseSystemUnitPath`. |
| **RoleClass** | A vendor-neutral description of what an object *is* ("this is a drive"). Objects declare it with `RoleRequirements`. |
| **InterfaceClass**, **AttributeType** | Reusable definitions for interfaces and attributes. |

Libraries and classes are referenced by path, such as `MyComponents/Motor`.

This SDK lets you work with all of that as ordinary Python objects. It saves to
**AML XML**, the standard `.aml` format every AutomationML tool understands,
and to **AML JSON**, a JSON form with the same structure that is easier to use
from web applications and scripts.

## Installation

You need Python 3.11 or newer. A
[virtual environment](https://docs.python.org/3/library/venv.html) is
recommended:

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
```

The package is not on PyPI yet. Install the latest version from GitHub:

```bash
python -m pip install "automationml @ git+https://github.com/AutomationML/automationml-python"
```

Or install from a local checkout if you want to edit the code or run the
learning notebooks:

```bash
git clone https://github.com/AutomationML/automationml-python
cd automationml-python
python -m pip install -e .
```

Optional features need extra dependencies, which you select in square
brackets, for example `python -m pip install -e ".[opcua,rdf]"`:

| Extra | Adds |
| --- | --- |
| `opcua` | Conversion to and from OPC UA NodeSets |
| `rdf` | Conversion to and from RDF/Turtle |
| `learning` | Jupyter, for the [learning notebooks](learning/) |
| `dev` | Everything needed to run the test suite |

## Tutorial: your first plant model

This walkthrough uses only the base installation. Run the snippets in order in
one Python session.

### 1. Build a plant

```python
from automationml import attribute, caex_file, instance_hierarchy, internal_element

# A new, empty AutomationML document
doc = caex_file("my-first-plant.aml")

# One motor with one attribute
motor = internal_element(
    "Motor-1",
    id="motor-1",
    attributes=[attribute("speed", 1500, unit="rpm", data_type="xs:double")],
)

# The plant is an InstanceHierarchy that contains the motor
doc.instance_hierarchies.append(
    instance_hierarchy("Plant", internal_elements=[motor])
)

print(doc.to_aml_json())
```

The printed AML JSON uses the official AutomationML names:

```json
{
  "SuperiorStandardVersion": [
    "AutomationML 2.1"
  ],
  "SourceDocumentInformation": [
    {
      "OriginName": "AutomationML Python SDK",
      "OriginID": "automationml-python",
      "OriginVersion": "0.1.0",
      "LastWritingDateTime": "2026-10-17T12:00:00Z"
    }
  ],
  "InstanceHierarchy": [
    {
      "Name": "Plant",
      "InternalElement": [
        {
          "ID": "motor-1",
          "Name": "Motor-1",
          "Attribute": [
            {
              "Name": "speed",
              "Value": "1500",
              "Unit": "rpm",
              "AttributeDataType": "xs:double"
            }
          ]
        }
      ]
    }
  ],
  "SchemaVersion": "3.0",
  "FileName": "my-first-plant.aml"
}
```

`SourceDocumentInformation` records which tool wrote the file and when; the
SDK fills it in for you.

### 2. Save and load files

```python
from automationml import dump_json, dump_xml, load_json, load_xml

dump_json(doc, "my-first-plant.json")  # AML JSON
dump_xml(doc, "my-first-plant.aml")    # AML XML, opens in AutomationML tools

again = load_xml("my-first-plant.aml")
assert again.to_aml_dict() == doc.to_aml_dict()  # nothing was lost
```

`load_xml` reads both CAEX 3.0 and older CAEX 2.15 files. Older files are
upgraded to CAEX 3.0 automatically, with a warning.

### 3. Let validation find a mistake

Point the motor at a template that does not exist yet, then ask the SDK to
check the document:

```python
motor.ref_base_system_unit_path = "MyComponents/Motor"

for issue in doc.caex_validation_issues():
    print(issue.severity, issue.code)
    print("  at", issue.path)
    print("  ", issue.message)
```

```text
error unresolved-system-unit-class-reference
  at $.InstanceHierarchy[0].InternalElement[0].RefBaseSystemUnitPath
   Unresolved SystemUnitClass reference 'MyComponents/Motor'.
```

### 4. Fix it with a class library

Add the missing library with a `Motor` template:

```python
from automationml import system_unit_class, system_unit_class_lib

doc.system_unit_class_libs.append(
    system_unit_class_lib(
        "MyComponents",
        classes=[
            system_unit_class(
                "Motor",
                attributes=[attribute("speed", unit="rpm", data_type="xs:double")],
            )
        ],
    )
)

assert doc.caex_validation_issues() == []  # the reference resolves now
```

`role_class_lib`, `interface_class_lib`, and `attribute_type_lib` build the
other three kinds of library in the same way.

### 5. Create objects from the template

```python
motor_2 = doc.instantiate_system_unit_class("MyComponents/Motor", name="Motor-2")
doc.instance_hierarchies[0].internal_elements.append(motor_2)

print(motor_2.ref_base_system_unit_path)        # MyComponents/Motor
print([a.name for a in motor_2.attributes])     # ['speed']
```

The new object copies the template's attributes, interfaces, and children,
including inherited ones, and gets a fresh unique ID.

**Next step:** the [learning notebooks](learning/) continue from here with
interfaces, links, roles, and inheritance.

## Validation

`caex_validation_issues()` checks a document and returns a list of issues.
Each issue has:

- `severity`: `error` for broken documents, `warning` for best-practice hints;
- `code`: a stable identifier such as `duplicate-id`;
- `path`: where the problem is, such as `$.InstanceHierarchy[0].InternalElement[0]`;
- `message`, and optional `target` and `suggestion`.

Validation never changes or rejects your document, so incomplete files can
still be loaded and inspected; your application decides which severities
matter. It checks, among other things, that class, role, interface, and
attribute-type references resolve, that IDs are unique, and that InternalLinks
connect existing interfaces.

```python
doc.assert_caex_valid()                 # raise if there are issues
doc.assert_caex_valid(strict_xsd=True)  # also enforce every XSD-required field
```

The [validation suite](examples/validation-suite/) contains small, medium, and
large example files, valid and invalid, in both JSON and XML, with the issues
each one is expected to produce.

## Python names and file names

In Python you use `snake_case` names. In AML JSON and XML the SDK writes the
official CAEX names:

| Python | AML JSON / XML |
| --- | --- |
| `doc.file_name` | `FileName` |
| `doc.instance_hierarchies` | `InstanceHierarchy` |
| `element.internal_elements` | `InternalElement` |
| `element.ref_base_system_unit_path` | `RefBaseSystemUnitPath` |
| `element.role_requirements` | `RoleRequirements` |

All models are [Pydantic](https://docs.pydantic.dev/) models, so you can also
build them from dictionaries that use either kind of name, and they check your
values as you assign them. Editors and type checkers such as VS Code (Pylance),
pyright, and mypy understand the `snake_case` names, so you get autocompletion
and warnings for typos or missing required fields.

## What else can it do?

| Feature | Start here |
| --- | --- |
| Find objects by ID or path, follow references, and walk inheritance | `doc.query()` in the [core-platform guide](docs/core-platform.md#queries-and-instantiation) |
| Edit with automatic undo information, and diff two documents | `doc.edit()`, `diff_documents()` in the [core-platform guide](docs/core-platform.md#changes-and-transactions) |
| Merge two documents with explicit conflict rules | `merge_documents()` in the [core-platform guide](docs/core-platform.md#atomic-merge) |
| Load libraries referenced from other `.aml` files | `FileSystemResolver` in the [core-platform guide](docs/core-platform.md#local-external-references) |
| Inspect what happened when upgrading a CAEX 2.15 file | `CAEXFile.import_aml_xml()` in the [core-platform guide](docs/core-platform.md#legacy-import) |
| Convert to and from OPC UA NodeSets | The [OPC UA guide](docs/opcua.md) (needs the `opcua` extra) |
| Convert to and from RDF/Turtle | See below (needs the `rdf` extra) |
| Validate AML JSON from non-Python tools | See [JSON Schema](#json-schema) |

### RDF/Turtle

```python
from automationml import CAEXFile

ttl = doc.to_ttl()                          # Turtle text
restored = CAEXFile.from_ttl(ttl)           # and back
doc.round_trip_ttl().assert_equivalent()    # check that nothing is lost
```

The [RDF mapping notes](docs/rdf-mapping-audit.md) explain the mapping and how
it replaces the earlier `AML2TTL.xslt` stylesheet.

### JSON Schema

A JSON Schema for AML JSON lives in
[`schemas/automationml.caex3.schema.json`](schemas/automationml.caex3.schema.json).
Other languages and tools can use it to check AML JSON. Regenerate it after
changing the models:

```bash
python -m automationml.schema --output schemas/automationml.caex3.schema.json
```

## Learn more

- [`learning/`](learning/): three hands-on Jupyter notebooks. Install them with
  `python -m pip install -e ".[learning]"`, then run `jupyter lab learning`.
  1. Build a drive station step by step, from objects to reusable classes.
  2. Save one model as AML JSON and AML XML and prove both are equivalent.
  3. Explore inheritance and interfaces, fix validation warnings, and add an
     InternalLink.
- [`examples/validation-suite/`](examples/validation-suite/): ready-made valid
  and invalid example files.
- [`docs/core-platform.md`](docs/core-platform.md): queries, instantiation,
  editing, merging, external references, and CAEX 2.15 import.
- [`docs/opcua.md`](docs/opcua.md): AutomationML and OPC UA.
- [`docs/sdk-design.md`](docs/sdk-design.md): design decisions behind the
  JSON, Python, and XML contracts.

## Development

```bash
git clone https://github.com/AutomationML/automationml-python
cd automationml-python
python -m pip install -e ".[dev,xml]"
python -m pytest
```

Build the source distribution and wheel with:

```bash
python -m pip install build
python -m build
```

Repository layout:

- `src/automationml/`: the SDK package.
- `tests/`: the test suite.
- `examples/validation-suite/`: valid, invalid, and warning example documents.
- `learning/`: Jupyter lessons.
- `schemas/`: the generated AML JSON Schema and the CAEX 3.0 XSD.
- `docs/`: guides and design notes.
- `evaluation/`, `tools/`: OPC UA comparison tooling and maintenance scripts.

Issues and pull requests are welcome; see [CONTRIBUTING.md](CONTRIBUTING.md).
Changes to validation behavior should include a focused test and, where
useful, a matching example in the validation suite.

## License

MIT. See [LICENSE](LICENSE).
