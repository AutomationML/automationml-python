"""SystemUnitClass inheritance materialization and instance creation."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable, Iterable, TypeVar
from uuid import uuid4

from .exceptions import ReferenceNotFoundError
from .models import (
    AmlModel,
    Attribute,
    CAEXFile,
    CAEXObject,
    InterfaceClass,
    InternalElement,
    InternalLink,
    SupportedRoleClass,
    SystemUnitClass,
    SystemUnitFamily,
)
from .validation import canonical_id

T = TypeVar("T", bound=CAEXObject)


def instantiate_system_unit_class(
    document: CAEXFile,
    path: str,
    *,
    name: str,
    id: str | None = None,
    id_factory: Callable[[], str] | None = None,
) -> InternalElement:
    """Create an unattached, deeply materialized InternalElement instance."""

    query = document.query()
    leaf = query.find_by_path(path, kind="SystemUnitClass")
    if leaf is None:
        raise ReferenceNotFoundError(f"SystemUnitClass {path!r} was not found")

    chain: list[SystemUnitFamily] = []
    current = leaf
    seen: set[str] = set()
    while current is not None:
        if current.aml_path in seen:
            raise ValueError(f"SystemUnitClass inheritance cycle at {current.aml_path!r}")
        seen.add(current.aml_path)
        if not isinstance(current.obj, SystemUnitFamily):
            raise TypeError(f"{current.aml_path!r} is not a SystemUnitClass")
        chain.append(current.obj)
        base = current.obj.ref_base_class_path
        if not base:
            break
        current = query.find_by_path(base, kind="SystemUnitClass")
        if current is None:
            raise ReferenceNotFoundError(
                f"Base SystemUnitClass {base!r} referenced by "
                f"{chain[-1].name!r} was not found"
            )

    effective = deepcopy(chain[-1])
    for definition in reversed(chain[:-1]):
        effective = _overlay_system_unit(effective, definition)

    source_root_id = effective.id
    payload = effective.to_aml_dict(include_change_mode=True, prune_empty=False)
    payload.pop("SystemUnitClass", None)
    payload.pop("RefBaseClassPath", None)
    payload["Name"] = name
    payload["RefBaseSystemUnitPath"] = path
    payload["ID"] = id or _new_id(id_factory)
    instance = InternalElement.model_validate(payload)
    _remap_instance_ids(
        instance,
        id_factory=id_factory,
        root_id=payload["ID"],
        source_root_id=source_root_id,
    )
    return instance


def _overlay_system_unit(
    base: SystemUnitFamily,
    derived: SystemUnitFamily,
) -> SystemUnitFamily:
    result = base.model_copy(deep=True)
    _overlay_headers(result, derived)
    result.name = derived.name
    result.id = derived.id or result.id
    result.attributes = _merge_named(result.attributes, derived.attributes, _overlay_attribute)
    result.external_interfaces = _merge_named(
        result.external_interfaces,
        derived.external_interfaces,
        _overlay_interface,
    )
    result.internal_elements = _merge_named(
        result.internal_elements,
        derived.internal_elements,
        _overlay_internal_element,
    )
    result.supported_role_classes = _merge_keyed(
        result.supported_role_classes,
        derived.supported_role_classes,
        key=lambda item: item.ref_role_class_path,
    )
    result.internal_links = _merge_named(
        result.internal_links,
        derived.internal_links,
        lambda _base, item: item.model_copy(deep=True),
    )
    result.ref_base_class_path = derived.ref_base_class_path
    return result


def _overlay_internal_element(base: InternalElement, derived: InternalElement) -> InternalElement:
    result = base.model_copy(deep=True)
    _overlay_headers(result, derived)
    result.id = derived.id or result.id
    result.ref_base_system_unit_path = (
        derived.ref_base_system_unit_path or result.ref_base_system_unit_path
    )
    result.attributes = _merge_named(result.attributes, derived.attributes, _overlay_attribute)
    result.external_interfaces = _merge_named(
        result.external_interfaces, derived.external_interfaces, _overlay_interface
    )
    result.internal_elements = _merge_named(
        result.internal_elements, derived.internal_elements, _overlay_internal_element
    )
    result.supported_role_classes = _merge_keyed(
        result.supported_role_classes,
        derived.supported_role_classes,
        key=lambda item: item.ref_role_class_path,
    )
    result.internal_links = _merge_named(
        result.internal_links,
        derived.internal_links,
        lambda _base, item: item.model_copy(deep=True),
    )
    if derived.role_requirements:
        result.role_requirements = deepcopy(derived.role_requirements)
    return result


def _overlay_attribute(base: Attribute, derived: Attribute) -> Attribute:
    result = base.model_copy(deep=True)
    _overlay_headers(result, derived)
    for field in ("id", "default_value", "value", "unit", "attribute_data_type", "ref_attribute_type"):
        value = getattr(derived, field)
        if value is not None:
            setattr(result, field, value)
    result.attributes = _merge_named(result.attributes, derived.attributes, _overlay_attribute)
    if derived.ref_semantic:
        result.ref_semantic = deepcopy(derived.ref_semantic)
    if derived.constraint:
        result.constraint = deepcopy(derived.constraint)
    return result


def _overlay_interface(base: InterfaceClass, derived: InterfaceClass) -> InterfaceClass:
    result = base.model_copy(deep=True)
    _overlay_headers(result, derived)
    result.id = derived.id or result.id
    result.ref_base_class_path = derived.ref_base_class_path or result.ref_base_class_path
    result.attributes = _merge_named(result.attributes, derived.attributes, _overlay_attribute)
    result.external_interfaces = _merge_named(
        result.external_interfaces, derived.external_interfaces, _overlay_interface
    )
    return result


def _overlay_headers(target: CAEXObject, source: CAEXObject) -> None:
    for field in (
        "description",
        "version",
        "revision",
        "copyright",
        "additional_information",
        "source_object_information",
        "change_mode",
    ):
        value = getattr(source, field)
        if value not in (None, [], "state"):
            setattr(target, field, deepcopy(value))


def _merge_named(
    base: Iterable[T],
    derived: Iterable[T],
    overlay: Callable[[T, T], T],
) -> list[T]:
    result = [item.model_copy(deep=True) for item in base]
    positions = {item.name: index for index, item in enumerate(result)}
    for item in derived:
        if item.name in positions:
            position = positions[item.name]
            result[position] = overlay(result[position], item)
        else:
            positions[item.name] = len(result)
            result.append(item.model_copy(deep=True))
    return result


def _merge_keyed(base, derived, *, key):
    result = [item.model_copy(deep=True) for item in base]
    positions = {key(item): index for index, item in enumerate(result)}
    for item in derived:
        marker = key(item)
        copy = item.model_copy(deep=True)
        if marker in positions:
            result[positions[marker]] = copy
        else:
            positions[marker] = len(result)
            result.append(copy)
    return result


def _remap_instance_ids(
    instance: InternalElement,
    *,
    id_factory: Callable[[], str] | None,
    root_id: str,
    source_root_id: str | None,
) -> None:
    id_map: dict[str, str] = (
        {source_root_id: root_id} if source_root_id is not None else {}
    )
    objects = list(_walk_models(instance))
    for obj in objects:
        if not isinstance(obj, CAEXObject):
            continue
        old_id = obj.id
        should_identify = isinstance(obj, (InternalElement, InterfaceClass)) or old_id is not None
        if obj is instance:
            new_id = root_id
        elif should_identify:
            new_id = _new_id(id_factory)
        else:
            continue
        if old_id and obj is not instance:
            if canonical_id(old_id) in {canonical_id(item) for item in id_map}:
                raise ValueError(f"Cannot instantiate duplicate source ID {old_id!r}")
            id_map[old_id] = new_id
        obj.id = new_id

    for obj in objects:
        if isinstance(obj, InternalLink):
            obj.ref_partner_side_a = _rewrite_reference(obj.ref_partner_side_a, id_map)
            obj.ref_partner_side_b = _rewrite_reference(obj.ref_partner_side_b, id_map)
        for field in ("system_unit_interface_id", "role_interface_id"):
            value = getattr(obj, field, None)
            if value:
                setattr(obj, field, _rewrite_reference(value, id_map))

    generated_ids = {
        obj.id for obj in objects if isinstance(obj, CAEXObject) and obj.id is not None
    }
    for obj in objects:
        if not isinstance(obj, InternalLink):
            continue
        for side in (obj.ref_partner_side_a, obj.ref_partner_side_b):
            if side not in generated_ids:
                raise ReferenceNotFoundError(
                    f"InternalLink {obj.name!r} endpoint {side!r} cannot be "
                    "safely rewritten inside the instantiated class"
                )


def _rewrite_reference(value: str, id_map: dict[str, str]) -> str:
    # Source IDs may be written with or without GUID braces; references to
    # them may use the other spelling, so match on the canonical form.
    canonical_map = {canonical_id(old): new for old, new in id_map.items()}
    key = canonical_id(value)
    if key in canonical_map:
        return canonical_map[key]
    if ":" in value:
        owner, suffix = value.split(":", 1)
        owner_key = canonical_id(owner)
        if owner_key in canonical_map:
            return f"{canonical_map[owner_key]}:{suffix}"
    return value


def _walk_models(value: Any):
    if isinstance(value, AmlModel):
        yield value
        for field in type(value).model_fields:
            yield from _walk_models(getattr(value, field))
    elif isinstance(value, list):
        for item in value:
            yield from _walk_models(item)


def _new_id(factory: Callable[[], str] | None) -> str:
    return str(factory() if factory is not None else uuid4())
