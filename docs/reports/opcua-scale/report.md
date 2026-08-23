# OPC UA scale report

Generated: 2026-08-17

Peak memory is process resident-set size sampled every 10 ms and includes native mapper/runtime allocations.

| Case | Engine | Status | Nodes | References | Cold ms | Warm median ms | Reverse ms | Peak RSS MiB | Bytes | Deterministic | Roundtrip |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| flat-1k-5k | PY-STRICT | pass | 1000 | 5939 | 279.441 | 322.412 | 332.929 | 76.48 | 929678 | yes | yes |
| flat-10k-50k | PY-STRICT | pass | 10000 | 59939 | 4101.152 | 3891.172 | 5030.844 | 266.98 | 9340182 | yes | yes |
| depth-64 | PY-STRICT | pass | 133 | 398 | 23.881 | 18.471 | 23.433 | 79.12 | 79782 | yes | yes |
| flat-1k-5k | XSLT-RAW | measured | 999 | 4947 | 583.698 | 457.298 | 56.034 | 215.84 | 878837 | yes | no |
| flat-10k-50k | XSLT-RAW | measured | 9999 | 49947 | 4541.909 | 4743.801 | 707.003 | 407.59 | 8744841 | no | no |
| depth-64 | XSLT-RAW | measured | 133 | 268 | 70.689 | 79.055 | 7.615 | 394.97 | 73501 | yes | no |
