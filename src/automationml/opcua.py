"""AutomationML and OPC UA UANodeSet conversion.

The forward path is a typed Python mapper.  The pinned, patched
AutomationML/OPC Foundation XSLT is retained as a development comparison
engine while the Python coverage is expanded and evaluated.
"""

from __future__ import annotations

import base64
import binascii
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from functools import lru_cache
from hashlib import sha256
from hmac import compare_digest
from pathlib import Path
from typing import Literal

from lxml import etree
from pydantic import BaseModel, ConfigDict, JsonValue, computed_field

from .models import CAEXFile
from .opcua_mapping import (
    DEFAULT_MAPPING_PROFILE,
    UnsupportedDataTypeError,
    canonical_internal_link_identity,
    normalize_partner_reference,
)
from .opcua_nodeset import UANodeSet


UA_NODESET_NS = "http://opcfoundation.org/UA/2011/03/UANodeSet.xsd"
ROUNDTRIP_NS = "urn:automationml:opcua:nodeset-roundtrip:1"
REVERSE_MAPPING_VERSION = "automationml-python-semantic-v3"

IRDI_DICTIONARY_URI = "http://opcfoundation.org/UA/Dictionary/IRDI"
URI_DICTIONARY_URI = "http://opcfoundation.org/UA/Dictionary/URI"
AML_MODEL_URI = "http://opcfoundation.org/UA/AML/"

_BUILTIN_UA_ALIASES = {
    "Boolean": "i=1",
    "SByte": "i=2",
    "Byte": "i=3",
    "Int16": "i=4",
    "UInt16": "i=5",
    "Int32": "i=6",
    "UInt32": "i=7",
    "Int64": "i=8",
    "UInt64": "i=9",
    "Float": "i=10",
    "Double": "i=11",
    "String": "i=12",
    "DateTime": "i=13",
    "ByteString": "i=15",
    "Organizes": "i=35",
    "HasTypeDefinition": "i=40",
    "HasSubtype": "i=45",
    "HasProperty": "i=46",
    "HasComponent": "i=47",
    "BaseObjectType": "i=58",
    "FolderType": "i=61",
    "PropertyType": "i=68",
    "BaseDataVariableType": "i=63",
    "HasDictionaryEntry": "i=17597",
}
_AML_COMPANION_ALIAS_IDS = {
    "CAEXObjectType": 1001,
    "CAEXFileType": 1005,
    "AMLConstraintVariableType": 2000,
    "NominalScaledConstraint": 2001,
    "OrdinalScaledConstraint": 2002,
    "UnknownConstraint": 2003,
    "AMLBaseVariableType": 3001,
    "HasAMLRoleReference": 4001,
    "HasAMLInternalLink": 4002,
}

_NS = {"ua": UA_NODESET_NS, "amlrt": ROUNDTRIP_NS}
_DANGEROUS_XML = re.compile(br"<!\s*(?:DOCTYPE|ENTITY)\b", re.IGNORECASE)
_NODE_ID = re.compile(
    r"^(?:ns=\d+;)?(?:i=\d+|s=.+|g=[0-9A-Fa-f-]{36}|b=[A-Za-z0-9+/=]+)$"
)


class OPCUAConversionError(ValueError):
    """Raised when AutomationML/OPC UA conversion cannot produce valid XML."""


class OPCUARoundTripUnavailable(OPCUAConversionError):
    """Raised when neither source recovery nor semantic reverse mapping can run."""


class OPCUAReverseMappingUnsupported(OPCUARoundTripUnavailable):
    """Raised when a NodeSet uses features outside the semantic profile."""


class OPCUARoundTripMismatch(OPCUAConversionError):
    """Raised when both mappings run but do not preserve AML semantics."""


class RoundTripDifference(BaseModel):
    """One stable, JSON-Pointer-addressed semantic difference."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str
    kind: Literal["added", "removed", "changed"]
    source_value: JsonValue | None = None
    recovered_value: JsonValue | None = None


class _RoundTripResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    differences: tuple[RoundTripDifference, ...]
    mapping_profile: str

    @computed_field
    @property
    def semantically_equivalent(self) -> bool:
        """Whether the AutomationML semantic projections are equal."""

        return not self.differences

    def _raise_mismatch(self) -> None:
        if self.semantically_equivalent:
            return
        paths = ", ".join(item.path for item in self.differences[:3])
        suffix = "" if len(self.differences) <= 3 else ", ..."
        raise OPCUARoundTripMismatch(
            "The OPC UA round trip completed but changed AutomationML "
            f"semantics at {paths}{suffix}."
        )


class OPCUARoundTripResult(_RoundTripResult):
    """Validated evidence from an AML -> NodeSet -> AML semantic round trip."""

    source_document: CAEXFile
    nodeset: UANodeSet
    nodeset_xml: str
    recovered_document: CAEXFile

    def assert_equivalent(self) -> CAEXFile:
        """Return the recovered document or fail with a roundtrip-specific error."""

        self._raise_mismatch()
        return self.recovered_document


class UANodeSetRoundTripResult(_RoundTripResult):
    """Evidence from an OPC UA -> AML -> OPC UA semantic round trip."""

    source_nodeset: UANodeSet
    document: CAEXFile
    regenerated_nodeset: UANodeSet
    regenerated_nodeset_xml: str
    verification_document: CAEXFile

    def assert_equivalent(self) -> UANodeSet:
        """Return the regenerated graph when its AML projection is stable."""

        self._raise_mismatch()
        return self.regenerated_nodeset


def document_to_nodeset(
    document: CAEXFile,
    *,
    pretty: bool = True,
    include_roundtrip: bool = False,
    publication_date: date | datetime | str | None = None,
) -> str:
    """Convert a CAEX document to an OPC UA UANodeSet XML document."""

    aml_xml = document.to_aml_xml(
        pretty=False,
        include_default_change_mode=True,
    )
    aml_bytes = aml_xml.encode("utf-8")
    publication_date_text = _publication_date_text(publication_date)
    root = _map_document_to_nodeset_python(
        document,
        publication_date=publication_date_text,
    )
    return _finish_forward_mapping(
        root,
        aml_bytes=aml_bytes,
        pretty=pretty,
        include_roundtrip=include_roundtrip,
    )


def document_to_nodeset_model(
    document: CAEXFile,
    *,
    publication_date: date | datetime | str | None = None,
) -> UANodeSet:
    """Map a CAEX document directly to the validated Python NodeSet graph."""

    publication_date_text = _publication_date_text(publication_date)
    from pydantic import ValidationError

    from .opcua_python import PythonMappingUnsupported, build_python_nodeset

    try:
        return build_python_nodeset(
            document,
            publication_date=publication_date_text,
        )
    except (PythonMappingUnsupported, ValidationError, ValueError) as exc:
        raise OPCUAConversionError(f"Python OPC UA mapping failed: {exc}") from exc


def compare_aml_semantics(
    source: CAEXFile,
    recovered: CAEXFile,
) -> tuple[RoundTripDifference, ...]:
    """Compare canonical CAEX semantics and return structured differences."""

    return _compare_json_values(
        source.to_aml_dict(include_change_mode=True),
        recovered.to_aml_dict(include_change_mode=True),
    )


def round_trip_document(
    document: CAEXFile,
    *,
    pretty: bool = True,
    publication_date: date | datetime | str | None = None,
) -> OPCUARoundTripResult:
    """Exercise both semantic mappings without embedding the source AML.

    The result retains both validated CAEX models and the intervening NodeSet,
    making the round trip inspectable instead of reducing it to a Boolean.
    ``assert_equivalent()`` is convenient for scripts and tests which require a
    lossless result.
    """

    nodeset_xml = document_to_nodeset(
        document,
        pretty=pretty,
        include_roundtrip=False,
        publication_date=publication_date,
    )
    recovered = nodeset_to_document(
        nodeset_xml,
        prefer_embedded_source=False,
    )
    return OPCUARoundTripResult(
        differences=compare_aml_semantics(document, recovered),
        mapping_profile=(
            f"{DEFAULT_MAPPING_PROFILE.name}-v{DEFAULT_MAPPING_PROFILE.version}"
        ),
        source_document=document,
        nodeset=UANodeSet.from_xml(nodeset_xml),
        nodeset_xml=nodeset_xml,
        recovered_document=recovered,
    )


def round_trip_nodeset(
    nodeset: UANodeSet | str | bytes,
    *,
    pretty: bool = True,
    publication_date: date | datetime | str | None = None,
) -> UANodeSetRoundTripResult:
    """Exercise an OPC-UA-origin semantic round trip without source recovery.

    OPC UA NodeIds, aliases, namespace prefixes, and XML order may be
    canonicalized. Equivalence is therefore evaluated on the strict
    AutomationML semantic projection: UA -> AML -> UA -> AML must be stable.
    """

    try:
        source_nodeset = (
            nodeset if isinstance(nodeset, UANodeSet) else UANodeSet.from_xml(nodeset)
        )
    except ValueError as exc:
        raise OPCUAConversionError(
            f"OPC UA graph could not be loaded into the typed NodeSet model: {exc}"
        ) from exc
    document = nodeset_to_document(
        source_nodeset,
        prefer_embedded_source=False,
    )
    regenerated_xml = document_to_nodeset(
        document,
        pretty=pretty,
        include_roundtrip=False,
        publication_date=publication_date,
    )
    regenerated_nodeset = UANodeSet.from_xml(regenerated_xml)
    verification_document = nodeset_to_document(
        regenerated_nodeset,
        prefer_embedded_source=False,
    )
    return UANodeSetRoundTripResult(
        differences=compare_aml_semantics(document, verification_document),
        mapping_profile=(
            f"{DEFAULT_MAPPING_PROFILE.name}-v{DEFAULT_MAPPING_PROFILE.version}"
        ),
        source_nodeset=source_nodeset,
        document=document,
        regenerated_nodeset=regenerated_nodeset,
        regenerated_nodeset_xml=regenerated_xml,
        verification_document=verification_document,
    )


def _compare_json_values(
    source: JsonValue,
    recovered: JsonValue,
    path: str = "",
) -> tuple[RoundTripDifference, ...]:
    from .changes import diff_payloads

    return tuple(
        RoundTripDifference(
            path=(f"{path}{operation.path}" or "/"),
            kind={"add": "added", "remove": "removed", "replace": "changed"}[
                operation.op
            ],
            source_value=operation.before,
            recovered_value=operation.after,
        )
        for operation in diff_payloads(source, recovered)
    )


def _json_pointer_segment(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def aml_xml_to_nodeset(
    aml_xml: str | bytes,
    *,
    pretty: bool = True,
    include_roundtrip: bool = False,
    publication_date: date | datetime | str | None = None,
) -> str:
    """Convert CAEX XML to an OPC UA UANodeSet with the Python mapper."""

    aml_bytes = _xml_bytes(aml_xml)
    _reject_unsafe_xml(aml_bytes)
    _assert_root(aml_bytes, "CAEXFile", "AutomationML")
    # The public SDK accepts CAEX 2.15 only as an import source. Normalize it
    # before mapping so the resulting NodeSet consistently represents the
    # supported CAEX 3.0 model rather than reviving a legacy write path.
    if b'SchemaVersion="2.15"' in aml_bytes or b"SchemaVersion='2.15'" in aml_bytes:
        from .legacy import import_aml_xml

        imported = import_aml_xml(aml_bytes)
        aml_bytes = imported.document.to_aml_xml(pretty=False).encode("utf-8")
    publication_date_text = _publication_date_text(publication_date)
    from .models import CAEXFile

    try:
        document = CAEXFile.from_aml_xml(aml_bytes)
    except ValueError as exc:
        raise OPCUAConversionError(
            f"AutomationML could not be loaded for Python OPC UA mapping: {exc}"
        ) from exc
    root = _map_document_to_nodeset_python(
        document,
        publication_date=publication_date_text,
    )
    return _finish_forward_mapping(
        root,
        aml_bytes=aml_bytes,
        pretty=pretty,
        include_roundtrip=include_roundtrip,
    )


def _finish_forward_mapping(
    root: etree._Element,
    *,
    aml_bytes: bytes,
    pretty: bool,
    include_roundtrip: bool,
) -> str:
    _add_conversion_metadata(
        root,
        aml_bytes=aml_bytes if include_roundtrip else None,
    )
    etree.cleanup_namespaces(root)
    _validate_nodeset(root)
    return _serialize(root, pretty=pretty)


def nodeset_to_aml_xml(
    nodeset_xml: UANodeSet | str | bytes,
    *,
    prefer_embedded_source: bool = True,
    pretty: bool = True,
) -> str:
    """Convert a UANodeSet to AML using source recovery or the strict profile.

    Source recovery remains the lossless default for app-generated NodeSets.
    When the source extension is absent, or ``prefer_embedded_source`` is false,
    the Python reverse mapper reconstructs the subset described by
    ``REVERSE_MAPPING_VERSION``.
    """

    root = _load_nodeset_root(nodeset_xml)
    if prefer_embedded_source:
        aml_xml = _embedded_aml_xml(root)
        if aml_xml is not None:
            return aml_xml

    document = _semantic_nodeset_to_document(root)
    return document.to_aml_xml(pretty=pretty)


def nodeset_to_document(
    nodeset_xml: UANodeSet | str | bytes,
    *,
    prefer_embedded_source: bool = True,
) -> CAEXFile:
    """Convert a UANodeSet to a CAEX model.

    Embedded AML is preferred for exact app round trips. A NodeSet without that
    extension is reconstructed from its OPC UA nodes when it fits the semantic
    reverse profile.
    """

    from .models import CAEXFile

    root = _load_nodeset_root(nodeset_xml)
    if prefer_embedded_source:
        aml_xml = _embedded_aml_xml(root)
        if aml_xml is not None:
            return CAEXFile.from_aml_xml(aml_xml)
    return _semantic_nodeset_to_document(root)


def has_embedded_aml_source(nodeset_xml: UANodeSet | str | bytes) -> bool:
    """Return whether a valid UANodeSet has a valid embedded AML source."""

    return _embedded_aml_xml(_load_nodeset_root(nodeset_xml)) is not None


def _embedded_aml_xml(root: etree._Element) -> str | None:
    """Return and verify the source-preserving extension, when present."""

    payloads = root.xpath(
        "./ua:Extensions/ua:Extension/amlrt:AutomationMLExport/"
        "amlrt:OriginalAutomationML",
        namespaces=_NS,
    )
    if not payloads:
        return None
    if len(payloads) != 1:
        raise OPCUAConversionError(
            "The UANodeSet contains more than one embedded AutomationML payload."
        )

    payload = payloads[0]
    if payload.get("encoding") != "base64" or not payload.text:
        raise OPCUAConversionError("The embedded AutomationML payload is malformed.")
    try:
        aml_bytes = base64.b64decode(payload.text, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise OPCUAConversionError(
            "The embedded AutomationML payload is not valid base64."
        ) from exc

    expected_digest = payload.get("sha256", "")
    actual_digest = sha256(aml_bytes).hexdigest()
    if not expected_digest or not compare_digest(expected_digest, actual_digest):
        raise OPCUAConversionError(
            "The embedded AutomationML payload failed its SHA-256 integrity check."
        )

    _reject_unsafe_xml(aml_bytes)
    _assert_root(aml_bytes, "CAEXFile", "embedded AutomationML")
    return aml_bytes.decode("utf-8")


def is_nodeset_xml(xml: str | bytes) -> bool:
    """Return whether XML has an OPC UA UANodeSet root without resolving entities."""

    try:
        data = _xml_bytes(xml)
        _reject_unsafe_xml(data)
        root = _parse_xml(data)
    except (OPCUAConversionError, etree.XMLSyntaxError, ValueError, UnicodeError):
        return False
    name = etree.QName(root)
    return name.namespace == UA_NODESET_NS and name.localname == "UANodeSet"


_FILE_PROPERTY_NAMES = {
    "AMLChangeMode",
    "FileName",
    "SchemaVersion",
    "SourceDocumentInformation",
    "SuperiorStandardVersion",
}
_CONSTRAINT_VALUE_NAMES = {
    "RequiredMaxValue",
    "RequiredMinValue",
    "RequiredValue",
}
_ATTRIBUTE_METADATA_PROPERTY_NAMES = {
    "AMLAttributeDataType",
    "AMLChangeMode",
    "AMLDefaultValue",
    "AMLOriginalID",
    "AMLRefAttributeType",
    "AMLUnit",
    DEFAULT_MAPPING_PROFILE.default_value_property,
    DEFAULT_MAPPING_PROFILE.unit_property,
}
_SEMANTIC_URI = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
_SEMANTIC_IRDI = re.compile(r"^[0-9]{4}[-/].*#")


@dataclass(slots=True)
class _NodeSetIndex:
    """Resolved aliases, nodes, and references for the semantic reverse mapper."""

    root: etree._Element
    aliases: dict[str, str]
    nodes: dict[str, etree._Element]
    namespace_uris: dict[int, str]
    _reference_cache: dict[tuple[str, str, bool], tuple[str, ...]] = field(
        default_factory=dict,
        repr=False,
    )
    _class_path_cache: dict[str, dict[str, tuple[str, ...]]] = field(
        default_factory=dict,
        repr=False,
    )

    @classmethod
    def from_root(cls, root: etree._Element) -> _NodeSetIndex:
        aliases = {
            alias.get("Alias", ""): (alias.text or "").strip()
            for alias in root.xpath("./ua:Aliases/ua:Alias", namespaces=_NS)
        }
        nodes = {
            node.get("NodeId", ""): node
            for node in root.xpath("./ua:*[@NodeId]", namespaces=_NS)
        }
        namespace_uris = {
            position: (uri.text or "").strip()
            for position, uri in enumerate(
                root.xpath("./ua:NamespaceUris/ua:Uri", namespaces=_NS),
                start=1,
            )
        }
        return cls(
            root=root,
            aliases=aliases,
            nodes=nodes,
            namespace_uris=namespace_uris,
        )

    def resolve(self, node_id_or_alias: str) -> str:
        declared = self.aliases.get(node_id_or_alias)
        if declared is not None:
            return declared
        builtin = _BUILTIN_UA_ALIASES.get(node_id_or_alias)
        if builtin is not None:
            return builtin
        numeric = _AML_COMPANION_ALIAS_IDS.get(node_id_or_alias)
        if numeric is not None:
            indexes = [
                index
                for index, uri in self.namespace_uris.items()
                if uri == AML_MODEL_URI
            ]
            if len(indexes) == 1:
                return f"ns={indexes[0]};i={numeric}"
        return node_id_or_alias

    def reference_targets(
        self,
        node: etree._Element,
        reference_type: str,
        *,
        is_forward: bool = True,
    ) -> list[str]:
        expected_type = self.resolve(reference_type)
        node_id = node.get("NodeId", "")
        cache_key = (node_id, expected_type, is_forward)
        cached = self._reference_cache.get(cache_key)
        if cached is not None:
            return list(cached)
        targets: list[str] = []
        for reference in node.xpath("./ua:References/ua:Reference", namespaces=_NS):
            forward = reference.get("IsForward", "true").lower() != "false"
            if forward != is_forward:
                continue
            actual_type = self.resolve(reference.get("ReferenceType", ""))
            if actual_type == expected_type:
                targets.append(self.resolve((reference.text or "").strip()))
        if node_id:
            self._reference_cache[cache_key] = tuple(targets)
        return targets

    def target_nodes(
        self,
        node: etree._Element,
        reference_type: str,
        *,
        is_forward: bool = True,
    ) -> list[etree._Element]:
        result: list[etree._Element] = []
        for target in self.reference_targets(
            node,
            reference_type,
            is_forward=is_forward,
        ):
            target_node = self.nodes.get(target)
            if target_node is None:
                raise OPCUAConversionError(
                    f"UANodeSet reference from {_node_label(node)} points to "
                    f"missing node {target!r}."
                )
            result.append(target_node)
        return result

    def forward_reference_types(self, node: etree._Element) -> list[str]:
        return [
            reference.get("ReferenceType", "")
            for reference in node.xpath("./ua:References/ua:Reference", namespaces=_NS)
            if reference.get("IsForward", "true").lower() != "false"
        ]

    def class_paths(self, collection_name: str) -> dict[str, tuple[str, ...]]:
        """Return all local AML class paths, indexed once per collection."""

        cached = self._class_path_cache.get(collection_name)
        if cached is not None:
            return cached
        matches: dict[str, list[str]] = {}

        def visit(node: etree._Element, path: str, ancestors: set[str]) -> None:
            node_id = node.get("NodeId", "")
            if node_id in ancestors:
                raise OPCUAConversionError(
                    f"Organizes hierarchy contains a cycle at {node_id!r}."
                )
            paths = matches.setdefault(node_id, [])
            if path not in paths:
                paths.append(path)
            next_ancestors = {*ancestors, node_id}
            for child in self.target_nodes(node, "Organizes"):
                visit(
                    child,
                    f"{path}/{_node_name(child)}",
                    next_ancestors,
                )

        for collection in self.nodes.values():
            if _node_name(collection) != collection_name:
                continue
            for library in self.target_nodes(collection, "Organizes"):
                library_path = _node_name(library)
                for child in self.target_nodes(library, "Organizes"):
                    visit(
                        child,
                        f"{library_path}/{_node_name(child)}",
                        set(),
                    )
        result = {
            node_id: tuple(paths)
            for node_id, paths in matches.items()
        }
        self._class_path_cache[collection_name] = result
        return result


def _load_nodeset_root(
    nodeset_xml: UANodeSet | str | bytes,
) -> etree._Element:
    if isinstance(nodeset_xml, UANodeSet):
        root = nodeset_xml.to_etree()
        _validate_nodeset(root)
        return root
    nodeset_bytes = _xml_bytes(nodeset_xml)
    _reject_unsafe_xml(nodeset_bytes)
    try:
        root = _parse_xml(nodeset_bytes)
    except etree.XMLSyntaxError as exc:
        raise OPCUAConversionError(f"Invalid OPC UA UANodeSet XML: {exc}") from exc
    name = etree.QName(root)
    if name.namespace != UA_NODESET_NS or name.localname != "UANodeSet":
        raise OPCUAConversionError("Expected an OPC UA UANodeSet XML document.")
    _validate_nodeset(root)
    return root


def _semantic_nodeset_to_document(root: etree._Element) -> CAEXFile:
    """Reconstruct the intentionally small reverse-mapping profile."""

    from .models import CAEXFile

    index = _NodeSetIndex.from_root(root)
    _assert_component_graph_is_tree(index)
    _assert_class_ancestry_is_acyclic(index)
    file_roots = [
        node
        for node in index.nodes.values()
        if etree.QName(node).localname == "UAObject"
        and index.resolve("CAEXFileType")
        in index.reference_targets(node, "HasTypeDefinition")
    ]
    if len(file_roots) != 1:
        raise _reverse_unsupported(
            "a NodeSet without exactly one UAObject of CAEXFileType"
        )
    file_root = file_roots[0]

    properties = _properties_by_name(index, file_root)
    _merge_numbered_properties(properties, "SourceDocumentInformation")
    _merge_numbered_properties(properties, "SuperiorStandardVersion")
    additional_information_nodes = _extract_additional_information_properties(
        properties
    )
    external_references = _extract_external_reference_properties(index, properties)
    unknown_properties = set(properties) - _FILE_PROPERTY_NAMES
    if unknown_properties:
        raise _reverse_unsupported(
            "CAEXFile properties " + ", ".join(sorted(unknown_properties))
        )

    payload: dict[str, object] = {
        "FileName": _single_property_value(properties, "FileName"),
        "SchemaVersion": _single_property_value(properties, "SchemaVersion"),
    }
    documentation = file_root.find(_qname("Documentation"))
    if documentation is not None and (documentation.text or ""):
        payload["Description"] = {"value": documentation.text or ""}
    models = root.xpath("./ua:Models/ua:Model", namespaces=_NS)
    mapping_origin = root.xpath(
        "string(./ua:Extensions/ua:Extension/amlrt:AutomationMLExport/@mapping)",
        namespaces=_NS,
    )
    if models and mapping_origin != "AML-UA-XSLT":
        model_version = models[0].get("Version", "").strip()
        if model_version and model_version != "0.0.0":
            payload["Version"] = {"value": model_version}
    superior_versions = [
        _scalar_value(node)
        for node in properties.get("SuperiorStandardVersion", [])
    ]
    if superior_versions:
        payload["SuperiorStandardVersion"] = superior_versions

    source_documents = [
        _source_document_payload(_scalar_value(node))
        for node in properties.get("SourceDocumentInformation", [])
    ]
    if source_documents:
        payload["SourceDocumentInformation"] = source_documents

    if additional_information_nodes:
        payload["AdditionalInformation"] = [
            _additional_information_payload(_scalar_value(node))
            for node in additional_information_nodes
        ]
    if external_references:
        payload["ExternalReference"] = external_references
    if "AMLChangeMode" in properties:
        payload["ChangeMode"] = _mapped_string_property_value(
            index,
            properties,
            "AMLChangeMode",
            "CAEXFile",
        )

    _ensure_allowed_reference_types(
        index,
        file_root,
        {"HasTypeDefinition", "HasProperty", "Organizes"},
        "CAEXFile references",
    )
    hierarchy_collections: list[etree._Element] = []
    role_class_collections: list[etree._Element] = []
    system_unit_class_collections: list[etree._Element] = []
    interface_class_collections: list[etree._Element] = []
    attribute_type_collections: list[etree._Element] = []
    for collection in index.target_nodes(file_root, "Organizes"):
        collection_name = _node_name(collection)
        if collection_name == "InstanceHierarchies":
            hierarchy_collections.append(collection)
        elif collection_name == "RoleClassLibs":
            role_class_collections.append(collection)
        elif collection_name == "SystemUnitClassLibs":
            system_unit_class_collections.append(collection)
        elif collection_name == "InterfaceClassLibs":
            interface_class_collections.append(collection)
        elif collection_name == "AttributeTypeLibs":
            attribute_type_collections.append(collection)
        else:
            raise _reverse_unsupported(f"the {collection_name!r} CAEX collection")
    if len(hierarchy_collections) > 1:
        raise OPCUAConversionError(
            "The UANodeSet contains more than one InstanceHierarchies collection."
        )

    if hierarchy_collections:
        hierarchy_nodes = index.target_nodes(hierarchy_collections[0], "Organizes")
        seen_objects: set[str] = set()
        payload["InstanceHierarchy"] = [
            _instance_hierarchy_payload(index, node, seen_objects)
            for node in hierarchy_nodes
        ]
    if len(role_class_collections) > 1:
        raise OPCUAConversionError(
            "The UANodeSet contains more than one RoleClassLibs collection."
        )
    if role_class_collections:
        payload["RoleClassLib"] = [
            _role_class_library_payload(index, node)
            for node in index.target_nodes(role_class_collections[0], "Organizes")
        ]
    if len(system_unit_class_collections) > 1:
        raise OPCUAConversionError(
            "The UANodeSet contains more than one SystemUnitClassLibs collection."
        )
    if system_unit_class_collections:
        payload["SystemUnitClassLib"] = [
            _system_unit_class_library_payload(index, node)
            for node in index.target_nodes(
                system_unit_class_collections[0],
                "Organizes",
            )
        ]
    if len(interface_class_collections) > 1:
        raise OPCUAConversionError(
            "The UANodeSet contains more than one InterfaceClassLibs collection."
        )
    if interface_class_collections:
        payload["InterfaceClassLib"] = [
            _interface_class_library_payload(index, node)
            for node in index.target_nodes(
                interface_class_collections[0],
                "Organizes",
            )
        ]
    if len(attribute_type_collections) > 1:
        raise OPCUAConversionError(
            "The UANodeSet contains more than one AttributeTypeLibs collection."
        )
    if attribute_type_collections:
        payload["AttributeTypeLib"] = [
            _attribute_type_library_payload(index, node)
            for node in index.target_nodes(
                attribute_type_collections[0],
                "Organizes",
            )
        ]

    try:
        document = CAEXFile.model_validate(payload)
        from .legacy import upgrade_legacy_model

        return upgrade_legacy_model(document)
    except ValueError as exc:
        raise OPCUAConversionError(
            f"Semantic OPC UA reverse mapping produced invalid CAEX data: {exc}"
        ) from exc


def _assert_component_graph_is_tree(index: _NodeSetIndex) -> None:
    owners: dict[str, list[str]] = {}
    adjacency: dict[str, list[str]] = {}
    for owner_id, owner in index.nodes.items():
        type_definitions = index.reference_targets(owner, "HasTypeDefinition")
        if any(
            index.resolve(type_name) in type_definitions
            for type_name in ("PropertyType", "AMLBaseVariableType")
        ):
            adjacency[owner_id] = []
            continue
        # The legacy XSLT writes some metadata variables with a forward
        # HasComponent reference back to the node named in ParentNodeId.  That
        # is an inverted containment edge, not a second AML owner.  Ignore only
        # that mechanically identifiable legacy shape; native child edges are
        # still checked for both multiple ownership and cycles.
        parent_id = index.resolve(owner.get("ParentNodeId", ""))
        targets = [
            target
            for target in index.reference_targets(owner, "HasComponent")
            if target in index.nodes and target != parent_id
        ]
        adjacency[owner_id] = targets
        for target in targets:
            owners.setdefault(target, []).append(owner_id)
    multiply_owned = {
        target: sorted(source_ids)
        for target, source_ids in owners.items()
        if len(source_ids) > 1
    }
    if multiply_owned:
        target, source_ids = next(iter(sorted(multiply_owned.items())))
        raise OPCUAConversionError(
            f"Component graph node {target!r} has multiple owners: "
            + ", ".join(source_ids)
        )

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node_id: str) -> None:
        if node_id in visiting:
            raise OPCUAConversionError(
                f"Component graph contains a cycle at {node_id!r}."
            )
        if node_id in visited:
            return
        visiting.add(node_id)
        for target in adjacency.get(node_id, ()):
            visit(target)
        visiting.remove(node_id)
        visited.add(node_id)

    for node_id in adjacency:
        visit(node_id)


def _assert_class_ancestry_is_acyclic(index: _NodeSetIndex) -> None:
    classes = {
        node_id: node
        for node_id, node in index.nodes.items()
        if etree.QName(node).localname in {"UAObjectType", "UAVariableType"}
    }
    adjacency = {
        node_id: [
            target
            for target in index.reference_targets(
                node,
                "HasSubtype",
                is_forward=False,
            )
            if target in classes
        ]
        for node_id, node in classes.items()
    }
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node_id: str) -> None:
        if node_id in visiting:
            raise OPCUAConversionError(
                f"Class ancestry contains a cycle at {node_id!r}."
            )
        if node_id in visited:
            return
        visiting.add(node_id)
        for target in adjacency.get(node_id, ()):
            visit(target)
        visiting.remove(node_id)
        visited.add(node_id)

    for node_id in adjacency:
        visit(node_id)


def _role_class_library_payload(
    index: _NodeSetIndex,
    node: etree._Element,
) -> dict[str, object]:
    if etree.QName(node).localname != "UAObject":
        raise OPCUAConversionError("RoleClassLibs contains a non-object library.")
    if index.reference_targets(node, "HasTypeDefinition") != [
        index.resolve("FolderType")
    ]:
        raise OPCUAConversionError(
            f"RoleClassLib {_node_label(node)} is not a FolderType."
        )
    _ensure_allowed_reference_types(
        index,
        node,
        {"HasTypeDefinition", "HasProperty", "Organizes"},
        f"references on RoleClassLib {_node_label(node)}",
    )
    payload = _caex_object_header(index, node)
    role_classes = [
        _role_class_payload(index, child)
        for child in index.target_nodes(node, "Organizes")
    ]
    if role_classes:
        payload["RoleClass"] = role_classes
    return payload


def _role_class_payload(
    index: _NodeSetIndex,
    node: etree._Element,
) -> dict[str, object]:
    if etree.QName(node).localname != "UAObjectType":
        raise OPCUAConversionError(
            f"RoleClass tree contains {_node_label(node)}, not a UAObjectType."
        )
    ref_base_class_path = _optional_semantic_path_property(
        index,
        node,
        "AMLRefBaseClassPath",
    )
    if ref_base_class_path is None:
        ref_base_class_path = _implicit_base_class_path(
            index,
            node,
            "RoleClassLibs",
        )
    _ensure_allowed_reference_types(
        index,
        node,
        {"HasProperty", "HasComponent", "Organizes"},
        f"references on RoleClass {_node_label(node)}",
    )
    payload = _caex_object_header(
        index,
        node,
        allowed_properties={"AMLRefBaseClassPath"},
    )
    if ref_base_class_path is not None:
        payload["RefBaseClassPath"] = ref_base_class_path

    attributes: list[dict[str, object]] = []
    external_interfaces: list[dict[str, object]] = []
    seen_attributes: set[str] = set()
    for child in index.target_nodes(node, "HasComponent"):
        if etree.QName(child).localname == "UAVariable":
            attributes.append(_attribute_payload(index, child, seen_attributes))
        elif etree.QName(child).localname == "UAObject" and _is_external_interface(
            index,
            child,
        ):
            external_interfaces.append(
                _external_interface_payload(index, child, seen_attributes)
            )
        else:
            raise _reverse_unsupported(
                f"unsupported components on RoleClass {_node_label(node)}"
            )
    if attributes:
        payload["Attribute"] = attributes
    if external_interfaces:
        payload["ExternalInterface"] = external_interfaces

    nested_role_classes = [
        _role_class_payload(index, child)
        for child in index.target_nodes(node, "Organizes")
    ]
    if nested_role_classes:
        payload["RoleClass"] = nested_role_classes
    return payload


def _system_unit_class_library_payload(
    index: _NodeSetIndex,
    node: etree._Element,
) -> dict[str, object]:
    if etree.QName(node).localname != "UAObject":
        raise OPCUAConversionError(
            "SystemUnitClassLibs contains a non-object library."
        )
    if index.reference_targets(node, "HasTypeDefinition") != [
        index.resolve("FolderType")
    ]:
        raise OPCUAConversionError(
            f"SystemUnitClassLib {_node_label(node)} is not a FolderType."
        )
    _ensure_allowed_reference_types(
        index,
        node,
        {"HasTypeDefinition", "HasProperty", "Organizes"},
        f"references on SystemUnitClassLib {_node_label(node)}",
    )
    payload = _caex_object_header(index, node)
    classes = [
        _system_unit_class_payload(index, child, set())
        for child in index.target_nodes(node, "Organizes")
    ]
    if classes:
        payload["SystemUnitClass"] = classes
    return payload


def _system_unit_class_payload(
    index: _NodeSetIndex,
    node: etree._Element,
    seen_objects: set[str],
) -> dict[str, object]:
    if etree.QName(node).localname != "UAObjectType":
        raise OPCUAConversionError(
            f"SystemUnitClass tree contains {_node_label(node)}, not a UAObjectType."
        )
    ref_base_class_path = _optional_semantic_path_property(
        index,
        node,
        "AMLRefBaseClassPath",
    )
    if ref_base_class_path is None:
        ref_base_class_path = _implicit_base_class_path(
            index,
            node,
            "SystemUnitClassLibs",
        )
    _ensure_allowed_reference_types(
        index,
        node,
        {
            "HasProperty",
            "HasComponent",
            "Organizes",
            "HasAMLRoleReference",
        },
        f"references on SystemUnitClass {_node_label(node)}",
    )
    payload = _caex_object_header(
        index,
        node,
        allowed_properties={"AMLRefBaseClassPath"},
    )
    if ref_base_class_path is not None:
        payload["RefBaseClassPath"] = ref_base_class_path

    attributes: list[dict[str, object]] = []
    internal_elements: list[dict[str, object]] = []
    external_interfaces: list[dict[str, object]] = []
    supported_role_classes: list[dict[str, object]] = []
    internal_links: list[dict[str, object]] = []
    seen_attributes: set[str] = set()
    for child in index.target_nodes(node, "HasComponent"):
        child_kind = etree.QName(child).localname
        child_name = _node_name(child)
        if child_kind == "UAVariable":
            attributes.append(_attribute_payload(index, child, seen_attributes))
        elif child_kind == "UAObject" and (
            re.fullmatch(r"AMLSupportedRoleClass_\d+", child_name)
            or _is_native_role_relationship(
                index,
                child,
                "SupportedRoleClass",
            )
        ):
            supported_role_classes.append(
                _role_relationship_payload(
                    index,
                    child,
                    "AMLRefRoleClassPath",
                    seen_attributes,
                )
            )
        elif child_kind == "UAObject" and _is_external_interface(index, child):
            external_interfaces.append(
                _external_interface_payload(index, child, seen_attributes)
            )
        elif child_kind == "UAObject" and _has_property(
            index,
            child,
            "AMLRefPartnerSideA",
        ):
            internal_links.append(_internal_link_payload(index, child))
        elif child_kind == "UAObject":
            internal_elements.append(
                _internal_element_payload(index, child, seen_objects)
            )
        else:
            raise _reverse_unsupported(
                f"{child_kind} components on SystemUnitClass {_node_label(node)}"
            )
    role_rule = DEFAULT_MAPPING_PROFILE.role_rule("SystemUnitClass")
    native_role_paths = _native_role_paths(index, node, "SystemUnitClass")
    if native_role_paths:
        existing_role_paths = {
            str(role.get(role_rule.aml_path_field, ""))
            for role in supported_role_classes
        }
        supported_role_classes.extend(
            {role_rule.aml_path_field: path}
            for path in native_role_paths
            if path not in existing_role_paths
        )
    supported_role_classes.sort(
        key=lambda role: str(role.get(role_rule.aml_path_field, ""))
    )
    native_internal_links = _native_internal_link_payloads(
        index,
        node,
        payload.get("ID"),
    )
    if native_internal_links and internal_links:
        _assert_internal_link_projections_agree(
            native_internal_links,
            internal_links,
            f"SystemUnitClass {_node_label(node)}",
        )
    else:
        internal_links.extend(native_internal_links)
    if attributes:
        payload["Attribute"] = attributes
    if internal_elements:
        payload["InternalElement"] = internal_elements
    if external_interfaces:
        payload["ExternalInterface"] = external_interfaces
    if supported_role_classes:
        payload["SupportedRoleClass"] = supported_role_classes
    if internal_links:
        payload["InternalLink"] = internal_links

    nested_classes = [
        _system_unit_class_payload(index, child, seen_objects)
        for child in index.target_nodes(node, "Organizes")
    ]
    if nested_classes:
        payload["SystemUnitClass"] = nested_classes
    return payload


def _interface_class_library_payload(
    index: _NodeSetIndex,
    node: etree._Element,
) -> dict[str, object]:
    if etree.QName(node).localname != "UAObject":
        raise OPCUAConversionError(
            "InterfaceClassLibs contains a non-object library."
        )
    if index.reference_targets(node, "HasTypeDefinition") != [
        index.resolve("FolderType")
    ]:
        raise OPCUAConversionError(
            f"InterfaceClassLib {_node_label(node)} is not a FolderType."
        )
    _ensure_allowed_reference_types(
        index,
        node,
        {"HasTypeDefinition", "HasProperty", "Organizes"},
        f"references on InterfaceClassLib {_node_label(node)}",
    )
    payload = _caex_object_header(index, node)
    classes = [
        _interface_class_payload(index, child)
        for child in index.target_nodes(node, "Organizes")
    ]
    if classes:
        payload["InterfaceClass"] = classes
    return payload


def _interface_class_payload(
    index: _NodeSetIndex,
    node: etree._Element,
) -> dict[str, object]:
    if etree.QName(node).localname != "UAObjectType":
        raise OPCUAConversionError(
            f"InterfaceClass tree contains {_node_label(node)}, not a UAObjectType."
        )
    ref_base_class_path = _optional_semantic_path_property(
        index,
        node,
        "AMLRefBaseClassPath",
    )
    if ref_base_class_path is None:
        ref_base_class_path = _implicit_base_class_path(
            index,
            node,
            "InterfaceClassLibs",
        )
    _ensure_allowed_reference_types(
        index,
        node,
        {"HasProperty", "HasComponent", "Organizes"},
        f"references on InterfaceClass {_node_label(node)}",
    )
    payload = _caex_object_header(
        index,
        node,
        allowed_properties={"AMLRefBaseClassPath"},
    )
    if ref_base_class_path is not None:
        payload["RefBaseClassPath"] = ref_base_class_path

    attributes: list[dict[str, object]] = []
    external_interfaces: list[dict[str, object]] = []
    seen_attributes: set[str] = set()
    for child in index.target_nodes(node, "HasComponent"):
        if etree.QName(child).localname == "UAVariable":
            attributes.append(_attribute_payload(index, child, seen_attributes))
        elif etree.QName(child).localname == "UAObject" and _is_external_interface(
            index,
            child,
        ):
            external_interfaces.append(
                _external_interface_payload(index, child, seen_attributes)
            )
        else:
            raise _reverse_unsupported(
                f"unsupported components on InterfaceClass {_node_label(node)}"
            )
    if attributes:
        payload["Attribute"] = attributes
    if external_interfaces:
        payload["ExternalInterface"] = external_interfaces

    nested_classes = [
        _interface_class_payload(index, child)
        for child in index.target_nodes(node, "Organizes")
    ]
    if nested_classes:
        payload["InterfaceClass"] = nested_classes
    return payload


def _attribute_type_library_payload(
    index: _NodeSetIndex,
    node: etree._Element,
) -> dict[str, object]:
    if etree.QName(node).localname != "UAObject":
        raise OPCUAConversionError(
            "AttributeTypeLibs contains a non-object library."
        )
    if index.reference_targets(node, "HasTypeDefinition") != [
        index.resolve("FolderType")
    ]:
        raise OPCUAConversionError(
            f"AttributeTypeLib {_node_label(node)} is not a FolderType."
        )
    _ensure_allowed_reference_types(
        index,
        node,
        {"HasTypeDefinition", "HasProperty", "Organizes"},
        f"references on AttributeTypeLib {_node_label(node)}",
    )
    payload = _caex_object_header(index, node)
    attribute_types = [
        _attribute_type_payload(index, child)
        for child in index.target_nodes(node, "Organizes")
    ]
    if attribute_types:
        payload["AttributeType"] = attribute_types
    return payload


def _attribute_type_payload(
    index: _NodeSetIndex,
    node: etree._Element,
) -> dict[str, object]:
    if etree.QName(node).localname != "UAVariableType":
        raise OPCUAConversionError(
            f"AttributeType tree contains {_node_label(node)}, not a UAVariableType."
        )
    metadata = _attribute_metadata_properties(index, node, _node_name(node))
    implicit_attribute_type = (
        None
        if "AMLRefAttributeType" in metadata
        else _implicit_base_class_path(index, node, "AttributeTypeLibs")
    )
    actual_property_names = set(_properties_by_name(index, node)) - {
        "AML_ID",
        "Version",
    }
    _ensure_allowed_reference_types(
        index,
        node,
        {
            "HasProperty",
            "HasComponent",
            "Organizes",
            "HasDictionaryEntry",
            "HasConstraint",
        },
        f"references on AttributeType {_node_label(node)}",
    )
    payload = _caex_object_header(
        index,
        node,
        allowed_properties=actual_property_names,
    )
    if "AMLAttributeDataType" in metadata:
        payload["AttributeDataType"] = _single_property_value(
            metadata,
            "AMLAttributeDataType",
        )
    elif node.get("DataType"):
        payload["AttributeDataType"] = _canonical_aml_data_type(
            index,
            node.get("DataType", ""),
            f"AttributeType {_node_name(node)!r}",
        )
    default_value = _profile_metadata_value(
        metadata,
        DEFAULT_MAPPING_PROFILE.default_value_property,
        "AMLDefaultValue",
    )
    if default_value is not None:
        payload["DefaultValue"] = default_value
    unit = _profile_metadata_value(
        metadata, DEFAULT_MAPPING_PROFILE.unit_property, "AMLUnit"
    )
    if unit is not None:
        payload["Unit"] = unit
    if "AMLRefAttributeType" in metadata:
        payload["RefAttributeType"] = _single_property_value(
            metadata,
            "AMLRefAttributeType",
        )
    elif implicit_attribute_type is not None:
        payload["RefAttributeType"] = implicit_attribute_type
    value = _optional_scalar_value(node)
    if value is not None:
        payload["Value"] = value
    ref_semantics = _semantic_reference_values(
        index,
        node,
        metadata,
        _node_name(node),
    )
    if ref_semantics:
        payload["RefSemantic"] = [
            {"CorrespondingAttributePath": semantic_value}
            for semantic_value in ref_semantics
        ]
    constraints = _constraint_payloads(index, node, _node_name(node))
    if constraints:
        payload["Constraint"] = constraints

    attributes: list[dict[str, object]] = []
    seen_attributes: set[str] = set()
    for child in index.target_nodes(node, "HasComponent"):
        if _native_constraint_type(index, child) is not None:
            continue
        if etree.QName(child).localname != "UAVariable":
            raise _reverse_unsupported(
                f"non-attribute components on AttributeType {_node_label(node)}"
            )
        attributes.append(_attribute_payload(index, child, seen_attributes))
    if attributes:
        payload["Attribute"] = attributes

    nested_types = [
        _attribute_type_payload(index, child)
        for child in index.target_nodes(node, "Organizes")
    ]
    if nested_types:
        payload["AttributeType"] = nested_types
    return payload


def _instance_hierarchy_payload(
    index: _NodeSetIndex,
    node: etree._Element,
    seen_objects: set[str],
) -> dict[str, object]:
    if etree.QName(node).localname != "UAObject":
        raise OPCUAConversionError(
            "InstanceHierarchies contains a node that is not a UAObject."
        )
    payload = _caex_object_header(index, node)
    internal_elements: list[dict[str, object]] = []
    for child in index.target_nodes(node, "HasComponent"):
        if etree.QName(child).localname != "UAObject":
            raise _reverse_unsupported("non-object children of InstanceHierarchy")
        internal_elements.append(
            _internal_element_payload(index, child, seen_objects)
        )
    if internal_elements:
        payload["InternalElement"] = internal_elements
    return payload


def _internal_element_payload(
    index: _NodeSetIndex,
    node: etree._Element,
    seen_objects: set[str],
) -> dict[str, object]:
    node_id = node.get("NodeId", "")
    if node_id in seen_objects:
        raise OPCUAConversionError(
            f"The OPC UA component graph is not a CAEX tree at {node_id!r}."
        )
    seen_objects.add(node_id)

    ref_base_system_unit_path = _optional_semantic_path_property(
        index,
        node,
        "AMLRefBaseSystemUnitPath",
    )
    type_definitions = index.reference_targets(node, "HasTypeDefinition")
    if (
        ref_base_system_unit_path is None
        and len(type_definitions) == 1
        and type_definitions[0] != index.resolve("CAEXObjectType")
    ):
        ref_base_system_unit_path = _class_path_for_target(
            index,
            type_definitions[0],
            "SystemUnitClassLibs",
        )
    if ref_base_system_unit_path is not None:
        if len(type_definitions) > 1:
            raise OPCUAConversionError(
                f"Typed InternalElement {_node_label(node)} has more than one "
                "TypeDefinition."
            )
    elif type_definitions != [index.resolve("CAEXObjectType")]:
        raise _reverse_unsupported(
            f"typed or non-CAEX InternalElement {_node_label(node)}"
        )
    _ensure_allowed_reference_types(
        index,
        node,
        {
            "HasTypeDefinition",
            "HasProperty",
            "HasComponent",
            "HasAMLRoleReference",
            "IsMirroredAs",
        },
        f"references on InternalElement {_node_label(node)}",
    )

    payload = _caex_object_header(
        index,
        node,
        allowed_properties={"AMLRefBaseSystemUnitPath"},
    )
    if ref_base_system_unit_path is not None:
        payload["RefBaseSystemUnitPath"] = ref_base_system_unit_path
    attributes: list[dict[str, object]] = []
    internal_elements: list[dict[str, object]] = []
    external_interfaces: list[dict[str, object]] = []
    role_requirements: list[dict[str, object]] = []
    supported_role_classes: list[dict[str, object]] = []
    internal_links: list[dict[str, object]] = []
    seen_attributes: set[str] = set()
    for child in index.target_nodes(node, "HasComponent"):
        child_kind = etree.QName(child).localname
        if child_kind == "UAObject":
            child_name = _node_name(child)
            if re.fullmatch(
                r"AMLRoleRequirements_\d+",
                child_name,
            ) or _is_native_role_relationship(
                index,
                child,
                "RoleRequirements",
            ):
                role_requirements.append(
                    _role_relationship_payload(
                        index,
                        child,
                        "AMLRefBaseRoleClassPath",
                        seen_attributes,
                    )
                )
            elif re.fullmatch(
                r"AMLSupportedRoleClass_\d+",
                child_name,
            ) or _is_native_role_relationship(
                index,
                child,
                "SupportedRoleClass",
            ):
                supported_role_classes.append(
                    _role_relationship_payload(
                        index,
                        child,
                        "AMLRefRoleClassPath",
                        seen_attributes,
                    )
                )
            elif _is_external_interface(index, child):
                external_interfaces.append(
                    _external_interface_payload(index, child, seen_attributes)
                )
            elif _has_property(index, child, "AMLRefPartnerSideA"):
                internal_links.append(_internal_link_payload(index, child))
            else:
                internal_elements.append(
                    _internal_element_payload(index, child, seen_objects)
                )
        elif child_kind == "UAVariable":
            attributes.append(_attribute_payload(index, child, seen_attributes))
        else:
            raise _reverse_unsupported(
                f"{child_kind} children of InternalElement"
            )
    role_rule = DEFAULT_MAPPING_PROFILE.role_rule("InternalElement")
    native_role_paths = _native_role_paths(index, node, "InternalElement")
    if native_role_paths:
        # Accepted profile rule: a plain role reference on an InternalElement is
        # a RoleRequirement.  SystemUnitClass uses the same native edge for
        # SupportedRoleClass above.
        existing_role_paths = {
            str(role.get(role_rule.aml_path_field, ""))
            for role in role_requirements
        }
        existing_role_paths.update(
            str(role.get("RefRoleClassPath", ""))
            for role in supported_role_classes
        )
        role_requirements.extend(
            {role_rule.aml_path_field: path}
            for path in native_role_paths
            if path not in existing_role_paths
        )
    role_requirements.sort(
        key=lambda role: str(role.get(role_rule.aml_path_field, ""))
    )
    native_internal_links = _native_internal_link_payloads(
        index,
        node,
        payload.get("ID"),
    )
    if native_internal_links and internal_links:
        _assert_internal_link_projections_agree(
            native_internal_links,
            internal_links,
            f"InternalElement {_node_label(node)}",
        )
    else:
        internal_links.extend(native_internal_links)
    if attributes:
        payload["Attribute"] = attributes
    if internal_elements:
        payload["InternalElement"] = internal_elements
    if external_interfaces:
        payload["ExternalInterface"] = external_interfaces
    if supported_role_classes:
        payload["SupportedRoleClass"] = supported_role_classes
    if role_requirements:
        payload["RoleRequirements"] = role_requirements
    if internal_links:
        payload["InternalLink"] = internal_links
    return payload


def _role_relationship_payload(
    index: _NodeSetIndex,
    node: etree._Element,
    path_property_name: str,
    seen_attributes: set[str],
) -> dict[str, object]:
    if index.reference_targets(node, "HasTypeDefinition") != [
        index.resolve("BaseObjectType")
    ]:
        raise OPCUAConversionError(
            f"Semantic role relationship {_node_label(node)} is not a BaseObjectType."
        )
    _ensure_allowed_reference_types(
        index,
        node,
        {
            "HasTypeDefinition",
            "HasProperty",
            "HasComponent",
            "HasAMLRoleReference",
        },
        f"references on semantic role relationship {_node_label(node)}",
    )
    path = _optional_semantic_path_property(index, node, path_property_name)
    native_targets = index.reference_targets(node, "HasAMLRoleReference")
    native_paths = [
        _class_path_for_target(index, target, "RoleClassLibs")
        for target in native_targets
    ]
    if any(native_path is None for native_path in native_paths):
        raise _reverse_unsupported(
            f"role relationship {_node_label(node)} targeting outside RoleClassLibs"
        )
    if path is None:
        if len(native_paths) != 1:
            raise OPCUAConversionError(
                f"Semantic role relationship {_node_label(node)} has "
                f"{len(native_paths)} native role targets; exactly one is required."
            )
        path = native_paths[0]
    elif native_paths and native_paths != [path]:
        raise OPCUAConversionError(
            f"Semantic role relationship {_node_label(node)} has inconsistent "
            "native and explicit role targets."
        )
    payload: dict[str, object] = {
        (
            "RefBaseRoleClassPath"
            if path_property_name == "AMLRefBaseRoleClassPath"
            else "RefRoleClassPath"
        ): path
    }
    relationship_properties = _properties_by_name(index, node)
    documentation = node.find(_qname("Documentation"))
    if documentation is not None:
        payload["Description"] = {"value": documentation.text or ""}
    if "AMLChangeMode" in relationship_properties:
        payload["ChangeMode"] = _mapped_string_property_value(
            index,
            relationship_properties,
            "AMLChangeMode",
            f"semantic role relationship {_node_label(node)}",
        )
    if "Version" in relationship_properties:
        payload["Version"] = {
            "value": _single_property_value(relationship_properties, "Version")
        }
    mapping_object = _mapping_object_payload(index, node, path_property_name)
    if mapping_object is not None:
        payload["MappingObject"] = mapping_object
    attributes: list[dict[str, object]] = []
    external_interfaces: list[dict[str, object]] = []
    for child in index.target_nodes(node, "HasComponent"):
        if _node_name(child) == "MappingObject":
            continue
        if etree.QName(child).localname == "UAVariable":
            attributes.append(_attribute_payload(index, child, seen_attributes))
        elif etree.QName(child).localname == "UAObject" and _is_external_interface(
            index,
            child,
        ):
            external_interfaces.append(
                _external_interface_payload(index, child, seen_attributes)
            )
        else:
            raise _reverse_unsupported(
                f"non-attribute content on semantic role relationship "
                f"{_node_label(node)}"
            )
    if attributes:
        payload["Attribute"] = attributes
    if external_interfaces:
        payload["ExternalInterface"] = external_interfaces
    return payload


def _mapping_object_payload(
    index: _NodeSetIndex,
    node: etree._Element,
    path_property_name: str,
) -> dict[str, object] | None:
    properties = _properties_by_name(index, node)
    native_hosts = [
        child
        for child in index.target_nodes(node, "HasComponent")
        if etree.QName(child).localname == "UAObject"
        and _node_name(child) == "MappingObject"
    ]
    if len(native_hosts) > 1:
        raise OPCUAConversionError(
            f"Semantic role relationship {_node_label(node)} has more than one "
            "MappingObject."
        )
    marker_name = "AMLMappingObjectPresent"
    mapping_patterns = {
        "AttributeNameMapping": re.compile(
            r"AMLAttributeNameMapping_(\d+)_(SystemUnitAttributeName|RoleAttributeName)"
        ),
        "InterfaceIDMapping": re.compile(
            r"AMLInterfaceIDMapping_(\d+)_(SystemUnitInterfaceID|RoleInterfaceID)"
        ),
    }
    mapping_property_names = {
        property_name
        for property_name in properties
        if property_name == marker_name
        or any(
            pattern.fullmatch(property_name)
            for pattern in mapping_patterns.values()
        )
    }
    unknown_properties = set(properties) - {
        path_property_name,
        "AMLChangeMode",
        "Version",
        *mapping_property_names,
    }
    if unknown_properties:
        raise _reverse_unsupported(
            f"properties on semantic role relationship {_node_label(node)}: "
            + ", ".join(sorted(unknown_properties))
        )
    if native_hosts:
        if mapping_property_names:
            raise OPCUAConversionError(
                f"Semantic role relationship {_node_label(node)} mixes native "
                "and legacy MappingObject representations."
            )
        return _native_mapping_object_payload(index, native_hosts[0])
    if not mapping_property_names:
        return None
    if marker_name not in mapping_property_names:
        raise OPCUAConversionError(
            f"Semantic role relationship {_node_label(node)} has mapping fields "
            "without an AMLMappingObjectPresent marker."
        )
    if _mapped_string_property_value(
        index,
        properties,
        marker_name,
        f"semantic role relationship {_node_label(node)}",
    ).lower() != "true":
        raise OPCUAConversionError(
            f"Semantic role relationship {_node_label(node)} has an invalid "
            "AMLMappingObjectPresent marker."
        )

    payload: dict[str, object] = {}
    expected_fields = {
        "AttributeNameMapping": {
            "SystemUnitAttributeName",
            "RoleAttributeName",
        },
        "InterfaceIDMapping": {
            "SystemUnitInterfaceID",
            "RoleInterfaceID",
        },
    }
    for mapping_name, pattern in mapping_patterns.items():
        numbered_values: dict[int, dict[str, str]] = {}
        for property_name in mapping_property_names:
            match = pattern.fullmatch(property_name)
            if match is None:
                continue
            position = int(match.group(1))
            field_name = match.group(2)
            numbered_values.setdefault(position, {})[field_name] = (
                _mapped_string_property_value(
                    index,
                    properties,
                    property_name,
                    f"semantic role relationship {_node_label(node)}",
                )
            )
        for position, values in numbered_values.items():
            if set(values) != expected_fields[mapping_name]:
                raise OPCUAConversionError(
                    f"Semantic role relationship {_node_label(node)} has an "
                    f"incomplete {mapping_name} at position {position}."
                )
        if numbered_values:
            payload[mapping_name] = [
                numbered_values[position]
                for position in sorted(numbered_values)
            ]
    return payload


def _native_mapping_object_payload(
    index: _NodeSetIndex,
    node: etree._Element,
) -> dict[str, object]:
    if index.reference_targets(node, "HasTypeDefinition") != [
        index.resolve("BaseObjectType")
    ]:
        raise OPCUAConversionError(
            f"MappingObject {_node_label(node)} is not a BaseObjectType."
        )
    if _properties_by_name(index, node):
        raise _reverse_unsupported(
            f"header properties on MappingObject {_node_label(node)}"
        )
    _ensure_allowed_reference_types(
        index,
        node,
        {"HasTypeDefinition", "HasComponent"},
        f"references on MappingObject {_node_label(node)}",
    )
    result: dict[str, object] = {}
    field_sets = {
        "AttributeNameMapping": (
            "SystemUnitAttributeName",
            "RoleAttributeName",
        ),
        "InterfaceIDMapping": (
            "SystemUnitInterfaceID",
            "RoleInterfaceID",
        ),
    }
    grouped: dict[str, list[dict[str, str]]] = {
        name: [] for name in field_sets
    }
    for pair in index.target_nodes(node, "HasComponent"):
        pair_name = _node_name(pair)
        if etree.QName(pair).localname != "UAObject" or pair_name not in field_sets:
            raise OPCUAConversionError(
                f"MappingObject {_node_label(node)} contains unexpected pair "
                f"{_node_label(pair)}."
            )
        if index.reference_targets(pair, "HasTypeDefinition") != [
            index.resolve("BaseObjectType")
        ]:
            raise OPCUAConversionError(
                f"Mapping pair {_node_label(pair)} is not a BaseObjectType."
            )
        _ensure_allowed_reference_types(
            index,
            pair,
            {"HasTypeDefinition", "HasProperty"},
            f"references on mapping pair {_node_label(pair)}",
        )
        properties = _properties_by_name(index, pair)
        fields = field_sets[pair_name]
        if set(properties) != set(fields):
            raise OPCUAConversionError(
                f"Mapping pair {_node_label(pair)} has fields "
                f"{sorted(properties)}, expected {sorted(fields)}."
            )
        grouped[pair_name].append(
            {
                field: _mapped_string_property_value(
                    index,
                    properties,
                    field,
                    f"mapping pair {_node_label(pair)}",
                )
                for field in fields
            }
        )
    for pair_name, values in grouped.items():
        values.sort(key=lambda item: tuple(item[field] for field in field_sets[pair_name]))
        fingerprints = [
            tuple(item[field] for field in field_sets[pair_name])
            for item in values
        ]
        if len(fingerprints) != len(set(fingerprints)):
            raise OPCUAConversionError(
                f"MappingObject {_node_label(node)} repeats a {pair_name} pair."
            )
        if values:
            result[pair_name] = values
    return result


def _mapped_string_property_value(
    index: _NodeSetIndex,
    properties: dict[str, list[etree._Element]],
    property_name: str,
    context: str,
) -> str:
    property_nodes = properties.get(property_name, [])
    if len(property_nodes) != 1:
        raise OPCUAConversionError(
            f"{context} has {len(property_nodes)} {property_name!r} properties; "
            "exactly one is allowed."
        )
    property_node = property_nodes[0]
    if index.reference_targets(property_node, "HasTypeDefinition") != [
        index.resolve("PropertyType")
    ] or index.resolve(property_node.get("DataType", "")) != index.resolve(
        "String"
    ):
        raise OPCUAConversionError(
            f"{context} metadata {property_name!r} is not a String PropertyType."
        )
    return _scalar_value(property_node)


def _internal_link_payload(
    index: _NodeSetIndex,
    node: etree._Element,
) -> dict[str, object]:
    if index.reference_targets(node, "HasTypeDefinition") != [
        index.resolve("BaseObjectType")
    ]:
        raise OPCUAConversionError(
            f"InternalLink {_node_label(node)} is not a BaseObjectType."
        )
    _ensure_allowed_reference_types(
        index,
        node,
        {"HasTypeDefinition", "HasProperty"},
        f"references on InternalLink {_node_label(node)}",
    )
    ref_partner_side_a = _optional_semantic_path_property(
        index,
        node,
        "AMLRefPartnerSideA",
    )
    ref_partner_side_b = _optional_semantic_path_property(
        index,
        node,
        "AMLRefPartnerSideB",
    )
    if ref_partner_side_a is None or ref_partner_side_b is None:
        raise OPCUAConversionError(
            f"InternalLink {_node_label(node)} is missing exact partner metadata."
        )
    payload = _caex_object_header(
        index,
        node,
        allowed_properties={"AMLRefPartnerSideA", "AMLRefPartnerSideB"},
    )
    payload["RefPartnerSideA"] = ref_partner_side_a
    payload["RefPartnerSideB"] = ref_partner_side_b
    if index.target_nodes(node, "HasComponent"):
        raise _reverse_unsupported(
            f"components on InternalLink {_node_label(node)}"
        )
    return payload


def _native_internal_link_payloads(
    index: _NodeSetIndex,
    owner: etree._Element,
    owner_aml_id: object,
) -> list[dict[str, object]]:
    """Interpret directed partner-A edges owned by one CAEX object."""

    owner_id = str(owner_aml_id) if isinstance(owner_aml_id, str) else None
    links: list[dict[str, object]] = []
    seen_edges: set[tuple[str, str]] = set()
    for source in index.target_nodes(owner, "HasComponent"):
        if etree.QName(source).localname != "UAObject" or not _is_external_interface(
            index,
            source,
        ):
            continue
        targets = index.target_nodes(source, "HasAMLInternalLink")
        for target in targets:
            if etree.QName(target).localname != "UAObject" or not _is_external_interface(
                index,
                target,
            ):
                raise OPCUAConversionError(
                    f"Native InternalLink from {_node_label(source)} targets "
                    f"non-interface {_node_label(target)}."
                )
            edge = (source.get("NodeId", ""), target.get("NodeId", ""))
            if edge in seen_edges:
                raise OPCUAConversionError(
                    "Parallel native InternalLink references are not "
                    "representable as distinct CAEX links."
                )
            seen_edges.add(edge)
            target_owner = _component_owner(index, target)
            source_partner = _partner_reference(
                index,
                source,
                owner_id,
            )
            target_partner = _partner_reference(
                index,
                target,
                _node_aml_id(index, target_owner),
            )
            name, identifier = canonical_internal_link_identity(
                source_partner,
                target_partner,
            )
            links.append(
                {
                    "Name": name,
                    "ID": identifier,
                    "RefPartnerSideA": source_partner,
                    "RefPartnerSideB": target_partner,
                }
            )
    return sorted(
        links,
        key=lambda link: (
            str(link["RefPartnerSideA"]),
            str(link["RefPartnerSideB"]),
        ),
    )


def _assert_internal_link_projections_agree(
    native_links: list[dict[str, object]],
    explicit_links: list[dict[str, object]],
    owner_label: str,
) -> None:
    def endpoints(link: dict[str, object]) -> tuple[str, str]:
        return (
            normalize_partner_reference(str(link["RefPartnerSideA"])),
            normalize_partner_reference(str(link["RefPartnerSideB"])),
        )

    if {endpoints(link) for link in native_links} != {
        endpoints(link) for link in explicit_links
    }:
        raise OPCUAConversionError(
            f"{owner_label} contains inconsistent native and explicit "
            "InternalLink representations."
        )


def _component_owner(
    index: _NodeSetIndex,
    interface: etree._Element,
) -> etree._Element:
    current = interface
    visited: set[str] = set()
    while True:
        node_id = current.get("NodeId", "")
        if node_id in visited:
            raise OPCUAConversionError(
                f"ExternalInterface ownership contains a cycle at {node_id!r}."
            )
        visited.add(node_id)
        parents = [
            candidate
            for candidate in index.nodes.values()
            if node_id in index.reference_targets(candidate, "HasComponent")
        ]
        if len(parents) != 1:
            raise OPCUAConversionError(
                f"ExternalInterface {_node_label(interface)} has {len(parents)} "
                "component owners; exactly one is required for InternalLink."
            )
        parent = parents[0]
        if etree.QName(parent).localname == "UAObject" and _is_external_interface(
            index,
            parent,
        ):
            current = parent
            continue
        return parent


def _partner_reference(
    index: _NodeSetIndex,
    interface: etree._Element,
    owner_aml_id: str | None,
) -> str:
    if owner_aml_id:
        return normalize_partner_reference(
            f"{owner_aml_id}:{_node_name(interface)}"
        )
    interface_id = _node_aml_id(index, interface)
    if interface_id:
        return normalize_partner_reference(interface_id)
    raise OPCUAReverseMappingUnsupported(
        f"Native InternalLink endpoint {_node_label(interface)} has neither an "
        "own AML ID nor an owning object AML ID."
    )


def _node_aml_id(
    index: _NodeSetIndex,
    node: etree._Element,
) -> str | None:
    properties = _properties_by_name(index, node)
    original_nodes = properties.get("AMLOriginalID", [])
    id_nodes = properties.get("AML_ID", [])
    if len(original_nodes) > 1 or len(id_nodes) > 1:
        raise OPCUAConversionError(
            f"{_node_label(node)} has duplicate AML identity properties."
        )
    original = _scalar_value(original_nodes[0]) if original_nodes else None
    aml_id = _scalar_value(id_nodes[0]) if id_nodes else None
    if original is not None and aml_id is not None:
        if normalize_partner_reference(original) != normalize_partner_reference(aml_id):
            raise OPCUAConversionError(
                f"{_node_label(node)} has inconsistent AML identity properties."
            )
    value = original or aml_id
    return normalize_partner_reference(value) if value else None


def _external_interface_payload(
    index: _NodeSetIndex,
    node: etree._Element,
    seen_attributes: set[str],
) -> dict[str, object]:
    ref_base_class_path = _optional_semantic_path_property(
        index,
        node,
        "AMLRefBaseClassPath",
    )
    type_definitions = index.reference_targets(node, "HasTypeDefinition")
    if len(type_definitions) > 1:
        raise OPCUAConversionError(
            f"ExternalInterface {_node_label(node)} has more than one "
            "TypeDefinition."
        )
    if ref_base_class_path is None and type_definitions:
        ref_base_class_path = _class_path_for_target(
            index,
            type_definitions[0],
            "InterfaceClassLibs",
        )
    _ensure_allowed_reference_types(
        index,
        node,
        {
            "HasTypeDefinition",
            "HasProperty",
            "HasComponent",
            "HasAMLInternalLink",
        },
        f"references on ExternalInterface {_node_label(node)}",
    )
    payload = _caex_object_header(
        index,
        node,
        allowed_properties={"AMLRefBaseClassPath"},
    )
    if ref_base_class_path is not None:
        payload["RefBaseClassPath"] = ref_base_class_path

    attributes: list[dict[str, object]] = []
    nested_interfaces: list[dict[str, object]] = []
    for child in index.target_nodes(node, "HasComponent"):
        if etree.QName(child).localname == "UAVariable":
            attributes.append(_attribute_payload(index, child, seen_attributes))
        elif etree.QName(child).localname == "UAObject" and _is_external_interface(
            index,
            child,
        ):
            nested_interfaces.append(
                _external_interface_payload(index, child, seen_attributes)
            )
        else:
            raise _reverse_unsupported(
                f"content on ExternalInterface {_node_label(node)}"
            )
    if attributes:
        payload["Attribute"] = attributes
    if nested_interfaces:
        payload["ExternalInterface"] = nested_interfaces
    return payload


def _attribute_payload(
    index: _NodeSetIndex,
    node: etree._Element,
    seen_attributes: set[str],
) -> dict[str, object]:
    node_id = node.get("NodeId", "")
    if node_id in seen_attributes:
        raise OPCUAConversionError(
            f"The OPC UA attribute graph contains a cycle at {node_id!r}."
        )
    seen_attributes.add(node_id)

    name = _node_name(node)
    if name in _CONSTRAINT_VALUE_NAMES or name.startswith("AdditionalInformation"):
        raise _reverse_unsupported(f"the mapped variable {name!r}")
    metadata = _attribute_metadata_properties(index, node, name)
    type_definitions = index.reference_targets(node, "HasTypeDefinition")
    implicit_attribute_type: str | None = None
    if "AMLRefAttributeType" in metadata:
        if len(type_definitions) != 1:
            raise OPCUAConversionError(
                f"Typed AML Attribute {name!r} must have one TypeDefinition."
            )
    elif type_definitions != [index.resolve("AMLBaseVariableType")]:
        if len(type_definitions) == 1:
            implicit_attribute_type = _class_path_for_target(
                index,
                type_definitions[0],
                "AttributeTypeLibs",
            )
        if implicit_attribute_type is None:
            raise _reverse_unsupported(f"typed AML Attribute {name!r}")
    _ensure_allowed_reference_types(
        index,
        node,
        {
            "HasTypeDefinition",
            "HasComponent",
            "HasProperty",
            "HasDictionaryEntry",
            "HasConstraint",
        },
        f"references on Attribute {name!r}",
    )

    actual_property_names = set(_properties_by_name(index, node)) - {
        "AML_ID",
        "Version",
    }
    payload = _caex_object_header(
        index,
        node,
        allowed_properties=actual_property_names,
    )
    documentation = node.find(_qname("Documentation"))
    if documentation is not None:
        payload["Description"] = {"value": documentation.text or ""}

    if "AMLAttributeDataType" in metadata:
        payload["AttributeDataType"] = _single_property_value(
            metadata,
            "AMLAttributeDataType",
        )
    else:
        data_type = node.get("DataType")
        if data_type:
            payload["AttributeDataType"] = _canonical_aml_data_type(
                index,
                data_type,
                f"Attribute {name!r}",
            )
    default_value = _profile_metadata_value(
        metadata,
        DEFAULT_MAPPING_PROFILE.default_value_property,
        "AMLDefaultValue",
    )
    if default_value is not None:
        payload["DefaultValue"] = default_value
    unit = _profile_metadata_value(
        metadata, DEFAULT_MAPPING_PROFILE.unit_property, "AMLUnit"
    )
    if unit is not None:
        payload["Unit"] = unit
    if "AMLRefAttributeType" in metadata:
        payload["RefAttributeType"] = _single_property_value(
            metadata,
            "AMLRefAttributeType",
        )
    elif implicit_attribute_type is not None:
        payload["RefAttributeType"] = implicit_attribute_type

    value = _optional_scalar_value(node)
    if value is not None:
        payload["Value"] = value

    constraints = _constraint_payloads(index, node, name)
    if constraints:
        payload["Constraint"] = constraints

    nested_attributes: list[dict[str, object]] = []
    for child in index.target_nodes(node, "HasComponent"):
        if _native_constraint_type(index, child) is not None:
            continue
        if etree.QName(child).localname != "UAVariable":
            raise _reverse_unsupported(f"object children of Attribute {name!r}")
        nested_attributes.append(_attribute_payload(index, child, seen_attributes))
    if nested_attributes:
        payload["Attribute"] = nested_attributes

    ref_semantics = [
        {"CorrespondingAttributePath": semantic_value}
        for semantic_value in _semantic_reference_values(index, node, metadata, name)
    ]
    if ref_semantics:
        payload["RefSemantic"] = ref_semantics
    return payload


def _constraint_payloads(
    index: _NodeSetIndex,
    node: etree._Element,
    owner_name: str,
) -> list[dict[str, object]]:
    explicit = index.target_nodes(node, "HasConstraint")
    implicit = [
        child
        for child in index.target_nodes(node, "HasComponent")
        if _native_constraint_type(index, child) is not None
    ]
    explicit_ids = {item.get("NodeId", "") for item in explicit}
    implicit_ids = {item.get("NodeId", "") for item in implicit}
    if explicit_ids & implicit_ids:
        raise OPCUAConversionError(
            f"Attribute {owner_name!r} mixes explicit and implicit Constraint edges."
        )
    return [
        _constraint_payload(index, constraint_node, owner_name)
        for constraint_node in [*explicit, *implicit]
    ]


def _native_constraint_type(
    index: _NodeSetIndex,
    node: etree._Element,
) -> str | None:
    if etree.QName(node).localname != "UAVariable":
        return None
    type_definitions = index.reference_targets(node, "HasTypeDefinition")
    native_constraint_types = {
        index.resolve("NominalScaledConstraint"),
        index.resolve("OrdinalScaledConstraint"),
        index.resolve("UnknownConstraint"),
    }
    if len(type_definitions) == 1 and type_definitions[0] in native_constraint_types:
        return type_definitions[0]
    return None


def _constraint_payload(
    index: _NodeSetIndex,
    node: etree._Element,
    owner_name: str,
) -> dict[str, object]:
    if etree.QName(node).localname != "UAVariable":
        raise OPCUAConversionError(
            f"Constraint on {owner_name!r} targets {_node_label(node)}, not a "
            "UAVariable."
        )
    type_definitions = index.reference_targets(node, "HasTypeDefinition")
    native_constraint_type = _native_constraint_type(index, node)
    if native_constraint_type is not None:
        return _native_constraint_payload(
            index,
            node,
            owner_name,
            native_constraint_type,
        )
    if type_definitions != [index.resolve("AMLBaseVariableType")]:
        raise OPCUAConversionError(
            f"Constraint {_node_label(node)} has no recognized constraint "
            "TypeDefinition."
        )
    if index.resolve(node.get("DataType", "")) != index.resolve("String"):
        raise OPCUAConversionError(
            f"Constraint {_node_label(node)} must use String DataType."
        )
    _ensure_allowed_reference_types(
        index,
        node,
        {"HasTypeDefinition", "HasComponent"},
        f"references on Constraint {_node_label(node)}",
    )
    xml_fragment = _scalar_value(node)
    fragment_bytes = xml_fragment.encode("utf-8")
    _reject_unsafe_xml(fragment_bytes)
    try:
        fragment = _parse_xml(fragment_bytes)
    except etree.XMLSyntaxError as exc:
        raise OPCUAConversionError(
            f"Invalid mapped Constraint fragment on {owner_name!r}: {exc}"
        ) from exc
    if etree.QName(fragment).localname != "Constraint":
        raise OPCUAConversionError(
            f"Mapped Constraint on {owner_name!r} has an unexpected root."
        )
    constraint_name = fragment.get("Name")
    if constraint_name is None:
        raise OPCUAConversionError(
            f"Mapped Constraint on {owner_name!r} has no Name."
        )
    shape_elements = [
        child
        for child in fragment
        if isinstance(child.tag, str)
    ]
    if len(shape_elements) != 1:
        raise OPCUAConversionError(
            f"Mapped Constraint {constraint_name!r} must contain one scale shape."
        )
    shape = shape_elements[0]
    shape_name = etree.QName(shape).localname
    payload: dict[str, object] = {"Name": constraint_name}
    if fragment.get("ChangeMode") is not None:
        payload["ChangeMode"] = fragment.get("ChangeMode")
    expected_components: list[tuple[str, str]] = []
    if shape_name == "NominalScaledType":
        required_values = [
            child.text or ""
            for child in shape
            if isinstance(child.tag, str)
            and etree.QName(child).localname == "RequiredValue"
        ]
        payload[shape_name] = {"RequiredValue": required_values}
        expected_components = [
            ("RequiredValue", value) for value in required_values
        ]
    elif shape_name == "OrdinalScaledType":
        ordinal_payload: dict[str, str] = {}
        for child in shape:
            if not isinstance(child.tag, str):
                continue
            field_name = etree.QName(child).localname
            if field_name not in _CONSTRAINT_VALUE_NAMES:
                raise OPCUAConversionError(
                    f"Mapped ordinal Constraint {constraint_name!r} contains "
                    f"unsupported field {field_name!r}."
                )
            field_value = child.text or ""
            ordinal_payload[field_name] = field_value
            expected_components.append((field_name, field_value))
        payload[shape_name] = ordinal_payload
    elif shape_name == "UnknownType":
        requirements = next(
            (
                child.text or ""
                for child in shape
                if isinstance(child.tag, str)
                and etree.QName(child).localname == "Requirements"
            ),
            None,
        )
        payload[shape_name] = (
            {"Requirements": requirements}
            if requirements is not None
            else {}
        )
    else:
        raise _reverse_unsupported(
            f"Constraint shape {shape_name!r} on {owner_name!r}"
        )

    actual_components: list[tuple[str, str]] = []
    for component in index.target_nodes(node, "HasComponent"):
        displayed_component_name = _node_name(component)
        component_name = re.sub(r"_\d+$", "", displayed_component_name)
        if component_name not in _CONSTRAINT_VALUE_NAMES:
            raise OPCUAConversionError(
                f"Constraint {constraint_name!r} has unexpected component "
                f"{displayed_component_name!r}."
            )
        if index.reference_targets(component, "HasTypeDefinition") != [
            index.resolve(component_name)
        ]:
            raise OPCUAConversionError(
                f"Constraint component {_node_label(component)} has an invalid "
                "TypeDefinition."
            )
        _ensure_allowed_reference_types(
            index,
            component,
            {"HasTypeDefinition"},
            f"references on Constraint component {_node_label(component)}",
        )
        actual_components.append((component_name, _scalar_value(component)))
    if actual_components != expected_components:
        raise OPCUAConversionError(
            f"Constraint {constraint_name!r} has inconsistent XML and component "
            "representations."
        )
    return payload


def _native_constraint_payload(
    index: _NodeSetIndex,
    node: etree._Element,
    owner_name: str,
    constraint_type: str,
) -> dict[str, object]:
    """Reconstruct typed constraint facts without an embedded CAEX fragment."""

    _ensure_allowed_reference_types(
        index,
        node,
        {"HasTypeDefinition", "HasComponent", "HasProperty"},
        f"references on Constraint {_node_label(node)}",
    )
    payload = _caex_object_header(index, node)
    components: list[tuple[str, str]] = []
    for component in index.target_nodes(node, "HasComponent"):
        if etree.QName(component).localname != "UAVariable":
            raise OPCUAConversionError(
                f"Native Constraint on {owner_name!r} contains a non-variable "
                f"component {_node_label(component)}."
            )
        component_name = _node_name(component)
        if component_name not in _CONSTRAINT_VALUE_NAMES:
            raise OPCUAConversionError(
                f"Native Constraint {_node_label(node)} has unexpected component "
                f"{component_name!r}."
            )
        if index.reference_targets(component, "HasTypeDefinition") != [
            index.resolve("BaseDataVariableType")
        ]:
            raise OPCUAConversionError(
                f"Native Constraint component {_node_label(component)} has an "
                "invalid TypeDefinition."
            )
        if index.resolve(component.get("DataType", "")) != index.resolve(
            node.get("DataType", "")
        ):
            raise OPCUAConversionError(
                f"Native Constraint component {_node_label(component)} does not "
                "use its constraint DataType."
            )
        _ensure_allowed_reference_types(
            index,
            component,
            {"HasTypeDefinition"},
            f"references on Constraint component {_node_label(component)}",
        )
        components.append((component_name, _scalar_value(component)))

    value = _optional_scalar_value(node)
    if constraint_type == index.resolve("NominalScaledConstraint"):
        if value is not None:
            raise OPCUAConversionError(
                f"Native nominal Constraint {_node_label(node)} must not carry "
                "an opaque value."
            )
        if any(name != "RequiredValue" for name, _ in components):
            raise OPCUAConversionError(
                f"Native nominal Constraint {_node_label(node)} contains ordinal "
                "components."
            )
        values = sorted(component_value for _, component_value in components)
        if len(values) != len(set(values)):
            raise OPCUAConversionError(
                f"Native nominal Constraint {_node_label(node)} repeats a value."
            )
        payload["NominalScaledType"] = {"RequiredValue": values}
        return payload

    if constraint_type == index.resolve("OrdinalScaledConstraint"):
        if value is not None:
            raise OPCUAConversionError(
                f"Native ordinal Constraint {_node_label(node)} must not carry "
                "an opaque value."
            )
        ordinal: dict[str, str] = {}
        for component_name, component_value in components:
            if component_name in ordinal:
                raise OPCUAConversionError(
                    f"Native ordinal Constraint {_node_label(node)} repeats "
                    f"{component_name}."
                )
            ordinal[component_name] = component_value
        payload["OrdinalScaledType"] = ordinal
        return payload

    if components:
        raise OPCUAConversionError(
            f"Native unknown Constraint {_node_label(node)} must not carry scale "
            "components."
        )
    payload["UnknownType"] = (
        {"Requirements": value} if value is not None else {}
    )
    return payload


def _attribute_metadata_properties(
    index: _NodeSetIndex,
    node: etree._Element,
    attribute_name: str,
) -> dict[str, list[etree._Element]]:
    properties = _properties_by_name(index, node)
    unknown = {
        property_name
        for property_name in properties
        if property_name not in {"AML_ID", "Version"}
        and property_name not in _ATTRIBUTE_METADATA_PROPERTY_NAMES
        and not re.fullmatch(r"(?:AML)?RefSemantic_\d+", property_name)
    }
    if unknown:
        raise _reverse_unsupported(
            f"properties on Attribute {attribute_name!r}: "
            + ", ".join(sorted(unknown))
        )
    for property_name, property_nodes in properties.items():
        if property_name in {"AML_ID", "Version"}:
            continue
        if len(property_nodes) != 1:
            raise OPCUAConversionError(
                f"Attribute {attribute_name!r} has {len(property_nodes)} "
                f"{property_name!r} properties; exactly one is allowed."
            )
        property_node = property_nodes[0]
        if index.reference_targets(property_node, "HasTypeDefinition") != [
            index.resolve("PropertyType")
        ]:
            raise OPCUAConversionError(
                f"Attribute metadata {property_name!r} is not a PropertyType."
            )
        expected_data_type = (
            index.resolve(node.get("DataType", ""))
            if property_name == DEFAULT_MAPPING_PROFILE.default_value_property
            else index.resolve("String")
        )
        if index.resolve(property_node.get("DataType", "")) != expected_data_type:
            expected_label = (
                "the parent Variable DataType"
                if property_name == DEFAULT_MAPPING_PROFILE.default_value_property
                else "String DataType"
            )
            raise OPCUAConversionError(
                f"Attribute metadata {property_name!r} must use {expected_label}."
            )
    _merge_numbered_properties(properties, "AMLRefSemantic")
    _merge_numbered_properties(properties, "RefSemantic")
    return properties


def _semantic_reference_values(
    index: _NodeSetIndex,
    node: etree._Element,
    metadata: dict[str, list[etree._Element]],
    attribute_name: str,
) -> list[str]:
    def canonical(values: list[str]) -> list[str]:
        if len(values) != len(set(values)):
            raise OPCUAConversionError(
                f"Attribute {attribute_name!r} repeats a RefSemantic value."
            )
        return sorted(values)

    if metadata.get("AMLRefSemantic") and metadata.get("RefSemantic"):
        raise OPCUAConversionError(
            f"Attribute {attribute_name!r} mixes transitional AMLRefSemantic and "
            "plain RefSemantic properties."
        )
    exact_nodes = metadata.get("RefSemantic", metadata.get("AMLRefSemantic", []))
    exact_values = [_scalar_value(property_node) for property_node in exact_nodes]
    native_values = _dictionary_entry_targets(index, node, attribute_name)
    if exact_values:
        projected_values = [
            projection
            for value in exact_values
            if (projection := _semantic_dictionary_projection(value)) is not None
        ]
        if projected_values and sorted(native_values) != sorted(projected_values):
            raise OPCUAConversionError(
                f"Attribute {attribute_name!r} has inconsistent AMLRefSemantic "
                "properties and HasDictionaryEntry references."
            )
        if projected_values:
            return canonical(exact_values)
        # The strict writer emits plain properties only for values outside
        # Part 19.  Mixed authored graphs therefore combine native dictionary
        # entries with those unprojectable values in one canonical sequence.
        return canonical(
            [identifier for _, identifier in native_values] + exact_values
        )
    return canonical([identifier for _, identifier in native_values])


def _dictionary_entry_targets(
    index: _NodeSetIndex,
    node: etree._Element,
    attribute_name: str,
) -> list[tuple[str, str]]:
    values: list[tuple[str, str]] = []
    for target in index.reference_targets(node, "HasDictionaryEntry"):
        match = re.fullmatch(r"ns=(\d+);s=(.+)", target)
        if match is None:
            raise _reverse_unsupported(
                f"non-string dictionary entry {target!r} on Attribute "
                f"{attribute_name!r}"
            )
        namespace_uri = index.namespace_uris.get(int(match.group(1)))
        if namespace_uri not in {IRDI_DICTIONARY_URI, URI_DICTIONARY_URI}:
            raise _reverse_unsupported(
                f"dictionary namespace {namespace_uri!r} on Attribute "
                f"{attribute_name!r}"
            )
        values.append((namespace_uri, match.group(2)))
    return values


def _semantic_dictionary_projection(value: str) -> tuple[str, str] | None:
    normalized = value.strip()
    if normalized.upper().startswith("ECLASS:"):
        return IRDI_DICTIONARY_URI, normalized.split(":", 1)[1]
    if _SEMANTIC_IRDI.match(normalized):
        return IRDI_DICTIONARY_URI, normalized
    if _SEMANTIC_URI.match(normalized):
        return URI_DICTIONARY_URI, normalized
    return None


def _optional_semantic_path_property(
    index: _NodeSetIndex,
    node: etree._Element,
    property_name: str,
) -> str | None:
    properties = _properties_by_name(index, node)
    property_nodes = properties.get(property_name, [])
    if not property_nodes:
        return None
    if len(property_nodes) != 1:
        raise OPCUAConversionError(
            f"{_node_label(node)} has {len(property_nodes)} {property_name!r} "
            "properties; exactly one is allowed."
        )
    property_node = property_nodes[0]
    if index.reference_targets(property_node, "HasTypeDefinition") != [
        index.resolve("PropertyType")
    ]:
        raise OPCUAConversionError(
            f"Semantic path metadata {property_name!r} is not a PropertyType."
        )
    if index.resolve(property_node.get("DataType", "")) != index.resolve("String"):
        raise OPCUAConversionError(
            f"Semantic path metadata {property_name!r} must use String DataType."
        )
    return _scalar_value(property_node)


def _class_path_for_target(
    index: _NodeSetIndex,
    target_node_id: str,
    collection_name: str,
) -> str | None:
    """Infer an AML library path from native Organizes relationships."""

    resolved_target = index.resolve(target_node_id)
    matches = list(index.class_paths(collection_name).get(resolved_target, ()))
    target_node = index.nodes.get(resolved_target)
    external_path = (
        _optional_semantic_path_property(
            index,
            target_node,
            "AMLExternalClassPath",
        )
        if target_node is not None
        else None
    )

    if len(matches) > 1:
        raise OPCUAConversionError(
            f"OPC UA node {resolved_target!r} has more than one inferred AML "
            f"path in {collection_name}."
        )
    if external_path is not None:
        if matches:
            raise OPCUAConversionError(
                f"OPC UA node {resolved_target!r} is both a local class and an "
                "external class proxy."
            )
        return external_path
    return matches[0] if matches else None


def _implicit_base_class_path(
    index: _NodeSetIndex,
    node: etree._Element,
    collection_name: str,
) -> str | None:
    base_targets = index.reference_targets(
        node,
        "HasSubtype",
        is_forward=False,
    )
    inferred = [
        path
        for target in base_targets
        if (path := _class_path_for_target(index, target, collection_name))
        is not None
    ]
    if len(inferred) > 1:
        raise OPCUAConversionError(
            f"{_node_label(node)} has more than one AML base-class path."
        )
    return inferred[0] if inferred else None


def _is_external_interface(index: _NodeSetIndex, node: etree._Element) -> bool:
    if _has_property(index, node, "AMLRefBaseClassPath"):
        return True
    return any(
        _class_path_for_target(index, target, "InterfaceClassLibs") is not None
        for target in index.reference_targets(node, "HasTypeDefinition")
    )


def _native_role_paths(
    index: _NodeSetIndex,
    node: etree._Element,
    owner: Literal["InternalElement", "SystemUnitClass"],
) -> list[str]:
    rule = DEFAULT_MAPPING_PROFILE.role_rule(owner)
    paths: list[str] = []
    for target in index.reference_targets(node, rule.reference_type):
        path = _class_path_for_target(index, target, "RoleClassLibs")
        if path is None:
            raise _reverse_unsupported(
                f"{rule.reference_type} target {target!r} outside RoleClassLibs"
            )
        paths.append(path)
    if len(paths) != len(set(paths)):
        raise OPCUAConversionError(
            f"{owner} {_node_label(node)} repeats a native role relationship."
        )
    return sorted(paths)


def _is_native_role_relationship(
    index: _NodeSetIndex,
    node: etree._Element,
    relationship: Literal["RoleRequirements", "SupportedRoleClass"],
) -> bool:
    return (
        _node_name(node) == relationship
        and index.reference_targets(node, "HasTypeDefinition")
        == [index.resolve("BaseObjectType")]
        and bool(index.reference_targets(node, "HasAMLRoleReference"))
    )


def _caex_object_header(
    index: _NodeSetIndex,
    node: etree._Element,
    *,
    allowed_properties: set[str] | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {"Name": _node_name(node)}
    documentation = node.find(_qname("Documentation"))
    if documentation is not None and (documentation.text or ""):
        payload["Description"] = {"value": documentation.text or ""}

    properties = _properties_by_name(index, node)
    unknown_properties = set(properties) - {
        "AML_ID",
        "AMLChangeMode",
        "AMLOriginalID",
        "Version",
        *(allowed_properties or set()),
    }
    if unknown_properties:
        raise _reverse_unsupported(
            f"properties on {_node_label(node)}: "
            + ", ".join(sorted(unknown_properties))
        )
    if "AMLOriginalID" in properties:
        original_id = _mapped_string_property_value(
            index,
            properties,
            "AMLOriginalID",
            _node_label(node),
        )
        if "AML_ID" in properties:
            aml_id = _single_property_value(properties, "AML_ID")
            if aml_id.strip("{}") != original_id.strip("{}"):
                raise OPCUAConversionError(
                    f"{_node_label(node)} has inconsistent AML_ID and "
                    "AMLOriginalID properties."
                )
        payload["ID"] = original_id
    elif "AML_ID" in properties:
        aml_id = _single_property_value(properties, "AML_ID")
        if aml_id.startswith("{") and aml_id.endswith("}"):
            aml_id = aml_id[1:-1]
        payload["ID"] = aml_id
    if "AMLChangeMode" in properties:
        payload["ChangeMode"] = _mapped_string_property_value(
            index,
            properties,
            "AMLChangeMode",
            _node_label(node),
        )
    if "Version" in properties:
        payload["Version"] = {
            "value": _single_property_value(properties, "Version")
        }
    return payload


def _properties_by_name(
    index: _NodeSetIndex,
    node: etree._Element,
) -> dict[str, list[etree._Element]]:
    properties: dict[str, list[etree._Element]] = {}
    for property_node in index.target_nodes(node, "HasProperty"):
        if etree.QName(property_node).localname != "UAVariable":
            raise OPCUAConversionError(
                f"HasProperty target {_node_label(property_node)} is not a UAVariable."
            )
        properties.setdefault(_node_name(property_node), []).append(property_node)
    return properties


def _has_property(
    index: _NodeSetIndex,
    node: etree._Element,
    property_name: str,
) -> bool:
    return property_name in _properties_by_name(index, node)


def _merge_numbered_properties(
    properties: dict[str, list[etree._Element]],
    base_name: str,
) -> None:
    """Fold XSLT names such as ``SourceDocumentInformation_1`` together."""

    numbered_names = sorted(
        (
            name
            for name in properties
            if re.fullmatch(rf"{re.escape(base_name)}_\d+", name)
        ),
        key=lambda name: int(name.rsplit("_", 1)[1]),
    )
    if not numbered_names:
        return
    merged = properties.setdefault(base_name, [])
    for name in numbered_names:
        merged.extend(properties.pop(name))


def _extract_additional_information_properties(
    properties: dict[str, list[etree._Element]],
) -> list[etree._Element]:
    matches: list[tuple[int, etree._Element]] = []
    for property_name in list(properties):
        retained: list[etree._Element] = []
        for node in properties[property_name]:
            match = re.search(
                r"(?:^|;)s=CAEXFile_AdditionalInformation(?:_(\d+))?$",
                node.get("NodeId", ""),
            )
            if match is None:
                retained.append(node)
                continue
            matches.append((int(match.group(1) or 0), node))
        if retained:
            properties[property_name] = retained
        else:
            properties.pop(property_name)
    return [node for _, node in sorted(matches, key=lambda item: item[0])]


def _extract_external_reference_properties(
    index: _NodeSetIndex,
    properties: dict[str, list[etree._Element]],
) -> list[dict[str, str]]:
    aliases: dict[int, str] = {}
    paths: dict[int, str] = {}
    patterns = {
        "Alias": re.compile(r"AMLExternalReferenceAlias_(\d+)"),
        "Path": re.compile(r"AMLExternalReferencePath_(\d+)"),
    }
    for field_name, pattern in patterns.items():
        target = aliases if field_name == "Alias" else paths
        for property_name in list(properties):
            match = pattern.fullmatch(property_name)
            if match is None:
                continue
            property_nodes = properties.pop(property_name)
            if len(property_nodes) != 1:
                raise OPCUAConversionError(
                    f"CAEXFile has {len(property_nodes)} {property_name!r} "
                    "properties; exactly one is allowed."
                )
            property_node = property_nodes[0]
            if index.reference_targets(property_node, "HasTypeDefinition") != [
                index.resolve("PropertyType")
            ] or index.resolve(property_node.get("DataType", "")) != index.resolve(
                "String"
            ):
                raise OPCUAConversionError(
                    f"External-reference metadata {property_name!r} is not a "
                    "String PropertyType."
                )
            target[int(match.group(1))] = _scalar_value(property_node)
    if set(aliases) != set(paths):
        raise OPCUAConversionError(
            "CAEXFile external-reference alias/path metadata is incomplete."
        )
    return [
        {"Alias": aliases[position], "Path": paths[position]}
        for position in sorted(aliases)
    ]


def _single_property_value(
    properties: dict[str, list[etree._Element]],
    name: str,
) -> str:
    nodes = properties.get(name, [])
    if len(nodes) != 1:
        raise OPCUAConversionError(
            f"Semantic reverse mapping requires exactly one {name!r} property; "
            f"found {len(nodes)}."
        )
    return _scalar_value(nodes[0])


def _profile_metadata_value(
    properties: dict[str, list[etree._Element]],
    preferred_name: str,
    legacy_name: str,
) -> str | None:
    """Read one profile property while accepting the transitional AML prefix."""

    if preferred_name in properties and legacy_name in properties:
        raise OPCUAConversionError(
            f"Mapped attribute contains both {preferred_name!r} and legacy "
            f"{legacy_name!r} properties."
        )
    selected = preferred_name if preferred_name in properties else legacy_name
    if selected not in properties:
        return None
    return _single_property_value(properties, selected)


def _source_document_payload(xml_fragment: str) -> dict[str, str]:
    fragment_bytes = xml_fragment.encode("utf-8")
    _reject_unsafe_xml(fragment_bytes)
    try:
        fragment = _parse_xml(fragment_bytes)
    except etree.XMLSyntaxError as exc:
        raise OPCUAConversionError(
            f"Invalid mapped SourceDocumentInformation fragment: {exc}"
        ) from exc
    if etree.QName(fragment).localname != "SourceDocumentInformation":
        raise OPCUAConversionError(
            "Mapped SourceDocumentInformation does not contain the expected element."
        )
    return dict(fragment.attrib)


def _additional_information_payload(xml_fragment: str) -> dict[str, object]:
    fragment_bytes = xml_fragment.encode("utf-8")
    _reject_unsafe_xml(fragment_bytes)
    try:
        fragment = _parse_xml(fragment_bytes)
    except etree.XMLSyntaxError:
        return {"value": xml_fragment}
    if etree.QName(fragment).localname != "AdditionalInformation":
        return {"value": xml_fragment}
    from .xml import loads_additional_information

    try:
        return loads_additional_information(xml_fragment).to_aml_dict(
            include_change_mode=True,
            prune_empty=False,
        )
    except ValueError as exc:
        raise OPCUAConversionError(
            f"Invalid mapped AdditionalInformation fragment: {exc}"
        ) from exc


def _canonical_aml_data_type(
    index: _NodeSetIndex,
    data_type: str,
    feature: str,
) -> str:
    """Apply the same datatype rule used by the Python forward mapper."""

    resolved = index.resolve(data_type)
    try:
        return DEFAULT_MAPPING_PROFILE.data_types.from_ua(
            resolved
        ).canonical_aml_type
    except UnsupportedDataTypeError as exc:
        raise _reverse_unsupported(
            f"OPC UA DataType {data_type!r} on {feature}"
        ) from exc


def _optional_scalar_value(node: etree._Element) -> str | None:
    values = node.xpath("./ua:Value/*", namespaces=_NS)
    if not values:
        return None
    if len(values) != 1 or len(values[0]):
        raise _reverse_unsupported(f"non-scalar Value on {_node_label(node)}")
    return "".join(values[0].itertext())


def _scalar_value(node: etree._Element) -> str:
    value = _optional_scalar_value(node)
    if value is None:
        raise OPCUAConversionError(f"{_node_label(node)} has no scalar Value.")
    return value


def _node_name(node: etree._Element) -> str:
    browse_name = node.get("BrowseName", "")
    name = browse_name.split(":", 1)[-1]
    if name:
        return name
    display_name = node.find(_qname("DisplayName"))
    if display_name is not None and (display_name.text or ""):
        return display_name.text or ""
    if not name:
        raise OPCUAConversionError(f"{_node_label(node)} has no usable name.")
    return name


def _node_label(node: etree._Element) -> str:
    return f"{etree.QName(node).localname} {node.get('NodeId', '<without NodeId>')!r}"


def _ensure_allowed_reference_types(
    index: _NodeSetIndex,
    node: etree._Element,
    allowed: set[str],
    feature: str,
) -> None:
    allowed_resolved = {index.resolve(item) for item in allowed}
    unsupported = [
        item
        for item in index.forward_reference_types(node)
        if index.resolve(item) not in allowed_resolved
    ]
    if unsupported:
        raise _reverse_unsupported(
            f"{feature} using " + ", ".join(sorted(set(unsupported)))
        )


def _reverse_unsupported(feature: str) -> OPCUAReverseMappingUnsupported:
    return OPCUAReverseMappingUnsupported(
        f"The semantic OPC UA reverse mapping {REVERSE_MAPPING_VERSION!r} does "
        f"not yet support {feature}. Use an app export with embedded AML for an "
        "exact round trip."
    )


def _map_document_to_nodeset_python(
    document: CAEXFile,
    *,
    publication_date: str,
) -> etree._Element:
    """Build the strict Python profile graph and serialize it to UANodeSet XML."""

    return document_to_nodeset_model(
        document,
        publication_date=publication_date,
    ).to_etree()


def _add_conversion_metadata(
    root: etree._Element,
    *,
    aml_bytes: bytes | None,
) -> None:
    extensions = root.find(_qname("Extensions"))
    if extensions is None:
        extensions = etree.Element(_qname("Extensions"))
        header_names = {"NamespaceUris", "ServerUris", "Models", "Aliases"}
        insertion_index = 0
        for index, child in enumerate(root):
            if isinstance(child.tag, str) and etree.QName(child).localname in header_names:
                insertion_index = index + 1
        root.insert(insertion_index, extensions)

    extension = etree.SubElement(extensions, _qname("Extension"))
    metadata = etree.SubElement(
        extension,
        f"{{{ROUNDTRIP_NS}}}AutomationMLExport",
        nsmap={"amlrt": ROUNDTRIP_NS},
    )
    from .opcua_python import PYTHON_MAPPING_VERSION

    metadata.set("mapping", "automationml-python")
    metadata.set("mappingVersion", PYTHON_MAPPING_VERSION)
    metadata.set(
        "mappingProfile",
        f"{DEFAULT_MAPPING_PROFILE.name}-v{DEFAULT_MAPPING_PROFILE.version}",
    )
    metadata.set("reverseMapping", REVERSE_MAPPING_VERSION)
    metadata.set("validation", "automationml-python-v1")
    metadata.set("roundTrip", "embedded" if aml_bytes is not None else "none")

    if aml_bytes is not None:
        payload = etree.SubElement(
            metadata,
            f"{{{ROUNDTRIP_NS}}}OriginalAutomationML",
        )
        payload.set("mediaType", "application/automationml+xml")
        payload.set("encoding", "base64")
        payload.set("sha256", sha256(aml_bytes).hexdigest())
        payload.text = base64.b64encode(aml_bytes).decode("ascii")


def _validate_nodeset(root: etree._Element) -> None:
    schema = _nodeset_schema()
    if not schema.validate(root):
        error = schema.error_log.last_error
        raise OPCUAConversionError(
            f"Generated UANodeSet failed its XML Schema: {error or 'unknown error'}"
        )

    aliases = {
        alias.get("Alias", "")
        for alias in root.xpath("./ua:Aliases/ua:Alias", namespaces=_NS)
    }
    node_ids: set[str] = set()
    for node in root.xpath("./ua:*[@NodeId]", namespaces=_NS):
        node_id = node.get("NodeId", "")
        _assert_node_id(node_id, "NodeId")
        if node_id in node_ids:
            raise OPCUAConversionError(f"Generated UANodeSet has duplicate NodeId {node_id!r}.")
        node_ids.add(node_id)
        parent = node.get("ParentNodeId")
        if parent:
            _assert_node_id_or_alias(parent, aliases, "ParentNodeId")
        data_type = node.get("DataType")
        if data_type:
            _assert_node_id_or_alias(data_type, aliases, "DataType")

    for alias in root.xpath("./ua:Aliases/ua:Alias", namespaces=_NS):
        _assert_node_id(alias.text or "", f"alias {alias.get('Alias')!r}")

    for reference in root.xpath(".//ua:Reference", namespaces=_NS):
        _assert_node_id_or_alias(
            reference.get("ReferenceType", ""), aliases, "ReferenceType"
        )
        _assert_node_id_or_alias((reference.text or "").strip(), aliases, "reference")


def _assert_node_id(value: str, field: str) -> None:
    if not _NODE_ID.fullmatch(value):
        raise OPCUAConversionError(
            f"Generated UANodeSet has invalid {field} value {value!r}."
        )


def _assert_node_id_or_alias(value: str, aliases: set[str], field: str) -> None:
    if value not in aliases and not _NODE_ID.fullmatch(value):
        raise OPCUAConversionError(
            f"Generated UANodeSet has unresolved {field} value {value!r}."
        )


def _assert_root(data: bytes, local_name: str, label: str) -> None:
    try:
        root = _parse_xml(data)
    except etree.XMLSyntaxError as exc:
        raise OPCUAConversionError(f"Invalid {label} XML: {exc}") from exc
    if etree.QName(root).localname != local_name:
        raise OPCUAConversionError(
            f"Expected {label} root {local_name!r}, got {etree.QName(root).localname!r}."
        )


def _reject_unsafe_xml(data: bytes) -> None:
    if _DANGEROUS_XML.search(data):
        raise OPCUAConversionError("DTD and entity declarations are not accepted.")


def _parse_xml(data: str | bytes) -> etree._Element:
    parser = etree.XMLParser(
        resolve_entities=False,
        load_dtd=False,
        no_network=True,
        remove_blank_text=True,
        strip_cdata=False,
    )
    return etree.fromstring(_xml_bytes(data), parser=parser)


def _serialize(root: etree._Element, *, pretty: bool) -> str:
    return etree.tostring(
        root,
        encoding="UTF-8",
        xml_declaration=True,
        pretty_print=pretty,
    ).decode("utf-8")


def _xml_bytes(data: str | bytes) -> bytes:
    return data.encode("utf-8") if isinstance(data, str) else data


def _publication_date_text(value: date | datetime | str | None) -> str:
    if value is None:
        return date.today().isoformat()
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise OPCUAConversionError(
            "publication_date must be an ISO date such as '2026-08-16'."
        ) from exc


def _resource_path(name: str) -> Path:
    return Path(__file__).with_name("resources") / "opcua" / name


@lru_cache(maxsize=1)
def _nodeset_schema() -> etree.XMLSchema:
    return etree.XMLSchema(etree.parse(str(_resource_path("UANodeSet.xsd"))))


def _qname(local_name: str) -> str:
    return f"{{{UA_NODESET_NS}}}{local_name}"
