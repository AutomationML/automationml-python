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
