"""Atomic, policy-driven merging of CAEX 3.0 documents."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Callable
from uuid import NAMESPACE_URL, uuid5

from pydantic import BaseModel, ConfigDict

from .changes import ChangeSet, diff_documents
from .models import AmlModel, CAEXFile, CAEXObject
from .validation import canonical_id


class ConflictAction(StrEnum):
    ERROR = "error"
    KEEP_TARGET = "keep_target"
    REPLACE_TARGET = "replace_target"
    RENAME_SOURCE = "rename_source"
    REMAP_SOURCE_IDS = "remap_source_ids"


class MergePolicy(BaseModel):
    """Explicit behavior for each merge collision category."""

    model_config = ConfigDict(frozen=True)
    definitions: ConflictAction = ConflictAction.ERROR
    instance_hierarchies: ConflictAction = ConflictAction.ERROR
    external_references: ConflictAction = ConflictAction.ERROR
    ids: ConflictAction = ConflictAction.ERROR


@dataclass(frozen=True, slots=True)
class MergeConflict:
    code: str
    path: str
    message: str


@dataclass(frozen=True, slots=True)
class MergeResult:
    document: CAEXFile | None
    conflicts: tuple[MergeConflict, ...]
    warnings: tuple[str, ...]
    rewritten_references: tuple[tuple[str, str], ...]
    changes: ChangeSet | None

    @property
    def succeeded(self) -> bool:
        return self.document is not None and not self.conflicts


def merge_documents(
    target: CAEXFile,
    source: CAEXFile,
    *,
    policy: MergePolicy | None = None,
) -> MergeResult:
    """Merge into a new document or return structured conflicts atomically."""

    policy = policy or MergePolicy()
    source_copy = source.model_copy(deep=True)
    candidate = target.model_copy(deep=True)
    conflicts: list[MergeConflict] = []
    warnings: list[str] = []
    rewrites: list[tuple[str, str]] = []

    _handle_id_collisions(candidate, source_copy, policy.ids, conflicts, rewrites)
    if conflicts:
        return _failed(conflicts, warnings, rewrites)

    _merge_external_references(
        candidate, source_copy, policy.external_references, conflicts, rewrites
    )

    library_specs = (
        ("AttributeTypeLib", candidate.attribute_type_libs, source_copy.attribute_type_libs, "attribute_types"),
        ("InterfaceClassLib", candidate.interface_class_libs, source_copy.interface_class_libs, "interface_classes"),
        ("RoleClassLib", candidate.role_class_libs, source_copy.role_class_libs, "role_classes"),
        ("SystemUnitClassLib", candidate.system_unit_class_libs, source_copy.system_unit_class_libs, "system_unit_classes"),
    )
    for kind, target_libs, source_libs, child_field in library_specs:
        _merge_libraries(
            source_copy,
            target_libs,
            source_libs,
            child_field,
            kind,
            policy.definitions,
            conflicts,
            rewrites,
        )

    # Class conflict policies can rewrite paths throughout the source graph, so
    # copy instance hierarchies only after all definition rewrites are complete.
    _merge_named_roots(
        candidate.instance_hierarchies,
        source_copy.instance_hierarchies,
        policy.instance_hierarchies,
        "InstanceHierarchy",
        conflicts,
    )

    if conflicts:
        return _failed(conflicts, warnings, rewrites)

    _append_unique(candidate.source_document_information, source_copy.source_document_information)
    _append_unique(candidate.additional_information, source_copy.additional_information)
    _append_unique(candidate.superior_standard_versions, source_copy.superior_standard_versions)

    issues = candidate.caex_validation_issues()
    errors = [issue for issue in issues if issue.severity == "error"]
    if errors:
        conflicts.extend(
            MergeConflict(
                code="merged-document-invalid",
                path=issue.path,
                message=issue.message,
            )
            for issue in errors
        )
        return _failed(conflicts, warnings, rewrites)
    warnings.extend(issue.message for issue in issues if issue.severity == "warning")
    changes = diff_documents(target, candidate)
    return MergeResult(
        document=candidate,
        conflicts=(),
        warnings=tuple(warnings),
        rewritten_references=tuple(rewrites),
        changes=changes,
    )


def _handle_id_collisions(
    target: CAEXFile,
    source: CAEXFile,
    action: ConflictAction,
    conflicts: list[MergeConflict],
    rewrites: list[tuple[str, str]],
) -> None:
    # IDs are compared ignoring optional GUID braces: "{x}" and "x" collide.
    target_ids = {canonical_id(value) for value in target.reference_index().ids}
    source_objects = [
        obj for obj in _walk_models(source) if isinstance(obj, CAEXObject) and obj.id
    ]
    duplicates = sorted(
        {obj.id for obj in source_objects if canonical_id(obj.id) in target_ids}
    )
    if not duplicates:
        return
    if action != ConflictAction.REMAP_SOURCE_IDS:
        conflicts.extend(
            MergeConflict(
                code="duplicate-id",
                path=f"ID:{value}",
                message=(
                    f"ID {value!r} exists in both documents; select "
                    "ids='remap_source_ids' to rewrite the source graph."
                ),
            )
            for value in duplicates
        )
        return
    mapping = {
        value: str(uuid5(NAMESPACE_URL, f"{target.file_name}:{source.file_name}:{value}"))
        for value in duplicates
    }
    for value in list(mapping):
        # References may spell the ID with or without braces.
        bare = canonical_id(value)
        mapping.setdefault(bare, mapping[value])
        mapping.setdefault(f"{{{bare}}}", mapping[value])
    for obj in source_objects:
        if obj.id in mapping:
            old = obj.id
            obj.id = mapping[old]
            rewrites.append((old, obj.id))
    _rewrite_values(source, mapping)


def _merge_external_references(
    target: CAEXFile,
    source: CAEXFile,
    action: ConflictAction,
    conflicts: list[MergeConflict],
    rewrites: list[tuple[str, str]],
) -> None:
    by_alias = {item.file_alias: item for item in target.external_references}
    for reference in source.external_references:
        existing = by_alias.get(reference.file_alias)
        if existing is None:
            target.external_references.append(reference.model_copy(deep=True))
            by_alias[reference.file_alias] = reference
        elif existing.path == reference.path:
            continue
        elif action == ConflictAction.KEEP_TARGET:
            continue
        elif action == ConflictAction.REPLACE_TARGET:
            target.external_references[target.external_references.index(existing)] = reference.model_copy(deep=True)
        elif action == ConflictAction.RENAME_SOURCE:
            old = reference.file_alias
            reference.file_alias = _unique_name(old, set(by_alias))
            _rewrite_alias(source, old, reference.file_alias)
            rewrites.append((f"[{old}]", f"[{reference.file_alias}]"))
            target.external_references.append(reference.model_copy(deep=True))
            by_alias[reference.file_alias] = reference
        else:
            conflicts.append(
                MergeConflict(
                    code="external-alias-conflict",
                    path=f"ExternalReference:{reference.file_alias}",
                    message=f"Alias {reference.file_alias!r} refers to different paths.",
                )
            )


def _merge_named_roots(target, source, action, kind, conflicts) -> None:
    by_name = {item.name: item for item in target}
    for item in source:
        existing = by_name.get(item.name)
        if existing is None:
            target.append(item.model_copy(deep=True))
        elif _canonical(existing) == _canonical(item):
            continue
        elif action == ConflictAction.KEEP_TARGET:
            continue
        elif action == ConflictAction.REPLACE_TARGET:
            target[target.index(existing)] = item.model_copy(deep=True)
        elif action == ConflictAction.RENAME_SOURCE:
            copy = item.model_copy(deep=True)
            copy.name = _unique_name(copy.name, set(by_name))
            target.append(copy)
            by_name[copy.name] = copy
        else:
            conflicts.append(
                MergeConflict(
                    code="definition-conflict",
                    path=f"{kind}:{item.name}",
                    message=f"Unequal {kind} definitions share name {item.name!r}.",
                )
            )


def _merge_libraries(
    document: CAEXFile,
    target,
    source,
    child_field: str,
    kind: str,
    action: ConflictAction,
    conflicts: list[MergeConflict],
    rewrites: list[tuple[str, str]],
) -> None:
    by_name = {library.name: library for library in target}
    for library in source:
        existing = by_name.get(library.name)
        if existing is None:
            target.append(library.model_copy(deep=True))
            continue
        _merge_class_list(
            document,
            getattr(existing, child_field),
            getattr(library, child_field),
            library.name,
            child_field,
            action,
            conflicts,
            rewrites,
        )


def _merge_class_list(
    document: CAEXFile,
    target: list,
    source: list,
    parent_path: str,
    child_field: str,
    action: ConflictAction,
    conflicts: list[MergeConflict],
    rewrites: list[tuple[str, str]],
) -> None:
    by_name = {item.name: item for item in target}
    for item in source:
        path = f"{parent_path}/{item.name}"
        existing = by_name.get(item.name)
        if existing is None:
            target.append(item.model_copy(deep=True))
            continue
        if _canonical(existing) == _canonical(item):
            continue
        nested = getattr(item, child_field, None)
        target_nested = getattr(existing, child_field, None)
        shallow_existing = _without_field(existing, child_field)
        shallow_item = _without_field(item, child_field)
        if nested is not None and target_nested is not None and shallow_existing == shallow_item:
            _merge_class_list(
                document,
                target_nested,
                nested,
                path,
                child_field,
                action,
                conflicts,
                rewrites,
            )
        elif action == ConflictAction.KEEP_TARGET:
            continue
        elif action == ConflictAction.REPLACE_TARGET:
            target[target.index(existing)] = item.model_copy(deep=True)
        elif action == ConflictAction.RENAME_SOURCE:
            item.name = _unique_name(item.name, set(by_name))
            new_path = f"{parent_path}/{item.name}"
            _rewrite_values(document, {path: new_path})
            rewrites.append((path, new_path))
            copy = item.model_copy(deep=True)
            target.append(copy)
            by_name[copy.name] = copy
        else:
            conflicts.append(
                MergeConflict(
                    code="class-path-conflict",
                    path=path,
                    message=f"Unequal class definitions share path {path!r}.",
                )
            )


def _append_unique(target: list, source: list) -> None:
    existing = {_canonical(item) for item in target}
    for item in source:
        marker = _canonical(item)
        if marker not in existing:
            target.append(deepcopy(item))
            existing.add(marker)


def _rewrite_values(model: AmlModel, mapping: dict[str, str]) -> None:
    for item in _walk_models(model):
        for field_name in type(item).model_fields:
            value = getattr(item, field_name)
            if not isinstance(value, str):
                continue
            replacement = mapping.get(value)
            if replacement is None:
                for old, new in mapping.items():
                    if "/" in old and value.startswith(f"{old}/"):
                        replacement = f"{new}{value[len(old):]}"
                        break
            if replacement is None and ":" in value:
                owner, suffix = value.split(":", 1)
                if owner in mapping:
                    replacement = f"{mapping[owner]}:{suffix}"
            if replacement is not None:
                setattr(item, field_name, replacement)


def _rewrite_alias(model: AmlModel, old: str, new: str) -> None:
    prefix = f"[{old}]"
    for item in _walk_models(model):
        for field_name in item.model_fields:
            value = getattr(item, field_name)
            if isinstance(value, str) and value.startswith(prefix):
                setattr(item, field_name, f"[{new}]{value[len(prefix):]}")


def _walk_models(value: Any):
    if isinstance(value, AmlModel):
        yield value
        for field_name in type(value).model_fields:
            yield from _walk_models(getattr(value, field_name))
    elif isinstance(value, list):
        for item in value:
            yield from _walk_models(item)


def _canonical(value: Any) -> str:
    if isinstance(value, AmlModel):
        return value.to_aml_json(indent=None, include_change_mode=True, prune_empty=False)
    return repr(value)


def _without_field(value: AmlModel, field: str) -> dict[str, Any]:
    return value.model_dump(by_alias=True, mode="json", exclude={field})


def _unique_name(name: str, used: set[str]) -> str:
    index = 2
    candidate = f"{name}_{index}"
    while candidate in used:
        index += 1
        candidate = f"{name}_{index}"
    return candidate


def _failed(conflicts, warnings, rewrites) -> MergeResult:
    return MergeResult(
        document=None,
        conflicts=tuple(conflicts),
        warnings=tuple(warnings),
        rewritten_references=tuple(rewrites),
        changes=None,
    )
