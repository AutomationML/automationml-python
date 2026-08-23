# AutomationML / OPC UA mapping review checklist

Status: awaiting independent domain-expert signatures  
Profile: `strict-implicit-v1`  
Evidence date: 2026-08-17

This review is the human governance gate around the executable corpus. A green
test proves consistency with the declared oracle; it does not prove that the
oracle represents the standards communities' intended semantics.

## Evidence to inspect

- Mapping rules: `docs/opcua-strict-implicit-mapping.md`
- Executable plan: `docs/opcua-mapper-comparison-test-plan.md`
- Frozen manifest: `tests/opcua-comparison/release-manifest.json`
- Full result matrix: `docs/reports/opcua-release-comparison/report.md`
- Interoperability tests: `tests/test_opcua_interoperability.py`
- Scale evidence: `docs/reports/opcua-scale/report.md`
- Pinned companion model:
  `tests/vendor/aml-ua-xslt-e38653c/UnitTests/Opc.Ua.AMLBaseTypes.NodeSet2_V2.xml`

Relevant public OPC UA references include the
[AutomationML companion specification](https://reference.opcfoundation.org/AML/v100/docs/),
[OPC UA Part 3 address-space model](https://reference.opcfoundation.org/Core/Part3/v105/docs/),
[OPC UA Part 6 NodeSet XML](https://reference.opcfoundation.org/Core/Part6/v105/docs/),
and [OPC UA Part 19 dictionary references](https://reference.opcfoundation.org/specs/OPC-10000-19/full).
The AML reviewer should add the applicable CAEX/AutomationML edition and clause
numbers available under the reviewer's standards access.

## Decision review

| Decision | AutomationML review question | OPC UA review question | Automated evidence | State |
| --- | --- | --- | --- | --- |
| InternalElement role edge defaults to `RoleRequirements` | Is that the community default when no relation object exists? | Is owner NodeClass/context a sufficiently strict inverse? | `AML-ROLE-001`, `UA-ORIGIN-013` | Assumed; confirm |
| SystemUnitClass role edge means `SupportedRoleClass` | Does this preserve the CAEX relationship? | Is the same ReferenceType valid with contextual meaning? | `AML-ROLE-002`, `UA-ORIGIN-014` | Confirm |
| InternalLink source is PartnerA | Is the storing CAEX object only a container, with PartnerA the directed source? | Can serialized edge orientation safely override the companion's symmetric declaration? | `AML-LINK-002..005`, asyncua role/link test | **Open upstream risk** |
| Missing link Name/ID are deterministic | Are generated UUIDv5 identity and canonical name acceptable? | Does generation avoid claiming reference identity OPC UA does not have? | `AML-LINK-004`, `UA-ORIGIN-015` | Confirm |
| Value and DefaultValue remain distinct | Is plain `DefaultValue` faithful to AML runtime/default semantics? | Is a typed Property with the owner's DataType appropriate? | `AML-ATTR-001..004`, `UA-ORIGIN-008..009` | Confirm |
| Unit is a plain String in v1 | Is lexical Unit preservation preferable to partial normalization? | Is deferring `EngineeringUnits` acceptable for this profile? | `AML-ATTR-007..008` | Confirm / future rule |
| RefSemantic uses Part 19 objects | Are recognized IRDI/URI identifiers canonicalized correctly? | Are materialized `IrdiDictionaryEntryType`/`UriDictionaryEntryType` Objects and `HasDictionaryEntry` conformant? | `AML-SEM-001..003`, asyncua export | Confirm |
| Constraints are typed components | Do nominal/ordinal/unknown shapes preserve AML cardinality and value meaning? | Are companion constraint TypeDefinitions plus standard `HasComponent`/`BaseDataVariableType` appropriate? | `AML-CONSTRAINT-001..004` | Confirm |
| NodeIds and order are non-semantic | Are generated AML IDs used only where AML requires identity? | Does reverse mapping correctly ignore NodeId spelling, prefix/index, and XML order? | `UA-ORIGIN-002..007`, metamorphic 1-5 | Confirm |
| Strict ambiguity rejects loss | Are rejected parallel links, duplicate nominal values, and ambiguous roles genuinely non-representable? | Are diagnostics preferable to an undocumented choice? | `NEG-AML-009..010`, `NEG-UA-*` | Confirm |

## Mandatory manual checks

- [ ] Review expected AML in every `UA-ORIGIN-*` case without consulting Python
  output.
- [ ] Review expected OPC UA graph facts for each semantic family without
  consulting raw-XSLT output.
- [ ] Add clause references to the manifest or an attached review record.
- [ ] Decide whether `HasAMLInternalLink Symmetric="true"` must be corrected in
  the companion model. If it remains symmetric, explicitly approve or reject
  the profile's PartnerA-to-PartnerB serialization convention.
- [ ] Confirm that `RoleRequirements` is the default InternalElement role
  interpretation.
- [ ] Check all canonicalizations: UUID braces, datatype aliases, XML attribute
  whitespace, nominal sets, and relationship sets.
- [ ] Review every `EXPECTED_REJECTION` diagnostic for actionable wording.
- [ ] Record any dissent as a manifest/profile change followed by a fresh
  baseline; do not edit expected results merely to keep the implementation
  green.

## Sign-off

| Role | Name / organization | Standards editions reviewed | Decision | Date | Signature or review link |
| --- | --- | --- | --- | --- | --- |
| AutomationML/CAEX expert |  |  | Pending |  |  |
| OPC UA information-model expert |  |  | Pending |  |  |
| SDK maintainer |  |  | Pending |  |  |

Release wording may claim automated superiority over the pinned raw XSLT only
after the first two independent reviewers approve the expected semantics or
all of their objections are reflected in a new frozen corpus and report.
