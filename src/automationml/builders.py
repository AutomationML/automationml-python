"""Small builder helpers for ergonomic AutomationML authoring."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, Mapping

from .models import (
    Attribute,
    AttributeType,
    AttributeTypeLib,
    CAEXFile,
    InstanceHierarchy,
    InterfaceClass,
    InterfaceClassLib,
    InterfaceFamily,
    InternalElement,
    RoleClassLib,
    RoleFamily,
    RoleRequirements,
    SourceDocumentInformation,
    SupportedRoleClass,
    SystemUnitClassLib,
    SystemUnitFamily,
)

AttributeInput = Mapping[str, str | int | float | bool] | Iterable[Attribute] | None


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


def _attribute_list(attributes: AttributeInput) -> list[Attribute]:
    if attributes is None:
        return []
    if isinstance(attributes, Mapping):
        return [attribute(key, value) for key, value in attributes.items()]
    return list(attributes)


def internal_element(
    name: str,
    *,
    id: str | None = None,
    ref_base_system_unit_path: str | None = None,
    attributes: AttributeInput = None,
    role_paths: Iterable[str] | None = None,
    children: Iterable[InternalElement] | None = None,
    external_interfaces: Iterable[InterfaceClass] | None = None,
) -> InternalElement:
    """Create an InternalElement with common nested collections."""

    return InternalElement(
        id=id,
        name=name,
        ref_base_system_unit_path=ref_base_system_unit_path,
        attributes=_attribute_list(attributes),
        role_requirements=[
            role_requirement(role_path) for role_path in (role_paths or [])
        ],
        internal_elements=list(children or []),
        external_interfaces=list(external_interfaces or []),
    )


def system_unit_class(
    name: str,
    *,
    id: str | None = None,
    ref_base_class_path: str | None = None,
    attributes: AttributeInput = None,
    role_paths: Iterable[str] | None = None,
    children: Iterable[InternalElement] | None = None,
    external_interfaces: Iterable[InterfaceClass] | None = None,
    classes: Iterable[SystemUnitFamily] | None = None,
) -> SystemUnitFamily:
    """Create a SystemUnitClass, a reusable template for InternalElements.

    ``ref_base_class_path`` names a class to inherit from, ``role_paths``
    lists the RoleClasses the class supports, ``children`` holds its nested
    InternalElements, and ``classes`` nests further SystemUnitClasses below
    it in the library tree.
    """

    return SystemUnitFamily(
        id=id,
        name=name,
        ref_base_class_path=ref_base_class_path,
        attributes=_attribute_list(attributes),
        supported_role_classes=[
            SupportedRoleClass(ref_role_class_path=role_path)
            for role_path in (role_paths or [])
        ],
        internal_elements=list(children or []),
        external_interfaces=list(external_interfaces or []),
        system_unit_classes=list(classes or []),
    )


def system_unit_class_lib(
    name: str,
    *,
    classes: Iterable[SystemUnitFamily] | None = None,
    id: str | None = None,
) -> SystemUnitClassLib:
    """Create a SystemUnitClassLib holding SystemUnitClasses."""

    return SystemUnitClassLib(id=id, name=name, system_unit_classes=list(classes or []))


def role_class(
    name: str,
    *,
    id: str | None = None,
    ref_base_class_path: str | None = None,
    attributes: AttributeInput = None,
    external_interfaces: Iterable[InterfaceClass] | None = None,
    classes: Iterable[RoleFamily] | None = None,
) -> RoleFamily:
    """Create a RoleClass, a vendor-neutral description of what an object is.

    ``classes`` nests further RoleClasses below it in the library tree.
    """

    return RoleFamily(
        id=id,
        name=name,
        ref_base_class_path=ref_base_class_path,
        attributes=_attribute_list(attributes),
        external_interfaces=list(external_interfaces or []),
        role_classes=list(classes or []),
    )


def role_class_lib(
    name: str,
    *,
    classes: Iterable[RoleFamily] | None = None,
    id: str | None = None,
) -> RoleClassLib:
    """Create a RoleClassLib holding RoleClasses."""

    return RoleClassLib(id=id, name=name, role_classes=list(classes or []))


def interface_class(
    name: str,
    *,
    id: str | None = None,
    ref_base_class_path: str | None = None,
    attributes: AttributeInput = None,
    classes: Iterable[InterfaceFamily] | None = None,
) -> InterfaceFamily:
    """Create an InterfaceClass, a reusable type for ExternalInterfaces.

    ``classes`` nests further InterfaceClasses below it in the library tree.
    """

    return InterfaceFamily(
        id=id,
        name=name,
        ref_base_class_path=ref_base_class_path,
        attributes=_attribute_list(attributes),
        interface_classes=list(classes or []),
    )


def interface_class_lib(
    name: str,
    *,
    classes: Iterable[InterfaceFamily] | None = None,
    id: str | None = None,
) -> InterfaceClassLib:
    """Create an InterfaceClassLib holding InterfaceClasses."""

    return InterfaceClassLib(id=id, name=name, interface_classes=list(classes or []))


def attribute_type(
    name: str,
    value: str | int | float | bool | None = None,
    *,
    data_type: str | None = None,
    unit: str | None = None,
    id: str | None = None,
) -> AttributeType:
    """Create an AttributeType, a reusable attribute definition."""

    return AttributeType(
        id=id,
        name=name,
        value=None if value is None else str(value),
        attribute_data_type=data_type,
        unit=unit,
    )


def attribute_type_lib(
    name: str,
    *,
    attribute_types: Iterable[AttributeType] | None = None,
    id: str | None = None,
) -> AttributeTypeLib:
    """Create an AttributeTypeLib holding AttributeTypes."""

    return AttributeTypeLib(
        id=id,
        name=name,
        attribute_types=list(attribute_types or []),
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
