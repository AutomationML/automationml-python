# OPC UA strict-implicit mapping profile

Status: executable profile, version 1  
Scope: the Python AML/OPC UA forward and reverse mappers

This profile accepts implicit graph semantics when the inverse is unique. It
does not add ordering fields, generated-source paths, or embedded AML merely to
make a roundtrip exact. When a graph cannot determine one AML meaning, the
mapper either applies a documented canonical choice or rejects the graph.

## Model and hierarchy contract

- Application NodeSets require the OPC UA namespace and AutomationML companion
  namespace `http://opcfoundation.org/UA/AML/` version `1.00`, publication date
  `2026-06-25`.
- The CAEXFile instance is organized below OPC UA's Objects folder (`i=85`).
  Every local `Organizes`, `HasComponent`, and `HasProperty` containment edge
  is emitted in both directions; instance children also carry the matching
  `ParentNodeId`.
- Type nodes receive an inverse hierarchical reference but no `ParentNodeId`,
  because NodeSet2 does not allow that attribute on ObjectTypes or
  VariableTypes.
- Profile version 1 supports and scale-tests a CAEX containment depth of 64.
  Deeper input is outside this release profile and must not be silently
  truncated.

## Identity and ordering

- OPC UA NodeIds are transport identities. Reverse mapping never derives AML
  semantics from their spelling or generation pattern.
- XML node order, reference order, namespace prefixes, namespace indexes, and
  alias spelling are not semantic.
- UUID braces are lexical only. AML IDs are canonicalized to unbraced UUIDs.
- XML attribute line breaks and tabs are canonicalized according to XML
  attribute whitespace handling.
- Collections which are semantic sets are sorted by their semantic fields on
  reverse. No private order property is emitted.

## Datatypes, values, defaults, and units

- `Value` is the `UAVariable` value.
- `DefaultValue` is a plain `DefaultValue` Property whose DataType equals its
  owning Variable's DataType.
- `Unit` is a plain String Property in profile version 1. A future UNECE-aware
  EngineeringUnits rule may refine this without changing Value semantics.
- Many-to-one XML Schema datatype mappings use one declared inverse:
  `xs:integer -> xs:int`, `xs:positiveInteger -> xs:unsignedLong`,
  `xs:ID|xs:token|xs:anyURI -> xs:string`, and `xs:date -> xs:dateTime`.
- An omitted AML AttributeDataType is the String default and reverses as the
  explicit canonical `xs:string`.
- A recognized IRDI or URI `RefSemantic` uses `HasDictionaryEntry`. Its target
  is a real Part 19 `IrdiDictionaryEntryType` or `UriDictionaryEntryType`
  Object under the standard dictionary namespace, not a dangling NodeId-shaped
  string. No redundant `RefSemantic_n` shadow is emitted in this case.
- Plain `RefSemantic_n` String Properties are used only for AML semantic paths
  which cannot be represented by Part 19. When both representations are
  supplied by an external author, reverse mapping requires them to agree.
- Multiple `RefSemantic` values are a semantic set: reverse output is sorted by
  identifier and duplicate values are rejected. Reference/property order is
  never used as a hidden ordering channel.

## Role relationships

- A direct `HasAMLRoleReference` from an InternalElement is a
  `RoleRequirements` relationship.
- The same edge from a SystemUnitClass is a `SupportedRoleClass`
  relationship. Owner context makes the inverse strict.
- A relationship with no payload remains only that native edge.
- A relationship with actual payload is reified as a `BaseObjectType` object
  named `RoleRequirements` or `SupportedRoleClass`. The relation object points
  to its RoleClass using `HasAMLRoleReference`; its attributes and interfaces
  are ordinary `HasComponent` children.
- `MappingObject` is a component object containing `AttributeNameMapping` and
  `InterfaceIDMapping` pair objects. Pair fields are ordinary String
  Properties. Pairs are canonical sets sorted by their two field values.
- The profile does not emit `AMLMappingObjectPresent`, numbered pair-property
  names, or an explicit role-path shadow.
- Multiple payload-free role edges are a sorted set; duplicate edges are
  rejected and reference order is ignored.

## Constraints

- An Attribute contains each constraint through standard `HasComponent`.
  Constraint identity is inferred strictly from the child's companion-model
  `NominalScaledConstraint`, `OrdinalScaledConstraint`, or
  `UnknownConstraint` TypeDefinition; no invented constraint reference is
  required.
- Constraint Variables use `NominalScaledConstraint`,
  `OrdinalScaledConstraint`, or `UnknownConstraint` as their TypeDefinition.
- Required values are component Variables using OPC UA
  `BaseDataVariableType`; their BrowseNames are `RequiredValue`,
  `RequiredMinValue`, and `RequiredMaxValue`.
- A nominal RequiredValue collection is a set. Reverse output is sorted by
  value, and duplicate values are rejected.
- Unknown requirements use the constraint Variable's direct String value.
- No serialized `<Constraint>` fragment is placed in an OPC UA value.

## InternalLinks

- `HasAMLInternalLink` is used as a directed native edge from PartnerA's
  ExternalInterface to PartnerB's ExternalInterface.
- The InternalElement or SystemUnitClass storing the AML InternalLink must own
  PartnerA. This matches the profile's source/ownership rule.
- Reverse partner references prefer `owner AML ID:interface name`; an interface
  AML ID is used only when its owner has no AML ID.
- The link Name and ID do not exist on a native OPC UA reference. Reverse
  therefore generates both deterministically from the ordered PartnerA and
  PartnerB references. The ID is UUIDv5 and the Name is
  `InternalLink_<first-eight-uuid-hex>`.
- Two parallel AML links with the same directed endpoints are not representable
  by this edge and are rejected rather than collapsed.
- Link header metadata other than source Name/ID is rejected in this profile.
- The current AutomationML companion NodeSet declares `HasAMLInternalLink`
  `Symmetric="true"`. That declaration cannot normatively distinguish PartnerA
  from PartnerB. This profile therefore treats serialized/source edge
  orientation as PartnerA-to-PartnerB and verifies that convention through an
  asyncua export/reimport test, but records the companion declaration as an
  upstream interoperability risk requiring OPC Foundation/AutomationML review.

## External class references

- A class path using a declared `alias@library/path` becomes a native type or
  role edge to a local OPC UA proxy type.
- The proxy carries the actual `AMLExternalClassPath` semantic property and is
  not placed in a local AML class library. Reverse mapping therefore cannot
  mistake the proxy for a locally defined class.
- An unknown alias, a missing path, or a non-aliased unresolved class fails
  closed.

## Ambiguity policy

The mapper rejects, among other cases:

- competing TypeDefinitions;
- an InternalElement `SupportedRoleClass` without an explicit reified meaning;
- role references whose owner context does not determine the AML relationship;
- duplicate MappingObject pairs;
- repeated nominal constraint values;
- missing or multiply owned InternalLink endpoints; and
- parallel native InternalLinks with the same directed endpoints.

Every new canonical choice must be added here and to the comparison manifest
before implementation output is inspected.
