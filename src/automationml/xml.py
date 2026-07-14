"""CAEX XML import/export for the JSON-first models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from xml.dom import minidom
from xml.etree import ElementTree as ET

from pydantic import BaseModel

from .models import (
    AmlModel,
    Attribute,
    AttributeNameMapping,
    AttributeType,
    AttributeTypeLib,
    AttributeValueRequirement,
    CAEXBasicObject,
    CAEXFile,
    CAEXObject,
    ExternalReference,
    InstanceHierarchy,
    InterfaceClass,
    InterfaceClassLib,
    InterfaceFamily,
    InterfaceIDMapping,
    InternalElement,
    InternalLink,
    MappingObject,
    NominalScaledType,
    OrdinalScaledType,
    RefSemantic,
    Revision,
    RoleClass,
    RoleClassLib,
    RoleFamily,
    RoleRequirements,
    SourceDocumentInformation,
    SourceObjectInformation,
    SupportedRoleClass,
    SystemUnitClass,
    SystemUnitClassLib,
    SystemUnitFamily,
    TextElement,
    UnknownType,
    AdditionalInformation,
)

CAEX_NS = "http://www.dke.de/CAEX"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"

ET.register_namespace("", CAEX_NS)

XML_ATTRIBUTE_FIELDS: dict[type[AmlModel], tuple[str, ...]] = {
    CAEXBasicObject: ("change_mode",),
    CAEXObject: ("id", "name"),
    TextElement: ("change_mode",),
    SourceObjectInformation: ("origin_id", "source_obj_id"),
    SourceDocumentInformation: (
        "origin_name",
        "origin_id",
        "origin_vendor",
        "origin_vendor_url",
        "origin_version",
        "origin_release",
        "last_writing_date_time",
        "origin_project_title",
        "origin_project_id",
    ),
    ExternalReference: ("path", "file_alias"),
    AttributeNameMapping: ("system_unit_attribute_name", "role_attribute_name"),
    InterfaceIDMapping: ("system_unit_interface_id", "role_interface_id"),
    AttributeValueRequirement: ("name",),
    RefSemantic: ("corresponding_attribute_path",),
    Attribute: ("unit", "attribute_data_type", "ref_attribute_type"),
    InterfaceClass: ("ref_base_class_path",),
    RoleClass: ("ref_base_class_path",),
    SupportedRoleClass: ("ref_role_class_path",),
    InternalLink: ("ref_partner_side_a", "ref_partner_side_b"),
    RoleRequirements: ("ref_base_role_class_path",),
    InternalElement: ("ref_base_system_unit_path",),
    SystemUnitFamily: ("ref_base_class_path",),
    CAEXFile: ("schema_version", "file_name"),
}

XML_ELEMENT_FIELDS: dict[type[AmlModel], tuple[str, ...]] = {
    CAEXBasicObject: (
        "description",
        "version",
        "revision",
        "copyright",
        "additional_information",
        "source_object_information",
    ),
    Revision: (
        "revision_date",
        "old_version",
        "new_version",
        "author_name",
        "comment",
    ),
    CAEXFile: (
        "superior_standard_versions",
        "source_document_information",
        "external_references",
        "instance_hierarchies",
        "interface_class_libs",
        "role_class_libs",
        "system_unit_class_libs",
        "attribute_type_libs",
    ),
    MappingObject: ("attribute_name_mapping", "interface_id_mapping"),
    OrdinalScaledType: (
        "required_max_value",
        "required_value",
        "required_min_value",
    ),
    NominalScaledType: ("required_values",),
    UnknownType: ("requirements",),
    AttributeValueRequirement: (
        "ordinal_scaled_type",
        "nominal_scaled_type",
        "unknown_type",
    ),
    Attribute: (
        "default_value",
        "value",
        "ref_semantic",
        "constraint",
        "attributes",
    ),
    AttributeType: ("attribute_types",),
    InterfaceClass: ("attributes", "external_interfaces"),
    InterfaceFamily: ("interface_classes",),
    RoleClass: ("attributes", "external_interfaces"),
    RoleFamily: ("role_classes",),
    SupportedRoleClass: ("mapping_object",),
    SystemUnitClass: (
        "attributes",
        "external_interfaces",
        "internal_elements",
        "supported_role_classes",
        "internal_links",
    ),
    RoleRequirements: ("attributes", "external_interfaces", "mapping_object"),
    InternalElement: ("role_requirements",),
    SystemUnitFamily: ("system_unit_classes",),
    InstanceHierarchy: ("internal_elements",),
    InterfaceClassLib: ("interface_classes",),
    RoleClassLib: ("role_classes",),
    SystemUnitClassLib: ("system_unit_classes",),
    AttributeTypeLib: ("attribute_types",),
}

CHILD_MODEL_BY_FIELD: dict[str, type[AmlModel]] = {
    "description": TextElement,
    "version": TextElement,
    "copyright": TextElement,
    "additional_information": AdditionalInformation,
    "source_object_information": SourceObjectInformation,
    "revision": Revision,
    "source_document_information": SourceDocumentInformation,
    "external_references": ExternalReference,
    "instance_hierarchies": InstanceHierarchy,
    "interface_class_libs": InterfaceClassLib,
    "role_class_libs": RoleClassLib,
    "system_unit_class_libs": SystemUnitClassLib,
    "attribute_type_libs": AttributeTypeLib,
    "attribute_name_mapping": AttributeNameMapping,
    "interface_id_mapping": InterfaceIDMapping,
    "ordinal_scaled_type": OrdinalScaledType,
    "nominal_scaled_type": NominalScaledType,
    "unknown_type": UnknownType,
    "ref_semantic": RefSemantic,
    "constraint": AttributeValueRequirement,
    "attributes": Attribute,
    "attribute_types": AttributeType,
    "external_interfaces": InterfaceClass,
    "interface_classes": InterfaceFamily,
    "role_classes": RoleFamily,
    "mapping_object": MappingObject,
    "supported_role_classes": SupportedRoleClass,
    "internal_links": InternalLink,
    "role_requirements": RoleRequirements,
    "internal_elements": InternalElement,
    "system_unit_classes": SystemUnitFamily,
}


def dumps(
    document: CAEXFile,
    *,
    pretty: bool = True,
    xml_declaration: bool = True,
    encoding: str = "unicode",
    include_default_change_mode: bool = True,
) -> str:
    """Serialize a CAEX document to XML."""

    root = _model_to_element(
        document,
        "CAEXFile",
        include_default_change_mode=include_default_change_mode,
    )
    raw = ET.tostring(root, encoding=encoding)
    if not pretty:
        text = raw.decode() if isinstance(raw, bytes) else raw
        if xml_declaration:
            return f'<?xml version="1.0" encoding="UTF-8"?>\n{text}'
        return text

    text = raw.decode() if isinstance(raw, bytes) else raw
    pretty_text = minidom.parseString(text).toprettyxml(
        indent="  ",
        encoding="UTF-8" if xml_declaration else None,
    )
    if isinstance(pretty_text, bytes):
        return pretty_text.decode("utf-8")
    return pretty_text


def dump(
    document: CAEXFile,
    path: str,
    *,
    pretty: bool = True,
    include_default_change_mode: bool = True,
) -> None:
    """Write a CAEX document to an XML file."""

    with open(path, "w", encoding="utf-8") as handle:
        handle.write(
            dumps(
                document,
                pretty=pretty,
                include_default_change_mode=include_default_change_mode,
            )
        )


def loads(data: str | bytes) -> CAEXFile:
    """Parse CAEX XML into a CAEXFile model."""

    root = ET.fromstring(data)
    if _local_name(root.tag) != "CAEXFile":
        raise ValueError(f"Expected CAEXFile root element, got {_local_name(root.tag)!r}.")
    payload = _element_to_data(root, CAEXFile)
    return CAEXFile.model_validate(payload)


def load(path: str) -> CAEXFile:
    """Read a CAEX XML file into a CAEXFile model."""

    with open(path, "rb") as handle:
        return loads(handle.read())


def _model_to_element(
    model: AmlModel,
    tag: str,
    *,
    include_default_change_mode: bool,
) -> ET.Element:
    element = ET.Element(_qname(tag))

    for field_name in _field_names_for(model, XML_ATTRIBUTE_FIELDS):
        value = getattr(model, field_name)
        if value is None:
            continue
        alias = _alias(model, field_name)
        if (
            alias == "ChangeMode"
            and value == "state"
            and not include_default_change_mode
        ):
            continue
        element.set(alias, _xml_scalar(value))

    if isinstance(model, TextElement):
        element.text = model.value
        return element

    for field_name in _field_names_for(model, XML_ELEMENT_FIELDS):
        value = getattr(model, field_name)
        if value is None or value == []:
            continue
        alias = _alias(model, field_name)
        if isinstance(value, list):
            for item in value:
                element.append(
                    _value_to_element(
                        alias,
                        item,
                        include_default_change_mode=include_default_change_mode,
                    )
                )
        else:
            element.append(
                _value_to_element(
                    alias,
                    value,
                    include_default_change_mode=include_default_change_mode,
                )
            )

    return element


def _value_to_element(
    tag: str,
    value: Any,
    *,
    include_default_change_mode: bool,
) -> ET.Element:
    if isinstance(value, AmlModel):
        return _model_to_element(
            value,
            tag,
            include_default_change_mode=include_default_change_mode,
        )

    element = ET.Element(_qname(tag))
    element.text = _xml_scalar(value)
    return element


def _element_to_data(element: ET.Element, model_cls: type[AmlModel]) -> dict[str, Any]:
    data: dict[str, Any] = {}

    for field_name in _field_names_for(model_cls, XML_ATTRIBUTE_FIELDS):
        alias = _alias(model_cls, field_name)
        if alias in element.attrib:
            data[alias] = element.attrib[alias]

    if issubclass(model_cls, TextElement):
        data["value"] = element.text or ""
        return data

    child_fields = _child_field_lookup(model_cls)
    for child in element:
        tag = _local_name(child.tag)
        field_name = child_fields.get(tag)
        if field_name is None:
            continue
        field = model_cls.model_fields[field_name]
        alias = field.alias or field_name
        child_model = CHILD_MODEL_BY_FIELD.get(field_name)
        value: Any
        if child_model is not None:
            value = _element_to_data(child, child_model)
        else:
            value = child.text or ""

        annotation = field.annotation
        if _is_list_annotation(annotation):
            data.setdefault(alias, []).append(value)
        else:
            data[alias] = value

    return data


def _field_names_for(
    model_or_cls: AmlModel | type[AmlModel],
    registry: dict[type[AmlModel], tuple[str, ...]],
) -> tuple[str, ...]:
    cls = model_or_cls if isinstance(model_or_cls, type) else type(model_or_cls)
    names: list[str] = []
    for base in reversed(cls.mro()):
        values = registry.get(base)
        if values:
            names.extend(values)
    return tuple(dict.fromkeys(names))


def _child_field_lookup(model_cls: type[AmlModel]) -> dict[str, str]:
    fields: dict[str, str] = {}
    for field_name in _field_names_for(model_cls, XML_ELEMENT_FIELDS):
        alias = _alias(model_cls, field_name)
        fields[alias] = field_name
    return fields


def _alias(model_or_cls: AmlModel | type[AmlModel], field_name: str) -> str:
    cls = model_or_cls if isinstance(model_or_cls, type) else type(model_or_cls)
    field = cls.model_fields[field_name]
    return field.alias or field_name


def _is_list_annotation(annotation: Any) -> bool:
    return getattr(annotation, "__origin__", None) is list or annotation is list


def _xml_scalar(value: Any) -> str:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, BaseModel):
        raise TypeError(f"Cannot serialize model as scalar: {type(value).__name__}")
    return str(value)


def _qname(tag: str) -> str:
    return f"{{{CAEX_NS}}}{tag}"


def _local_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[1]
    return tag
