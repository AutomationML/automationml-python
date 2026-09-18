# CAEX core-platform APIs

The SDK treats CAEX 3.0 as its authoring model. CAEX 2.15 is accepted only at
an import boundary and is immediately upgraded; no 2.15 writer is exposed.

## Extension-safe XML

`AdditionalInformation` keeps simple text in `value` and non-trivial extension
content in `$xml`. Expanded XML names use ElementTree notation such as
`{urn:vendor}Item`. Attributes, text-before-children, child order, nested
elements, and child tails survive XML → model → JSON → model → XML. Namespace
prefixes, attribute order, formatting whitespace, and indentation are not part
of the fidelity guarantee. Unknown elements anywhere else in CAEX are rejected,
as are DTD and entity declarations.

The generated JSON Schema describes `XmlExtensionPayload` and
`XmlExtensionNode`. OPC UA carries the complete `AdditionalInformation` XML
fragment; converters must reject a structured extension if they cannot retain
it.

## Queries and instantiation

`document.query()` builds a new immutable lookup snapshot. Rebuild it after
mutating a Pydantic model directly.

```python
query = document.query()
motor = query.find_by_path("Equipment/Motor", kind="SystemUnitClass")
users = query.references_to(motor)
ports = query.connected_interfaces("interface-id")

instance = document.instantiate_system_unit_class(
    "Equipment/Motor",
    name="M-101",
)
document.instance_hierarchies[0].internal_elements.append(instance)
```

`find_by_id` and `find_by_path` return `None` when no object exists and raise
`AmbiguousReferenceError` when a lookup has multiple results. Their `all_*`
counterparts always return tuples. Instantiation resolves the full inheritance
chain, performs name-based derived overrides, allocates fresh UUID4 identifiers,
rewrites copied links/mappings, and returns an unattached element. Supplying an
`id_factory` makes generated IDs deterministic in tests.

Queries can also address a resolved external class as
`[Alias]Library/Class` by passing the resolver result's `documents` mapping to
`document.query(externals=...)`.

## Legacy import

```python
result = CAEXFile.import_aml_xml(data)
document = result.document
for issue in result.issues:
    print(issue.code, issue.path, issue.message)
```

`import_aml_xml` reports the detected version, whether conversion occurred, and
structured migration issues. Existing `from_aml_xml` and `load_xml` calls still
return a `CAEXFile`; for 2.15 input they emit `LegacyConversionWarning`.

The upgrader converts writer metadata, supported roles and mapping objects,
legacy interface-name mappings, attribute paths, InternalLink partners, and
mirror content using the original C# upgrader's move-to-master behavior.
Unresolvable or lossy conversions fail atomically. Input is validated against
the provenance-documented schema packaged at
`src/automationml/resources/caex/CAEX_ClassModel_V2.15.xsd`. The official AML
fixtures under `tests/vendor/aml-ua-xslt-e38653c` exercise that exact schema;
every successful fixture upgrade is then checked against
`schemas/caex/CAEX_ClassModel_V.3.0.xsd`.

## Changes and transactions

```python
edit = document.edit()
with edit as working:
    working.file_name = "revised.aml"
result = edit.result
restored = result.inverse.apply(result.document)
```

`diff_documents(before, after)` returns a `ChangeSet` of RFC 6901 addressed
`add`, `remove`, and `replace` operations. Each operation stores its old and new
values. Source/result SHA-256 digests prevent applying a patch to the wrong
document, and `inverse()` is deterministic. Apply and edit operations always
return new validated documents; an exception inside an edit context discards
the working copy.

## Atomic merge

`merge_documents(target, source, policy=MergePolicy())` never mutates either
input. The default policy reports conflicts. Per collision category, callers
can select `keep_target`, `replace_target`, deterministic `rename_source`, or
`remap_source_ids` where applicable. A successful `MergeResult` includes the
new document, reference rewrites, validation warnings, and a `ChangeSet` from
the target.

All four class-library kinds are merged recursively by class path. Identical
definitions and source metadata are deduplicated. IDs, aliases, class paths,
links, mappings, and mirror references are rewritten when their selected policy
changes a target.

## Local external references

```python
resolver = FileSystemResolver(project_directory)
resolution = resolve_external_references(
    document,
    resolver,
    recursive=True,
)
```

The filesystem resolver confines relative paths to its explicit base directory
and rejects path traversal. Absolute paths require `allow_absolute=True`.
Results contain documents and import diagnostics but are not merged
automatically. Duplicate aliases, missing files, cycles, and depth overflow are
reported as `ResolutionIssue` records. `resolve_and_merge` is the opt-in
convenience for resolving one reference and passing it through the same atomic
merge service.
