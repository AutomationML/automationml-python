# TODO

## Domain-expert sign-off on the OPC UA mapping oracle

`docs/opcua-mapping-review-checklist.md` is still awaiting independent
domain-expert signatures on the AutomationML/OPC UA mapping rules
(`strict-implicit-v1`). The automated corpus is green (see
`docs/reports/opcua-release-comparison/report.md`), but a green test only
proves consistency with the declared oracle - it does not prove the oracle
represents the standards communities' intended semantics. Get that review
done before treating the mapping profile as final.

## Next mapping increments (from `docs/opcua-python-mapper-research.md`)

1. Resolve the InternalLink direction/profile question, then implement its
   native edge and canonical AML reconstruction.
2. Map attribute constraints with typed Python models and tests.
3. Replace plain `Unit` with standard `EngineeringUnits` where a UNECE
   mapping is available.
4. Import generated NodeSets into `asyncua` as an independent
   interoperability check.
5. Run the complete upstream fixture set and maintain a capability matrix
   (Python pass / canonical difference / deferred / upstream-invalid).

---

_Commit history: the full Python OPC UA mapper, its tests, corpus, and
governance docs were committed on 2026-08-23 (`a30181d`)._
