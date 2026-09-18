# AML-to-RDF/TTL mapping: current-state analysis and roundtrip pathway

Status: analysis complete; a first Python MVP of the forward/reverse mapper described below now
exists (`automationml.rdf`, `automationml.rdf_mapping`) — see the "MVP status" note at the end.
Scope: `AML2TTL.xslt` (AutomationML → Turtle, from the `AML-FD4AML` effort) and what it would take to
get a roundtrip-capable, SDK-integrated replacement

## Why this doc exists

`AML2TTL.xslt` converts a CAEX document into Turtle triples against a specific external ontology
(`https://w3id.org/hsu-aut/AutomationML`). It is the RDF/ontology analogue of the AML↔OPC UA
XSLT work this project already evaluated: same category of problem (project an AML model into an
external standard's representation), same tool (a large hand-written XSLT), and — on inspection —
the same conclusion applies. This document records what the current file actually does and does
not do, contrasts it with the working-group OPC UA XSLT precedent and with what this SDK already
built to replace it, and lays out a concrete pathway to a roundtrip-capable mapping plus frontend
integration.

The XSLT was read directly (`AML2TTL.xslt`, 848 lines, XSLT 2.0). It `xsl:include`s a
`LibraryParsing.xslt` that was not available for review; findings below are scoped to what is
visible in `AML2TTL.xslt` itself, but nothing in it suggests the included file changes the
conclusions (it is only invoked for class-library lookups via a `GetClass` template).

## Current-state assessment

### What it does

The stylesheet walks a `CAEXFile` and, for each library (`InterfaceClassLib`, `RoleClassLib`,
`SystemUnitClassLib`, `AttributeTypeLib`) and `InstanceHierarchy`, emits Turtle text for:

- basic bookkeeping (`rdfs:label`, `hasName`, `hasID`, `hasDescription`, `hasVersion`,
  file/header metadata, `owl:imports` of the target ontology);
- class hierarchy (`rdfs:subClassOf` between library classes via `RefBaseClassPath`);
- `RoleRequirements` / `SupportedRoleClass` references, and an attempted `rdf:type` derived from
  role class;
- containment (`hasAttribute`, `hasInternalElement`, `hasInterface`) and attribute metadata
  (`hasDataType`, `hasUnitName`, `hasAttributeValue`, `hasDefaultValue`);
- `InternalLink` as an `isLinkedTo` edge between the two partner interfaces;
- a heuristic `hasMappingObject` link between a `RoleRequirements`-declared template
  attribute/interface and the instance's own attribute/interface of the same name.

Output is produced with `xsl:output method="text"`: Turtle is built by direct string
concatenation (`createUri`, `createString`, `createNl` helper templates), not through any RDF-aware
serializer.

### Concrete defects found in the file

1. **Literal escaping is incomplete.** `hasDescription` values are cleaned with
   `translate(translate(., '&#xA;', ''), '&quot;&quot;', '')` — this strips newlines and double
   quotes but nothing else. A description or name containing a backslash or other
   Turtle-significant character can produce invalid Turtle. No literal anywhere gets a datatype or
   language tag.
2. **No typed literals.** Attribute values are always emitted as plain string literals
   (`"1500"`, not `"1500"^^xsd:double`). `AttributeDataType` only shows up as a separate
   `hasDataType`/`hasAttributeDataType` triple pointing at a string like `"xs:double"`. A consumer
   (or a future reverse mapper) has to re-associate the two by convention; the RDF type system
   carries none of it.
3. **URIs aren't IRI-safe.** `createUri` only strips `{`, `}` and whitespace
   (`fn:replace($input, '[\{\}\s]', '')`); it does not percent-encode reserved characters. An AML
   `Name` with `<`, `>`, `"`, `\`, or many non-ASCII characters produces malformed or colliding
   URIs.
4. **Identity is inconsistent.** URIs use `@ID` when present, otherwise a `/`-joined path of
   ancestor `Name`s (`refPath`). `Attribute` elements normally have no `@ID`, so their identity is
   purely name-path-based: renaming any ancestor changes every descendant attribute's URI, and
   nothing guarantees the path is unique.
5. **No ordering.** `hasInternalElement` / `hasAttribute` are emitted as an unordered set of
   triples. Where AML document order is semantic (e.g. ordered process steps), it is lost on
   export with no index/sequence predicate to recover it from.
6. **A rule is explicitly dead.** Line 318 carries `<!-- TODO: funktioniert nicht -->` ("doesn't
   work") directly above a commented-out `rdf:type` rule for instances typed via
   `RefBaseSystemUnitPath` / `RefBaseClassPath` / `RefAttributeType` ("Regel 4" in the source
   comments). That relation is simply not produced today.
7. **A neighboring rule looks broken, not just incomplete.** "Regel 5" (line 330) is meant to type
   an `InternalElement`/`SystemUnitClass` via its role class, but reads `@RefBaseRoleClassPath`
   directly off that element. In CAEX, that attribute lives on the child `RoleRequirements` /
   `SupportedRoleClass` element, not on the `InternalElement` itself — so the read is always empty
   on ordinary AML files, and `locateElem` resolves nothing. This rule looks unreachable in
   practice.
8. **`InternalLink` partner resolution is a documented hack.** Lines 800–824 carry a
   `<!-- Hack for wrong format -->` comment and try two different interpretations of
   `RefPartnerSideA`/`B` (a bare ID vs. an `"ID:InterfaceName"` composite) to work around
   inconsistently formatted source files — i.e. the reference-resolution rule for one of AML's core
   relationship types is a best-effort patch rather than a schema-driven rule.
9. **`RefSemantic` is dropped.** The block that would map AML's standardized-attribute-semantics
   reference (e.g. eCl@ss/IEC identifiers) to `hasSemanticRef` is commented out entirely
   (lines 729–734). Standardized semantic references never reach the graph.
10. **Unhandled constructs disappear silently.** Only `CAEXFile`, `SourceDocumentInformation`,
    `InstanceHierarchy`, the four `*Lib` containers, `InterfaceClass`/`RoleClass`/
    `SystemUnitClass`/`AttributeType`/`InternalElement`, `Attribute`, `ExternalInterface`, and
    `InternalLink` have templates. Everything else (Mirror objects, Facets, Constraints, etc.)
    falls through the catch-all empty match (`<xsl:template match="@*|*"/>`, line 478) and is
    dropped without any warning.
11. **There is no reverse direction at all.** The stylesheet's `xsl:output` targets text/Turtle
    only. Nothing in this file (and nothing surfaced when researching the referenced repository)
    parses Turtle back into CAEX. This isn't a roundtrip with gaps — the return trip doesn't
    exist yet.

None of this means the file is useless — it is a reasonable one-way semantic export for feeding
data into a specific ontology/graph store, and several of the design choices (name-path fallback
URIs, text-mode Turtle) are typical of a first XSLT prototype in this space. But as a basis for
roundtripping it has real gaps, and at least one rule that is currently non-functional.

## How this compares to the OPC UA precedent

The situation is close to the OPC UA one, and the comparison is informative:

- `AML-UA-XSLT` (the working-group OPC UA transform) is nominally bidirectional
  (`AML2Nodeset.xslt` / `Nodeset2AML.xslt`), but its own README describes it as "work in progress"
  reflecting the current state of the joint AutomationML/OPC UA working group, with no documented
  fidelity guarantees.
- This SDK already decided, independently, that the XSLT path for that structurally identical
  problem — project AML into (and back out of) an external standard — wasn't trustworthy enough to
  be primary. It built a typed Python/Pydantic forward and reverse mapper with a frozen
  `AMLUAMappingProfile` that declares one canonical inverse per many-to-one rule, an explicit
  ambiguity-rejection policy, and a 120+ case comparison corpus. The recorded result:
  `PY-STRICT` 121/121 against the unmodified `XSLT-RAW` at 1/121 (30/30 vs 1/30 on critical cases).
  The legacy XSLT was kept only as an optional, explicitly-selected comparison engine
  (the evaluation harness's patched-XSLT engine), never the default.
- `AML2TTL.xslt` is the same category of problem, but is currently at an earlier and less mature
  stage than even the "before" state of the OPC UA work: it's one-directional, string-templated
  instead of built on an RDF library, and contains at least one dead rule and one very likely
  broken rule that is still active.

That prior result is the strongest evidence available for how this should go: not "XSLT can never
do this," but "on the nearest comparable problem this team already solved, the typed Python
approach dominated on correctness and was the only one that reached a testable, defensible
roundtrip."

## Roundtrip pathway

The concrete path mirrors the OPC UA mapper's shape, reusing the SDK's existing typed model instead
of re-deriving structure from raw XML text:

1. **Declare a mapping profile.** An `AMLRDFMappingProfile`, analogous to `AMLUAMappingProfile`:
   one canonical URI-minting rule (prefer `@ID`; where absent, mint and persist a deterministic
   UUIDv5 keyed by full hierarchy path + Name rather than re-deriving URIs from mutable Names on
   every pass), one canonical XSD-datatype table (the existing `xs:integer -> xs:int` style
   canonicalization used for OPC UA is largely reusable, since CAEX's `AttributeDataType`
   vocabulary is shared), and an explicit ordering rule wherever CAEX order is semantic.
2. **Typed literals.** Use `rdflib.Literal(value, datatype=XSD.<type>)` from that datatype table
   instead of bare strings, so type information survives in the RDF graph itself rather than in a
   side triple.
3. **Preserve order.** Add an explicit sequence predicate (e.g. `hasIndex`) on collection-membership
   triples where document order is semantic — the same problem this SDK already solved for OPC UA
   references being XML-order-independent.
4. **Stop silently dropping constructs.** `RefSemantic`, Mirror objects, Facets, and Constraints
   should either be mapped or fail explicitly, matching the SDK's existing stance ("unsupported or
   ambiguous features fail explicitly") rather than the current XSLT's silent catch-all.
5. **Forward mapper:** `CAEXFile.to_rdf_graph()` / `.to_ttl()`, built directly from the already
   validated Pydantic model. This eliminates most of the defects above by construction — identity,
   hierarchy, and datatypes are already correctly modeled in the SDK, instead of being re-derived
   by string-walking raw XML.
6. **Reverse mapper:** `RDFGraph -> CAEXFile` via SPARQL/graph traversal keyed off the profile's
   canonical predicates, writing into the SDK's existing typed builders
   (`internal_element(...)`, `attribute(...)`) so the reconstructed document is automatically run
   through `caex_validation_issues()`.
7. **Roundtrip verification:** `document.round_trip_ttl()` / `graph.round_trip_automationml()`
   returning the same `RoundTripDifference` / `semantically_equivalent` shape already used for
   OPC UA (JSON-Pointer-addressed differences, not a bare boolean), plus a comparison corpus and
   `compare_ttl_mappers.py` scoring the new Python mapper against the legacy XSLT the same way
   `compare_opcua_mappers.py` does today. The existing `examples/validation-suite` fixtures are a
   reasonable starting corpus.
8. **Governance.** Because the target vocabulary (`w3id.org/hsu-aut/AutomationML`) is maintained by
   a different external group than the AutomationML/OPC UA working group, add a
   `docs/rdf-mapping-review-checklist.md` twin to the OPC UA one — any canonical-inverse decision
   here needs sign-off from that ontology's maintainers, or the profile should be scoped explicitly
   as this project's own interpretation rather than a binding AML-to-ontology conformance claim.

## Does this need a switch to Python?

Yes, for the same reasons the OPC UA direction already did:

- The concrete defects found above (silent drops, one dead rule, one apparently-broken rule,
  missing escaping, missing datatypes) are exactly the class of error the Pydantic/JSON-first model
  already eliminates by construction on the OPC UA side.
- The reverse direction is close to unbuildable as maintainable XSLT: XSLT operates on trees, and
  Turtle isn't one. A "reverse XSLT" would need an RDF/XML pre-parse anyway — at which point real
  RDF tooling is already required, and there's no benefit to stopping short of doing the mapping
  logic itself in the same tool (Python + `rdflib`), consistent with how `UANodeSet.from_xml()` /
  `.to_xml()` were kept as a thin adapter boundary with all mapping logic on the Python side.
  Because RDF parses are the same regardless of the XSLT taking part or not, the XSLT path buys
  nothing here.
- This isn't a case for throwing the XSLT away outright: keep a fixed-up `AML2TTL.xslt` (worth
  fixing at minimum items 6/7/9 above if it's going to run at all) as an optional comparison oracle,
  exactly mirroring the harness's patched-XSLT engine for OPC UA — useful for catching regressions, not for production
  correctness.

## Frontend integration

`automationml-editor` already has the exact UI/API shape needed: an "Export OPC UA" action backed
by `document.to_opcua_nodeset_xml()` through FastAPI, with the legacy XSLT kept as an explicitly
selectable comparison engine and a profile-warning banner shown to the user. The RDF/TTL feature
should mirror this 1:1 rather than invent a new pattern:

- Add `to_rdf_graph()` / `to_ttl()` (and, once the reverse mapper clears its evidence bar,
  `from_ttl()`) to the SDK.
- Add matching FastAPI endpoints and "Export TTL" / "Import TTL" actions in the same graph-checker
  UI, reusing the existing document-summary/validation-issue display for RDF-side issues.
- Show the same kind of profile-warning language the OPC UA export already uses, since the RDF
  target vocabulary is likewise a project-specific interpretation, not a universal standard.
- Sequence it: ship forward-only TTL export first (lower risk, immediately useful for feeding an
  ontology/graph store), and gate "Import TTL" behind the roundtrip harness reaching an evidence bar
  comparable to the OPC UA release gate before exposing it in the UI — the editor's own README
  already flags the OPC UA reverse path the same way ("does not depend on AML-only metadata," still
  profile-warned).

## Suggested sequencing

1. Land this document (or a revised version of it) as `docs/rdf-mapping-audit.md` in
   `automationml-sdk`, so the defects above are a recorded baseline rather than tribal knowledge.
2. Define `AMLRDFMappingProfile` (URI, datatype, ordering, `RefSemantic` rules) plus a review
   checklist.
3. Implement `CAEXFile.to_rdf_graph()` / `.to_ttl()` using `rdflib`; unit-test against the existing
   validation-suite fixtures.
4. Implement the reverse mapper and `round_trip_ttl()` / `assert_equivalent()`.
5. Build a comparison corpus and `compare_ttl_mappers.py` scoring the Python mapper against the
   (at-minimum-patched) legacy XSLT.
6. Wire `Export TTL` — and, once it passes the gate, `Import TTL` — into `automationml-editor`,
   following the OPC UA button pattern.
7. Get the HSU-AUT ontology maintainers (or whoever owns the target vocabulary in your context) to
   review the canonical mapping profile before treating it as final, mirroring the domain-expert
   sign-off step already tracked for the OPC UA mapping in `TODO.md`.

## MVP status (steps 2–3 above)

A first Python mapper now exists, added to `automationml-sdk` as `src/automationml/rdf_mapping.py`
(the profile: URI minting, the AML/XSD datatype registry, the external-class-proxy rule) and
`src/automationml/rdf.py` (the forward and reverse mappers, `RDFRoundTripResult`, and
`round_trip_ttl()` — same shape as `round_trip_opcua()`), wired onto `CAEXFile` as `to_ttl()`,
`to_rdf_graph()`, `from_ttl()`, `from_rdf_graph()`, and `round_trip_ttl()`. A new `rdf` extra
(`rdflib>=7.0,<8`) was added to `pyproject.toml`.

Test corpus (`tests/test_rdf.py`): every fixture your team already vendored from the AML-UA-XSLT
unit-test corpus for the OPC UA comparison harness (`tests/fixtures/opcua_reverse/0_EmptyFile_V2.1
.aml` through `11_Constraints.aml` — empty file, a lone InternalElement, an InternalElement with an
Attribute, an empty InstanceHierarchy, class hierarchies with inheritance, an AttributeType
library, ExternalInterfaces + InternalLinks, RefSemantic, and Constraints), plus the SDK's own
`examples/validation-suite` XML fixtures (small/medium/big). All 13 round-trip AML → Turtle → AML
semantically equivalent (compared via the same canonical-AML-JSON diff the OPC UA
mapper uses), with no declared canonicalizations. An earlier version filled an omitted
`AttributeDataType` with `xs:string` and collapsed `xs:integer`/`xs:positiveInteger`/`xs:ID`/
`xs:token` into other types; since RDF has a native datatype for every XSD built-in AML uses, the
datatype table is now one-to-one and `hasAttributeDataType` carries the authored value (only when
present), while `hasDataType` carries the effective, defaulted type for consumers.

Bugs the reused corpus actually caught while building this (not hypothetical):

- **CAEX IDs written with UUID braces** (`ID="{...}"`) broke URI serialization outright until
  minting normalized them — the exact inconsistency the legacy XSLT's `createUri` regex existed to
  paper over, rediscovered independently.
- **`AutomationMLBaseInterface`-style bare base-class references** (no library path, no alias) are
  common, legitimate AML and are not distinguishable from a typo by syntax alone; the profile mints
  a stable `ExternalClassProxy` for any unresolvable-but-non-empty class path rather than guessing
  or failing, and documents that as a deliberate choice.
- **rdflib itself reformats numeric literal lexical forms on a serialize/parse cycle** (`"36"` typed
  as `xsd:double` comes back as `"36.0"`) — found only by round-tripping through actual Turtle text,
  not by inspecting the in-memory graph. `hasAttributeValue`/`hasDefaultValue` are now deliberately
  kept as untyped strings for fidelity, with a separate `hasTypedAttributeValue`/
  `hasTypedDefaultValue` pair carrying the RDF-native typed literal for SPARQL consumers who want it.
- **`NominalScaledType.RequiredValue` order was not preserved** (RDF triples are a set); it is now
  represented as an `rdf:List` instead of loose triples, the same fix in spirit as `hasIndex` on
  every other ordered collection this mapper emits.

Fixed after the first MVP (September 2026):

- **CAEX header metadata was silently dropped.** `Revision`, `Copyright`,
  `SourceObjectInformation`, per-object `AdditionalInformation`, the file-level `Description` /
  `Version`, and all header fields on `RoleRequirements`, `SupportedRoleClass`, `MappingObject`,
  its mapping pairs, `RefSemantic` and `ExternalReference` never reached the graph. Every
  `CAEXBasicObject` now goes through the same emit/apply path (`hasRevision`, `hasCopyright`,
  `hasSourceObjectInformation`, `hasAdditionalInformation`; `has*Json` literals preserve an empty
  text element or a non-default `ChangeMode`). The new `$xml` extension content in
  `AdditionalInformation` is carried inside its JSON literal.
- **Lossy datatypes.** See above.
- **GUID braces.** IDs are kept exactly as authored (`{...}` or bare), but every ID lookup
  (`ReferenceIndex.resolve_id`, InternalLink validation, `CAEXQuery`, instantiation, merge) now
  ignores the optional braces, so a CAEX 2.15 file migrated to a braced interface ID converts
  cleanly.

Corpus result after these fixes: every loadable AML/JSON fixture in the repository (58 files,
including the vendored AML-UA-XSLT test data) round-trips with zero differences; the five
deliberately broken fixtures fail explicitly.

Not yet done, in order of what should come next: a `docs/rdf-mapping-review-checklist.md` twin (this
mapper's canonical choices -- the external-proxy fallback especially -- have not been reviewed by
anyone outside this project); a comparison harness against the legacy XSLT analogous to
`compare_opcua_mappers.py`, so future changes are scored rather than eyeballed; and a wider
adversarial fixture set (Mirror objects, Facets, malformed real-world files). Separately, the
CAEX 2.15 importer rejects several vendored real-world files whose base classes live in the
standard AutomationML libraries (`AutomationMLBaseRole`, `Structure`) without being embedded, so
those files cannot reach the RDF mapper yet.
