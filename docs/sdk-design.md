# SDK Design Notes

## North star

AutomationML should have a first-class Python SDK, not just an XSD conversion.
The SDK should make JSON the everyday representation while still emitting valid
CAEX XML for existing AutomationML tools.

## JSON contract

The JSON serialization uses the canonical CAEX names from the XSD:

- XML elements become JSON object properties.
- XML attributes also become JSON object properties.
- Repeating XML elements are represented as arrays, even when they contain one
  item.
- Simple text XML elements such as `Description` and `Version` use
  `{ "value": "..." }` so their `ChangeMode` attribute can still be represented.

This keeps the JSON mechanically close to CAEX while remaining readable.

## Python contract

The Python API should not force CAEX casing into application code. A user writes:

```python
doc.instance_hierarchies[0].internal_elements[0].ref_base_system_unit_path
```

and the SDK serializes:

```json
{
  "InstanceHierarchy": [
    {
      "InternalElement": [
        {
          "RefBaseSystemUnitPath": "..."
        }
      ]
    }
  ]
}
```

## XML contract

XML is an adapter, not the primary model. The XML layer:

- uses the CAEX namespace `http://www.dke.de/CAEX`;
- emits elements in the XSD order;
- preserves CAEX attributes as XML attributes;
- can parse XML back into the same JSON-first models.

## Strictness

The SDK accepts existing practical JSON, including documents that omit
`SourceDocumentInformation`. The stricter XSD-required checks are available via:

```python
doc.assert_caex_valid(strict_xsd=True)
```

That split lets migration projects load real-world files first, then ratchet up
conformance when producing association-grade artifacts.

## OPC UA roundtripping contract

OPC UA conversion follows the same Python-first design:

- `UANode`, `UAReference`, `UAScalarValue`, `UAModel`, and `UANodeSet` are
  frozen Pydantic value objects with forbidden extra fields and shape checks.
- Repeated values are tuples and aliases are exposed as an immutable mapping,
  so a validated graph cannot be invalidated by mutating a nested collection.
- `UANodeSetBuilder` is the deliberate mutable boundary. It detects duplicate
  NodeIds when they are added and revalidates the complete graph at `build()`.
- `UANodeSet.from_xml()` and `to_xml()` provide a strict adapter for the subset
  used by the AutomationML mapping. Unsupported NodeClasses fail explicitly.
- `CAEXFile.to_opcua_nodeset()` returns that Pydantic graph directly; callers
  only use `to_opcua_nodeset_xml()` when XML is actually the boundary format.
- Forward and reverse converters use the same frozen `AMLUAMappingProfile`.
  Each many-to-one datatype rule declares its canonical AML inverse. Contextual
  role edges declare their AutomationML owner and reverse relationship.

The user-facing roundtrip operation never proves itself with embedded source
data:

```python
result = document.round_trip_opcua(publication_date="2026-08-17")

if result.semantically_equivalent:
    recovered = result.assert_equivalent()
else:
    print(result.source_document)
    print(result.recovered_document)
```

`OPCUARoundTripResult` intentionally retains the source model, generated
NodeSet XML, and reconstructed model. A Boolean alone would make a failed or
canonicalized mapping impossible to investigate.

The OPC UA side is an equal entry point:

```python
nodeset = UANodeSet.from_xml(opcua_xml)
document = nodeset.to_automationml()
result = nodeset.round_trip_automationml(publication_date="2026-08-17")
canonical_nodeset = result.assert_equivalent()
```

`UANodeSetRoundTripResult` verifies the semantic projection
`UA -> AML -> UA -> AML`. NodeIds, aliases, namespace prefixes, and XML order
may be canonicalized, so raw XML equality is deliberately not the criterion.
Tests replace all generated document NodeIds with OPC-UA-authored identifiers
and prove that reconstruction does not depend on the mapper's NodeId layout.

Both result types contain frozen `RoundTripDifference` records addressed by
JSON Pointer. Their `semantically_equivalent` field is computed from the empty
or non-empty difference tuple; callers cannot supply a contradictory Boolean.

Shared Python code does not make a non-injective standard mapping invertible.
Such cases must have a documented canonical inverse in the profile or fail as
ambiguous. This is the meaning of the strict-implicit policy.
