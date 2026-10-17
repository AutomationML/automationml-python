# AutomationML and OPC UA

[OPC UA](https://opcfoundation.org/about/opc-technologies/opc-ua/) is the
communication standard many machines and controllers use to publish their
information models. Those models are exchanged as *UANodeSet* XML files. The
SDK can turn an AutomationML document into a NodeSet and turn a supported
NodeSet back into AutomationML, so the same plant model can be engineered in
AutomationML and served over OPC UA.

The conversion follows a versioned mapping profile (`strict-implicit-v1`). It
is not a claim to convert arbitrary third-party NodeSets: unsupported or
ambiguous features fail explicitly instead of being guessed.

## Install

The OPC UA runtime needs `lxml`, which the `opcua` extra installs:

```bash
python -m pip install "automationml[opcua]"
# or, from a local checkout:
python -m pip install -e ".[opcua]"
```

## Convert in both directions

```python
from pathlib import Path

from automationml import CAEXFile

aml_xml = Path("examples/validation-suite/xml/small-valid-motor.aml").read_bytes()
document = CAEXFile.from_aml_xml(aml_xml)

# AutomationML -> OPC UA
nodeset = document.to_opcua_nodeset()        # typed Python graph
nodeset_xml = document.to_opcua_nodeset_xml()  # UANodeSet XML text

# OPC UA -> AutomationML, using the semantic reverse mapping
semantic = CAEXFile.from_opcua_nodeset_xml(nodeset_xml)

# An archival export can embed the original AML for exact recovery.
archival_nodeset = document.to_opcua_nodeset_xml(include_roundtrip=True)
archival_recovery = CAEXFile.from_opcua_nodeset_xml(archival_nodeset)

# Select the semantic path explicitly, even for an archival export.
semantic = CAEXFile.from_opcua_nodeset_xml(
    archival_nodeset,
    prefer_embedded_source=False,
)
```

## Check that nothing is lost

A round trip converts in both directions without embedding the source and
reports every difference it finds:

```python
roundtrip = document.round_trip_opcua(publication_date="2026-08-17")
recovered = roundtrip.assert_equivalent()

# The lifecycle may start from an OPC-UA-authored graph as well.
opcua_roundtrip = nodeset.round_trip_automationml(publication_date="2026-08-17")
canonical_nodeset = opcua_roundtrip.assert_equivalent()
```

Both round-trip results expose `differences` as frozen Pydantic records. Each
record has an RFC 6901-style JSON Pointer such as
`/InstanceHierarchy/0/InternalElement/0/Attribute/0/Value`, a change kind, and
the source/recovered values. `semantically_equivalent` is computed from this
evidence rather than stored as an independently writable Boolean.

## Inspect the OPC UA graph

```python
from automationml.opcua_nodeset import UANodeSet

graph = UANodeSet.from_xml(nodeset_xml)
# Equivalent Python-first path, without an XML serialization step:
graph = document.to_opcua_nodeset()
file_node = graph.node("ns=1;s=CAEXFile")
properties = graph.outgoing(file_node.node_id, "HasProperty")
```

The OPC UA authoring layer uses immutable Pydantic value objects and an explicit
mutable `UANodeSetBuilder`. `UANodeSet.from_xml()` and `to_xml()` allow the
supported graph to be inspected independently of either mapper. Forward and
reverse conversion share validated datatype and contextual role-reference
rules, including their documented canonical inverses. This prevents the two
directions from silently growing separate lookup tables. See the
[SDK design notes](sdk-design.md#opc-ua-roundtripping-contract) for the
contract behind these types.

## What the mapping covers

The default forward mapper builds a typed Pydantic OPC UA graph and validates
the serialized UANodeSet without output repair. The strict profile covers file
metadata, instance trees, attributes and datatypes, all four class-library
kinds, inheritance/type relations, contextual roles and MappingObjects,
interfaces, directed InternalLinks, constraints, mirrors, facets, and real OPC
UA Part 19 dictionary-entry Objects. Unsupported or ambiguous features fail
explicitly.

The Python semantic reverse maps supported OPC UA graphs to canonical AML
without requiring an embedded source payload. It also reads NodeSets produced
by the AutomationML/OPC Foundation working-group XSLT like any other supported
graph. The [strict-implicit mapping profile](opcua-strict-implicit-mapping.md)
documents every induced and canonical reverse choice.

## Evidence and comparison with the working-group XSLT

The pinned, patched AutomationML/OPC Foundation XSLT is retained as a
development comparison engine in `evaluation/`, not as SDK API: it scores 1/121
against the Python mapper's 121/121, so it is evidence rather than a conversion
path anyone should ship.

The versioned [mapper comparison test plan](opcua-mapper-comparison-test-plan.md)
defines the independent oracles, 120-case minimum corpus, OPC-UA-origin cases,
and publication gates used to compare the Python profile with the unmodified
working-group XSLT.

The frozen release corpus declares 145 cases, of which 121 are scored. The
current evidence is `PY-STRICT` 121/121 versus unmodified `XSLT-RAW` 1/121,
with 30/30 versus 1/30 critical cases. Inspect the
[release manifest](../tests/opcua-comparison/release-manifest.json),
[complete result matrix](reports/opcua-release-comparison/report.md),
[scale report](reports/opcua-scale/report.md), and
[expert-review checklist](opcua-mapping-review-checklist.md).

Regenerate the release JSON, JUnit, and Markdown evidence with the evaluation
dependencies installed (`python -m pip install -e ".[xml,opcua-evaluation]"`):

```bash
python tools/compare_opcua_mappers.py \
  --manifest tests/opcua-comparison/release-manifest.json \
  --output-dir build/opcua-release

python tools/benchmark_opcua_scale.py \
  --repeats 1 \
  --output-dir build/opcua-scale
```

The [evaluation harness README](../evaluation/README.md) explains why that
tooling lives outside the distributed package.
