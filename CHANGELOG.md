# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Removed

- The forward `mapper="xslt"` engine is no longer part of the SDK. The patched
  working-group stylesheets moved to `evaluation/resources/xslt/` and the
  engine is now produced by the evaluation harness, which is where the
  comparison evidence is generated. It scored 1/121 against the Python
  mapper's 121/121, so it was evidence rather than a conversion path to ship.
  `document_to_nodeset`, `aml_xml_to_nodeset`, `round_trip_document`,
  `round_trip_nodeset`, `CAEXFile.to_opcua_nodeset_xml`,
  `CAEXFile.round_trip_opcua` and `UANodeSet.round_trip_automationml` no longer
  take a `mapper` argument, and the round-trip results no longer carry a
  `mapper` field. Reading NodeSets produced by that stylesheet is unaffected:
  the semantic reverse still recognizes AML-UA-XSLT-origin graphs. The now
  unused `opcua-xslt` extra was removed; `opcua-evaluation` still installs
  Saxon for the harness.

### Changed

- Regenerated the committed release and phase-1 comparison evidence. Scored
  outcomes are unchanged (`PY-STRICT` 121/121, `XSLT-RAW` 1/121, critical 30/30
  versus 1/30); six unscored upstream cases improved after the CAEX 2.15
  migration fix, and `REG-DETERMINISM-001` now records the accurate `FAIL` for
  `XSLT-RUNNER` instead of a same-day calendar coincidence. See the note in
  `docs/opcua-mapper-comparison-test-plan.md`.
- The OPC UA mapper comparison harness moved from
  `automationml.opcua_evaluation` to `evaluation/opcua_evaluation.py` and is no
  longer part of the distributed package. It is development evidence tooling
  that no library code path imports, so SDK users no longer install the harness
  that judges the SDK. It remains in the source distribution so published
  evidence stays reproducible, and `tools/compare_opcua_mappers.py` and
  `tools/benchmark_opcua_scale.py` run unchanged.

### Fixed

- CAEX 2.15 migration no longer raises when a RoleClass derives from a base
  class the document does not carry, which is normal for files that rely on
  the standard AutomationML libraries. The resolvable part of the inheritance
  chain is still materialized and the gap is reported as an
  `unresolved-base-role-class` migration warning, keeping migration consistent
  with the SDK's non-destructive validation stance.

### Added

- Extension-safe, namespace-aware mixed XML content in `AdditionalInformation`
  with a documented AML JSON `$xml` representation and generated schema.
- Immutable `CAEXQuery` snapshots with ID/path lookup, reverse references,
  connectivity, descendants, inheritance, instances, and resolved-alias paths.
- Inheritance-aware SystemUnitClass instantiation with fresh injectable IDs and
  copied-reference rewriting.
- Atomic CAEX 2.15 import to CAEX 3.0 with diagnostics, legacy warnings,
  metadata/role/mapping/link conversion, and mirror normalization.
- Reversible digest-bound RFC 6901 change sets and copy-on-write document edit
  transactions.
- Atomic recursive document merge with explicit conflict policies, reference
  rewrites, validation, and a resulting change set.
- Extensible external-reference resolution and a confined local filesystem
  resolver with alias, cycle, depth, missing-file, and traversal diagnostics.
- AML <-> RDF/Turtle mapping (`to_ttl`, `from_ttl`, `round_trip_ttl`) covering
  all CAEX header metadata (Revision, Copyright, SourceObjectInformation,
  AdditionalInformation including `$xml`) and preserving the authored
  `AttributeDataType`.
- ID lookups and InternalLink partner matching ignore optional GUID braces
  (`{...}`) while keeping IDs exactly as authored.
- GitHub governance and contribution documentation.
- Cross-platform CI for supported Python versions and package builds.
- Typed Pydantic OPC UA UANodeSet authoring models and a Python-native forward
  mapping MVP for file metadata, instance trees, attributes, class libraries,
  interfaces, inheritance/type references, and simple role relations.
- Frozen OPC UA value models, an explicit `UANodeSetBuilder`, typed NodeSet XML
  parsing/query helpers, a public inspectable roundtrip result, and one shared
  validated mapping profile for forward/reverse datatypes and role references.
- Symmetric AML-origin and OPC-UA-origin roundtrip APIs with typed graphs and
  frozen JSON-Pointer semantic differences; OPC-UA-authored NodeIds are tested
  independently from the forward mapper's deterministic identifier layout.
- The pinned, patched AML-UA-XSLT mapper as an explicit comparison engine,
  including mapping-source fixes, schema and semantic checks, and provenance.
- Semantic-v3 AutomationML/OPC UA mapping for Part 19 semantic dictionary
  entries, exact class/type/role paths, class libraries, role mappings,
  constraints, interfaces, internal links, mirrors, facets, lexical IDs, and
  change modes, with payload-free reverse tests against official fixtures.
- A frozen 145-case mapper comparison corpus with 121 scored cases, 12
  known-defect mutants, 16 OPC-UA-origin cases, 12 typed negative/security
  cases, JSON/JUnit/Markdown evidence, and an unmodified upstream-XSLT
  baseline.
- Eight deterministic Hypothesis metamorphic families, four asyncua
  import/browse/export gates, Windows/Linux acceptance CI, and reproducible
  1k/10k/depth scale reporting.
- Standards-consistent inverse hierarchy edges and materialized Part 19 IRDI/
  URI dictionary-entry Objects; batched graph construction and cached reverse
  class-path indexes keep the 10k-node roundtrip linear enough for release
  measurement.

## [0.1.0a1] - Unreleased

### Added

- JSON-first Pydantic models for AutomationML CAEX 3.0 documents.
- Canonical AML JSON serialization and parsing.
- AML XML import, export, and round-trip support.
- AML JSON Schema generation.
- Builder helpers for common authoring workflows.
- Structured semantic validation and reference indexing.
- JSON and XML validation example catalog with expected outcomes.

[Unreleased]: https://github.com/AutomationML/automationml-python/compare/v0.1.0a1...HEAD
[0.1.0a1]: https://github.com/AutomationML/automationml-python/releases/tag/v0.1.0a1
