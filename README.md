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

Install the optional OPC UA conversion runtime when UANodeSet export is needed:

```bash
python -m pip install "automationml[opcua]"
```

Install `automationml[opcua-xslt]` only when the retained Saxon/XSLT comparison
engine is required.

```python
from automationml import CAEXFile

document = CAEXFile.from_aml_xml(aml_xml)
nodeset = document.to_opcua_nodeset()
nodeset_xml = document.to_opcua_nodeset_xml()
archival_nodeset = document.to_opcua_nodeset_xml(include_roundtrip=True)

# The patched working-group XSLT is retained as a comparison engine.
xslt_baseline = document.to_opcua_nodeset_xml(mapper="xslt")

# Source-preserving only for exports that explicitly embed an AML payload.
archival_recovery = CAEXFile.from_opcua_nodeset_xml(archival_nodeset)

# The normal NodeSet uses the Python semantic reverse profile.
semantic = CAEXFile.from_opcua_nodeset_xml(nodeset_xml)

# The semantic path can also be selected explicitly for an app export.
semantic = CAEXFile.from_opcua_nodeset_xml(
    nodeset_xml,
    prefer_embedded_source=False,
)

# Exercise and inspect both directions without source embedding.
roundtrip = document.round_trip_opcua(publication_date="2026-08-17")
recovered = roundtrip.assert_equivalent()

# The lifecycle may start from an OPC-UA-authored graph as well.
opcua_roundtrip = nodeset.round_trip_automationml(
    publication_date="2026-08-17"
)
canonical_nodeset = opcua_roundtrip.assert_equivalent()
```

The default forward mapper builds a typed Pydantic OPC UA graph and validates
the serialized UANodeSet without output repair. The strict profile covers file
metadata, instance trees, attributes and datatypes, all four class-library
kinds, inheritance/type relations, contextual roles and MappingObjects,
interfaces, directed InternalLinks, constraints, mirrors, facets, and real OPC
UA Part 19 dictionary-entry Objects. Unsupported or ambiguous features fail
explicitly. The pinned, patched AutomationML/OPC Foundation XSLT remains
available through `mapper="xslt"`; it requires the `opcua-xslt` extra. The
Python semantic reverse maps supported OPC UA graphs to canonical AML without
requiring an embedded source payload. This is a versioned AutomationML mapping
profile, not a claim to convert arbitrary third-party NodeSets.

The OPC UA authoring layer uses immutable Pydantic value objects and an explicit
mutable `UANodeSetBuilder`. `UANodeSet.from_xml()` and `to_xml()` allow the
supported graph to be inspected independently of either mapper. Forward and
reverse conversion share validated datatype and contextual role-reference
rules, including their documented canonical inverses. This prevents the two
directions from silently growing separate lookup tables.

The versioned [mapper comparison test plan](docs/opcua-mapper-comparison-test-plan.md)
defines the independent oracles, 120-case minimum corpus, OPC-UA-origin cases,
and publication gates used to compare the Python profile with the unmodified
working-group XSLT. The companion
[strict-implicit mapping profile](docs/opcua-strict-implicit-mapping.md)
documents every induced and canonical reverse choice.

The frozen release corpus declares 145 cases, of which 121 are scored. The
current evidence is `PY-STRICT` 121/121 versus unmodified `XSLT-RAW` 1/121,
with 30/30 versus 1/30 critical cases. Inspect the
[release manifest](tests/opcua-comparison/release-manifest.json),
[complete result matrix](docs/reports/opcua-release-comparison/report.md),
[scale report](docs/reports/opcua-scale/report.md), and
[expert-review checklist](docs/opcua-mapping-review-checklist.md).
Regenerate the release JSON, JUnit, and Markdown evidence with:

```bash
python tools/compare_opcua_mappers.py \
  --manifest tests/opcua-comparison/release-manifest.json \
  --output-dir build/opcua-release

python tools/benchmark_opcua_scale.py \
  --repeats 1 \
  --output-dir build/opcua-scale
```

Both roundtrip results expose `differences` as frozen Pydantic records. Each
record has an RFC 6901-style JSON Pointer such as
`/InstanceHierarchy/0/InternalElement/0/Attribute/0/Value`, a change kind, and
the source/recovered values. `semantically_equivalent` is computed from this
evidence rather than stored as an independently writable Boolean.

```python
from automationml.opcua_nodeset import UANodeSet

graph = UANodeSet.from_xml(nodeset_xml)
# Equivalent Python-first path, without an XML serialization step:
graph = document.to_opcua_nodeset()
file_node = graph.node("ns=1;s=CAEXFile")
properties = graph.outgoing(file_node.node_id, "HasProperty")
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

## Learning notebooks

Three self-guided notebooks in `learning/` introduce AutomationML through the
same public SDK APIs used by applications:

1. Build a drive station progressively from concrete equipment to stable class
   semantics.
2. Round-trip one validated model through AML JSON and AML XML.
3. Explore SystemUnitClass inheritance, interface materialization, semantic
   warnings, repairs, and InternalLink partners.

Install the local learning environment and open the notebooks with:

```bash
python -m pip install -e ".[learning]"
jupyter lab learning
```

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
- `learning/`: executable, self-guided AutomationML lessons.
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
