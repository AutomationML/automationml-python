import sys

import pytest

import automationml
from automationml import (
    AMLParseError,
    AutomationMLError,
    CAEXFile,
    LegacyConversionError,
    MissingDependencyError,
    caex_file,
)


def test_source_document_records_the_sdk_version():
    document = caex_file("plant.aml")

    assert document.source_document_information[0].origin_version == (
        automationml.__version__
    )


@pytest.mark.parametrize(
    "data",
    [
        b"<CAEXFile",
        b"<Plant/>",
        b'<CAEXFile SchemaVersion="9.0" FileName="plant.aml"/>',
    ],
    ids=["malformed", "wrong-root", "unsupported-version"],
)
def test_unreadable_aml_xml_raises_parse_error(data):
    with pytest.raises(AMLParseError) as excinfo:
        CAEXFile.from_aml_xml(data)

    # Earlier versions raised LegacyConversionError; existing handlers still work.
    assert isinstance(excinfo.value, LegacyConversionError)
    assert isinstance(excinfo.value, AutomationMLError)


@pytest.mark.parametrize(
    ("dependency", "extra", "modules", "convert"),
    [
        (
            "lxml",
            "opcua",
            (
                "automationml.opcua",
                "automationml.opcua_nodeset",
                "automationml.opcua_python",
            ),
            lambda document: document.to_opcua_nodeset_xml(),
        ),
        (
            "rdflib",
            "rdf",
            ("automationml.rdf", "automationml.rdf_mapping"),
            lambda document: document.to_ttl(),
        ),
    ],
    ids=["opcua", "rdf"],
)
def test_missing_optional_dependency_names_the_extra(
    monkeypatch, dependency, extra, modules, convert
):
    monkeypatch.setitem(sys.modules, dependency, None)
    for module in modules:
        monkeypatch.delitem(sys.modules, module, raising=False)

    expected = rf"automationml\[{extra}\]"
    with pytest.raises(MissingDependencyError, match=expected) as excinfo:
        convert(caex_file("plant.aml"))

    assert isinstance(excinfo.value, ModuleNotFoundError)
    assert excinfo.value.name == dependency
