# AutomationML / OPC UA strict-profile release comparison

Baseline commit: `e38653c1bc58ffc658595093e0a2d163a7ecebf7`  
Generated: `2026-08-17T13:44:31.872403+00:00`  
Platform: `Windows-10-10.0.26200-SP0`

## Score

| System | Passed | Scored | Percent | Critical |
| --- | ---: | ---: | ---: | ---: |
| `PY-STRICT` | 121 | 121 | 100.00% | 30/30 |
| `XSLT-RAW` | 1 | 121 | 0.83% | 1/30 |
| `XSLT-RUNNER` | 0 | 0 | 0.00% | 0/0 |
| `XSLT-PATCHED` | 0 | 0 | 0.00% | 0/0 |

Scores count conformance outcomes, not independent root causes. A single global NodeSet defect can correctly fail many cases which all require a valid NodeSet.

## Unscored engine outcomes

These are diagnostic appendix counts over non-observation cases. They are not headline scores and cannot improve or reduce either candidate.

| System | Passing outcomes | Applicable mandatory cases |
| --- | ---: | ---: |
| `XSLT-RUNNER` | 2 | 121 |
| `XSLT-PATCHED` | 38 | 121 |

## Full result matrix

| Case | Family | Severity | System | Scored | Outcome | Diagnostic |
| --- | --- | --- | --- | --- | --- | --- |
| `UP-UNIT-000` | upstream-unit-legacy | observation | `PY-STRICT` | no | **PASS** |  |
| `UP-UNIT-000` | upstream-unit-legacy | observation | `XSLT-RAW` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `UP-UNIT-000` | upstream-unit-legacy | observation | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `UP-UNIT-000` | upstream-unit-legacy | observation | `XSLT-PATCHED` | no | **PASS** |  |
| `UP-UNIT-001` | upstream-unit | must | `PY-STRICT` | yes | **PASS** |  |
| `UP-UNIT-001` | upstream-unit | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `UP-UNIT-001` | upstream-unit | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `UP-UNIT-001` | upstream-unit | must | `XSLT-PATCHED` | no | **PASS** |  |
| `UP-UNIT-002` | upstream-unit | must | `PY-STRICT` | yes | **CANONICAL_PASS** |  |
| `UP-UNIT-002` | upstream-unit | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `UP-UNIT-002` | upstream-unit | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `UP-UNIT-002` | upstream-unit | must | `XSLT-PATCHED` | no | **FAIL** | no_roundtrip_metadata: forbidden shadow nodes AMLAttributeDataType |
| `UP-UNIT-003` | upstream-unit-legacy | observation | `PY-STRICT` | no | **PASS** |  |
| `UP-UNIT-003` | upstream-unit-legacy | observation | `XSLT-RAW` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `UP-UNIT-003` | upstream-unit-legacy | observation | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `UP-UNIT-003` | upstream-unit-legacy | observation | `XSLT-PATCHED` | no | **PASS** |  |
| `UP-UNIT-004` | upstream-unit-legacy | observation | `PY-STRICT` | no | **PASS** |  |
| `UP-UNIT-004` | upstream-unit-legacy | observation | `XSLT-RAW` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `UP-UNIT-004` | upstream-unit-legacy | observation | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `UP-UNIT-004` | upstream-unit-legacy | observation | `XSLT-PATCHED` | no | **FAIL** | no_roundtrip_metadata: forbidden shadow nodes AMLAttributeDataType, AMLDefaultValue, AMLUnit |
| `UP-UNIT-005` | upstream-unit-legacy | observation | `PY-STRICT` | no | **PASS** |  |
| `UP-UNIT-005` | upstream-unit-legacy | observation | `XSLT-RAW` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `UP-UNIT-005` | upstream-unit-legacy | observation | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `UP-UNIT-005` | upstream-unit-legacy | observation | `XSLT-PATCHED` | no | **PASS** |  |
| `UP-UNIT-006` | upstream-unit | must | `PY-STRICT` | yes | **PASS** |  |
| `UP-UNIT-006` | upstream-unit | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `UP-UNIT-006` | upstream-unit | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `UP-UNIT-006` | upstream-unit | must | `XSLT-PATCHED` | no | **FAIL** | no_roundtrip_metadata: forbidden shadow nodes AMLAttributeDataType, AMLDefaultValue, AMLUnit |
| `UP-UNIT-007` | upstream-unit-legacy | observation | `PY-STRICT` | no | **PASS** |  |
| `UP-UNIT-007` | upstream-unit-legacy | observation | `XSLT-RAW` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `UP-UNIT-007` | upstream-unit-legacy | observation | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `UP-UNIT-007` | upstream-unit-legacy | observation | `XSLT-PATCHED` | no | **FAIL** | no_roundtrip_metadata: forbidden shadow nodes AMLAttributeDataType, AMLDefaultValue, AMLUnit |
| `UP-UNIT-008` | upstream-unit-legacy | observation | `PY-STRICT` | no | **PASS** |  |
| `UP-UNIT-008` | upstream-unit-legacy | observation | `XSLT-RAW` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `UP-UNIT-008` | upstream-unit-legacy | observation | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `UP-UNIT-008` | upstream-unit-legacy | observation | `XSLT-PATCHED` | no | **FAIL** | no_roundtrip_metadata: forbidden shadow nodes AMLAttributeDataType, AMLDefaultValue, AMLUnit |
| `UP-UNIT-009` | upstream-unit | must | `PY-STRICT` | yes | **CANONICAL_PASS** |  |
| `UP-UNIT-009` | upstream-unit | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `UP-UNIT-009` | upstream-unit | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `UP-UNIT-009` | upstream-unit | must | `XSLT-PATCHED` | no | **FAIL** | no_roundtrip_metadata: forbidden shadow nodes AMLAttributeDataType |
| `UP-UNIT-010` | upstream-unit-legacy | observation | `PY-STRICT` | no | **FAIL** | Python OPC UA mapping failed: SupportedRoleClass on an InternalElement is ambiguous in the implicit role profile; only RoleRequirements is supported. |
| `UP-UNIT-010` | upstream-unit-legacy | observation | `XSLT-RAW` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `UP-UNIT-010` | upstream-unit-legacy | observation | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `UP-UNIT-010` | upstream-unit-legacy | observation | `XSLT-PATCHED` | no | **FAIL** | canonical_aml: first difference at /AdditionalInformation/1/value |
| `UP-UNIT-011` | upstream-unit | must | `PY-STRICT` | yes | **PASS** |  |
| `UP-UNIT-011` | upstream-unit | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `UP-UNIT-011` | upstream-unit | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `UP-UNIT-011` | upstream-unit | must | `XSLT-PATCHED` | no | **FAIL** | no_roundtrip_metadata: forbidden shadow nodes AMLAttributeDataType |
| `UP-UNIT-012` | upstream-unit | must | `PY-STRICT` | yes | **CANONICAL_PASS** |  |
| `UP-UNIT-012` | upstream-unit | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `UP-UNIT-012` | upstream-unit | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `UP-UNIT-012` | upstream-unit | must | `XSLT-PATCHED` | no | **FAIL** | no_roundtrip_metadata: forbidden shadow nodes AMLAttributeDataType |
| `UP-UNIT-013` | upstream-unit | must | `PY-STRICT` | yes | **CANONICAL_PASS** |  |
| `UP-UNIT-013` | upstream-unit | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `UP-UNIT-013` | upstream-unit | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `UP-UNIT-013` | upstream-unit | must | `XSLT-PATCHED` | no | **UNSUPPORTED** | The semantic OPC UA reverse mapping 'automationml-python-semantic-v3' does not yet support HasAMLRoleReference target 'ns=3;s=Resource' outside RoleClassLibs. Use an app export ... |
| `UP-UNIT-014` | upstream-unit | must | `PY-STRICT` | yes | **CANONICAL_PASS** |  |
| `UP-UNIT-014` | upstream-unit | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `UP-UNIT-014` | upstream-unit | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `UP-UNIT-014` | upstream-unit | must | `XSLT-PATCHED` | no | **FAIL** | no_roundtrip_metadata: forbidden shadow nodes AMLAttributeDataType, AMLUnit |
| `UP-APP-000` | upstream-application-legacy | observation | `PY-STRICT` | no | **FAIL** | Python OPC UA mapping failed: SupportedRoleClass on an InternalElement is ambiguous in the implicit role profile; only RoleRequirements is supported. |
| `UP-APP-000` | upstream-application-legacy | observation | `XSLT-RAW` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `UP-APP-000` | upstream-application-legacy | observation | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `UP-APP-000` | upstream-application-legacy | observation | `XSLT-PATCHED` | no | **FAIL** | no_roundtrip_metadata: forbidden shadow nodes AMLAttributeDataType, AMLDefaultValue, AMLUnit |
| `UP-APP-001` | upstream-application-legacy | observation | `PY-STRICT` | no | **PASS** |  |
| `UP-APP-001` | upstream-application-legacy | observation | `XSLT-RAW` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `UP-APP-001` | upstream-application-legacy | observation | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `UP-APP-001` | upstream-application-legacy | observation | `XSLT-PATCHED` | no | **FAIL** | no_roundtrip_metadata: forbidden shadow nodes AMLAttributeDataType |
| `UP-APP-002` | upstream-application-legacy | observation | `PY-STRICT` | no | **PASS** |  |
| `UP-APP-002` | upstream-application-legacy | observation | `XSLT-RAW` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `UP-APP-002` | upstream-application-legacy | observation | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `UP-APP-002` | upstream-application-legacy | observation | `XSLT-PATCHED` | no | **FAIL** | no_roundtrip_metadata: forbidden shadow nodes AMLAttributeDataType, AMLDefaultValue |
| `UP-APP-003` | upstream-application-legacy | observation | `PY-STRICT` | no | **FAIL** | Python OPC UA mapping failed: SupportedRoleClass on an InternalElement is ambiguous in the implicit role profile; only RoleRequirements is supported. |
| `UP-APP-003` | upstream-application-legacy | observation | `XSLT-RAW` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `UP-APP-003` | upstream-application-legacy | observation | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `UP-APP-003` | upstream-application-legacy | observation | `XSLT-PATCHED` | no | **FAIL** | no_roundtrip_metadata: forbidden shadow nodes AMLAttributeDataType, AMLDefaultValue |
| `UP-APP-004` | upstream-application-legacy | observation | `PY-STRICT` | no | **INVALID_FIXTURE** | invalid AutomationML XML: expected '>', line 15, column 54 (<string>, line 15) |
| `UP-APP-004` | upstream-application-legacy | observation | `XSLT-RAW` | no | **INVALID_FIXTURE** | invalid AutomationML XML: expected '>', line 15, column 54 (<string>, line 15) |
| `UP-APP-004` | upstream-application-legacy | observation | `XSLT-RUNNER` | no | **INVALID_FIXTURE** | invalid AutomationML XML: expected '>', line 15, column 54 (<string>, line 15) |
| `UP-APP-004` | upstream-application-legacy | observation | `XSLT-PATCHED` | no | **INVALID_FIXTURE** | invalid AutomationML XML: expected '>', line 15, column 54 (<string>, line 15) |
| `UP-APP-005` | upstream-application-legacy | observation | `PY-STRICT` | no | **FAIL** | Python OPC UA mapping failed: SupportedRoleClass on an InternalElement is ambiguous in the implicit role profile; only RoleRequirements is supported. |
| `UP-APP-005` | upstream-application-legacy | observation | `XSLT-RAW` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `UP-APP-005` | upstream-application-legacy | observation | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `UP-APP-005` | upstream-application-legacy | observation | `XSLT-PATCHED` | no | **FAIL** | no_roundtrip_metadata: forbidden shadow nodes AMLAttributeDataType, AMLDefaultValue |
| `UP-APP-006` | upstream-application | must | `PY-STRICT` | yes | **PASS** |  |
| `UP-APP-006` | upstream-application | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `UP-APP-006` | upstream-application | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `UP-APP-006` | upstream-application | must | `XSLT-PATCHED` | no | **PASS** |  |
| `UP-APP-007` | upstream-application | must | `PY-STRICT` | yes | **PASS** |  |
| `UP-APP-007` | upstream-application | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `UP-APP-007` | upstream-application | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `UP-APP-007` | upstream-application | must | `XSLT-PATCHED` | no | **PASS** |  |
| `UP-APP-008` | upstream-application | must | `PY-STRICT` | yes | **PASS** |  |
| `UP-APP-008` | upstream-application | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `UP-APP-008` | upstream-application | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `UP-APP-008` | upstream-application | must | `XSLT-PATCHED` | no | **PASS** |  |
| `UP-APP-009` | upstream-application | must | `PY-STRICT` | yes | **PASS** |  |
| `UP-APP-009` | upstream-application | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `UP-APP-009` | upstream-application | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `UP-APP-009` | upstream-application | must | `XSLT-PATCHED` | no | **PASS** |  |
| `UP-APP-010` | upstream-application-legacy | observation | `PY-STRICT` | no | **FAIL** | Python OPC UA mapping failed: SupportedRoleClass on an InternalElement is ambiguous in the implicit role profile; only RoleRequirements is supported. |
| `UP-APP-010` | upstream-application-legacy | observation | `XSLT-RAW` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `UP-APP-010` | upstream-application-legacy | observation | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `UP-APP-010` | upstream-application-legacy | observation | `XSLT-PATCHED` | no | **FAIL** | no_roundtrip_metadata: forbidden shadow nodes AMLAttributeDataType |
| `UP-APP-011` | upstream-application-legacy | observation | `PY-STRICT` | no | **FAIL** | Python OPC UA mapping failed: SupportedRoleClass on an InternalElement is ambiguous in the implicit role profile; only RoleRequirements is supported. |
| `UP-APP-011` | upstream-application-legacy | observation | `XSLT-RAW` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `UP-APP-011` | upstream-application-legacy | observation | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `UP-APP-011` | upstream-application-legacy | observation | `XSLT-PATCHED` | no | **FAIL** | no_roundtrip_metadata: forbidden shadow nodes AMLAttributeDataType |
| `UP-APP-012` | upstream-application-legacy | observation | `PY-STRICT` | no | **FAIL** | Python OPC UA mapping failed: SupportedRoleClass on an InternalElement is ambiguous in the implicit role profile; only RoleRequirements is supported. |
| `UP-APP-012` | upstream-application-legacy | observation | `XSLT-RAW` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `UP-APP-012` | upstream-application-legacy | observation | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `UP-APP-012` | upstream-application-legacy | observation | `XSLT-PATCHED` | no | **PASS** |  |
| `UP-APP-013` | upstream-application-legacy | observation | `PY-STRICT` | no | **FAIL** | Python OPC UA mapping failed: SupportedRoleClass on an InternalElement is ambiguous in the implicit role profile; only RoleRequirements is supported. |
| `UP-APP-013` | upstream-application-legacy | observation | `XSLT-RAW` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `UP-APP-013` | upstream-application-legacy | observation | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `UP-APP-013` | upstream-application-legacy | observation | `XSLT-PATCHED` | no | **PASS** |  |
| `UP-APP-014` | upstream-application | must | `PY-STRICT` | yes | **PASS** |  |
| `UP-APP-014` | upstream-application | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `UP-APP-014` | upstream-application | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `UP-APP-014` | upstream-application | must | `XSLT-PATCHED` | no | **PASS** |  |
| `UP-OPC-000` | upstream-opc-observation | observation | `PY-STRICT` | no | **PASS** |  |
| `UP-OPC-000` | upstream-opc-observation | observation | `XSLT-RAW` | no | **PASS** |  |
| `UP-OPC-000` | upstream-opc-observation | observation | `XSLT-RUNNER` | no | **PASS** |  |
| `UP-OPC-000` | upstream-opc-observation | observation | `XSLT-PATCHED` | no | **PASS** |  |
| `UP-OPC-001` | upstream-opc-observation | observation | `PY-STRICT` | no | **UNSUPPORTED** | The semantic OPC UA reverse mapping 'automationml-python-semantic-v3' does not yet support a NodeSet without exactly one UAObject of CAEXFileType. Use an app export with embedde... |
| `UP-OPC-001` | upstream-opc-observation | observation | `XSLT-RAW` | no | **PASS** |  |
| `UP-OPC-001` | upstream-opc-observation | observation | `XSLT-RUNNER` | no | **PASS** |  |
| `UP-OPC-001` | upstream-opc-observation | observation | `XSLT-PATCHED` | no | **UNSUPPORTED** | The semantic OPC UA reverse mapping 'automationml-python-semantic-v3' does not yet support a NodeSet without exactly one UAObject of CAEXFileType. Use an app export with embedde... |
| `UP-OPC-002` | upstream-opc-observation | observation | `PY-STRICT` | no | **UNSUPPORTED** | The semantic OPC UA reverse mapping 'automationml-python-semantic-v3' does not yet support CAEXFile properties CAEXSchemaVersion, Version. Use an app export with embedded AML fo... |
| `UP-OPC-002` | upstream-opc-observation | observation | `XSLT-RAW` | no | **PASS** |  |
| `UP-OPC-002` | upstream-opc-observation | observation | `XSLT-RUNNER` | no | **PASS** |  |
| `UP-OPC-002` | upstream-opc-observation | observation | `XSLT-PATCHED` | no | **UNSUPPORTED** | The semantic OPC UA reverse mapping 'automationml-python-semantic-v3' does not yet support CAEXFile properties CAEXSchemaVersion, Version. Use an app export with embedded AML fo... |
| `UP-OPC-003` | upstream-opc-observation | observation | `PY-STRICT` | no | **UNSUPPORTED** | The semantic OPC UA reverse mapping 'automationml-python-semantic-v3' does not yet support a NodeSet without exactly one UAObject of CAEXFileType. Use an app export with embedde... |
| `UP-OPC-003` | upstream-opc-observation | observation | `XSLT-RAW` | no | **PASS** |  |
| `UP-OPC-003` | upstream-opc-observation | observation | `XSLT-RUNNER` | no | **PASS** |  |
| `UP-OPC-003` | upstream-opc-observation | observation | `XSLT-PATCHED` | no | **UNSUPPORTED** | The semantic OPC UA reverse mapping 'automationml-python-semantic-v3' does not yet support a NodeSet without exactly one UAObject of CAEXFileType. Use an app export with embedde... |
| `UP-OPC-004` | upstream-opc-observation | observation | `PY-STRICT` | no | **INVALID_FIXTURE** | invalid NodeSet fixture: nodeset_semantics: unresolved reference target 'ns=8;s=' |
| `UP-OPC-004` | upstream-opc-observation | observation | `XSLT-RAW` | no | **INVALID_FIXTURE** | invalid NodeSet fixture: nodeset_semantics: unresolved reference target 'ns=8;s=' |
| `UP-OPC-004` | upstream-opc-observation | observation | `XSLT-RUNNER` | no | **INVALID_FIXTURE** | invalid NodeSet fixture: nodeset_semantics: unresolved reference target 'ns=8;s=' |
| `UP-OPC-004` | upstream-opc-observation | observation | `XSLT-PATCHED` | no | **INVALID_FIXTURE** | invalid NodeSet fixture: nodeset_semantics: unresolved reference target 'ns=8;s=' |
| `UP-OPC-005` | upstream-opc-observation | observation | `PY-STRICT` | no | **PASS** |  |
| `UP-OPC-005` | upstream-opc-observation | observation | `XSLT-RAW` | no | **PASS** |  |
| `UP-OPC-005` | upstream-opc-observation | observation | `XSLT-RUNNER` | no | **PASS** |  |
| `UP-OPC-005` | upstream-opc-observation | observation | `XSLT-PATCHED` | no | **PASS** |  |
| `UP-OPC-006` | upstream-opc-observation | observation | `PY-STRICT` | no | **UNSUPPORTED** | The semantic OPC UA reverse mapping 'automationml-python-semantic-v3' does not yet support CAEXFile properties CAEXSchemaVersion. Use an app export with embedded AML for an exac... |
| `UP-OPC-006` | upstream-opc-observation | observation | `XSLT-RAW` | no | **PASS** |  |
| `UP-OPC-006` | upstream-opc-observation | observation | `XSLT-RUNNER` | no | **PASS** |  |
| `UP-OPC-006` | upstream-opc-observation | observation | `XSLT-PATCHED` | no | **UNSUPPORTED** | The semantic OPC UA reverse mapping 'automationml-python-semantic-v3' does not yet support CAEXFile properties CAEXSchemaVersion. Use an app export with embedded AML for an exac... |
| `REG-NODEID-001` | known-defect | critical | `PY-STRICT` | yes | **PASS** |  |
| `REG-NODEID-001` | known-defect | critical | `XSLT-RAW` | yes | **FAIL** | expected_graph: NodeIds match forbidden 'ns=\\d+;ns=': ['ns=2;ns=2;i=2004', 'ns=2;ns=2;i=2005', 'ns=2;ns=2;i=2006'] |
| `REG-NODEID-001` | known-defect | critical | `XSLT-RUNNER` | no | **FAIL** | expected_graph: NodeIds match forbidden 'ns=\\d+;ns=': ['ns=2;ns=2;i=2004', 'ns=2;ns=2;i=2005', 'ns=2;ns=2;i=2006'] |
| `REG-NODEID-001` | known-defect | critical | `XSLT-PATCHED` | no | **PASS** |  |
| `REG-REF-001` | known-defect | critical | `PY-STRICT` | yes | **PASS** |  |
| `REG-REF-001` | known-defect | critical | `XSLT-RAW` | yes | **FAIL** | expected_graph: forbidden reference types HasComponnent |
| `REG-REF-001` | known-defect | critical | `XSLT-RUNNER` | no | **FAIL** | expected_graph: forbidden reference types HasComponnent |
| `REG-REF-001` | known-defect | critical | `XSLT-PATCHED` | no | **FAIL** | no_roundtrip_metadata: forbidden shadow nodes AMLAttributeDataType |
| `REG-MODEL-001` | known-defect | critical | `PY-STRICT` | yes | **PASS** |  |
| `REG-MODEL-001` | known-defect | critical | `XSLT-RAW` | yes | **FAIL** | expected_graph: a Model Version is absent or empty |
| `REG-MODEL-001` | known-defect | critical | `XSLT-RUNNER` | no | **FAIL** | expected_graph: a Model Version is absent or empty |
| `REG-MODEL-001` | known-defect | critical | `XSLT-PATCHED` | no | **FAIL** | no_roundtrip_metadata: forbidden shadow nodes AMLAttributeDataType |
| `REG-DETERMINISM-001` | known-defect | critical | `PY-STRICT` | yes | **PASS** |  |
| `REG-DETERMINISM-001` | known-defect | critical | `XSLT-RAW` | yes | **FAIL** | expected_graph: required PublicationDate '2026-08-17T00:00:00Z' is absent; got ['2026-08-17T03:44:15Z'] |
| `REG-DETERMINISM-001` | known-defect | critical | `XSLT-RUNNER` | no | **PASS** |  |
| `REG-DETERMINISM-001` | known-defect | critical | `XSLT-PATCHED` | no | **PASS** |  |
| `REG-DTYPE-001` | known-defect | critical | `PY-STRICT` | yes | **PASS** |  |
| `REG-DTYPE-001` | known-defect | critical | `XSLT-RAW` | yes | **FAIL** | expected_graph: UAVariable 'identifier' count is 0, expected 1 |
| `REG-DTYPE-001` | known-defect | critical | `XSLT-RUNNER` | no | **FAIL** | expected_graph: UAVariable 'identifier' count is 0, expected 1 |
| `REG-DTYPE-001` | known-defect | critical | `XSLT-PATCHED` | no | **FAIL** | no_roundtrip_metadata: forbidden shadow nodes AMLAttributeDataType |
| `REG-DTYPE-002` | known-defect | critical | `PY-STRICT` | yes | **PASS** |  |
| `REG-DTYPE-002` | known-defect | critical | `XSLT-RAW` | yes | **FAIL** | expected_graph: UAVariable 'timestamp' count is 0, expected 1 |
| `REG-DTYPE-002` | known-defect | critical | `XSLT-RUNNER` | no | **FAIL** | expected_graph: UAVariable 'timestamp' count is 0, expected 1 |
| `REG-DTYPE-002` | known-defect | critical | `XSLT-PATCHED` | no | **FAIL** | no_roundtrip_metadata: forbidden shadow nodes AMLAttributeDataType |
| `REG-DTYPE-003` | known-defect | critical | `PY-STRICT` | yes | **PASS** |  |
| `REG-DTYPE-003` | known-defect | critical | `XSLT-RAW` | yes | **FAIL** | expected_graph: UAVariable 'token' count is 0, expected 1 |
| `REG-DTYPE-003` | known-defect | critical | `XSLT-RUNNER` | no | **FAIL** | expected_graph: UAVariable 'token' count is 0, expected 1 |
| `REG-DTYPE-003` | known-defect | critical | `XSLT-PATCHED` | no | **FAIL** | no_roundtrip_metadata: forbidden shadow nodes AMLAttributeDataType |
| `REG-CLASS-001` | known-defect | critical | `PY-STRICT` | yes | **PASS** |  |
| `REG-CLASS-001` | known-defect | critical | `XSLT-RAW` | yes | **FAIL** | expected_graph: NodeIds match forbidden '/': ['ConnectorLib/BaseConnector/PortConnector'] |
| `REG-CLASS-001` | known-defect | critical | `XSLT-RUNNER` | no | **FAIL** | expected_graph: NodeIds match forbidden '/': ['ConnectorLib/BaseConnector/PortConnector'] |
| `REG-CLASS-001` | known-defect | critical | `XSLT-PATCHED` | no | **PASS** |  |
| `REG-IDENTITY-001` | known-defect | critical | `PY-STRICT` | yes | **PASS** |  |
| `REG-IDENTITY-001` | known-defect | critical | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `REG-IDENTITY-001` | known-defect | critical | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `REG-IDENTITY-001` | known-defect | critical | `XSLT-PATCHED` | no | **FAIL** | expected_graph: UAVariable 'SourceDocumentInformation_2' count is 0, expected 1 |
| `REG-CLASS-002` | known-defect | critical | `PY-STRICT` | yes | **PASS** |  |
| `REG-CLASS-002` | known-defect | critical | `XSLT-RAW` | yes | **PASS** |  |
| `REG-CLASS-002` | known-defect | critical | `XSLT-RUNNER` | no | **PASS** |  |
| `REG-CLASS-002` | known-defect | critical | `XSLT-PATCHED` | no | **PASS** |  |
| `REG-ATTR-001` | known-defect | critical | `PY-STRICT` | yes | **PASS** |  |
| `REG-ATTR-001` | known-defect | critical | `XSLT-RAW` | yes | **FAIL** | expected_graph: UAVariable 'DefaultValue' count is 0, expected 1 |
| `REG-ATTR-001` | known-defect | critical | `XSLT-RUNNER` | no | **FAIL** | expected_graph: UAVariable 'DefaultValue' count is 0, expected 1 |
| `REG-ATTR-001` | known-defect | critical | `XSLT-PATCHED` | no | **FAIL** | no_roundtrip_metadata: forbidden shadow nodes AMLAttributeDataType, AMLDefaultValue |
| `REG-ATTR-002` | known-defect | critical | `PY-STRICT` | yes | **PASS** |  |
| `REG-ATTR-002` | known-defect | critical | `XSLT-RAW` | yes | **FAIL** | expected_graph: UAVariable 'state' count is 0, expected 1 |
| `REG-ATTR-002` | known-defect | critical | `XSLT-RUNNER` | no | **FAIL** | expected_graph: UAVariable 'state' count is 0, expected 1 |
| `REG-ATTR-002` | known-defect | critical | `XSLT-PATCHED` | no | **FAIL** | no_roundtrip_metadata: forbidden shadow nodes AMLAttributeDataType, AMLDefaultValue |
| `AML-DOC-001` | document-header | must | `PY-STRICT` | yes | **PASS** |  |
| `AML-DOC-001` | document-header | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-DOC-001` | document-header | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-DOC-001` | document-header | must | `XSLT-PATCHED` | no | **PASS** |  |
| `AML-DOC-002` | document-header | must | `PY-STRICT` | yes | **CANONICAL_PASS** |  |
| `AML-DOC-002` | document-header | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-DOC-002` | document-header | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-DOC-002` | document-header | must | `XSLT-PATCHED` | no | **FAIL** | Generated UANodeSet has duplicate NodeId 'ns=1;s=CAEXFile_SuperiorStandardVersion'. |
| `AML-DOC-003` | document-header | must | `PY-STRICT` | yes | **CANONICAL_PASS** |  |
| `AML-DOC-003` | document-header | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-DOC-003` | document-header | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-DOC-003` | document-header | must | `XSLT-PATCHED` | no | **FAIL** | Generated UANodeSet has duplicate NodeId 'ns=1;s=CAEXFile_SuperiorStandardVersion'. |
| `AML-DOC-004` | document-header | must | `PY-STRICT` | yes | **CANONICAL_PASS** |  |
| `AML-DOC-004` | document-header | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-DOC-004` | document-header | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-DOC-004` | document-header | must | `XSLT-PATCHED` | no | **FAIL** | Generated UANodeSet has duplicate NodeId 'ns=1;s=CAEXFile_SuperiorStandardVersion'. |
| `AML-DOC-005` | document-header | must | `PY-STRICT` | yes | **CANONICAL_PASS** |  |
| `AML-DOC-005` | document-header | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-DOC-005` | document-header | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-DOC-005` | document-header | must | `XSLT-PATCHED` | no | **FAIL** | Generated UANodeSet has duplicate NodeId 'ns=1;s=CAEXFile_SuperiorStandardVersion'. |
| `AML-DOC-006` | document-header | critical | `PY-STRICT` | yes | **EXPECTED_REJECTION** | Python OPC UA mapping failed: Python OPC UA strict profile does not yet support CAEXFile Revision. |
| `AML-DOC-006` | document-header | critical | `XSLT-RAW` | yes | **FAIL** | expected_rejection: mapper accepted input that must be rejected |
| `AML-DOC-006` | document-header | critical | `XSLT-RUNNER` | no | **FAIL** | expected_rejection: mapper accepted input that must be rejected |
| `AML-DOC-006` | document-header | critical | `XSLT-PATCHED` | no | **FAIL** | expected_rejection: mapper accepted input that must be rejected |
| `AML-TREE-001` | hierarchy-class | must | `PY-STRICT` | yes | **CANONICAL_PASS** |  |
| `AML-TREE-001` | hierarchy-class | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-TREE-001` | hierarchy-class | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-TREE-001` | hierarchy-class | must | `XSLT-PATCHED` | no | **FAIL** | Generated UANodeSet has duplicate NodeId 'ns=1;s=CAEXFile_SuperiorStandardVersion'. |
| `AML-TREE-002` | hierarchy-class | must | `PY-STRICT` | yes | **CANONICAL_PASS** |  |
| `AML-TREE-002` | hierarchy-class | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-TREE-002` | hierarchy-class | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-TREE-002` | hierarchy-class | must | `XSLT-PATCHED` | no | **FAIL** | Generated UANodeSet has duplicate NodeId 'ns=1;s=CAEXFile_SuperiorStandardVersion'. |
| `AML-TREE-003` | hierarchy-class | must | `PY-STRICT` | yes | **CANONICAL_PASS** |  |
| `AML-TREE-003` | hierarchy-class | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-TREE-003` | hierarchy-class | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-TREE-003` | hierarchy-class | must | `XSLT-PATCHED` | no | **FAIL** | Generated UANodeSet has duplicate NodeId 'ns=1;s=CAEXFile_SuperiorStandardVersion'. |
| `AML-TREE-004` | hierarchy-class | must | `PY-STRICT` | yes | **CANONICAL_PASS** |  |
| `AML-TREE-004` | hierarchy-class | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-TREE-004` | hierarchy-class | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-TREE-004` | hierarchy-class | must | `XSLT-PATCHED` | no | **FAIL** | Generated UANodeSet has duplicate NodeId 'ns=1;s=CAEXFile_SuperiorStandardVersion'. |
| `AML-TREE-005` | hierarchy-class | must | `PY-STRICT` | yes | **CANONICAL_PASS** |  |
| `AML-TREE-005` | hierarchy-class | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-TREE-005` | hierarchy-class | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-TREE-005` | hierarchy-class | must | `XSLT-PATCHED` | no | **FAIL** | Generated UANodeSet has duplicate NodeId 'ns=1;s=CAEXFile_SuperiorStandardVersion'. |
| `AML-TREE-006` | hierarchy-class | must | `PY-STRICT` | yes | **CANONICAL_PASS** |  |
| `AML-TREE-006` | hierarchy-class | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-TREE-006` | hierarchy-class | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-TREE-006` | hierarchy-class | must | `XSLT-PATCHED` | no | **FAIL** | Generated UANodeSet has duplicate NodeId 'ns=1;s=CAEXFile_SuperiorStandardVersion'. |
| `AML-TREE-007` | hierarchy-class | must | `PY-STRICT` | yes | **CANONICAL_PASS** |  |
| `AML-TREE-007` | hierarchy-class | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-TREE-007` | hierarchy-class | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-TREE-007` | hierarchy-class | must | `XSLT-PATCHED` | no | **FAIL** | Generated UANodeSet has duplicate NodeId 'ns=1;s=CAEXFile_SuperiorStandardVersion'. |
| `AML-TREE-008` | hierarchy-class | must | `PY-STRICT` | yes | **CANONICAL_PASS** |  |
| `AML-TREE-008` | hierarchy-class | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-TREE-008` | hierarchy-class | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-TREE-008` | hierarchy-class | must | `XSLT-PATCHED` | no | **FAIL** | Generated UANodeSet has duplicate NodeId 'ns=1;s=CAEXFile_SuperiorStandardVersion'. |
| `AML-TREE-009` | hierarchy-class | must | `PY-STRICT` | yes | **CANONICAL_PASS** |  |
| `AML-TREE-009` | hierarchy-class | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-TREE-009` | hierarchy-class | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-TREE-009` | hierarchy-class | must | `XSLT-PATCHED` | no | **FAIL** | Generated UANodeSet has duplicate NodeId 'ns=1;s=CAEXFile_SuperiorStandardVersion'. |
| `AML-TREE-010` | hierarchy-class | must | `PY-STRICT` | yes | **CANONICAL_PASS** |  |
| `AML-TREE-010` | hierarchy-class | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-TREE-010` | hierarchy-class | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-TREE-010` | hierarchy-class | must | `XSLT-PATCHED` | no | **FAIL** | Generated UANodeSet has duplicate NodeId 'ns=1;s=CAEXFile_SuperiorStandardVersion'. |
| `AML-DTYPE-001` | datatype-matrix | must | `PY-STRICT` | yes | **CANONICAL_PASS** |  |
| `AML-DTYPE-001` | datatype-matrix | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-DTYPE-001` | datatype-matrix | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-DTYPE-001` | datatype-matrix | must | `XSLT-PATCHED` | no | **FAIL** | Generated UANodeSet has duplicate NodeId 'ns=1;s=CAEXFile_SuperiorStandardVersion'. |
| `AML-DTYPE-002` | datatype-matrix | must | `PY-STRICT` | yes | **CANONICAL_PASS** |  |
| `AML-DTYPE-002` | datatype-matrix | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-DTYPE-002` | datatype-matrix | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-DTYPE-002` | datatype-matrix | must | `XSLT-PATCHED` | no | **FAIL** | Generated UANodeSet has duplicate NodeId 'ns=1;s=CAEXFile_SuperiorStandardVersion'. |
| `AML-DTYPE-003` | datatype-matrix | must | `PY-STRICT` | yes | **CANONICAL_PASS** |  |
| `AML-DTYPE-003` | datatype-matrix | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-DTYPE-003` | datatype-matrix | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-DTYPE-003` | datatype-matrix | must | `XSLT-PATCHED` | no | **FAIL** | Generated UANodeSet has duplicate NodeId 'ns=1;s=CAEXFile_SuperiorStandardVersion'. |
| `AML-DTYPE-004` | datatype-matrix | must | `PY-STRICT` | yes | **CANONICAL_PASS** |  |
| `AML-DTYPE-004` | datatype-matrix | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-DTYPE-004` | datatype-matrix | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-DTYPE-004` | datatype-matrix | must | `XSLT-PATCHED` | no | **FAIL** | Generated UANodeSet has duplicate NodeId 'ns=1;s=CAEXFile_SuperiorStandardVersion'. |
| `AML-DTYPE-005` | datatype-matrix | must | `PY-STRICT` | yes | **CANONICAL_PASS** |  |
| `AML-DTYPE-005` | datatype-matrix | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-DTYPE-005` | datatype-matrix | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-DTYPE-005` | datatype-matrix | must | `XSLT-PATCHED` | no | **FAIL** | Generated UANodeSet has duplicate NodeId 'ns=1;s=CAEXFile_SuperiorStandardVersion'. |
| `AML-DTYPE-006` | datatype-matrix | must | `PY-STRICT` | yes | **CANONICAL_PASS** |  |
| `AML-DTYPE-006` | datatype-matrix | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-DTYPE-006` | datatype-matrix | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-DTYPE-006` | datatype-matrix | must | `XSLT-PATCHED` | no | **FAIL** | Generated UANodeSet has duplicate NodeId 'ns=1;s=CAEXFile_SuperiorStandardVersion'. |
| `AML-DTYPE-007` | datatype-matrix | must | `PY-STRICT` | yes | **CANONICAL_PASS** |  |
| `AML-DTYPE-007` | datatype-matrix | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-DTYPE-007` | datatype-matrix | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-DTYPE-007` | datatype-matrix | must | `XSLT-PATCHED` | no | **FAIL** | Generated UANodeSet has duplicate NodeId 'ns=1;s=CAEXFile_SuperiorStandardVersion'. |
| `AML-DTYPE-008` | datatype-matrix | must | `PY-STRICT` | yes | **CANONICAL_PASS** |  |
| `AML-DTYPE-008` | datatype-matrix | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-DTYPE-008` | datatype-matrix | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-DTYPE-008` | datatype-matrix | must | `XSLT-PATCHED` | no | **FAIL** | Generated UANodeSet has duplicate NodeId 'ns=1;s=CAEXFile_SuperiorStandardVersion'. |
| `AML-DTYPE-009` | datatype-matrix | must | `PY-STRICT` | yes | **CANONICAL_PASS** |  |
| `AML-DTYPE-009` | datatype-matrix | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-DTYPE-009` | datatype-matrix | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-DTYPE-009` | datatype-matrix | must | `XSLT-PATCHED` | no | **FAIL** | Generated UANodeSet has duplicate NodeId 'ns=1;s=CAEXFile_SuperiorStandardVersion'. |
| `AML-DTYPE-010` | datatype-matrix | must | `PY-STRICT` | yes | **CANONICAL_PASS** |  |
| `AML-DTYPE-010` | datatype-matrix | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-DTYPE-010` | datatype-matrix | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-DTYPE-010` | datatype-matrix | must | `XSLT-PATCHED` | no | **FAIL** | Generated UANodeSet has duplicate NodeId 'ns=1;s=CAEXFile_SuperiorStandardVersion'. |
| `AML-DTYPE-011` | datatype-matrix | must | `PY-STRICT` | yes | **CANONICAL_PASS** |  |
| `AML-DTYPE-011` | datatype-matrix | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-DTYPE-011` | datatype-matrix | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-DTYPE-011` | datatype-matrix | must | `XSLT-PATCHED` | no | **FAIL** | Generated UANodeSet has duplicate NodeId 'ns=1;s=CAEXFile_SuperiorStandardVersion'. |
| `AML-DTYPE-012` | datatype-matrix | must | `PY-STRICT` | yes | **CANONICAL_PASS** |  |
| `AML-DTYPE-012` | datatype-matrix | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-DTYPE-012` | datatype-matrix | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-DTYPE-012` | datatype-matrix | must | `XSLT-PATCHED` | no | **FAIL** | Generated UANodeSet has duplicate NodeId 'ns=1;s=CAEXFile_SuperiorStandardVersion'. |
| `AML-DTYPE-013` | datatype-matrix | must | `PY-STRICT` | yes | **CANONICAL_PASS** |  |
| `AML-DTYPE-013` | datatype-matrix | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-DTYPE-013` | datatype-matrix | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-DTYPE-013` | datatype-matrix | must | `XSLT-PATCHED` | no | **FAIL** | Generated UANodeSet has duplicate NodeId 'ns=1;s=CAEXFile_SuperiorStandardVersion'. |
| `AML-DTYPE-014` | datatype-matrix | must | `PY-STRICT` | yes | **CANONICAL_PASS** |  |
| `AML-DTYPE-014` | datatype-matrix | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-DTYPE-014` | datatype-matrix | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-DTYPE-014` | datatype-matrix | must | `XSLT-PATCHED` | no | **FAIL** | Generated UANodeSet has duplicate NodeId 'ns=1;s=CAEXFile_SuperiorStandardVersion'. |
| `AML-DTYPE-015` | datatype-matrix | must | `PY-STRICT` | yes | **CANONICAL_PASS** |  |
| `AML-DTYPE-015` | datatype-matrix | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-DTYPE-015` | datatype-matrix | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-DTYPE-015` | datatype-matrix | must | `XSLT-PATCHED` | no | **FAIL** | Generated UANodeSet has duplicate NodeId 'ns=1;s=CAEXFile_SuperiorStandardVersion'. |
| `AML-DTYPE-016` | datatype-matrix | must | `PY-STRICT` | yes | **CANONICAL_PASS** |  |
| `AML-DTYPE-016` | datatype-matrix | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-DTYPE-016` | datatype-matrix | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-DTYPE-016` | datatype-matrix | must | `XSLT-PATCHED` | no | **FAIL** | Generated UANodeSet has duplicate NodeId 'ns=1;s=CAEXFile_SuperiorStandardVersion'. |
| `AML-DTYPE-017` | datatype-matrix | must | `PY-STRICT` | yes | **CANONICAL_PASS** |  |
| `AML-DTYPE-017` | datatype-matrix | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-DTYPE-017` | datatype-matrix | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-DTYPE-017` | datatype-matrix | must | `XSLT-PATCHED` | no | **FAIL** | Generated UANodeSet has duplicate NodeId 'ns=1;s=CAEXFile_SuperiorStandardVersion'. |
| `AML-DTYPE-018` | datatype-matrix | must | `PY-STRICT` | yes | **CANONICAL_PASS** |  |
| `AML-DTYPE-018` | datatype-matrix | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-DTYPE-018` | datatype-matrix | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-DTYPE-018` | datatype-matrix | must | `XSLT-PATCHED` | no | **FAIL** | Generated UANodeSet has duplicate NodeId 'ns=1;s=CAEXFile_SuperiorStandardVersion'. |
| `AML-DTYPE-019` | datatype-matrix | must | `PY-STRICT` | yes | **CANONICAL_PASS** |  |
| `AML-DTYPE-019` | datatype-matrix | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-DTYPE-019` | datatype-matrix | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-DTYPE-019` | datatype-matrix | must | `XSLT-PATCHED` | no | **FAIL** | Generated UANodeSet has duplicate NodeId 'ns=1;s=CAEXFile_SuperiorStandardVersion'. |
| `AML-DTYPE-020` | datatype-matrix | must | `PY-STRICT` | yes | **CANONICAL_PASS** |  |
| `AML-DTYPE-020` | datatype-matrix | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-DTYPE-020` | datatype-matrix | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-DTYPE-020` | datatype-matrix | must | `XSLT-PATCHED` | no | **FAIL** | Generated UANodeSet has duplicate NodeId 'ns=1;s=CAEXFile_SuperiorStandardVersion'. |
| `AML-DTYPE-021` | datatype-matrix | critical | `PY-STRICT` | yes | **EXPECTED_REJECTION** | Python OPC UA mapping failed: Python OPC UA strict profile cannot safely translate AML AttributeDataType 'xs:decimal'. |
| `AML-DTYPE-021` | datatype-matrix | critical | `XSLT-RAW` | yes | **FAIL** | expected_rejection: mapper accepted input that must be rejected |
| `AML-DTYPE-021` | datatype-matrix | critical | `XSLT-RUNNER` | no | **FAIL** | expected_rejection: mapper accepted input that must be rejected |
| `AML-DTYPE-021` | datatype-matrix | critical | `XSLT-PATCHED` | no | **FAIL** | Generated UANodeSet has unresolved DataType value 'Decimal'. |
| `AML-ATTR-001` | attribute-semantics | must | `PY-STRICT` | yes | **CANONICAL_PASS** |  |
| `AML-ATTR-001` | attribute-semantics | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-ATTR-001` | attribute-semantics | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-ATTR-001` | attribute-semantics | must | `XSLT-PATCHED` | no | **FAIL** | Generated UANodeSet has duplicate NodeId 'ns=1;s=CAEXFile_SuperiorStandardVersion'. |
| `AML-ATTR-002` | attribute-semantics | must | `PY-STRICT` | yes | **CANONICAL_PASS** |  |
| `AML-ATTR-002` | attribute-semantics | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-ATTR-002` | attribute-semantics | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-ATTR-002` | attribute-semantics | must | `XSLT-PATCHED` | no | **FAIL** | Generated UANodeSet has duplicate NodeId 'ns=1;s=CAEXFile_SuperiorStandardVersion'. |
| `AML-ATTR-003` | attribute-semantics | must | `PY-STRICT` | yes | **PASS** |  |
| `AML-ATTR-003` | attribute-semantics | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-ATTR-003` | attribute-semantics | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-ATTR-003` | attribute-semantics | must | `XSLT-PATCHED` | no | **FAIL** | no_roundtrip_metadata: forbidden shadow nodes AMLAttributeDataType, AMLDefaultValue |
| `AML-ATTR-004` | attribute-semantics | must | `PY-STRICT` | yes | **CANONICAL_PASS** |  |
| `AML-ATTR-004` | attribute-semantics | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-ATTR-004` | attribute-semantics | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-ATTR-004` | attribute-semantics | must | `XSLT-PATCHED` | no | **FAIL** | Generated UANodeSet has duplicate NodeId 'ns=1;s=CAEXFile_SuperiorStandardVersion'. |
| `AML-ATTR-005` | attribute-semantics | must | `PY-STRICT` | yes | **CANONICAL_PASS** |  |
| `AML-ATTR-005` | attribute-semantics | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-ATTR-005` | attribute-semantics | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-ATTR-005` | attribute-semantics | must | `XSLT-PATCHED` | no | **FAIL** | Generated UANodeSet has duplicate NodeId 'ns=1;s=CAEXFile_SuperiorStandardVersion'. |
| `AML-ATTR-006` | attribute-semantics | must | `PY-STRICT` | yes | **CANONICAL_PASS** |  |
| `AML-ATTR-006` | attribute-semantics | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-ATTR-006` | attribute-semantics | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-ATTR-006` | attribute-semantics | must | `XSLT-PATCHED` | no | **FAIL** | Generated UANodeSet has duplicate NodeId 'ns=1;s=CAEXFile_SuperiorStandardVersion'. |
| `AML-ATTR-007` | attribute-semantics | must | `PY-STRICT` | yes | **CANONICAL_PASS** |  |
| `AML-ATTR-007` | attribute-semantics | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-ATTR-007` | attribute-semantics | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-ATTR-007` | attribute-semantics | must | `XSLT-PATCHED` | no | **FAIL** | Generated UANodeSet has duplicate NodeId 'ns=1;s=CAEXFile_SuperiorStandardVersion'. |
| `AML-ATTR-008` | attribute-semantics | must | `PY-STRICT` | yes | **CANONICAL_PASS** |  |
| `AML-ATTR-008` | attribute-semantics | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-ATTR-008` | attribute-semantics | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-ATTR-008` | attribute-semantics | must | `XSLT-PATCHED` | no | **FAIL** | Generated UANodeSet has duplicate NodeId 'ns=1;s=CAEXFile_SuperiorStandardVersion'. |
| `AML-SEM-001` | attribute-semantics | must | `PY-STRICT` | yes | **CANONICAL_PASS** |  |
| `AML-SEM-001` | attribute-semantics | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-SEM-001` | attribute-semantics | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-SEM-001` | attribute-semantics | must | `XSLT-PATCHED` | no | **FAIL** | Generated UANodeSet has duplicate NodeId 'ns=1;s=CAEXFile_SuperiorStandardVersion'. |
| `AML-SEM-002` | attribute-semantics | must | `PY-STRICT` | yes | **CANONICAL_PASS** |  |
| `AML-SEM-002` | attribute-semantics | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-SEM-002` | attribute-semantics | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-SEM-002` | attribute-semantics | must | `XSLT-PATCHED` | no | **FAIL** | Generated UANodeSet has duplicate NodeId 'ns=1;s=CAEXFile_SuperiorStandardVersion'. |
| `AML-SEM-003` | attribute-semantics | must | `PY-STRICT` | yes | **CANONICAL_PASS** |  |
| `AML-SEM-003` | attribute-semantics | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-SEM-003` | attribute-semantics | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-SEM-003` | attribute-semantics | must | `XSLT-PATCHED` | no | **FAIL** | Generated UANodeSet has duplicate NodeId 'ns=1;s=CAEXFile_SuperiorStandardVersion'. |
| `AML-ROLE-001` | roles-mapping | must | `PY-STRICT` | yes | **CANONICAL_PASS** |  |
| `AML-ROLE-001` | roles-mapping | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-ROLE-001` | roles-mapping | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-ROLE-001` | roles-mapping | must | `XSLT-PATCHED` | no | **FAIL** | Generated UANodeSet has duplicate NodeId 'ns=1;s=CAEXFile_SuperiorStandardVersion'. |
| `AML-ROLE-002` | roles-mapping | must | `PY-STRICT` | yes | **CANONICAL_PASS** |  |
| `AML-ROLE-002` | roles-mapping | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-ROLE-002` | roles-mapping | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-ROLE-002` | roles-mapping | must | `XSLT-PATCHED` | no | **FAIL** | Generated UANodeSet has duplicate NodeId 'ns=1;s=CAEXFile_SuperiorStandardVersion'. |
| `AML-ROLE-003` | roles-mapping | must | `PY-STRICT` | yes | **CANONICAL_PASS** |  |
| `AML-ROLE-003` | roles-mapping | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-ROLE-003` | roles-mapping | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-ROLE-003` | roles-mapping | must | `XSLT-PATCHED` | no | **FAIL** | Generated UANodeSet has duplicate NodeId 'ns=1;s=CAEXFile_SuperiorStandardVersion'. |
| `AML-ROLE-004` | roles-mapping | must | `PY-STRICT` | yes | **CANONICAL_PASS** |  |
| `AML-ROLE-004` | roles-mapping | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-ROLE-004` | roles-mapping | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-ROLE-004` | roles-mapping | must | `XSLT-PATCHED` | no | **FAIL** | Generated UANodeSet has duplicate NodeId 'ns=1;s=CAEXFile_SuperiorStandardVersion'. |
| `AML-ROLE-005` | roles-mapping | must | `PY-STRICT` | yes | **CANONICAL_PASS** |  |
| `AML-ROLE-005` | roles-mapping | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-ROLE-005` | roles-mapping | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-ROLE-005` | roles-mapping | must | `XSLT-PATCHED` | no | **FAIL** | Generated UANodeSet has duplicate NodeId 'ns=1;s=CAEXFile_SuperiorStandardVersion'. |
| `AML-ROLE-006` | roles-mapping | must | `PY-STRICT` | yes | **CANONICAL_PASS** |  |
| `AML-ROLE-006` | roles-mapping | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-ROLE-006` | roles-mapping | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-ROLE-006` | roles-mapping | must | `XSLT-PATCHED` | no | **FAIL** | Generated UANodeSet has duplicate NodeId 'ns=1;s=CAEXFile_SuperiorStandardVersion'. |
| `AML-ROLE-007` | roles-mapping | critical | `PY-STRICT` | yes | **EXPECTED_REJECTION** | Python OPC UA mapping failed: SupportedRoleClass on an InternalElement is ambiguous in the implicit role profile; only RoleRequirements is supported. |
| `AML-ROLE-007` | roles-mapping | critical | `XSLT-RAW` | yes | **FAIL** | expected_rejection: mapper accepted input that must be rejected |
| `AML-ROLE-007` | roles-mapping | critical | `XSLT-RUNNER` | no | **FAIL** | expected_rejection: mapper accepted input that must be rejected |
| `AML-ROLE-007` | roles-mapping | critical | `XSLT-PATCHED` | no | **FAIL** | expected_rejection: mapper accepted input that must be rejected |
| `AML-LINK-001` | interfaces-links | must | `PY-STRICT` | yes | **CANONICAL_PASS** |  |
| `AML-LINK-001` | interfaces-links | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-LINK-001` | interfaces-links | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-LINK-001` | interfaces-links | must | `XSLT-PATCHED` | no | **FAIL** | Generated UANodeSet has duplicate NodeId 'ns=1;s=CAEXFile_SuperiorStandardVersion'. |
| `AML-LINK-002` | interfaces-links | must | `PY-STRICT` | yes | **CANONICAL_PASS** |  |
| `AML-LINK-002` | interfaces-links | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-LINK-002` | interfaces-links | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-LINK-002` | interfaces-links | must | `XSLT-PATCHED` | no | **FAIL** | Generated UANodeSet has duplicate NodeId 'ns=1;s=CAEXFile_SuperiorStandardVersion'. |
| `AML-LINK-003` | interfaces-links | must | `PY-STRICT` | yes | **CANONICAL_PASS** |  |
| `AML-LINK-003` | interfaces-links | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-LINK-003` | interfaces-links | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-LINK-003` | interfaces-links | must | `XSLT-PATCHED` | no | **FAIL** | Generated UANodeSet has duplicate NodeId 'ns=1;s=CAEXFile_SuperiorStandardVersion'. |
| `AML-LINK-004` | interfaces-links | must | `PY-STRICT` | yes | **PASS** |  |
| `AML-LINK-004` | interfaces-links | must | `XSLT-RAW` | yes | **FAIL** | canonical_aml: first difference at /FileName |
| `AML-LINK-004` | interfaces-links | must | `XSLT-RUNNER` | no | **FAIL** | canonical_aml: first difference at /FileName |
| `AML-LINK-004` | interfaces-links | must | `XSLT-PATCHED` | no | **PASS** |  |
| `AML-LINK-005` | interfaces-links | must | `PY-STRICT` | yes | **CANONICAL_PASS** |  |
| `AML-LINK-005` | interfaces-links | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-LINK-005` | interfaces-links | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-LINK-005` | interfaces-links | must | `XSLT-PATCHED` | no | **FAIL** | Generated UANodeSet has duplicate NodeId 'ns=1;s=CAEXFile_SuperiorStandardVersion'. |
| `AML-LINK-006` | interfaces-links | critical | `PY-STRICT` | yes | **EXPECTED_REJECTION** | Python OPC UA mapping failed: Parallel AML InternalLinks between the same directed ExternalInterfaces cannot be represented by one native edge. |
| `AML-LINK-006` | interfaces-links | critical | `XSLT-RAW` | yes | **FAIL** | expected_rejection: mapper accepted input that must be rejected |
| `AML-LINK-006` | interfaces-links | critical | `XSLT-RUNNER` | no | **FAIL** | expected_rejection: mapper accepted input that must be rejected |
| `AML-LINK-006` | interfaces-links | critical | `XSLT-PATCHED` | no | **FAIL** | expected_rejection: mapper accepted input that must be rejected |
| `AML-LINK-007` | interfaces-links | critical | `PY-STRICT` | yes | **EXPECTED_REJECTION** | Python OPC UA mapping failed: InternalLink 'broken' references unknown partner 'missing-owner:Missing'. |
| `AML-LINK-007` | interfaces-links | critical | `XSLT-RAW` | yes | **FAIL** | expected_rejection: mapper accepted input that must be rejected |
| `AML-LINK-007` | interfaces-links | critical | `XSLT-RUNNER` | no | **FAIL** | expected_rejection: mapper accepted input that must be rejected |
| `AML-LINK-007` | interfaces-links | critical | `XSLT-PATCHED` | no | **FAIL** | Generated UANodeSet has unresolved reference value 'ns=5;s='. |
| `AML-CONSTRAINT-001` | constraints-mirror-facet | must | `PY-STRICT` | yes | **CANONICAL_PASS** |  |
| `AML-CONSTRAINT-001` | constraints-mirror-facet | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-CONSTRAINT-001` | constraints-mirror-facet | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-CONSTRAINT-001` | constraints-mirror-facet | must | `XSLT-PATCHED` | no | **FAIL** | Generated UANodeSet has duplicate NodeId 'ns=1;s=CAEXFile_SuperiorStandardVersion'. |
| `AML-CONSTRAINT-002` | constraints-mirror-facet | must | `PY-STRICT` | yes | **CANONICAL_PASS** |  |
| `AML-CONSTRAINT-002` | constraints-mirror-facet | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-CONSTRAINT-002` | constraints-mirror-facet | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-CONSTRAINT-002` | constraints-mirror-facet | must | `XSLT-PATCHED` | no | **FAIL** | Generated UANodeSet has duplicate NodeId 'ns=1;s=CAEXFile_SuperiorStandardVersion'. |
| `AML-CONSTRAINT-003` | constraints-mirror-facet | must | `PY-STRICT` | yes | **CANONICAL_PASS** |  |
| `AML-CONSTRAINT-003` | constraints-mirror-facet | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-CONSTRAINT-003` | constraints-mirror-facet | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-CONSTRAINT-003` | constraints-mirror-facet | must | `XSLT-PATCHED` | no | **FAIL** | Generated UANodeSet has duplicate NodeId 'ns=1;s=CAEXFile_SuperiorStandardVersion'. |
| `AML-CONSTRAINT-004` | constraints-mirror-facet | must | `PY-STRICT` | yes | **CANONICAL_PASS** |  |
| `AML-CONSTRAINT-004` | constraints-mirror-facet | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-CONSTRAINT-004` | constraints-mirror-facet | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-CONSTRAINT-004` | constraints-mirror-facet | must | `XSLT-PATCHED` | no | **FAIL** | Generated UANodeSet has duplicate NodeId 'ns=1;s=CAEXFile_SuperiorStandardVersion'. |
| `AML-MIRROR-001` | constraints-mirror-facet | must | `PY-STRICT` | yes | **CANONICAL_PASS** |  |
| `AML-MIRROR-001` | constraints-mirror-facet | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-MIRROR-001` | constraints-mirror-facet | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-MIRROR-001` | constraints-mirror-facet | must | `XSLT-PATCHED` | no | **UNSUPPORTED** | The semantic OPC UA reverse mapping 'automationml-python-semantic-v3' does not yet support HasAMLRoleReference target 'ns=3;s=Resource' outside RoleClassLibs. Use an app export ... |
| `AML-FACET-001` | constraints-mirror-facet | must | `PY-STRICT` | yes | **CANONICAL_PASS** |  |
| `AML-FACET-001` | constraints-mirror-facet | must | `XSLT-RAW` | yes | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-FACET-001` | constraints-mirror-facet | must | `XSLT-RUNNER` | no | **FAIL** | nodeset_semantics: invalid alias 'RequiredValue' 'ns=2;ns=2;i=2004' |
| `AML-FACET-001` | constraints-mirror-facet | must | `XSLT-PATCHED` | no | **FAIL** | no_roundtrip_metadata: forbidden shadow nodes AMLAttributeDataType, AMLUnit |
| `UA-ORIGIN-001` | ua-origin | must | `PY-STRICT` | yes | **PASS** |  |
| `UA-ORIGIN-001` | ua-origin | must | `XSLT-RAW` | yes | **FAIL** | canonical_aml: first difference at /FileName |
| `UA-ORIGIN-001` | ua-origin | must | `XSLT-RUNNER` | no | **FAIL** | canonical_aml: first difference at /FileName |
| `UA-ORIGIN-001` | ua-origin | must | `XSLT-PATCHED` | no | **PASS** |  |
| `UA-ORIGIN-002` | ua-origin | must | `PY-STRICT` | yes | **PASS** |  |
| `UA-ORIGIN-002` | ua-origin | must | `XSLT-RAW` | yes | **FAIL** | canonical_aml: first difference at /FileName |
| `UA-ORIGIN-002` | ua-origin | must | `XSLT-RUNNER` | no | **FAIL** | canonical_aml: first difference at /FileName |
| `UA-ORIGIN-002` | ua-origin | must | `XSLT-PATCHED` | no | **PASS** |  |
| `UA-ORIGIN-003` | ua-origin | must | `PY-STRICT` | yes | **PASS** |  |
| `UA-ORIGIN-003` | ua-origin | must | `XSLT-RAW` | yes | **FAIL** | canonical_aml: first difference at /FileName |
| `UA-ORIGIN-003` | ua-origin | must | `XSLT-RUNNER` | no | **FAIL** | canonical_aml: first difference at /FileName |
| `UA-ORIGIN-003` | ua-origin | must | `XSLT-PATCHED` | no | **PASS** |  |
| `UA-ORIGIN-004` | ua-origin | must | `PY-STRICT` | yes | **PASS** |  |
| `UA-ORIGIN-004` | ua-origin | must | `XSLT-RAW` | yes | **FAIL** | canonical_aml: first difference at /FileName |
| `UA-ORIGIN-004` | ua-origin | must | `XSLT-RUNNER` | no | **FAIL** | canonical_aml: first difference at /FileName |
| `UA-ORIGIN-004` | ua-origin | must | `XSLT-PATCHED` | no | **PASS** |  |
| `UA-ORIGIN-005` | ua-origin | must | `PY-STRICT` | yes | **PASS** |  |
| `UA-ORIGIN-005` | ua-origin | must | `XSLT-RAW` | yes | **FAIL** | canonical_aml: first difference at /FileName |
| `UA-ORIGIN-005` | ua-origin | must | `XSLT-RUNNER` | no | **FAIL** | canonical_aml: first difference at /FileName |
| `UA-ORIGIN-005` | ua-origin | must | `XSLT-PATCHED` | no | **PASS** |  |
| `UA-ORIGIN-006` | ua-origin | must | `PY-STRICT` | yes | **PASS** |  |
| `UA-ORIGIN-006` | ua-origin | must | `XSLT-RAW` | yes | **FAIL** | canonical_aml: first difference at /FileName |
| `UA-ORIGIN-006` | ua-origin | must | `XSLT-RUNNER` | no | **FAIL** | canonical_aml: first difference at /FileName |
| `UA-ORIGIN-006` | ua-origin | must | `XSLT-PATCHED` | no | **PASS** |  |
| `UA-ORIGIN-007` | ua-origin | must | `PY-STRICT` | yes | **PASS** |  |
| `UA-ORIGIN-007` | ua-origin | must | `XSLT-RAW` | yes | **FAIL** | canonical_aml: first difference at /FileName |
| `UA-ORIGIN-007` | ua-origin | must | `XSLT-RUNNER` | no | **FAIL** | canonical_aml: first difference at /FileName |
| `UA-ORIGIN-007` | ua-origin | must | `XSLT-PATCHED` | no | **PASS** |  |
| `UA-ORIGIN-008` | ua-origin | must | `PY-STRICT` | yes | **PASS** |  |
| `UA-ORIGIN-008` | ua-origin | must | `XSLT-RAW` | yes | **FAIL** | canonical_aml: first difference at /FileName |
| `UA-ORIGIN-008` | ua-origin | must | `XSLT-RUNNER` | no | **FAIL** | canonical_aml: first difference at /FileName |
| `UA-ORIGIN-008` | ua-origin | must | `XSLT-PATCHED` | no | **PASS** |  |
| `UA-ORIGIN-009` | ua-origin | must | `PY-STRICT` | yes | **PASS** |  |
| `UA-ORIGIN-009` | ua-origin | must | `XSLT-RAW` | yes | **FAIL** | canonical_aml: first difference at /FileName |
| `UA-ORIGIN-009` | ua-origin | must | `XSLT-RUNNER` | no | **FAIL** | canonical_aml: first difference at /FileName |
| `UA-ORIGIN-009` | ua-origin | must | `XSLT-PATCHED` | no | **PASS** |  |
| `UA-ORIGIN-010` | ua-origin | must | `PY-STRICT` | yes | **PASS** |  |
| `UA-ORIGIN-010` | ua-origin | must | `XSLT-RAW` | yes | **FAIL** | canonical_aml: first difference at /FileName |
| `UA-ORIGIN-010` | ua-origin | must | `XSLT-RUNNER` | no | **FAIL** | canonical_aml: first difference at /FileName |
| `UA-ORIGIN-010` | ua-origin | must | `XSLT-PATCHED` | no | **PASS** |  |
| `UA-ORIGIN-011` | ua-origin | must | `PY-STRICT` | yes | **PASS** |  |
| `UA-ORIGIN-011` | ua-origin | must | `XSLT-RAW` | yes | **FAIL** | canonical_aml: first difference at /FileName |
| `UA-ORIGIN-011` | ua-origin | must | `XSLT-RUNNER` | no | **FAIL** | canonical_aml: first difference at /FileName |
| `UA-ORIGIN-011` | ua-origin | must | `XSLT-PATCHED` | no | **PASS** |  |
| `UA-ORIGIN-012` | ua-origin | must | `PY-STRICT` | yes | **PASS** |  |
| `UA-ORIGIN-012` | ua-origin | must | `XSLT-RAW` | yes | **FAIL** | canonical_aml: first difference at /FileName |
| `UA-ORIGIN-012` | ua-origin | must | `XSLT-RUNNER` | no | **FAIL** | canonical_aml: first difference at /FileName |
| `UA-ORIGIN-012` | ua-origin | must | `XSLT-PATCHED` | no | **PASS** |  |
| `UA-ORIGIN-013` | ua-origin | must | `PY-STRICT` | yes | **PASS** |  |
| `UA-ORIGIN-013` | ua-origin | must | `XSLT-RAW` | yes | **FAIL** | canonical_aml: first difference at /FileName |
| `UA-ORIGIN-013` | ua-origin | must | `XSLT-RUNNER` | no | **FAIL** | canonical_aml: first difference at /FileName |
| `UA-ORIGIN-013` | ua-origin | must | `XSLT-PATCHED` | no | **PASS** |  |
| `UA-ORIGIN-014` | ua-origin | must | `PY-STRICT` | yes | **PASS** |  |
| `UA-ORIGIN-014` | ua-origin | must | `XSLT-RAW` | yes | **FAIL** | canonical_aml: first difference at /FileName |
| `UA-ORIGIN-014` | ua-origin | must | `XSLT-RUNNER` | no | **FAIL** | canonical_aml: first difference at /FileName |
| `UA-ORIGIN-014` | ua-origin | must | `XSLT-PATCHED` | no | **PASS** |  |
| `UA-ORIGIN-015` | ua-origin | must | `PY-STRICT` | yes | **PASS** |  |
| `UA-ORIGIN-015` | ua-origin | must | `XSLT-RAW` | yes | **FAIL** | canonical_aml: first difference at /FileName |
| `UA-ORIGIN-015` | ua-origin | must | `XSLT-RUNNER` | no | **FAIL** | canonical_aml: first difference at /FileName |
| `UA-ORIGIN-015` | ua-origin | must | `XSLT-PATCHED` | no | **PASS** |  |
| `UA-ORIGIN-016` | ua-origin | critical | `PY-STRICT` | yes | **EXPECTED_REJECTION** | The semantic OPC UA reverse mapping 'automationml-python-semantic-v3' does not yet support typed or non-CAEX InternalElement UAObject 'ns=1;s=authored:unknown-component'. Use an... |
| `UA-ORIGIN-016` | ua-origin | critical | `XSLT-RAW` | yes | **FAIL** | expected_rejection: mapper accepted input that must be rejected |
| `UA-ORIGIN-016` | ua-origin | critical | `XSLT-RUNNER` | no | **FAIL** | expected_rejection: mapper accepted input that must be rejected |
| `UA-ORIGIN-016` | ua-origin | critical | `XSLT-PATCHED` | no | **EXPECTED_REJECTION** | The semantic OPC UA reverse mapping 'automationml-python-semantic-v3' does not yet support typed or non-CAEX InternalElement UAObject 'ns=1;s=authored:unknown-component'. Use an... |
| `NEG-UA-001` | negative-security | critical | `PY-STRICT` | yes | **EXPECTED_REJECTION** | Generated UANodeSet has duplicate NodeId 'ns=1;s=aml:attribute:temperature:4d82e1918aa56596'. |
| `NEG-UA-001` | negative-security | critical | `XSLT-RAW` | yes | **FAIL** | expected_rejection: mapper accepted input that must be rejected |
| `NEG-UA-001` | negative-security | critical | `XSLT-RUNNER` | no | **FAIL** | expected_rejection: mapper accepted input that must be rejected |
| `NEG-UA-001` | negative-security | critical | `XSLT-PATCHED` | no | **EXPECTED_REJECTION** | Generated UANodeSet has duplicate NodeId 'ns=1;s=aml:attribute:temperature:4d82e1918aa56596'. |
| `NEG-UA-002` | negative-security | critical | `PY-STRICT` | yes | **EXPECTED_REJECTION** | Generated UANodeSet has invalid NodeId value 'not-a-node-id'. |
| `NEG-UA-002` | negative-security | critical | `XSLT-RAW` | yes | **FAIL** | expected_rejection: mapper accepted input that must be rejected |
| `NEG-UA-002` | negative-security | critical | `XSLT-RUNNER` | no | **FAIL** | expected_rejection: mapper accepted input that must be rejected |
| `NEG-UA-002` | negative-security | critical | `XSLT-PATCHED` | no | **EXPECTED_REJECTION** | Generated UANodeSet has invalid NodeId value 'not-a-node-id'. |
| `NEG-UA-003` | negative-security | critical | `PY-STRICT` | yes | **EXPECTED_REJECTION** | UANodeSet reference from UAObject 'ns=1;s=aml:object:Motor:54496f6c1a21fbee' points to missing node 'ns=1;s=authored:missing-target'. |
| `NEG-UA-003` | negative-security | critical | `XSLT-RAW` | yes | **FAIL** | expected_rejection: mapper accepted input that must be rejected |
| `NEG-UA-003` | negative-security | critical | `XSLT-RUNNER` | no | **FAIL** | expected_rejection: mapper accepted input that must be rejected |
| `NEG-UA-003` | negative-security | critical | `XSLT-PATCHED` | no | **EXPECTED_REJECTION** | UANodeSet reference from UAObject 'ns=1;s=aml:object:Motor:54496f6c1a21fbee' points to missing node 'ns=1;s=authored:missing-target'. |
| `NEG-UA-004` | negative-security | critical | `PY-STRICT` | yes | **EXPECTED_REJECTION** | ExternalInterface UAObject 'ns=1;s=aml:object:PortA:a4be6dafd95df876' has more than one TypeDefinition. |
| `NEG-UA-004` | negative-security | critical | `XSLT-RAW` | yes | **FAIL** | expected_rejection: mapper accepted input that must be rejected |
| `NEG-UA-004` | negative-security | critical | `XSLT-RUNNER` | no | **FAIL** | expected_rejection: mapper accepted input that must be rejected |
| `NEG-UA-004` | negative-security | critical | `XSLT-PATCHED` | no | **EXPECTED_REJECTION** | ExternalInterface UAObject 'ns=1;s=aml:object:PortA:a4be6dafd95df876' has more than one TypeDefinition. |
| `NEG-UA-005` | negative-security | critical | `PY-STRICT` | yes | **EXPECTED_REJECTION** | Class ancestry contains a cycle at 'ns=1;s=aml:interface-class:Port%231:1d20475a3bb09d25'. |
| `NEG-UA-005` | negative-security | critical | `XSLT-RAW` | yes | **FAIL** | expected_rejection: mapper accepted input that must be rejected |
| `NEG-UA-005` | negative-security | critical | `XSLT-RUNNER` | no | **FAIL** | expected_rejection: mapper accepted input that must be rejected |
| `NEG-UA-005` | negative-security | critical | `XSLT-PATCHED` | no | **EXPECTED_REJECTION** | Class ancestry contains a cycle at 'ns=1;s=aml:interface-class:Port%231:1d20475a3bb09d25'. |
| `NEG-UA-006` | negative-security | critical | `PY-STRICT` | yes | **EXPECTED_REJECTION** | Component graph node 'ns=1;s=aml:object:PortA:a4be6dafd95df876' has multiple owners: ns=1;s=aml:object:Device:a2b69bb0c81169d2, ns=1;s=aml:object:Motor:54496f6c1a21fbee |
| `NEG-UA-006` | negative-security | critical | `XSLT-RAW` | yes | **FAIL** | expected_rejection: mapper accepted input that must be rejected |
| `NEG-UA-006` | negative-security | critical | `XSLT-RUNNER` | no | **FAIL** | expected_rejection: mapper accepted input that must be rejected |
| `NEG-UA-006` | negative-security | critical | `XSLT-PATCHED` | no | **EXPECTED_REJECTION** | Component graph node 'ns=1;s=aml:object:PortA:a4be6dafd95df876' has multiple owners: ns=1;s=aml:object:Device:a2b69bb0c81169d2, ns=1;s=aml:object:Motor:54496f6c1a21fbee |
| `NEG-UA-007` | negative-security | critical | `PY-STRICT` | yes | **EXPECTED_REJECTION** | Generated UANodeSet failed its XML Schema: <string>:188:0:ERROR:SCHEMASV:SCHEMAV_ELEMENT_CONTENT: Element '{http://opcfoundation.org/UA/2011/03/UANodeSet.xsd}Value': This elemen... |
| `NEG-UA-007` | negative-security | critical | `XSLT-RAW` | yes | **FAIL** | expected_rejection: mapper accepted input that must be rejected |
| `NEG-UA-007` | negative-security | critical | `XSLT-RUNNER` | no | **FAIL** | expected_rejection: mapper accepted input that must be rejected |
| `NEG-UA-007` | negative-security | critical | `XSLT-PATCHED` | no | **EXPECTED_REJECTION** | Generated UANodeSet failed its XML Schema: <string>:188:0:ERROR:SCHEMASV:SCHEMAV_ELEMENT_CONTENT: Element '{http://opcfoundation.org/UA/2011/03/UANodeSet.xsd}Value': This elemen... |
| `NEG-UA-008` | negative-security | critical | `PY-STRICT` | yes | **EXPECTED_REJECTION** | Attribute metadata 'DefaultValue' must use the parent Variable DataType. |
| `NEG-UA-008` | negative-security | critical | `XSLT-RAW` | yes | **FAIL** | expected_rejection: mapper accepted input that must be rejected |
| `NEG-UA-008` | negative-security | critical | `XSLT-RUNNER` | no | **FAIL** | expected_rejection: mapper accepted input that must be rejected |
| `NEG-UA-008` | negative-security | critical | `XSLT-PATCHED` | no | **EXPECTED_REJECTION** | Attribute metadata 'DefaultValue' must use the parent Variable DataType. |
| `NEG-AML-009` | negative-security | critical | `PY-STRICT` | yes | **EXPECTED_REJECTION** | Python OPC UA mapping failed: SupportedRoleClass on an InternalElement is ambiguous in the implicit role profile; only RoleRequirements is supported. |
| `NEG-AML-009` | negative-security | critical | `XSLT-RAW` | yes | **FAIL** | expected_rejection: mapper accepted input that must be rejected |
| `NEG-AML-009` | negative-security | critical | `XSLT-RUNNER` | no | **FAIL** | expected_rejection: mapper accepted input that must be rejected |
| `NEG-AML-009` | negative-security | critical | `XSLT-PATCHED` | no | **FAIL** | expected_rejection: mapper accepted input that must be rejected |
| `NEG-AML-010` | negative-security | critical | `PY-STRICT` | yes | **EXPECTED_REJECTION** | Python OPC UA mapping failed: Parallel AML InternalLinks between the same directed ExternalInterfaces cannot be represented by one native edge. |
| `NEG-AML-010` | negative-security | critical | `XSLT-RAW` | yes | **FAIL** | expected_rejection: mapper accepted input that must be rejected |
| `NEG-AML-010` | negative-security | critical | `XSLT-RUNNER` | no | **FAIL** | expected_rejection: mapper accepted input that must be rejected |
| `NEG-AML-010` | negative-security | critical | `XSLT-PATCHED` | no | **FAIL** | expected_rejection: mapper accepted input that must be rejected |
| `NEG-UA-011` | negative-security | critical | `PY-STRICT` | yes | **EXPECTED_REJECTION** | The semantic OPC UA reverse mapping 'automationml-python-semantic-v3' does not yet support OPC UA DataType 'i=22' on Attribute 'temperature'. Use an app export with embedded AML... |
| `NEG-UA-011` | negative-security | critical | `XSLT-RAW` | yes | **FAIL** | expected_rejection: mapper accepted input that must be rejected |
| `NEG-UA-011` | negative-security | critical | `XSLT-RUNNER` | no | **FAIL** | expected_rejection: mapper accepted input that must be rejected |
| `NEG-UA-011` | negative-security | critical | `XSLT-PATCHED` | no | **EXPECTED_REJECTION** | The semantic OPC UA reverse mapping 'automationml-python-semantic-v3' does not yet support OPC UA DataType 'i=22' on Attribute 'temperature'. Use an app export with embedded AML... |
| `NEG-SEC-012` | negative-security | critical | `PY-STRICT` | yes | **EXPECTED_REJECTION** | DTD and entity declarations are not accepted. |
| `NEG-SEC-012` | negative-security | critical | `XSLT-RAW` | yes | **FAIL** | upstream forward XSLT failed: SXXP0003: I/O error reported by XML parser processing null Caused by: \this-resource-must-never-be-read (Das System kann die angegebene Datei nicht... |
| `NEG-SEC-012` | negative-security | critical | `XSLT-RUNNER` | no | **FAIL** | upstream forward XSLT failed: SXXP0003: I/O error reported by XML parser processing null Caused by: \this-resource-must-never-be-read (Das System kann die angegebene Datei nicht... |
| `NEG-SEC-012` | negative-security | critical | `XSLT-PATCHED` | no | **EXPECTED_REJECTION** | DTD and entity declarations are not accepted. |

`INVALID_FIXTURE` and observation rows are visible but excluded from scores. `UNSUPPORTED` is not a pass.
