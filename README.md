# AutomationML Python SDK

[![CI](https://github.com/AutomationML/automationml-python/actions/workflows/ci.yml/badge.svg)](https://github.com/AutomationML/automationml-python/actions/workflows/ci.yml)

A JSON-first Python SDK for creating, reading, validating, and converting
AutomationML CAEX 3.0 documents.

The SDK is based on the CAEX 3.0 XSD shape, but its primary developer experience
is Pydantic and AML JSON: readable Python attributes in code, canonical
AutomationML names in serialized JSON, and XML when an existing AML toolchain
requires `.aml` output.

> **Project status:** Alpha. The core model, JSON/XML round trips, schema
> generation, and semantic validation are usable, but the public API may still
> change before the first stable release.

## Requirements

- Python 3.11 or newer
- Pydantic 2

## Installation

Install the current development version from a local checkout:

```bash
python -m pip install -e .
```

Install development and validation dependencies:

```bash
python -m pip install -e ".[dev]"
```

Once the first package release is available, the intended installation command
will be:

```bash
python -m pip install automationml
```

## Design stance

- Python API: `snake_case` fields and small builder helpers.
- JSON serialization: canonical CAEX names such as `InstanceHierarchy`,
  `InternalElement`, `RefBaseSystemUnitPath`, and `SchemaVersion`.
- XML serialization: explicit adapter, namespace-aware, ordered according to the
  CAEX object model.
- Semantic validation: structured issues for unresolved class paths, duplicate
  IDs, attribute type references, role links, interface references, and internal
  link partners.
- XSD conformance: practical by default so existing JSON examples load, with
  stricter checks available through `assert_caex_valid(strict_xsd=True)`.

## Quick start

```python
from automationml import attribute, caex_file, instance_hierarchy, internal_element

doc = caex_file("plant.aml")
motor = internal_element(
    "Motor",
    id="ie-1",
    ref_base_system_unit_path="ExampleSystemUnitClassLib/Motor",
    attributes=[attribute("speed", 1500, unit="rpm", data_type="xs:double")],
    role_paths=["ExampleRoleClassLib/Drive"],
)

doc.instance_hierarchies.append(
    instance_hierarchy("Plant", internal_elements=[motor])
)

json_text = doc.to_aml_json()
xml_text = doc.to_aml_xml()

for issue in doc.caex_validation_issues():
    print(issue.code, issue.path, issue.message)
```

The JSON output stays compact and canonical:

```json
{
  "SchemaVersion": "3.0",
  "FileName": "plant.aml",
  "SourceDocumentInformation": [
    {
      "OriginName": "AutomationML Python SDK",
      "OriginID": "automationml-python",
      "OriginVersion": "0.1.0",
      "LastWritingDateTime": "2026-06-28T00:00:00Z"
    }
  ],
  "InstanceHierarchy": [
    {
      "Name": "Plant",
      "InternalElement": [
        {
          "ID": "ie-1",
          "Name": "Motor",
          "RefBaseSystemUnitPath": "ExampleSystemUnitClassLib/Motor",
          "Attribute": [
            {
              "Name": "speed",
              "Value": "1500",
              "Unit": "rpm",
              "AttributeDataType": "xs:double"
            }
          ],
          "RoleRequirements": [
            {
              "RefBaseRoleClassPath": "ExampleRoleClassLib/Drive"
            }
          ]
        }
      ]
    }
  ]
}
```

## Generate the JSON Schema

```bash
python -m automationml.schema --output schemas/automationml.caex3.schema.json
```

The generated schema is intentionally keyed by AML names. That makes it useful
for non-Python producers and validators while preserving a clean Python SDK.

## Semantic validation

Use `caex_validation_issues()` when an application needs structured validation
results. Each issue includes `severity`, `code`, `path`, `message`, and optional
`target` / `suggestion` fields. Use `reference_index()` when authoring tools
need to resolve AML paths such as `SystemUnitClassLib/Motor` or
`RoleClassLib/Drive`.

Validation is intentionally non-destructive. Invalid or incomplete documents
can still be loaded and inspected, while applications decide which issue
severities should block their workflows.

## Validation example suite

Ready-to-upload AML JSON and AML XML examples live in
`examples/validation-suite`. The suite includes small, medium, and big positive
and negative cases, plus a `manifest.json` with expected SDK validation issue
counts. The SDK test suite reads these same files so the public examples stay
locked to the validator.

## Development

```bash
python -m pip install -e ".[dev]"
pytest
```

Build the source distribution and wheel:

```bash
python -m pip install build
python -m build
```

## Repository layout

- `src/automationml/`: public SDK models, builders, serialization, schema, and
  validation APIs.
- `tests/`: unit, round-trip, schema, and semantic validation tests.
- `examples/validation-suite/`: catalog of valid, invalid, and warning-focused
  AML JSON/XML documents.
- `schemas/`: generated AML JSON Schema artifacts.
- `docs/`: design and SDK documentation.
- `tools/`: repository maintenance and generation utilities.

## Contributing

Issues and pull requests are welcome. Before submitting a change, install the
development dependencies and run the complete test suite:

```bash
pytest
```

Changes to validation behavior should include a focused test and, when useful
to SDK consumers, a matching example in the validation suite.

The optional `xml` extra is reserved for pydantic-xml integration work. The
current XML adapter is kept separate from the public model so XML concerns do
not dominate the JSON-first model design.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
