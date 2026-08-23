"""Python-native AutomationML to OPC UA UANodeSet strict mapping profile.

This mapper intentionally works from the validated AutomationML Pydantic
domain model rather than walking CAEX XML.  It currently covers file metadata,
instance trees, the four CAEX libraries, attributes, interfaces, and simple
role relations.  More involved relation payloads and constraints fail closed
instead of being silently dropped.
"""

from __future__ import annotations

from hashlib import sha256
from typing import Iterable
from urllib.parse import quote
from xml.etree import ElementTree as ET

from .models import (
    AdditionalInformation,
    Attribute,
    AttributeType,
    AttributeValueRequirement,
    CAEXBasicObject,
    CAEXFile,
    CAEXObject,
    InstanceHierarchy,
    InterfaceClass,
    InterfaceClassLib,
    InterfaceFamily,
    InternalElement,
    InternalLink,
    MappingObject,
    RoleClass,
    RoleClassLib,
    RoleFamily,
    RoleRequirements,
    SourceDocumentInformation,
    SupportedRoleClass,
    SystemUnitClass,
    SystemUnitClassLib,
    SystemUnitFamily,
)
from .opcua_nodeset import (
    UAModel,
    UANode,
    UANodeSet,
    UANodeSetBuilder,
    UAReference,
    UARequiredModel,
    UAScalarValue,
)
from .opcua_mapping import (
    DEFAULT_MAPPING_PROFILE,
    UnsupportedDataTypeError,
    normalize_partner_reference,
)


PYTHON_MAPPING_VERSION = "automationml-python-bidirectional-v1"
AML_MODEL_URI = "http://opcfoundation.org/UA/AML/"
UA_MODEL_URI = "http://opcfoundation.org/UA/"
IRDI_DICTIONARY_URI = "http://opcfoundation.org/UA/Dictionary/IRDI"
URI_DICTIONARY_URI = "http://opcfoundation.org/UA/Dictionary/URI"

_ALIASES = {
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
    "HasComponent": "i=47",
    "HasProperty": "i=46",
    "Organizes": "i=35",
    "HasSubtype": "i=45",
    "HasTypeDefinition": "i=40",
    "HasDictionaryEntry": "i=17597",
    "IrdiDictionaryEntryType": "i=17598",
    "UriDictionaryEntryType": "i=17600",
    "BaseObjectType": "i=58",
    "FolderType": "i=61",
    "PropertyType": "i=68",
    "BaseDataVariableType": "i=63",
    "CAEXObjectType": "ns=2;i=1001",
    "CAEXFileType": "ns=2;i=1005",
    "AMLBaseVariableType": "ns=2;i=3001",
    "AMLConstraintVariableType": "ns=2;i=2000",
    "NominalScaledConstraint": "ns=2;i=2001",
    "OrdinalScaledConstraint": "ns=2;i=2002",
    "UnknownConstraint": "ns=2;i=2003",
    "HasAMLRoleReference": "ns=2;i=4001",
    "HasAMLInternalLink": "ns=2;i=4002",
}

class PythonMappingUnsupported(ValueError):
    """Raised when the deliberately bounded profile would otherwise lose data."""


def build_python_nodeset(
    document: CAEXFile,
    *,
    publication_date: str,
) -> UANodeSet:
    """Build a typed UANodeSet without executing XSLT."""

    return _PythonMapper(document, publication_date=publication_date).build()


class _PythonMapper:
    def __init__(self, document: CAEXFile, *, publication_date: str) -> None:
        self.document = document
        self.publication_date = f"{publication_date}T00:00:00Z"
        file_segment = quote(document.file_name, safe="-._~")
        self.model_uri = f"{AML_MODEL_URI}{file_segment}"
        self.nodeset = UANodeSetBuilder(
            namespace_uris=[self.model_uri, AML_MODEL_URI],
            aliases=dict(_ALIASES),
        )
        self._system_classes: dict[str, str] = {}
        self._interface_classes: dict[str, str] = {}
        self._role_classes: dict[str, str] = {}
        self._attribute_types: dict[str, str] = {}
        self._interfaces_by_partner: dict[str, UANode] = {}
        self._deferred_internal_links: list[tuple[str, InternalLink, str]] = []
        self._external_aliases = {
            reference.file_alias: reference.path
            for reference in document.external_references
        }
        if len(self._external_aliases) != len(document.external_references):
            raise PythonMappingUnsupported(
                "ExternalReference aliases must be unique in the strict profile."
            )
        self._external_class_proxies: dict[tuple[str, str], str] = {}
        self._dictionary_entries: dict[tuple[str, str], str] = {}
        self._index_classes()

    def build(self) -> UANodeSet:
        self._reject_file_features_outside_mvp()
        version = self.document.version.value if self.document.version else "0.0.0"
        self.nodeset.add_model(
            UAModel(
                model_uri=self.model_uri,
                version=version or "0.0.0",
                publication_date=self.publication_date,
                required_models=[
                    UARequiredModel(
                        model_uri=UA_MODEL_URI,
                        version="1.04.3",
                        publication_date="2019-09-09T00:00:00Z",
                    ),
                    UARequiredModel(
                        model_uri=AML_MODEL_URI,
                        version="1.00",
                        publication_date="2026-06-25T00:00:00Z",
                    ),
                ],
            )
        )

        file_id = "ns=1;s=CAEXFile"
        file_node = self._add_node(
            UANode(
                node_class="UAObject",
                node_id=file_id,
                parent_node_id="i=85",
                browse_name="1:CAEXFile",
                display_name=self.document.file_name,
                documentation=(
                    self.document.description.value
                    if self.document.description is not None
                    else None
                ),
                references=[
                    self._reference("HasTypeDefinition", "CAEXFileType"),
                    self._reference("Organizes", "i=85", is_forward=False),
                ],
            )
        )
        self._add_property(
            file_node,
            "FileName",
            self.document.file_name,
            key="file/file-name",
            type_definition="AMLBaseVariableType",
        )
        self._add_property(
            file_node,
            "SchemaVersion",
            self.document.schema_version,
            key="file/schema-version",
            type_definition="AMLBaseVariableType",
        )
        self._add_change_mode(file_node, self.document, "file")
        for position, value in enumerate(
            self.document.superior_standard_versions,
            start=1,
        ):
            self._add_property(
                file_node,
                f"SuperiorStandardVersion_{position}",
                value,
                key=f"file/superior-standard-version/{position}",
                type_definition="AMLBaseVariableType",
            )
        for position, source in enumerate(
            self.document.source_document_information,
            start=1,
        ):
            self._add_property(
                file_node,
                f"SourceDocumentInformation_{position}",
                _source_document_xml(source),
                key=f"file/source-document/{position}",
                type_definition="AMLBaseVariableType",
            )
        for position, information in enumerate(
            self.document.additional_information,
            start=1,
        ):
            self._add_property(
                file_node,
                f"AdditionalInformation_{position}",
                _additional_information_xml(information),
                key=f"file/additional-information/{position}",
                type_definition="AMLBaseVariableType",
                node_id=f"ns=1;s=CAEXFile_AdditionalInformation_{position}",
            )
        for position, external in enumerate(
            self.document.external_references,
            start=1,
        ):
            self._add_property(
                file_node,
                f"AMLExternalReferenceAlias_{position}",
                external.file_alias,
                key=f"file/external-reference/{position}/alias",
            )
            self._add_property(
                file_node,
                f"AMLExternalReferencePath_{position}",
                external.path,
                key=f"file/external-reference/{position}/path",
            )

        self._build_instance_hierarchies(file_node)
        self._build_interface_libraries(file_node)
        self._build_role_libraries(file_node)
        self._build_system_unit_libraries(file_node)
        self._build_attribute_type_libraries(file_node)
        self._resolve_internal_links()
        return self.nodeset.build()

    def _reject_file_features_outside_mvp(self) -> None:
        unsupported: list[str] = []
        if self.document.revision:
            unsupported.append("CAEXFile Revision")
        if self.document.copyright is not None:
            unsupported.append("CAEXFile Copyright")
        if self.document.source_object_information:
            unsupported.append("CAEXFile SourceObjectInformation")
        if any(
            information.aml_version is not None
            or information.document_versions is not None
            or bool(information.model_extra)
            for information in self.document.additional_information
        ):
            unsupported.append("structured CAEXFile AdditionalInformation")
        if unsupported:
            raise PythonMappingUnsupported(
                "Python OPC UA strict profile does not yet support "
                + ", ".join(unsupported)
                + "."
            )

    def _index_classes(self) -> None:
        for library in self.document.system_unit_class_libs:
            self._index_class_tree(
                library.name,
                library.system_unit_classes,
                self._system_classes,
                "system-class",
                lambda item: item.system_unit_classes,
            )
        for library in self.document.interface_class_libs:
            self._index_class_tree(
                library.name,
                library.interface_classes,
                self._interface_classes,
                "interface-class",
                lambda item: item.interface_classes,
            )
        for library in self.document.role_class_libs:
            self._index_class_tree(
                library.name,
                library.role_classes,
                self._role_classes,
                "role-class",
                lambda item: item.role_classes,
            )
        for library in self.document.attribute_type_libs:
            self._index_class_tree(
                library.name,
                library.attribute_types,
                self._attribute_types,
                "attribute-type",
                lambda item: item.attribute_types,
            )

    def _index_class_tree(
        self,
        prefix: str,
        items: Iterable[CAEXObject],
        target: dict[str, str],
        kind: str,
        children,
    ) -> None:
        for position, item in enumerate(items, start=1):
            path = f"{prefix}/{item.name}"
            if path in target:
                raise PythonMappingUnsupported(
                    f"Duplicate AML class path {path!r} cannot become one NodeId."
                )
            target[path] = self._node_id(kind, f"{path}#{position}")
            self._index_class_tree(path, children(item), target, kind, children)

    def _build_instance_hierarchies(self, file_node: UANode) -> None:
        if not self.document.instance_hierarchies:
            return
        collection = self._add_folder(
            "InstanceHierarchies",
            "collection/instance-hierarchies",
        )
        self._add_reference(file_node, self._reference("Organizes", collection.node_id))
        for position, hierarchy in enumerate(
            self.document.instance_hierarchies,
            start=1,
        ):
            key = f"instance-hierarchy/{position}/{hierarchy.name}"
            node = self._add_object(
                hierarchy,
                key,
                type_definition="FolderType",
            )
            self._add_reference(collection, self._reference("Organizes", node.node_id))
            children: list[UANode] = []
            for child_position, element in enumerate(
                hierarchy.internal_elements,
                start=1,
            ):
                child = self._build_internal_element(
                    element,
                    f"{key}/internal-element/{child_position}/{element.name}",
                )
                children.append(child)
            self._add_hierarchical_references(node, "HasComponent", children)

    def _build_internal_element(self, element: InternalElement, key: str) -> UANode:
        if element.supported_role_classes:
            raise PythonMappingUnsupported(
                "SupportedRoleClass on an InternalElement is ambiguous in the "
                "implicit role profile; only RoleRequirements is supported."
            )
        type_definition = "CAEXObjectType"
        unresolved_type_path: str | None = None
        if element.ref_base_system_unit_path:
            resolved = self._system_classes.get(element.ref_base_system_unit_path)
            if resolved is not None:
                type_definition = resolved
            elif "@" in element.ref_base_system_unit_path:
                type_definition = self._external_class_target(
                    element.ref_base_system_unit_path,
                    "system",
                )
            else:
                unresolved_type_path = element.ref_base_system_unit_path
        node = self._add_object(element, key, type_definition=type_definition)
        if unresolved_type_path is not None:
            self._add_property(
                node,
                "AMLRefBaseSystemUnitPath",
                unresolved_type_path,
                key=f"{key}/ref-base-system-unit-path",
            )
        self._add_attributes(node, element.attributes, key)
        self._add_external_interfaces(
            node,
            element.external_interfaces,
            key,
            partner_owner_id=element.id,
        )
        self._defer_internal_links(element, key)
        for position, requirement in enumerate(element.role_requirements, start=1):
            self._add_role_requirement(node, requirement, f"{key}/role/{position}")
        for position, child_element in enumerate(element.internal_elements, start=1):
            child = self._build_internal_element(
                child_element,
                f"{key}/internal-element/{position}/{child_element.name}",
            )
            self._add_reference(node, self._reference("HasComponent", child.node_id))
        return node

    def _build_interface_libraries(self, file_node: UANode) -> None:
        if not self.document.interface_class_libs:
            return
        collection = self._add_folder(
            "InterfaceClassLibs",
            "collection/interface-class-libs",
        )
        self._add_reference(file_node, self._reference("Organizes", collection.node_id))
        for position, library in enumerate(self.document.interface_class_libs, start=1):
            key = f"interface-library/{position}/{library.name}"
            library_node = self._add_library(library, key)
            self._add_reference(
                collection, self._reference("Organizes", library_node.node_id)
            )
            self._build_interface_classes(
                library_node,
                library,
                library.interface_classes,
                library.name,
                key,
            )

    def _build_interface_classes(
        self,
        parent: UANode,
        library: InterfaceClassLib,
        classes: Iterable[InterfaceFamily],
        path_prefix: str,
        key_prefix: str,
    ) -> None:
        for position, item in enumerate(classes, start=1):
            path = f"{path_prefix}/{item.name}"
            key = f"{key_prefix}/class/{position}/{item.name}"
            node = self._add_class_node(
                item,
                key,
                node_id=self._interface_classes[path],
                base_path=item.ref_base_class_path,
                base_index=self._interface_classes,
                default_base="BaseObjectType",
                proxy_kind="interface",
            )
            self._add_reference(parent, self._reference("Organizes", node.node_id))
            self._add_attributes(node, item.attributes, key)
            self._add_external_interfaces(node, item.external_interfaces, key)
            self._build_interface_classes(
                node,
                library,
                item.interface_classes,
                path,
                key,
            )

    def _build_role_libraries(self, file_node: UANode) -> None:
        if not self.document.role_class_libs:
            return
        collection = self._add_folder("RoleClassLibs", "collection/role-class-libs")
        self._add_reference(file_node, self._reference("Organizes", collection.node_id))
        for position, library in enumerate(self.document.role_class_libs, start=1):
            key = f"role-library/{position}/{library.name}"
            library_node = self._add_library(library, key)
            self._add_reference(
                collection, self._reference("Organizes", library_node.node_id)
            )
            self._build_role_classes(
                library_node,
                library,
                library.role_classes,
                library.name,
                key,
            )

    def _build_role_classes(
        self,
        parent: UANode,
        library: RoleClassLib,
        classes: Iterable[RoleFamily],
        path_prefix: str,
        key_prefix: str,
    ) -> None:
        for position, item in enumerate(classes, start=1):
            path = f"{path_prefix}/{item.name}"
            key = f"{key_prefix}/class/{position}/{item.name}"
            node = self._add_class_node(
                item,
                key,
                node_id=self._role_classes[path],
                base_path=item.ref_base_class_path,
                base_index=self._role_classes,
                default_base="BaseObjectType",
                proxy_kind="role",
            )
            self._add_reference(parent, self._reference("Organizes", node.node_id))
            self._add_attributes(node, item.attributes, key)
            self._add_external_interfaces(node, item.external_interfaces, key)
            self._build_role_classes(
                node,
                library,
                item.role_classes,
                path,
                key,
            )

    def _build_system_unit_libraries(self, file_node: UANode) -> None:
        if not self.document.system_unit_class_libs:
            return
        collection = self._add_folder(
            "SystemUnitClassLibs",
            "collection/system-unit-class-libs",
        )
        self._add_reference(file_node, self._reference("Organizes", collection.node_id))
        for position, library in enumerate(
            self.document.system_unit_class_libs,
            start=1,
        ):
            key = f"system-unit-library/{position}/{library.name}"
            library_node = self._add_library(library, key)
            self._add_reference(
                collection, self._reference("Organizes", library_node.node_id)
            )
            self._build_system_unit_classes(
                library_node,
                library,
                library.system_unit_classes,
                library.name,
                key,
            )

    def _build_system_unit_classes(
        self,
        parent: UANode,
        library: SystemUnitClassLib,
        classes: Iterable[SystemUnitFamily],
        path_prefix: str,
        key_prefix: str,
    ) -> None:
        for position, item in enumerate(classes, start=1):
            path = f"{path_prefix}/{item.name}"
            key = f"{key_prefix}/class/{position}/{item.name}"
            node = self._add_class_node(
                item,
                key,
                node_id=self._system_classes[path],
                base_path=item.ref_base_class_path,
                base_index=self._system_classes,
                default_base="CAEXObjectType",
                proxy_kind="system",
            )
            self._add_reference(parent, self._reference("Organizes", node.node_id))
            self._add_attributes(node, item.attributes, key)
            self._add_external_interfaces(
                node,
                item.external_interfaces,
                key,
                partner_owner_id=item.id,
            )
            self._defer_internal_links(item, key)
            for role_position, role in enumerate(
                item.supported_role_classes,
                start=1,
            ):
                self._add_supported_role(
                    node,
                    role,
                    f"{key}/supported-role/{role_position}",
                )
            for child_position, element in enumerate(item.internal_elements, start=1):
                child = self._build_internal_element(
                    element,
                    f"{key}/internal-element/{child_position}/{element.name}",
                )
                self._add_reference(node, self._reference("HasComponent", child.node_id))
            self._build_system_unit_classes(
                node,
                library,
                item.system_unit_classes,
                path,
                key,
            )

    def _build_attribute_type_libraries(self, file_node: UANode) -> None:
        if not self.document.attribute_type_libs:
            return
        collection = self._add_folder(
            "AttributeTypeLibs",
            "collection/attribute-type-libs",
        )
        self._add_reference(file_node, self._reference("Organizes", collection.node_id))
        for position, library in enumerate(self.document.attribute_type_libs, start=1):
            key = f"attribute-type-library/{position}/{library.name}"
            library_node = self._add_library(library, key)
            self._add_reference(
                collection, self._reference("Organizes", library_node.node_id)
            )
            self._build_attribute_types(
                library_node,
                library.attribute_types,
                library.name,
                key,
            )

    def _build_attribute_types(
        self,
        parent: UANode,
        attribute_types: Iterable[AttributeType],
        path_prefix: str,
        key_prefix: str,
    ) -> None:
        for position, item in enumerate(attribute_types, start=1):
            path = f"{path_prefix}/{item.name}"
            key = f"{key_prefix}/type/{position}/{item.name}"
            data_type, scalar_type = self._data_type(item.attribute_data_type)
            base_target = "AMLBaseVariableType"
            unresolved_attribute_type: str | None = None
            if item.ref_attribute_type:
                resolved = self._attribute_types.get(item.ref_attribute_type)
                if resolved is not None:
                    base_target = resolved
                else:
                    unresolved_attribute_type = item.ref_attribute_type
            references = [
                self._reference("HasSubtype", base_target, is_forward=False)
            ]
            node = self._add_node(
                UANode(
                    node_class="UAVariableType",
                    node_id=self._attribute_types[path],
                    browse_name=f"1:{item.name}",
                    display_name=item.name,
                    documentation=(item.description.value if item.description else None),
                    data_type=data_type,
                    value_rank=-1,
                    value=(
                        UAScalarValue(type_name=scalar_type, value=item.value)
                        if item.value is not None
                        else None
                    ),
                    is_abstract=False,
                    references=references,
                )
            )
            self._add_reference(parent, self._reference("Organizes", node.node_id))
            self._add_common_header_properties(node, item, key)
            self._add_attribute_metadata(node, item, key, data_type, scalar_type)
            self._add_constraints(
                node,
                item.constraint,
                key,
                data_type,
                scalar_type,
            )
            if unresolved_attribute_type is not None:
                self._add_property(
                    node,
                    "AMLRefAttributeType",
                    unresolved_attribute_type,
                    key=f"{key}/ref-attribute-type",
                )
            self._add_attributes(node, item.attributes, key)
            self._build_attribute_types(
                node,
                item.attribute_types,
                path,
                key,
            )

    def _add_attributes(
        self,
        owner: UANode,
        attributes: Iterable[Attribute],
        key_prefix: str,
    ) -> None:
        for position, attribute in enumerate(attributes, start=1):
            key = f"{key_prefix}/attribute/{position}/{attribute.name}"
            node = self._build_attribute(attribute, key)
            self._add_reference(owner, self._reference("HasComponent", node.node_id))

    def _build_attribute(self, attribute: Attribute, key: str) -> UANode:
        data_type, scalar_type = self._data_type(attribute.attribute_data_type)
        type_definition = "AMLBaseVariableType"
        unresolved_attribute_type: str | None = None
        if attribute.ref_attribute_type:
            resolved = self._attribute_types.get(attribute.ref_attribute_type)
            if resolved is not None:
                type_definition = resolved
            else:
                unresolved_attribute_type = attribute.ref_attribute_type
        node = self._add_node(
            UANode(
                node_class="UAVariable",
                node_id=self._node_id("attribute", key),
                browse_name=f"1:{attribute.name}",
                display_name=attribute.name,
                documentation=(
                    attribute.description.value
                    if attribute.description is not None
                    else None
                ),
                data_type=data_type,
                value=(
                    UAScalarValue(type_name=scalar_type, value=attribute.value)
                    if attribute.value is not None
                    else None
                ),
                references=[
                    self._reference("HasTypeDefinition", type_definition),
                ],
            )
        )
        self._add_common_header_properties(node, attribute, key)
        self._add_attribute_metadata(node, attribute, key, data_type, scalar_type)
        self._add_constraints(
            node,
            attribute.constraint,
            key,
            data_type,
            scalar_type,
        )
        if unresolved_attribute_type is not None:
            self._add_property(
                node,
                "AMLRefAttributeType",
                unresolved_attribute_type,
                key=f"{key}/ref-attribute-type",
            )
        self._add_attributes(node, attribute.attributes, key)
        return node

    def _add_attribute_metadata(
        self,
        node: UANode,
        attribute: Attribute,
        key: str,
        data_type: str,
        scalar_type: str,
    ) -> None:
        if attribute.default_value is not None:
            self._add_property(
                node,
                DEFAULT_MAPPING_PROFILE.default_value_property,
                attribute.default_value,
                key=f"{key}/default-value",
                data_type=data_type,
                scalar_type=scalar_type,
            )
        if attribute.unit is not None:
            self._add_property(
                node,
                DEFAULT_MAPPING_PROFILE.unit_property,
                attribute.unit,
                key=f"{key}/unit",
            )
        for position, semantic in enumerate(attribute.ref_semantic, start=1):
            semantic_value = semantic.corresponding_attribute_path
            projection = _dictionary_projection(semantic_value)
            if projection is None:
                self._add_property(
                    node,
                    f"RefSemantic_{position}",
                    semantic_value,
                    key=f"{key}/ref-semantic/{position}",
                )
            else:
                namespace_uri, identifier = projection
                target = self._add_dictionary_entry(namespace_uri, identifier)
                self._add_reference(
                    node,
                    self._reference(
                        "HasDictionaryEntry",
                        target,
                    ),
                )

    def _add_dictionary_entry(self, namespace_uri: str, identifier: str) -> str:
        """Materialize the Part 19 Object required by HasDictionaryEntry."""

        key = (namespace_uri, identifier)
        existing = self._dictionary_entries.get(key)
        if existing is not None:
            return existing
        namespace_index = self._namespace_index(namespace_uri)
        node_id = f"ns={namespace_index};s={identifier}"
        type_definition = (
            "IrdiDictionaryEntryType"
            if namespace_uri == IRDI_DICTIONARY_URI
            else "UriDictionaryEntryType"
        )
        self._add_node(
            UANode(
                node_class="UAObject",
                node_id=node_id,
                parent_node_id="i=17594",
                browse_name=f"{namespace_index}:{identifier}",
                display_name=identifier,
                references=[
                    self._reference("HasTypeDefinition", type_definition),
                    self._reference("HasComponent", "i=17594", is_forward=False),
                ],
            )
        )
        self._dictionary_entries[key] = node_id
        return node_id

    def _add_constraints(
        self,
        owner: UANode,
        constraints: Iterable[AttributeValueRequirement],
        key_prefix: str,
        data_type: str,
        scalar_type: str,
    ) -> None:
        for position, constraint in enumerate(constraints, start=1):
            shapes = [
                constraint.nominal_scaled_type,
                constraint.ordinal_scaled_type,
                constraint.unknown_type,
            ]
            if sum(shape is not None for shape in shapes) != 1:
                raise PythonMappingUnsupported(
                    f"Constraint {constraint.name!r} must select exactly one "
                    "nominal, ordinal, or unknown shape."
                )
            key = f"{key_prefix}/constraint/{position}/{constraint.name}"
            value: UAScalarValue | None = None
            constraint_data_type = data_type
            if constraint.nominal_scaled_type is not None:
                type_definition = "NominalScaledConstraint"
            elif constraint.ordinal_scaled_type is not None:
                type_definition = "OrdinalScaledConstraint"
            else:
                type_definition = "UnknownConstraint"
                constraint_data_type = "String"
                requirements = constraint.unknown_type.requirements
                if requirements is not None:
                    value = UAScalarValue(type_name="String", value=requirements)
            constraint_node = self._add_node(
                UANode(
                    node_class="UAVariable",
                    node_id=self._node_id("constraint", key),
                    browse_name=f"1:{constraint.name}",
                    display_name=constraint.name,
                    documentation=(
                        constraint.description.value
                        if constraint.description is not None
                        else None
                    ),
                    data_type=constraint_data_type,
                    value=value,
                    references=[
                        self._reference("HasTypeDefinition", type_definition)
                    ],
                )
            )
            self._add_common_header_properties(constraint_node, constraint, key)
            self._add_reference(
                owner,
                self._reference("HasComponent", constraint_node.node_id),
            )
            if constraint.nominal_scaled_type is not None:
                required_values = constraint.nominal_scaled_type.required_values
                if len(required_values) != len(set(required_values)):
                    raise PythonMappingUnsupported(
                        f"Nominal Constraint {constraint.name!r} repeats a "
                        "RequiredValue; the strict graph treats these as a set."
                    )
                for required_value in sorted(required_values):
                    self._add_constraint_component(
                        constraint_node,
                        "RequiredValue",
                        required_value,
                        key=f"{key}/required-value/{sha256(required_value.encode()).hexdigest()[:12]}",
                        data_type=data_type,
                        scalar_type=scalar_type,
                    )
            elif constraint.ordinal_scaled_type is not None:
                ordinal = constraint.ordinal_scaled_type
                for component_name, component_value in (
                    ("RequiredMinValue", ordinal.required_min_value),
                    ("RequiredValue", ordinal.required_value),
                    ("RequiredMaxValue", ordinal.required_max_value),
                ):
                    if component_value is not None:
                        self._add_constraint_component(
                            constraint_node,
                            component_name,
                            component_value,
                            key=f"{key}/{component_name}",
                            data_type=data_type,
                            scalar_type=scalar_type,
                        )

    def _add_constraint_component(
        self,
        owner: UANode,
        name: str,
        value: str,
        *,
        key: str,
        data_type: str,
        scalar_type: str,
    ) -> None:
        component = self._add_node(
            UANode(
                node_class="UAVariable",
                node_id=self._node_id("constraint-value", key),
                browse_name=f"1:{name}",
                display_name=name,
                data_type=data_type,
                value=UAScalarValue(type_name=scalar_type, value=value),
                references=[
                    self._reference("HasTypeDefinition", "BaseDataVariableType")
                ],
            )
        )
        self._add_reference(owner, self._reference("HasComponent", component.node_id))

    def _add_external_interfaces(
        self,
        owner: UANode,
        interfaces: Iterable[InterfaceClass],
        key_prefix: str,
        *,
        partner_owner_id: str | None = None,
    ) -> None:
        for position, interface in enumerate(interfaces, start=1):
            key = f"{key_prefix}/external-interface/{position}/{interface.name}"
            type_definition = None
            unresolved_path = interface.ref_base_class_path
            if interface.ref_base_class_path:
                type_definition = self._interface_classes.get(
                    interface.ref_base_class_path
                )
                if type_definition is not None:
                    unresolved_path = None
                elif "@" in interface.ref_base_class_path:
                    type_definition = self._external_class_target(
                        interface.ref_base_class_path,
                        "interface",
                    )
                    unresolved_path = None
            node = self._add_object(
                interface,
                key,
                type_definition=type_definition,
            )
            if unresolved_path is not None:
                self._add_property(
                    node,
                    "AMLRefBaseClassPath",
                    unresolved_path,
                    key=f"{key}/ref-base-class-path",
                )
            self._add_reference(owner, self._reference("HasComponent", node.node_id))
            self._register_interface_partner(
                interface,
                node,
                partner_owner_id=partner_owner_id,
            )
            self._add_attributes(node, interface.attributes, key)
            self._add_external_interfaces(
                node,
                interface.external_interfaces,
                key,
                partner_owner_id=partner_owner_id,
            )

    def _register_interface_partner(
        self,
        interface: InterfaceClass,
        node: UANode,
        *,
        partner_owner_id: str | None,
    ) -> None:
        partner_keys: set[str] = set()
        if interface.id:
            partner_keys.add(normalize_partner_reference(interface.id))
        if partner_owner_id:
            partner_keys.add(
                normalize_partner_reference(
                    f"{partner_owner_id}:{interface.name}"
                )
            )
        for partner_key in partner_keys:
            existing = self._interfaces_by_partner.get(partner_key)
            if existing is not None and existing.node_id != node.node_id:
                raise PythonMappingUnsupported(
                    f"AML partner reference {partner_key!r} resolves to more "
                    "than one ExternalInterface."
                )
            self._interfaces_by_partner[partner_key] = node

    def _defer_internal_links(self, item: SystemUnitClass, key: str) -> None:
        if not item.internal_links:
            return
        if not item.id:
            raise PythonMappingUnsupported(
                f"InternalLink owner {item.name!r} needs an AML ID so strict "
                "PartnerA ownership can be reconstructed."
            )
        owner_id = normalize_partner_reference(item.id)
        for position, link in enumerate(item.internal_links, start=1):
            self._assert_relation_header_is_empty(link, "InternalLink")
            partner_a = normalize_partner_reference(link.ref_partner_side_a)
            if ":" in partner_a and partner_a.split(":", 1)[0] != owner_id:
                raise PythonMappingUnsupported(
                    f"InternalLink {link.name!r} is stored on {item.name!r}, "
                    "but PartnerA is owned by another InternalElement."
                )
            self._deferred_internal_links.append(
                (owner_id, link, f"{key}/internal-link/{position}")
            )

    def _resolve_internal_links(self) -> None:
        seen_edges: set[tuple[str, str]] = set()
        for _owner_id, link, _key in self._deferred_internal_links:
            partner_a = normalize_partner_reference(link.ref_partner_side_a)
            partner_b = normalize_partner_reference(link.ref_partner_side_b)
            source = self._interfaces_by_partner.get(partner_a)
            target = self._interfaces_by_partner.get(partner_b)
            if source is None or target is None:
                missing = partner_a if source is None else partner_b
                raise PythonMappingUnsupported(
                    f"InternalLink {link.name!r} references unknown partner "
                    f"{missing!r}."
                )
            edge = (source.node_id, target.node_id)
            if edge in seen_edges:
                raise PythonMappingUnsupported(
                    "Parallel AML InternalLinks between the same directed "
                    "ExternalInterfaces cannot be represented by one native edge."
                )
            seen_edges.add(edge)
            self._add_reference(
                source,
                self._reference("HasAMLInternalLink", target.node_id),
            )

    def _add_role_requirement(
        self,
        owner: UANode,
        requirement: RoleRequirements,
        key: str,
    ) -> None:
        target = self._role_classes.get(requirement.ref_base_role_class_path)
        if target is None:
            target = self._external_class_target(
                requirement.ref_base_role_class_path,
                "role",
            )
        rule = DEFAULT_MAPPING_PROFILE.role_rule(
            "InternalElement", "RoleRequirements"
        )
        if (
            requirement.attributes
            or requirement.external_interfaces
            or requirement.mapping_object is not None
            or self._has_relation_header(requirement)
        ):
            self._add_role_relationship_node(
                owner,
                requirement,
                target,
                key,
                relationship="RoleRequirements",
                reference_type=rule.reference_type,
            )
        else:
            self._add_reference(owner, self._reference(rule.reference_type, target))

    def _add_supported_role(
        self,
        owner: UANode,
        role: SupportedRoleClass,
        key: str,
    ) -> None:
        target = self._role_classes.get(role.ref_role_class_path)
        if target is None:
            target = self._external_class_target(
                role.ref_role_class_path,
                "role",
            )
        rule = DEFAULT_MAPPING_PROFILE.role_rule(
            "SystemUnitClass", "SupportedRoleClass"
        )
        if role.mapping_object is not None or self._has_relation_header(role):
            self._add_role_relationship_node(
                owner,
                role,
                target,
                key,
                relationship="SupportedRoleClass",
                reference_type=rule.reference_type,
            )
        else:
            self._add_reference(owner, self._reference(rule.reference_type, target))

    def _add_role_relationship_node(
        self,
        owner: UANode,
        relation: RoleRequirements | SupportedRoleClass,
        target: str,
        key: str,
        *,
        relationship: str,
        reference_type: str,
    ) -> None:
        node = self._add_node(
            UANode(
                node_class="UAObject",
                node_id=self._node_id("role-relationship", key),
                browse_name=f"1:{relationship}",
                display_name=relationship,
                documentation=(
                    relation.description.value
                    if relation.description is not None
                    else None
                ),
                references=[
                    self._reference("HasTypeDefinition", "BaseObjectType"),
                    self._reference(reference_type, target),
                ],
            )
        )
        self._add_reference(owner, self._reference("HasComponent", node.node_id))
        self._add_common_header_properties(node, relation, key)
        if isinstance(relation, RoleRequirements):
            self._add_attributes(node, relation.attributes, key)
            self._add_external_interfaces(node, relation.external_interfaces, key)
        if relation.mapping_object is not None:
            self._add_mapping_object(node, relation.mapping_object, key)

    def _add_mapping_object(
        self,
        owner: UANode,
        mapping: MappingObject,
        key_prefix: str,
    ) -> None:
        self._assert_relation_header_is_empty(mapping, "MappingObject")
        host_key = f"{key_prefix}/mapping-object"
        host = self._add_node(
            UANode(
                node_class="UAObject",
                node_id=self._node_id("mapping-object", host_key),
                browse_name="1:MappingObject",
                display_name="MappingObject",
                references=[self._reference("HasTypeDefinition", "BaseObjectType")],
            )
        )
        self._add_reference(owner, self._reference("HasComponent", host.node_id))

        attribute_pairs = sorted(
            mapping.attribute_name_mapping,
            key=lambda item: (
                item.system_unit_attribute_name,
                item.role_attribute_name,
            ),
        )
        if len(attribute_pairs) != len(
            {
                (item.system_unit_attribute_name, item.role_attribute_name)
                for item in attribute_pairs
            }
        ):
            raise PythonMappingUnsupported(
                "MappingObject repeats an AttributeNameMapping pair."
            )
        for position, pair in enumerate(attribute_pairs, start=1):
            self._assert_relation_header_is_empty(
                pair,
                "AttributeNameMapping",
            )
            pair_node = self._add_mapping_pair(
                host,
                "AttributeNameMapping",
                f"{host_key}/attribute/{position}",
            )
            self._add_property(
                pair_node,
                "SystemUnitAttributeName",
                pair.system_unit_attribute_name,
                key=f"{host_key}/attribute/{position}/system-unit",
            )
            self._add_property(
                pair_node,
                "RoleAttributeName",
                pair.role_attribute_name,
                key=f"{host_key}/attribute/{position}/role",
            )

        interface_pairs = sorted(
            mapping.interface_id_mapping,
            key=lambda item: (
                item.system_unit_interface_id,
                item.role_interface_id,
            ),
        )
        if len(interface_pairs) != len(
            {
                (item.system_unit_interface_id, item.role_interface_id)
                for item in interface_pairs
            }
        ):
            raise PythonMappingUnsupported(
                "MappingObject repeats an InterfaceIDMapping pair."
            )
        for position, pair in enumerate(interface_pairs, start=1):
            self._assert_relation_header_is_empty(pair, "InterfaceIDMapping")
            pair_node = self._add_mapping_pair(
                host,
                "InterfaceIDMapping",
                f"{host_key}/interface/{position}",
            )
            self._add_property(
                pair_node,
                "SystemUnitInterfaceID",
                pair.system_unit_interface_id,
                key=f"{host_key}/interface/{position}/system-unit",
            )
            self._add_property(
                pair_node,
                "RoleInterfaceID",
                pair.role_interface_id,
                key=f"{host_key}/interface/{position}/role",
            )

    def _add_mapping_pair(
        self,
        owner: UANode,
        name: str,
        key: str,
    ) -> UANode:
        pair = self._add_node(
            UANode(
                node_class="UAObject",
                node_id=self._node_id("mapping-pair", key),
                browse_name=f"1:{name}",
                display_name=name,
                references=[self._reference("HasTypeDefinition", "BaseObjectType")],
            )
        )
        self._add_reference(owner, self._reference("HasComponent", pair.node_id))
        return pair

    def _external_class_target(self, path: str, kind: str) -> str:
        alias, separator, external_path = path.partition("@")
        if not separator or not alias or not external_path:
            raise PythonMappingUnsupported(
                f"Class target {path!r} is not present in this AML document and "
                "does not use an ExternalReference alias."
            )
        if alias not in self._external_aliases:
            raise PythonMappingUnsupported(
                f"Class target {path!r} uses unknown ExternalReference alias "
                f"{alias!r}."
            )
        proxy_key = (kind, path)
        existing = self._external_class_proxies.get(proxy_key)
        if existing is not None:
            return existing
        default_base = {
            "interface": "BaseObjectType",
            "role": "BaseObjectType",
            "system": "CAEXObjectType",
        }.get(kind)
        if default_base is None:
            raise PythonMappingUnsupported(
                f"Unsupported external class proxy kind {kind!r}."
            )
        node_id = self._node_id(f"external-{kind}-class", path)
        proxy = self._add_node(
            UANode(
                node_class="UAObjectType",
                node_id=node_id,
                browse_name=f"1:{external_path.rsplit('/', 1)[-1]}",
                display_name=external_path.rsplit("/", 1)[-1],
                is_abstract=False,
                references=[
                    self._reference("HasSubtype", default_base, is_forward=False)
                ],
            )
        )
        self._add_property(
            proxy,
            "AMLExternalClassPath",
            path,
            key=f"external-class/{kind}/{path}",
        )
        self._external_class_proxies[proxy_key] = node_id
        return node_id

    def _add_class_node(
        self,
        item: CAEXObject,
        key: str,
        *,
        node_id: str,
        base_path: str | None,
        base_index: dict[str, str],
        default_base: str,
        proxy_kind: str,
    ) -> UANode:
        base_target = default_base
        unresolved_path: str | None = None
        if base_path:
            resolved = base_index.get(base_path)
            if resolved is not None:
                base_target = resolved
            elif "@" in base_path:
                base_target = self._external_class_target(base_path, proxy_kind)
            else:
                unresolved_path = base_path
        node = self._add_node(
            UANode(
                node_class="UAObjectType",
                node_id=node_id,
                browse_name=f"1:{item.name}",
                display_name=item.name,
                documentation=(item.description.value if item.description else None),
                is_abstract=False,
                references=[
                    self._reference("HasSubtype", base_target, is_forward=False)
                ],
            )
        )
        self._add_common_header_properties(node, item, key)
        if unresolved_path is not None:
            self._add_property(
                node,
                "AMLRefBaseClassPath",
                unresolved_path,
                key=f"{key}/ref-base-class-path",
            )
        return node

    def _add_library(self, library: CAEXObject, key: str) -> UANode:
        return self._add_object(library, key, type_definition="FolderType")

    def _add_folder(self, name: str, key: str) -> UANode:
        return self._add_node(
            UANode(
                node_class="UAObject",
                node_id=self._node_id("folder", key),
                browse_name=f"1:{name}",
                display_name=name,
                references=[self._reference("HasTypeDefinition", "FolderType")],
            )
        )

    def _add_object(
        self,
        item: CAEXObject,
        key: str,
        *,
        type_definition: str | None,
    ) -> UANode:
        references = (
            [self._reference("HasTypeDefinition", type_definition)]
            if type_definition is not None
            else []
        )
        node = self._add_node(
            UANode(
                node_class="UAObject",
                node_id=self._node_id("object", key),
                browse_name=f"1:{item.name}",
                display_name=item.name,
                documentation=(item.description.value if item.description else None),
                references=references,
            )
        )
        self._add_common_header_properties(node, item, key)
        return node

    def _add_common_header_properties(
        self,
        node: UANode,
        item: CAEXBasicObject,
        key: str,
    ) -> None:
        unsupported: list[str] = []
        if item.revision:
            unsupported.append("Revision")
        if item.copyright is not None:
            unsupported.append("Copyright")
        if item.additional_information:
            unsupported.append("AdditionalInformation")
        if item.source_object_information:
            unsupported.append("SourceObjectInformation")
        if unsupported:
            raise PythonMappingUnsupported(
                f"Python OPC UA strict profile does not yet support "
                f"{', '.join(unsupported)} on {node.display_name!r}."
            )
        if isinstance(item, CAEXObject) and item.id:
            projected_id = (
                item.id if item.id.startswith("{") else f"{{{item.id}}}"
            )
            self._add_property(
                node,
                "AML_ID",
                projected_id,
                key=f"{key}/id",
                type_definition="AMLBaseVariableType",
            )
        if item.version is not None:
            self._add_property(
                node,
                "Version",
                item.version.value,
                key=f"{key}/version",
                type_definition="AMLBaseVariableType",
            )
        self._add_change_mode(node, item, key)

    def _add_change_mode(
        self,
        node: UANode,
        item: CAEXBasicObject,
        key: str,
    ) -> None:
        if item.change_mode != "state":
            self._add_property(
                node,
                "AMLChangeMode",
                str(item.change_mode),
                key=f"{key}/change-mode",
            )

    def _add_property(
        self,
        owner: UANode,
        name: str,
        value: str,
        *,
        key: str,
        data_type: str = "String",
        scalar_type: str = "String",
        type_definition: str = "PropertyType",
        node_id: str | None = None,
    ) -> UANode:
        property_node = self._add_node(
            UANode(
                node_class="UAVariable",
                node_id=node_id or self._node_id("property", key),
                browse_name=f"1:{name}",
                display_name=name,
                parent_node_id=owner.node_id,
                data_type=data_type,
                value=UAScalarValue(type_name=scalar_type, value=value),
                references=[
                    self._reference("HasTypeDefinition", type_definition),
                ],
            )
        )
        self._add_reference(
            owner, self._reference("HasProperty", property_node.node_id)
        )
        return property_node

    def _add_node(self, node: UANode) -> UANode:
        try:
            return self.nodeset.add_node(node)
        except ValueError as exc:
            raise PythonMappingUnsupported(
                f"Python mapper generated duplicate NodeId {node.node_id!r}."
            ) from exc

    def _add_reference(self, owner: UANode, reference: UAReference) -> None:
        if reference.is_forward and reference.reference_type in {
            "Organizes",
            "HasComponent",
            "HasProperty",
        }:
            self.nodeset.add_hierarchical_reference(
                owner,
                reference.target,
                reference.reference_type,
            )
            return
        self.nodeset.add_reference(owner, reference)

    def _add_hierarchical_references(
        self,
        owner: UANode,
        reference_type: str,
        targets: list[UANode],
    ) -> None:
        if targets:
            self.nodeset.add_hierarchical_references(
                owner,
                targets,
                reference_type,
            )

    def _data_type(self, aml_data_type: str | None) -> tuple[str, str]:
        try:
            rule = DEFAULT_MAPPING_PROFILE.data_types.from_aml(aml_data_type)
        except UnsupportedDataTypeError as exc:
            raise PythonMappingUnsupported(
                f"Python OPC UA strict profile cannot safely translate AML "
                f"AttributeDataType {aml_data_type!r}."
            ) from exc
        return rule.ua_alias, rule.scalar_type

    def _namespace_index(self, uri: str) -> int:
        return self.nodeset.add_namespace(uri)

    def _node_id(self, kind: str, key: str) -> str:
        digest = sha256(f"{kind}\0{key}".encode("utf-8")).hexdigest()[:16]
        readable = quote(key.rsplit("/", 1)[-1], safe="-._~")[:48] or kind
        return f"ns=1;s=aml:{kind}:{readable}:{digest}"

    @staticmethod
    def _reference(
        reference_type: str,
        target: str,
        *,
        is_forward: bool = True,
    ) -> UAReference:
        return UAReference(
            reference_type=reference_type,
            target=target,
            is_forward=is_forward,
        )

    @staticmethod
    def _has_relation_header(relation: CAEXBasicObject) -> bool:
        return bool(
            relation.description is not None
            or relation.version is not None
            or relation.revision
            or relation.copyright is not None
            or relation.additional_information
            or relation.source_object_information
            or relation.change_mode != "state"
        )

    @classmethod
    def _assert_relation_header_is_empty(
        cls,
        relation: CAEXBasicObject,
        label: str,
    ) -> None:
        if cls._has_relation_header(relation):
            raise PythonMappingUnsupported(
                f"Python OPC UA strict profile does not yet preserve header "
                f"metadata on {label}."
            )


def _source_document_xml(source: SourceDocumentInformation) -> str:
    element = ET.Element("SourceDocumentInformation")
    for key, value in source.model_dump(
        by_alias=True,
        mode="json",
        exclude_none=True,
    ).items():
        element.set(key, str(value))
    return ET.tostring(element, encoding="unicode", short_empty_elements=True)


def _additional_information_xml(information: AdditionalInformation) -> str:
    element = ET.Element("AdditionalInformation")
    element.text = information.value
    return ET.tostring(element, encoding="unicode", short_empty_elements=True)


def _dictionary_projection(value: str) -> tuple[str, str] | None:
    normalized = value.strip()
    if normalized.upper().startswith("ECLASS:"):
        return IRDI_DICTIONARY_URI, normalized.split(":", 1)[1]
    if normalized[:4].isdigit() and "#" in normalized:
        return IRDI_DICTIONARY_URI, normalized
    if ":" in normalized and normalized.split(":", 1)[0].replace("+", "").replace(
        "-", ""
    ).replace(".", "").isalnum():
        return URI_DICTIONARY_URI, normalized
    return None
