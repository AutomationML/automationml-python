# Evaluation harness

`opcua_evaluation.py` is the manifest-driven evidence harness behind the
AutomationML / OPC UA mapper comparison: independent oracles, case scoring,
outcome classification, and the JSON / JUnit / Markdown reports under
`docs/reports/`.

It lives here rather than in `src/automationml/` on purpose. It is development
and evidence tooling, not SDK API: no library code path imports it, and it is
not part of the distributed wheel. Keeping it out of the package means SDK
users do not install the harness that judges the SDK.

It stays in the source distribution so the published evidence can be
reproduced from a release tarball.

## Use

The test suite reaches it through the repository-root `conftest.py`, which puts
this directory on `sys.path`. The scripts in `tools/` bootstrap it explicitly,
so they run unchanged from the repository root:

```bash
python tools/compare_opcua_mappers.py \
  --manifest tests/opcua-comparison/release-manifest.json \
  --output-dir build/opcua-release

python tools/benchmark_opcua_scale.py --repeats 1 --output-dir build/opcua-scale
```

Running it needs the evaluation dependencies:

```bash
python -m pip install -e ".[xml,opcua-evaluation]"
```
