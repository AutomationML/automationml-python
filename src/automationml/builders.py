"""Small builder helpers for ergonomic AutomationML authoring."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, Mapping

from .models import (
    Attribute,
    CAEXFile,
    InstanceHierarchy,
    InterfaceClass,
    InternalElement,
    RoleRequirements,
    SourceDocumentInformation,
)


def source_document(
    *,
    origin_name: str = "AutomationML Python SDK",
    origin_id: str = "automationml-python",
    origin_version: str = "0.1.0",
    last_writing_date_time: datetime | None = None,
) -> SourceDocumentInformation:
    """Create CAEX source document metadata."""

    return SourceDocumentInformation(
        origin_name=origin_name,
        origin_id=origin_id,
        origin_version=origin_version,
        last_writing_date_time=last_writing_date_time
        or datetime.now(timezone.utc).replace(microsecond=0),
    )


def caex_file(
    file_name: str,
    *,
    source_documents: Iterable[SourceDocumentInformation] | None = None,
) -> CAEXFile:
    """Create a CAEX 3.0 document."""

    return CAEXFile(
        file_name=file_name,
        superior_standard_versions=["AutomationML 2.1"],
        source_document_information=list(source_documents or [source_document()]),
    )


def attribute(
    name: str,
    value: str | int | float | bool | None = None,
    *,
    data_type: str | None = None,
    unit: str | None = None,
    ref_attribute_type: str | None = None,
    id: str | None = None,
) -> Attribute:
    """Create a CAEX Attribute."""

    return Attribute(
        id=id,
        name=name,
        value=None if value is None else str(value),
        attribute_data_type=data_type,
        unit=unit,
        ref_attribute_type=ref_attribute_type,
    )


def external_interface(
    name: str,
    *,
    id: str | None = None,
    ref_base_class_path: str | None = None,
) -> InterfaceClass:
    """Create an ExternalInterface-compatible interface model."""

    return InterfaceClass(
        id=id,
        name=name,
        ref_base_class_path=ref_base_class_path,
    )


def role_requirement(ref_base_role_class_path: str) -> RoleRequirements:
    """Create a RoleRequirements object."""

    return RoleRequirements(ref_base_role_class_path=ref_base_role_class_path)


def internal_element(
    name: str,
    *,
    id: str | None = None,
    ref_base_system_unit_path: str | None = None,
    attributes: Mapping[str, str | int | float | bool] | Iterable[Attribute] | None = None,
    role_paths: Iterable[str] | None = None,
    children: Iterable[InternalElement] | None = None,
    external_interfaces: Iterable[InterfaceClass] | None = None,
) -> InternalElement:
    """Create an InternalElement with common nested collections."""

    attr_list: list[Attribute]
    if attributes is None:
        attr_list = []
    elif isinstance(attributes, Mapping):
        attr_list = [attribute(key, value) for key, value in attributes.items()]
    else:
        attr_list = list(attributes)

    return InternalElement(
        id=id,
        name=name,
        ref_base_system_unit_path=ref_base_system_unit_path,
        attributes=attr_list,
        role_requirements=[
            role_requirement(role_path) for role_path in (role_paths or [])
        ],
        internal_elements=list(children or []),
        external_interfaces=list(external_interfaces or []),
    )


def instance_hierarchy(
    name: str,
    *,
    internal_elements: Iterable[InternalElement] | None = None,
    id: str | None = None,
) -> InstanceHierarchy:
    """Create an InstanceHierarchy."""

    return InstanceHierarchy(
        id=id,
        name=name,
        internal_elements=list(internal_elements or []),
    )
