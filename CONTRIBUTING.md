# Contributing to AutomationML Python

Thank you for helping improve the JSON-first Python SDK for AutomationML.

## Before opening an issue

- Search existing issues and discussions for related work.
- Reduce bugs to the smallest AML JSON, AML XML, or Python example that still
  demonstrates the behavior.
- Remove confidential engineering data from example documents.
- Use a GitHub Security Advisory instead of a public issue for vulnerabilities.

## Development setup

Create and activate a Python 3.11 or newer virtual environment, then install the
SDK and development dependencies:

```bash
python -m venv .venv
python -m pip install -e ".[dev,xml]"
```

Run the complete test suite before submitting a pull request:

```bash
python -m pytest
```

To verify distribution metadata and package contents:

```bash
python -m pip install build twine
python -m build
python -m twine check dist/*
```

## Making changes

- Keep the Pydantic model and AML JSON representation canonical to CAEX 3.0.
- Keep XML concerns in the XML adapter unless the model contract requires a
  shared change.
- Do not duplicate semantic validation logic in consumers of the SDK.
- Add focused tests for behavioral changes and regressions.
- Add or update validation-suite examples when a rule benefits from a public,
  executable example.
- Update `CHANGELOG.md` for user-visible changes.

## Pull requests

Pull requests should explain the AutomationML use case, describe public API or
serialization changes, and list the verification performed. Small, focused
changes are easier to review and release safely.

By contributing, you agree that your contribution is licensed under the MIT
License used by this repository.
