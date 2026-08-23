# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

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
