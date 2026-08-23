"""Strict, offline OPC UA UANodeSet authoring models.

These models intentionally cover the NodeClasses and scalar values used by the
AutomationML mapping. Pydantic value objects are immutable after validation;
``UANodeSetBuilder`` is the explicit mutable construction boundary. This
prevents a valid graph from becoming invalid through unnoticed list mutation.
"""

from __future__ import annotations

import re
from collections import Counter
from datetime import date, datetime
from typing import TYPE_CHECKING, Literal, Self
from urllib.parse import urlparse

from lxml import etree
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
    StrictStr,
    field_validator,
    model_validator,
)

if TYPE_CHECKING:
    from .models import CAEXFile
    from .opcua import UANodeSetRoundTripResult


UA_NODESET_NS = "http://opcfoundation.org/UA/2011/03/UANodeSet.xsd"
UA_TYPES_NS = "http://opcfoundation.org/UA/2008/02/Types.xsd"

NodeClass = Literal["UAObject", "UAVariable", "UAObjectType", "UAVariableType"]

_NODE_ID = re.compile(
    r"^(?:ns=\d+;)?(?:i=\d+|s=.+|g=[0-9A-Fa-f-]{36}|b=[A-Za-z0-9+/=]+)$"
)
_ALIAS = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_BROWSE_NAME = re.compile(r"^(?P<namespace>\d+):(?P<name>.+)$")
_XML_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]*$")
_DANGEROUS_XML = re.compile(br"<!\s*(?:DOCTYPE|ENTITY)\b", re.IGNORECASE)


def _is_node_id(value: str) -> bool:
    return bool(_NODE_ID.fullmatch(value)) and not any(
        ord(character) < 0x20 for character in value
    )


def _is_node_id_or_alias(value: str) -> bool:
    return _is_node_id(value) or bool(_ALIAS.fullmatch(value))


def _validate_uri(value: str, label: str) -> str:
    if not urlparse(value).scheme:
        raise ValueError(f"{label} must be an absolute URI, got {value!r}.")
    return value


def _validate_timestamp(value: str, label: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{label} must be an ISO 8601 timestamp.") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{label} must include a timezone.")
    return value


class _FrozenDict(dict[str, str]):
    """Small deeply immutable mapping used inside frozen Pydantic models."""

    def _immutable(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("This validated OPC UA mapping is immutable.")

    __setitem__ = _immutable
    __delitem__ = _immutable
    clear = _immutable
    pop = _immutable
    popitem = _immutable
    setdefault = _immutable
    update = _immutable
    __ior__ = _immutable

    def __deepcopy__(self, _memo: dict[int, object]) -> _FrozenDict:
        return self


class _NodeSetModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        validate_default=True,
    )


class UAReference(_NodeSetModel):
    """One typed edge from the containing source node to a target node."""

    reference_type: StrictStr
    target: StrictStr
    is_forward: StrictBool = True

    @field_validator("reference_type", "target")
    @classmethod
    def _validate_identifier(cls, value: str) -> str:
        if not _is_node_id_or_alias(value):
            raise ValueError(f"Expected an OPC UA NodeId or alias, got {value!r}.")
        return value


class UAScalarValue(_NodeSetModel):
    """A scalar UANodeSet value in its canonical XML lexical form."""

    type_name: StrictStr = "String"
    value: StrictStr

    @field_validator("type_name")
    @classmethod
    def _validate_type_name(cls, value: str) -> str:
        if not _XML_NAME.fullmatch(value):
            raise ValueError(f"Invalid OPC UA scalar XML type {value!r}.")
        return value


class UANode(_NodeSetModel):
    """The common authoring surface for the supported OPC UA NodeClasses."""

    node_class: NodeClass
    node_id: StrictStr
    browse_name: StrictStr
    display_name: StrictStr
    documentation: StrictStr | None = None
    parent_node_id: StrictStr | None = None
    data_type: StrictStr | None = None
    value_rank: StrictInt | None = None
    value: UAScalarValue | None = None
    is_abstract: StrictBool | None = None
    references: tuple[UAReference, ...] = Field(default_factory=tuple)

    @field_validator("node_id", "parent_node_id")
    @classmethod
    def _validate_node_id(cls, value: str | None) -> str | None:
        if value is not None and not _is_node_id(value):
            raise ValueError(f"Invalid OPC UA NodeId {value!r}.")
        return value

    @field_validator("data_type")
    @classmethod
    def _validate_data_type(cls, value: str | None) -> str | None:
        if value is not None and not _is_node_id_or_alias(value):
            raise ValueError(f"Invalid OPC UA DataType {value!r}.")
        return value

    @field_validator("browse_name")
    @classmethod
    def _validate_browse_name(cls, value: str) -> str:
        if not _BROWSE_NAME.fullmatch(value):
            raise ValueError(
                "BrowseName must include a numeric namespace index, for example "
                "'1:Motor'."
            )
        return value

    @field_validator("display_name")
    @classmethod
    def _validate_display_name(cls, value: str) -> str:
        if not value:
            raise ValueError("DisplayName cannot be empty.")
        return value

    @model_validator(mode="after")
    def _validate_node_shape(self) -> Self:
        variable = self.node_class in {"UAVariable", "UAVariableType"}
        if not variable and (
            self.data_type is not None
            or self.value is not None
            or self.value_rank is not None
        ):
            raise ValueError(f"{self.node_class} cannot carry Variable fields.")
        if variable and self.data_type is None:
            raise ValueError(f"{self.node_class} requires a DataType.")
        type_node = self.node_class in {"UAObjectType", "UAVariableType"}
        if type_node and self.is_abstract is None:
            object.__setattr__(self, "is_abstract", False)
        if not type_node and self.is_abstract is not None:
            raise ValueError(f"{self.node_class} cannot declare IsAbstract.")
        return self

    def with_reference(self, reference: UAReference) -> UANode:
        """Return a validated copy with one additional outgoing reference."""

        return UANode.model_validate(
            {**self.model_dump(), "references": (*self.references, reference)}
        )

    def to_element(self) -> etree._Element:
        """Serialize this validated node to its UANodeSet XML element."""

        attributes = {"NodeId": self.node_id, "BrowseName": self.browse_name}
        if self.parent_node_id:
            attributes["ParentNodeId"] = self.parent_node_id
        if self.data_type:
            attributes["DataType"] = self.data_type
        if self.value_rank is not None:
            attributes["ValueRank"] = str(self.value_rank)
        if self.is_abstract is not None:
            attributes["IsAbstract"] = str(self.is_abstract).lower()

        element = etree.Element(_qname(self.node_class), **attributes)
        display_name = etree.SubElement(element, _qname("DisplayName"))
        display_name.text = self.display_name
        if self.documentation is not None:
            documentation = etree.SubElement(element, _qname("Documentation"))
            documentation.text = self.documentation
        if self.references:
            references = etree.SubElement(element, _qname("References"))
            for item in self.references:
                reference_attributes = {"ReferenceType": item.reference_type}
                if not item.is_forward:
                    reference_attributes["IsForward"] = "false"
                reference = etree.SubElement(
                    references, _qname("Reference"), **reference_attributes
                )
                reference.text = item.target
        if self.value is not None:
            value = etree.SubElement(element, _qname("Value"))
            encoded = etree.SubElement(
                value, f"{{{UA_TYPES_NS}}}{self.value.type_name}"
            )
            encoded.text = self.value.value
        return element


class UARequiredModel(_NodeSetModel):
    model_uri: StrictStr
    version: StrictStr
    publication_date: StrictStr

    @field_validator("model_uri")
    @classmethod
    def _validate_model_uri(cls, value: str) -> str:
        return _validate_uri(value, "RequiredModel ModelUri")

    @field_validator("publication_date")
    @classmethod
    def _validate_publication_date(cls, value: str) -> str:
        return _validate_timestamp(value, "RequiredModel PublicationDate")


class UAModel(_NodeSetModel):
    model_uri: StrictStr
    version: StrictStr
    publication_date: StrictStr
    required_models: tuple[UARequiredModel, ...] = Field(default_factory=tuple)

    @field_validator("model_uri")
    @classmethod
    def _validate_model_uri(cls, value: str) -> str:
        return _validate_uri(value, "ModelUri")

    @field_validator("publication_date")
    @classmethod
    def _validate_publication_date(cls, value: str) -> str:
        return _validate_timestamp(value, "PublicationDate")


class UANodeSet(_NodeSetModel):
    """A deterministic, validated subset of a UANodeSet document."""

    namespace_uris: tuple[StrictStr, ...] = Field(default_factory=tuple)
    models: tuple[UAModel, ...] = Field(default_factory=tuple)
    aliases: dict[StrictStr, StrictStr] = Field(default_factory=dict)
    nodes: tuple[UANode, ...] = Field(default_factory=tuple)

    @field_validator("namespace_uris")
    @classmethod
    def _validate_namespace_uris(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        for value in values:
            _validate_uri(value, "Namespace URI")
        return values

    @model_validator(mode="after")
    def _validate_graph_identity(self) -> Self:
        duplicate_namespaces = sorted(
            uri
            for uri, count in Counter(self.namespace_uris).items()
            if count > 1
        )
        if duplicate_namespaces:
            raise ValueError(
                "Duplicate OPC UA namespace URIs: " + ", ".join(duplicate_namespaces)
            )
        node_ids = [node.node_id for node in self.nodes]
        duplicate_node_ids = sorted(
            node_id for node_id, count in Counter(node_ids).items() if count > 1
        )
        if duplicate_node_ids:
            raise ValueError(
                "Duplicate OPC UA NodeIds: " + ", ".join(duplicate_node_ids)
            )
        invalid_aliases = {
            name: node_id
            for name, node_id in self.aliases.items()
            if not _ALIAS.fullmatch(name) or not _is_node_id(node_id)
        }
        if invalid_aliases:
            raise ValueError(f"Invalid OPC UA aliases: {invalid_aliases!r}.")
        for node in self.nodes:
            identifiers = [
                *(item.reference_type for item in node.references),
                *(item.target for item in node.references),
                *([node.data_type] if node.data_type is not None else []),
            ]
            unresolved = sorted(
                {
                    identifier
                    for identifier in identifiers
                    if not _is_node_id(identifier) and identifier not in self.aliases
                }
            )
            if unresolved:
                raise ValueError(
                    f"Node {node.node_id!r} uses unresolved aliases: "
                    + ", ".join(unresolved)
                )
        object.__setattr__(self, "aliases", _FrozenDict(self.aliases))
        return self

    @classmethod
    def from_xml(cls, data: str | bytes) -> UANodeSet:
        """Parse the supported NodeSet subset into validated Pydantic models."""

        encoded = data.encode("utf-8") if isinstance(data, str) else data
        if _DANGEROUS_XML.search(encoded):
            raise ValueError("DTD and entity declarations are not accepted.")
        parser = etree.XMLParser(
            resolve_entities=False,
            load_dtd=False,
            no_network=True,
            remove_blank_text=True,
        )
        root = etree.fromstring(encoded, parser=parser)
        name = etree.QName(root)
        if name.namespace != UA_NODESET_NS or name.localname != "UANodeSet":
            raise ValueError("Expected an OPC UA UANodeSet XML document.")

        namespace_uris = tuple(
            (uri.text or "").strip()
            for uri in root.xpath("./ua:NamespaceUris/ua:Uri", namespaces=_NS)
        )
        models = tuple(
            _model_from_element(item)
            for item in root.xpath("./ua:Models/ua:Model", namespaces=_NS)
        )
        aliases = {
            alias.get("Alias", ""): (alias.text or "").strip()
            for alias in root.xpath("./ua:Aliases/ua:Alias", namespaces=_NS)
        }
        nodes: list[UANode] = []
        supported = {"UAObject", "UAVariable", "UAObjectType", "UAVariableType"}
        for child in root:
            if not isinstance(child.tag, str) or child.get("NodeId") is None:
                continue
            local_name = etree.QName(child).localname
            if local_name not in supported:
                raise ValueError(
                    f"NodeClass {local_name!r} is outside the supported Pydantic "
                    "NodeSet subset."
                )
            nodes.append(_node_from_element(child, local_name))  # type: ignore[arg-type]
        return cls(
            namespace_uris=namespace_uris,
            models=models,
            aliases=aliases,
            nodes=tuple(nodes),
        )

    def node(self, node_id: str) -> UANode:
        """Return one node by NodeId, raising ``KeyError`` when it is absent."""

        for node in self.nodes:
            if node.node_id == node_id:
                return node
        raise KeyError(node_id)

    def resolve(self, node_id_or_alias: str) -> str:
        """Resolve an alias and leave an expanded NodeId unchanged."""

        if _is_node_id(node_id_or_alias):
            return node_id_or_alias
        try:
            return self.aliases[node_id_or_alias]
        except KeyError as exc:
            raise KeyError(f"Unknown OPC UA alias {node_id_or_alias!r}.") from exc

    def outgoing(
        self,
        source_node_id: str,
        reference_type: str | None = None,
    ) -> tuple[UAReference, ...]:
        """Return outgoing references, optionally filtered by resolved type."""

        references = self.node(source_node_id).references
        if reference_type is None:
            return references
        expected = self.resolve(reference_type)
        return tuple(
            reference
            for reference in references
            if self.resolve(reference.reference_type) == expected
        )

    def to_automationml(self) -> CAEXFile:
        """Map this typed graph to canonical AutomationML semantics."""

        from .opcua import nodeset_to_document

        return nodeset_to_document(self, prefer_embedded_source=False)

    def round_trip_automationml(
        self,
        *,
        pretty: bool = True,
        publication_date: date | datetime | str | None = None,
        mapper: Literal["python", "xslt"] = "python",
    ) -> UANodeSetRoundTripResult:
        """Run and inspect an OPC UA -> AML -> OPC UA semantic round trip."""

        from .opcua import round_trip_nodeset

        return round_trip_nodeset(
            self,
            pretty=pretty,
            publication_date=publication_date,
            mapper=mapper,
        )

    def to_etree(self) -> etree._Element:
        """Serialize this graph to a UANodeSet element tree."""

        root = etree.Element(
            _qname("UANodeSet"),
            nsmap={None: UA_NODESET_NS, "uax": UA_TYPES_NS},
        )
        if self.namespace_uris:
            namespace_uris = etree.SubElement(root, _qname("NamespaceUris"))
            for value in self.namespace_uris:
                uri = etree.SubElement(namespace_uris, _qname("Uri"))
                uri.text = value
        if self.models:
            models = etree.SubElement(root, _qname("Models"))
            for item in self.models:
                model = etree.SubElement(
                    models,
                    _qname("Model"),
                    ModelUri=item.model_uri,
                    Version=item.version,
                    PublicationDate=item.publication_date,
                )
                for required in item.required_models:
                    etree.SubElement(
                        model,
                        _qname("RequiredModel"),
                        ModelUri=required.model_uri,
                        Version=required.version,
                        PublicationDate=required.publication_date,
                    )
        if self.aliases:
            aliases = etree.SubElement(root, _qname("Aliases"))
            for name, node_id in self.aliases.items():
                alias = etree.SubElement(aliases, _qname("Alias"), Alias=name)
                alias.text = node_id
        for node in self.nodes:
            root.append(node.to_element())
        return root

    def to_xml(self, *, pretty: bool = True) -> str:
        """Serialize to a standalone UTF-8 UANodeSet XML document."""

        return etree.tostring(
            self.to_etree(),
            encoding="UTF-8",
            xml_declaration=True,
            pretty_print=pretty,
        ).decode("utf-8")


class UANodeSetBuilder:
    """Mutable, duplicate-safe builder which emits an immutable ``UANodeSet``."""

    def __init__(
        self,
        *,
        namespace_uris: tuple[str, ...] | list[str] = (),
        models: tuple[UAModel, ...] | list[UAModel] = (),
        aliases: dict[str, str] | None = None,
    ) -> None:
        self._namespace_uris = list(namespace_uris)
        self._models = list(models)
        self._aliases = dict(aliases or {})
        self._nodes: dict[str, UANode] = {}

    @property
    def namespace_uris(self) -> tuple[str, ...]:
        return tuple(self._namespace_uris)

    def add_namespace(self, uri: str) -> int:
        """Add a namespace once and return its NodeSet namespace index."""

        _validate_uri(uri, "Namespace URI")
        try:
            return self._namespace_uris.index(uri) + 1
        except ValueError:
            self._namespace_uris.append(uri)
            return len(self._namespace_uris)

    def add_model(self, model: UAModel) -> UAModel:
        if any(item.model_uri == model.model_uri for item in self._models):
            raise ValueError(f"Duplicate OPC UA ModelUri {model.model_uri!r}.")
        self._models.append(model)
        return model

    def add_node(self, node: UANode) -> UANode:
        if node.node_id in self._nodes:
            raise ValueError(f"Duplicate OPC UA NodeId {node.node_id!r}.")
        self._nodes[node.node_id] = node
        return node

    def add_reference(self, source: UANode | str, reference: UAReference) -> UANode:
        source_node_id = source.node_id if isinstance(source, UANode) else source
        try:
            current = self._nodes[source_node_id]
        except KeyError as exc:
            raise KeyError(f"Unknown source node {source_node_id!r}.") from exc
        updated = current.with_reference(reference)
        self._nodes[source_node_id] = updated
        return updated

    def add_hierarchical_reference(
        self,
        source: UANode | str,
        target: UANode | str,
        reference_type: str,
    ) -> tuple[UANode, UANode]:
        """Add a consistent local parent/child relationship in both directions."""

        source_node, target_nodes = self.add_hierarchical_references(
            source,
            (target,),
            reference_type,
        )
        return source_node, target_nodes[0]

    def add_hierarchical_references(
        self,
        source: UANode | str,
        targets: tuple[UANode | str, ...] | list[UANode | str],
        reference_type: str,
    ) -> tuple[UANode, tuple[UANode, ...]]:
        """Batch local child edges while copying the source reference tuple once."""

        source_node_id = source.node_id if isinstance(source, UANode) else source
        try:
            source_node = self._nodes[source_node_id]
        except KeyError as exc:
            raise KeyError(
                f"Unknown hierarchical reference endpoint {exc.args[0]!r}."
            ) from exc
        target_ids = tuple(
            target.node_id if isinstance(target, UANode) else target
            for target in targets
        )
        if len(target_ids) != len(set(target_ids)):
            raise ValueError("Duplicate targets in one hierarchical reference batch.")
        target_nodes: list[UANode] = []
        for target_node_id in target_ids:
            try:
                target_nodes.append(self._nodes[target_node_id])
            except KeyError as exc:
                raise KeyError(
                    f"Unknown hierarchical reference endpoint {exc.args[0]!r}."
                ) from exc

        forwards = tuple(
            UAReference(reference_type=reference_type, target=target_node_id)
            for target_node_id in target_ids
        )
        missing_forwards = tuple(
            reference
            for reference in forwards
            if reference not in source_node.references
        )
        if missing_forwards:
            source_node = UANode.model_validate(
                {
                    **source_node.model_dump(),
                    "references": (*source_node.references, *missing_forwards),
                }
            )
            self._nodes[source_node_id] = source_node

        updated_targets: list[UANode] = []
        for target_node_id, target_node in zip(
            target_ids,
            target_nodes,
            strict=True,
        ):
            supports_parent_attribute = target_node.node_class in {
                "UAObject",
                "UAVariable",
                "UAMethod",
            }
            if (
                supports_parent_attribute
                and target_node.parent_node_id not in {None, source_node_id}
            ):
                raise ValueError(
                    f"Node {target_node_id!r} already has parent "
                    f"{target_node.parent_node_id!r}."
                )
            inverse = UAReference(
                reference_type=reference_type,
                target=source_node_id,
                is_forward=False,
            )
            if inverse not in target_node.references or (
                supports_parent_attribute and target_node.parent_node_id is None
            ):
                target_payload = target_node.model_dump()
                if supports_parent_attribute:
                    target_payload["parent_node_id"] = source_node_id
                if inverse not in target_node.references:
                    target_payload["references"] = (*target_node.references, inverse)
                target_node = UANode.model_validate(target_payload)
                self._nodes[target_node_id] = target_node
            updated_targets.append(target_node)
        return source_node, tuple(updated_targets)

    def build(self) -> UANodeSet:
        """Validate and freeze the complete graph."""

        return UANodeSet(
            namespace_uris=tuple(self._namespace_uris),
            models=tuple(self._models),
            aliases=dict(self._aliases),
            nodes=tuple(self._nodes.values()),
        )


_NS = {"ua": UA_NODESET_NS}


def _model_from_element(element: etree._Element) -> UAModel:
    return UAModel(
        model_uri=element.get("ModelUri", ""),
        version=element.get("Version", ""),
        publication_date=element.get("PublicationDate", ""),
        required_models=tuple(
            UARequiredModel(
                model_uri=required.get("ModelUri", ""),
                version=required.get("Version", ""),
                publication_date=required.get("PublicationDate", ""),
            )
            for required in element.findall(_qname("RequiredModel"))
        ),
    )


def _node_from_element(element: etree._Element, node_class: NodeClass) -> UANode:
    display_name = element.find(_qname("DisplayName"))
    documentation = element.find(_qname("Documentation"))
    value_element = element.find(_qname("Value"))
    value: UAScalarValue | None = None
    if value_element is not None:
        children = list(value_element)
        if len(children) != 1 or len(children[0]):
            raise ValueError(
                f"Node {element.get('NodeId')!r} does not have one scalar Value."
            )
        value = UAScalarValue(
            type_name=etree.QName(children[0]).localname,
            value=children[0].text or "",
        )
    references = tuple(
        UAReference(
            reference_type=reference.get("ReferenceType", ""),
            target=(reference.text or "").strip(),
            is_forward=reference.get("IsForward", "true").lower() != "false",
        )
        for reference in element.xpath("./ua:References/ua:Reference", namespaces=_NS)
    )
    is_abstract_text = element.get("IsAbstract")
    return UANode(
        node_class=node_class,
        node_id=element.get("NodeId", ""),
        browse_name=element.get("BrowseName", ""),
        display_name=(
            display_name.text
            if display_name is not None and display_name.text is not None
            else element.get("BrowseName", "").split(":", 1)[-1]
        ),
        documentation=(
            documentation.text
            if documentation is not None and documentation.text is not None
            else None
        ),
        parent_node_id=element.get("ParentNodeId"),
        data_type=element.get("DataType"),
        value_rank=(
            int(element.get("ValueRank", ""))
            if element.get("ValueRank") is not None
            else None
        ),
        value=value,
        is_abstract=(
            is_abstract_text.lower() == "true"
            if is_abstract_text is not None
            else None
        ),
        references=references,
    )


def _qname(local_name: str) -> str:
    return f"{{{UA_NODESET_NS}}}{local_name}"
