from __future__ import annotations

import asyncio
from pathlib import Path

from asyncua import Server, ua
from lxml import etree

from automationml import CAEXFile
from automationml.opcua import UA_NODESET_NS, nodeset_to_document


REPO = Path(__file__).parents[1]
FIXTURES = REPO / "tests" / "opcua-comparison" / "fixtures"
AML_BASE_TYPES = (
    REPO
    / "tests"
    / "vendor"
    / "aml-ua-xslt-e38653c"
    / "UnitTests"
    / "Opc.Ua.AMLBaseTypes.NodeSet2_V2.xml"
)
AML_MODEL_URI = "http://opcfoundation.org/UA/AML/"
NS = {"ua": UA_NODESET_NS}


async def _server_with_model(xml_path: Path, model_uri: str) -> tuple[Server, int]:
    server = Server()
    await server.init()
    await server.import_xml(path=str(AML_BASE_TYPES))
    await server.import_xml(path=str(xml_path))
    return server, await server.get_namespace_index(model_uri)


def _source_node_id(xml: str, display_name: str) -> str:
    root = etree.fromstring(xml.encode("utf-8"))
    nodes = [
        node
        for node in root.xpath("./ua:*[@NodeId]", namespaces=NS)
        if node.findtext(f"{{{UA_NODESET_NS}}}DisplayName") == display_name
    ]
    assert len(nodes) == 1
    return nodes[0].get("NodeId", "")


def _server_node(server: Server, source_node_id: str, model_index: int):
    remapped = source_node_id.replace("ns=1;", f"ns={model_index};", 1)
    return server.get_node(ua.NodeId.from_string(remapped))


def test_asyncua_imports_minimal_model_and_browses_file_root(tmp_path: Path):
    async def run() -> None:
        document = CAEXFile.from_aml_xml((FIXTURES / "minimal-caex3.aml").read_bytes())
        xml = document.to_opcua_nodeset_xml(
            include_roundtrip=False,
            publication_date="2026-08-17",
        )
        path = tmp_path / "minimal.NodeSet2.xml"
        path.write_text(xml, encoding="utf-8")
        model_uri = "http://opcfoundation.org/UA/AML/minimal-caex3.aml"
        server, model_index = await _server_with_model(path, model_uri)
        root = _server_node(server, _source_node_id(xml, "minimal-caex3.aml"), model_index)
        assert (await root.read_display_name()).Text == "minimal-caex3.aml"
        properties = await root.get_properties()
        names = {str((await item.read_browse_name()).Name) for item in properties}
        assert {"FileName", "SchemaVersion"}.issubset(names)

    asyncio.run(run())


def test_asyncua_reads_typed_attribute_and_class_model(tmp_path: Path):
    async def run() -> None:
        document = CAEXFile.from_aml_xml((FIXTURES / "focused-profile.aml").read_bytes())
        xml = document.to_opcua_nodeset_xml(
            include_roundtrip=False,
            publication_date="2026-08-17",
        )
        path = tmp_path / "typed.NodeSet2.xml"
        path.write_text(xml, encoding="utf-8")
        model_uri = "http://opcfoundation.org/UA/AML/focused-profile.aml"
        server, model_index = await _server_with_model(path, model_uri)
        attribute = _server_node(
            server,
            _source_node_id(xml, "signedInt"),
            model_index,
        )
        speed_type = _server_node(
            server,
            _source_node_id(xml, "Speed"),
            model_index,
        )
        assert await attribute.read_value() == -2147483648
        assert await attribute.read_data_type() == ua.NodeId(ua.ObjectIds.Int32)
        assert (await speed_type.read_browse_name()).Name == "Speed"

    asyncio.run(run())


def test_asyncua_browses_native_role_and_directed_link_references(tmp_path: Path):
    async def run() -> None:
        xml = (FIXTURES / "ua-origin-base.xml").read_text(encoding="utf-8")
        path = tmp_path / "role-link.NodeSet2.xml"
        path.write_text(xml, encoding="utf-8")
        model_uri = "http://opcfoundation.org/UA/AML/ua-origin.aml"
        server, model_index = await _server_with_model(path, model_uri)
        companion_index = await server.get_namespace_index(AML_MODEL_URI)
        motor = _server_node(server, _source_node_id(xml, "Motor"), model_index)
        port_a = _server_node(server, _source_node_id(xml, "PortA"), model_index)
        role_refs = await motor.get_references(
            refs=ua.NodeId(4001, companion_index),
            direction=ua.BrowseDirection.Forward,
            includesubtypes=False,
        )
        link_refs = await port_a.get_references(
            refs=ua.NodeId(4002, companion_index),
            direction=ua.BrowseDirection.Forward,
            includesubtypes=False,
        )
        assert [item.BrowseName.Name for item in role_refs] == ["Drive"]
        assert [item.BrowseName.Name for item in link_refs] == ["PortB"]

    asyncio.run(run())


def test_asyncua_export_reimports_to_stable_aml_projection(tmp_path: Path):
    async def run() -> None:
        source = FIXTURES / "ua-origin-base.xml"
        model_uri = "http://opcfoundation.org/UA/AML/ua-origin.aml"
        server, model_index = await _server_with_model(source, model_uri)
        exported = tmp_path / "asyncua-export.NodeSet2.xml"
        await server.export_xml_by_ns(
            str(exported),
            namespaces=[model_index],
            export_values=True,
        )
        recovered = nodeset_to_document(
            exported.read_bytes(),
            prefer_embedded_source=False,
        )
        expected = CAEXFile.from_aml_xml(
            (FIXTURES / "ua-origin-expected.aml").read_bytes()
        )
        assert recovered.to_aml_dict() == expected.to_aml_dict()

    asyncio.run(run())
