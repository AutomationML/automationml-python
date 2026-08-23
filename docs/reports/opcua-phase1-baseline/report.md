# AutomationML / OPC UA mapper Phase 1 baseline

Baseline commit: `e38653c1bc58ffc658595093e0a2d163a7ecebf7`  
Generated: `2026-08-17T12:28:21.406696+00:00`  
Platform: `Windows-10-10.0.26200-SP0`

## Score

| System | Passed | Scored | Percent | Critical |
| --- | ---: | ---: | ---: | ---: |
| `PY-STRICT` | 25 | 25 | 100.00% | 12/12 |
| `XSLT-RAW` | 1 | 25 | 4.00% | 1/12 |
| `XSLT-RUNNER` | 0 | 0 | 0.00% | 0/0 |
| `XSLT-PATCHED` | 0 | 0 | 0.00% | 0/0 |

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
| `UP-OPC-002` | upstream-opc-observation | observation | `PY-STRICT` | no | **UNSUPPORTED** | The semantic OPC UA reverse mapping 'automationml-python-semantic-v3' does not yet support a NodeSet without exactly one UAObject of CAEXFileType. Use an app export with embedde... |
| `UP-OPC-002` | upstream-opc-observation | observation | `XSLT-RAW` | no | **PASS** |  |
| `UP-OPC-002` | upstream-opc-observation | observation | `XSLT-RUNNER` | no | **PASS** |  |
| `UP-OPC-002` | upstream-opc-observation | observation | `XSLT-PATCHED` | no | **UNSUPPORTED** | The semantic OPC UA reverse mapping 'automationml-python-semantic-v3' does not yet support a NodeSet without exactly one UAObject of CAEXFileType. Use an app export with embedde... |
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
| `UP-OPC-006` | upstream-opc-observation | observation | `PY-STRICT` | no | **UNSUPPORTED** | The semantic OPC UA reverse mapping 'automationml-python-semantic-v3' does not yet support a NodeSet without exactly one UAObject of CAEXFileType. Use an app export with embedde... |
| `UP-OPC-006` | upstream-opc-observation | observation | `XSLT-RAW` | no | **PASS** |  |
| `UP-OPC-006` | upstream-opc-observation | observation | `XSLT-RUNNER` | no | **PASS** |  |
| `UP-OPC-006` | upstream-opc-observation | observation | `XSLT-PATCHED` | no | **UNSUPPORTED** | The semantic OPC UA reverse mapping 'automationml-python-semantic-v3' does not yet support a NodeSet without exactly one UAObject of CAEXFileType. Use an app export with embedde... |
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
| `REG-DETERMINISM-001` | known-defect | critical | `XSLT-RAW` | yes | **FAIL** | expected_graph: required PublicationDate '2026-08-17T00:00:00Z' is absent; got ['2026-08-17T02:28:20Z'] |
| `REG-DETERMINISM-001` | known-defect | critical | `XSLT-RUNNER` | no | **PASS** |  |
| `REG-DETERMINISM-001` | known-defect | critical | `XSLT-PATCHED` | no | **PASS** |  |
| `REG-DTYPE-001` | known-defect | critical | `PY-STRICT` | yes | **PASS** |  |
| `REG-DTYPE-001` | known-defect | critical | `XSLT-RAW` | yes | **FAIL** | expected_graph: 'identifier' @DataType is 'id', expected 'String' |
| `REG-DTYPE-001` | known-defect | critical | `XSLT-RUNNER` | no | **FAIL** | expected_graph: 'identifier' @DataType is 'id', expected 'String' |
| `REG-DTYPE-001` | known-defect | critical | `XSLT-PATCHED` | no | **FAIL** | no_roundtrip_metadata: forbidden shadow nodes AMLAttributeDataType |
| `REG-DTYPE-002` | known-defect | critical | `PY-STRICT` | yes | **PASS** |  |
| `REG-DTYPE-002` | known-defect | critical | `XSLT-RAW` | yes | **FAIL** | expected_graph: 'timestamp' @DataType is 'datetime', expected 'DateTime' |
| `REG-DTYPE-002` | known-defect | critical | `XSLT-RUNNER` | no | **FAIL** | expected_graph: 'timestamp' @DataType is 'datetime', expected 'DateTime' |
| `REG-DTYPE-002` | known-defect | critical | `XSLT-PATCHED` | no | **FAIL** | no_roundtrip_metadata: forbidden shadow nodes AMLAttributeDataType |
| `REG-DTYPE-003` | known-defect | critical | `PY-STRICT` | yes | **PASS** |  |
| `REG-DTYPE-003` | known-defect | critical | `XSLT-RAW` | yes | **FAIL** | expected_graph: 'token' @DataType is 'Guid', expected 'String' |
| `REG-DTYPE-003` | known-defect | critical | `XSLT-RUNNER` | no | **FAIL** | expected_graph: 'token' @DataType is 'Guid', expected 'String' |
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
| `REG-ATTR-002` | known-defect | critical | `XSLT-RAW` | yes | **FAIL** | expected_graph: 'state' documentation is None, expected 'Current operating state' |
| `REG-ATTR-002` | known-defect | critical | `XSLT-RUNNER` | no | **FAIL** | expected_graph: 'state' documentation is None, expected 'Current operating state' |
| `REG-ATTR-002` | known-defect | critical | `XSLT-PATCHED` | no | **FAIL** | no_roundtrip_metadata: forbidden shadow nodes AMLAttributeDataType, AMLDefaultValue |

`INVALID_FIXTURE` and observation rows are visible but excluded from scores. `UNSUPPORTED` is not a pass.
