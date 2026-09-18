"""Immutable query snapshots and reverse-reference indexes for CAEX documents."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Iterator

from pydantic import BaseModel

from .exceptions import AmbiguousReferenceError
from .models import (
    AmlModel,
    AttributeType,
    CAEXFile,
    CAEXObject,
    InterfaceFamily,
    InternalElement,
    InternalLink,
    RoleFamily,
    SystemUnitFamily,
)
from .validation import (
    ReferenceIndex,
    ReferenceTarget,
    canonical_id,
    canonical_partner_reference,
)


@dataclass(frozen=True, slots=True)
class ReferenceEdge:
    """One reference-bearing field and its raw target."""

    source: ReferenceTarget
    field: str
    path: str
    target: str
    relation: str


_REFERENCE_FIELDS = {
    "ref_base_class_path": "base-class",
    "ref_attribute_type": "attribute-type",
    "ref_base_system_unit_path": "system-unit-instance",
    "ref_role_class_path": "supported-role",
    "ref_base_role_class_path": "role-requirement",
    "ref_partner_side_a": "internal-link-a",
    "ref_partner_side_b": "internal-link-b",
    "system_unit_interface_id": "interface-mapping-source",
    "role_interface_id": "interface-mapping-target",
}


class CAEXQuery:
    """A fresh, immutable lookup snapshot over one document and optional aliases."""

    def __init__(
        self,
        document: CAEXFile,
        index: ReferenceIndex,
        *,
        externals: dict[str, CAEXFile] | None = None,
    ) -> None:
        self.document = document
        self._index = index
        self._externals = {
            alias: external.model_copy(deep=True)
            for alias, external in (externals or {}).items()
        }
        self._original_to_snapshot: dict[int, AmlModel] = {}
        indexed = list(_unique_targets(index))
        indexed_objects = {id(target.obj) for target in indexed}
        for model, model_path in _walk_models_with_path(document):
            if not isinstance(model, CAEXObject) or id(model) in indexed_objects:
                continue
            indexed.append(
                ReferenceTarget(
                    kind=type(model).__name__,
                    name=model.name,
                    path=model_path,
                    aml_path=model_path,
                    id=model.id,
                    obj=model,
                )
            )
            indexed_objects.add(id(model))
        self._targets = tuple(indexed)
        self._target_by_object = {id(target.obj): target for target in self._targets}
        self._edges = tuple(self._build_edges(document))

    @classmethod
    def from_document(
        cls,
        document: CAEXFile,
        *,
        externals: dict[str, CAEXFile] | None = None,
    ) -> "CAEXQuery":
        snapshot = document.model_copy(deep=True)
        query = cls(
            snapshot,
            ReferenceIndex.from_document(snapshot),
            externals=externals,
        )
        query._original_to_snapshot = {
            id(original): copied
            for original, copied in zip(
                _walk_models(document),
                _walk_models(snapshot),
                strict=True,
            )
        }
        return query

    @property
    def references(self) -> tuple[ReferenceEdge, ...]:
        return self._edges

    def all_by_id(self, id_value: str) -> tuple[ReferenceTarget, ...]:
        return tuple(self._index.targets_for_id(id_value))

    def find_by_id(self, id_value: str) -> ReferenceTarget | None:
        return _one_or_none(self.all_by_id(id_value), f"ID {id_value!r}")

    def all_by_path(
        self,
        path: str,
        *,
        kind: str | None = None,
    ) -> tuple[ReferenceTarget, ...]:
        external = _split_external_path(path)
        if external is not None:
            alias, local_path = external
            document = self._externals.get(alias)
            if document is None:
                return ()
            return document.query().all_by_path(local_path, kind=kind)

        registries = (
            self._index.system_unit_class_paths,
            self._index.role_class_paths,
            self._index.interface_class_paths,
            self._index.attribute_type_paths,
        )
        result = [target for registry in registries for target in registry.get(path, ())]
        if kind is not None:
            result = [target for target in result if target.kind == kind]
        return tuple(result)

    def find_by_path(
        self,
        path: str,
        *,
        kind: str | None = None,
    ) -> ReferenceTarget | None:
        return _one_or_none(self.all_by_path(path, kind=kind), f"path {path!r}")

    def derived_classes(
        self,
        path: str,
        *,
        recursive: bool = True,
    ) -> tuple[ReferenceTarget, ...]:
        base = self.find_by_path(path)
        if base is None:
            return ()
        category = _class_category(base.obj)
        found: list[ReferenceTarget] = []
        frontier = [path]
        seen = {path}
        while frontier:
            parent = frontier.pop(0)
            direct = [
                target
                for target in self._targets
                if _class_category(target.obj) == category
                and getattr(target.obj, "ref_base_class_path", None) == parent
            ]
            found.extend(direct)
            if recursive:
                for target in direct:
                    if target.aml_path not in seen:
                        seen.add(target.aml_path)
                        frontier.append(target.aml_path)
        return tuple(found)

    def instances_of(
        self,
        path: str,
        *,
        include_derived: bool = True,
    ) -> tuple[ReferenceTarget, ...]:
        accepted = {path}
        if include_derived:
            accepted.update(item.aml_path for item in self.derived_classes(path))
        return tuple(
            target
            for target in self._targets
            if isinstance(target.obj, InternalElement)
            and target.path.startswith("$.InstanceHierarchy")
            and target.obj.ref_base_system_unit_path in accepted
        )

    def references_to(
        self,
        target: ReferenceTarget | str,
    ) -> tuple[ReferenceEdge, ...]:
        values = {target} if isinstance(target, str) else {target.aml_path}
        if isinstance(target, ReferenceTarget) and target.id:
            values.add(target.id)
        return tuple(edge for edge in self._edges if edge.target in values)

    def connected_interfaces(self, interface_id: str) -> tuple[ReferenceTarget, ...]:
        connected: list[ReferenceTarget] = []
        for target in self._targets:
            if not isinstance(target.obj, InternalLink):
                continue
            sides = (target.obj.ref_partner_side_a, target.obj.ref_partner_side_b)
            wanted = canonical_id(interface_id)
            canonical_sides = tuple(canonical_partner_reference(side) for side in sides)
            if wanted not in canonical_sides:
                continue
            other = sides[1] if canonical_sides[0] == wanted else sides[0]
            resolved = self.find_by_id(other)
            if resolved is not None:
                connected.append(resolved)
        return tuple(connected)

    def descendants(
        self,
        obj: AmlModel,
        *,
        kind: str | None = None,
    ) -> tuple[ReferenceTarget, ...]:
        obj = self._original_to_snapshot.get(id(obj), obj)
        descendants = {id(item) for item in _walk_models(obj) if item is not obj}
        return tuple(
            target
            for target in self._targets
            if id(target.obj) in descendants and (kind is None or target.kind == kind)
        )

    def _build_edges(self, document: CAEXFile) -> Iterator[ReferenceEdge]:
        for model, model_path in _walk_models_with_path(document):
            source = self._target_by_object.get(id(model))
            if source is None:
                source = ReferenceTarget(
                    kind=type(model).__name__,
                    name=getattr(model, "name", type(model).__name__),
                    path=model_path,
                    aml_path=model_path,
                    id=getattr(model, "id", None),
                    obj=model,
                )
            for field_name, relation in _REFERENCE_FIELDS.items():
                value = getattr(model, field_name, None)
                if isinstance(value, str) and value:
                    alias = type(model).model_fields[field_name].alias or field_name
                    yield ReferenceEdge(
                        source=source,
                        field=field_name,
                        path=f"{source.path}.{alias}",
                        target=value,
                        relation=relation,
                    )


def _unique_targets(index: ReferenceIndex) -> tuple[ReferenceTarget, ...]:
    result: list[ReferenceTarget] = []
    seen: set[int] = set()
    registries: Iterable[dict[str, list[ReferenceTarget]]] = (
        index.ids,
        index.system_unit_class_paths,
        index.role_class_paths,
        index.interface_class_paths,
        index.attribute_type_paths,
    )
    for registry in registries:
        for targets in registry.values():
            for target in targets:
                marker = id(target.obj)
                if marker not in seen:
                    seen.add(marker)
                    result.append(target)
    return tuple(result)


def _walk_models(value: Any) -> Iterator[AmlModel]:
    if isinstance(value, AmlModel):
        yield value
        for field_name in type(value).model_fields:
            yield from _walk_models(getattr(value, field_name))
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _walk_models(item)


def _walk_models_with_path(value: Any, path: str = "$"):
    if isinstance(value, AmlModel):
        yield value, path
        for field_name, field in type(value).model_fields.items():
            alias = field.alias or field_name
            child = getattr(value, field_name)
            if isinstance(child, list):
                for index, item in enumerate(child):
                    yield from _walk_models_with_path(item, f"{path}.{alias}[{index}]")
            else:
                yield from _walk_models_with_path(child, f"{path}.{alias}")


def _one_or_none(
    values: tuple[ReferenceTarget, ...],
    label: str,
) -> ReferenceTarget | None:
    if len(values) > 1:
        raise AmbiguousReferenceError(f"{label} resolves to {len(values)} objects")
    return values[0] if values else None


def _split_external_path(path: str) -> tuple[str, str] | None:
    if not path.startswith("[") or "]" not in path:
        return None
    alias, local = path[1:].split("]", 1)
    return alias, local.lstrip("/.")


def _class_category(value: AmlModel) -> type[AmlModel] | None:
    for category in (SystemUnitFamily, RoleFamily, InterfaceFamily, AttributeType):
        if isinstance(value, category):
            return category
    return None
