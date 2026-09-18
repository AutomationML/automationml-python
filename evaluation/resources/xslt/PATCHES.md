# AML-UA-XSLT local patch set

The stylesheets in this directory are based on AutomationML/AML-UA-XSLT commit
`e38653c1bc58ffc658595093e0a2d163a7ecebf7`. The SDK identifies the current
XSLT comparison contract as `automationml-xslt-v3`; the corresponding Python
semantic reverse profile is `automationml-python-semantic-v3`. Since
2026-08-17, the app and SDK forward default is the typed Python mapper
`automationml-python-bidirectional-v1`; these stylesheets remain the explicit
`mapper="xslt"` breadth baseline.

This v3 contract is now classified as transitional AML-origin source recovery.
It is not the accepted definition of OPC-UA-first reverse interoperability. The
target is the strict implicit profile documented in
`docs/opcua-strict-implicit-mapping.md`: native OPC UA and
companion-model semantics are authoritative, reverse output is canonical AML,
and `__AMLMeta_` properties are not required.

Do not infer Python-profile behavior from this transitional patch inventory.
In particular, the Python mapper uses standard `HasComponent` plus companion
constraint TypeDefinitions (not the invented `HasConstraint` aliases), emits
consistent inverse hierarchy edges, and materializes real Part 19 dictionary
entry Objects instead of dangling semantic NodeIds. The raw, runner, patched,
and Python systems remain separately identified in every comparison report.

Corrections are made at the XSLT generation sites. Python independently
validates the resulting UANodeSet and never repairs generated nodes or
references.

## Upstream correctness fixes

- `RequiredValue`, `RequiredMinValue`, and `RequiredMaxValue` aliases receive
  exactly one namespace prefix, and constraint components use `HasComponent`.
- Generated model versions default to `0.0.0`; publication dates come from the
  explicit, reproducible `publication-date` transform parameter.
- `xs:ID` and `xs:token` map to OPC UA `String`, `xs:dateTime` maps to `DateTime`, and
  datatype-table comparisons normalize case and whitespace.
- External-reference aliases are removed before class lookup, and resolved
  class/type references are emitted as namespace-qualified NodeIds.
- Repeated `SourceDocumentInformation` elements receive unique, consistently
  referenced NodeIds.
- Nested class trees expose `Organizes` edges, standard-named AML libraries are
  not silently excluded, and library descriptions, versions, IDs, and class
  inheritance are retained.

## Transitional semantic-v3 source-recovery contract

The normative companion references remain the primary OPC UA projection. Local
document-namespace `PropertyType` nodes and structured relationship objects
retain AML distinctions that the companion model cannot express by itself.

- Attribute `Description` uses standard UANodeSet `Documentation`.
- Exact `AttributeDataType`, `DefaultValue`, `Unit`, and `RefAttributeType`
  values use `AMLAttributeDataType`, `AMLDefaultValue`, `AMLUnit`, and
  `AMLRefAttributeType` properties. The main variable contains only the current
  CAEX `Value`.
- Ordered `RefSemantic` values use `AMLRefSemantic_1`,
  `AMLRefSemantic_2`, and so on. Recognizable ECLASS/IRDI and URI identifiers
  additionally use OPC UA Part 19 `HasDictionaryEntry` (`i=17597`) references
  in the standard IRDI or URI dictionary namespace. Arbitrary AML semantic
  strings remain exact local properties and are not mislabeled as dictionary
  entries.
- The obsolete local `HasReferenceType`/`i=4003` invention and misspelled
  `RefSematic` variables are not emitted.
- Exact class and role paths use `AMLRefBaseSystemUnitPath`,
  `AMLRefBaseClassPath`, `AMLRefBaseRoleClassPath`, and
  `AMLRefRoleClassPath`; native `HasTypeDefinition`, `HasSubtype`, and
  `HasAMLRoleReference` relationships remain present.
- `RoleRequirements` and `SupportedRoleClass` are represented by structured
  `BaseObjectType` components because the companion model's shared
  `HasAMLRoleReference` cannot distinguish the two or carry nested payload.
  Their `MappingObject` pairs use ordered `AMLAttributeNameMapping_*` and
  `AMLInterfaceIDMapping_*` String properties.
- Interfaces retain native `HasAMLInternalLink` relationships. Each CAEX
  `InternalLink` is also a structured component with exact name, optional ID,
  description, and `AMLRefPartnerSideA` / `AMLRefPartnerSideB` properties.
- External-reference alias/path pairs use ordered
  `AMLExternalReferenceAlias_*` and `AMLExternalReferencePath_*` properties.
- Constraints retain the upstream native constraint nodes and their XML
  representation; the reverse mapper verifies both representations agree.
- `AMLOriginalID` preserves the lexical ID spelling (including optional GUID
  braces) independently from the companion AML-ID projection. `AMLChangeMode`
  preserves CAEX lifecycle state.

The embedded AML extension remains available for byte/logical source recovery.
The semantic-v3 reverse profile does not depend on that extension for the
official AML-UA-XSLT unit inputs through `13_Facet`.
