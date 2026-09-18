"""Validated, invertible document diffs and non-mutating edit transactions."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from .exceptions import ChangeSetError
from .models import CAEXFile


class ChangeOperation(BaseModel):
    """One RFC 6901-addressed add, remove, or replace operation."""

    model_config = ConfigDict(frozen=True)
    op: Literal["add", "remove", "replace"]
    path: str
    before: Any = None
    after: Any = None


class ChangeSet(BaseModel):
    """An atomic, base-bound sequence of document changes."""

    model_config = ConfigDict(frozen=True)
    operations: tuple[ChangeOperation, ...]
    source_digest: str
    result_digest: str

    def apply(self, document: CAEXFile) -> CAEXFile:
        if document_digest(document) != self.source_digest:
            raise ChangeSetError("ChangeSet source digest does not match the document")
        payload = _document_payload(document)
        for operation in self.operations:
            _apply_operation(payload, operation)
        result = CAEXFile.model_validate(payload)
        errors = [
            issue for issue in result.caex_validation_issues() if issue.severity == "error"
        ]
        if errors:
            detail = "; ".join(f"{issue.path}: {issue.message}" for issue in errors[:3])
            raise ChangeSetError(f"ChangeSet produced an invalid CAEX document: {detail}")
        if document_digest(result) != self.result_digest:
            raise ChangeSetError("ChangeSet produced an unexpected result digest")
        return result

    def inverse(self) -> "ChangeSet":
        inverse_ops: list[ChangeOperation] = []
        for operation in reversed(self.operations):
            if operation.op == "add":
                inverse_ops.append(
                    ChangeOperation(op="remove", path=operation.path, before=operation.after)
                )
            elif operation.op == "remove":
                inverse_ops.append(
                    ChangeOperation(op="add", path=operation.path, after=operation.before)
                )
            else:
                inverse_ops.append(
                    ChangeOperation(
                        op="replace",
                        path=operation.path,
                        before=operation.after,
                        after=operation.before,
                    )
                )
        return ChangeSet(
            operations=tuple(inverse_ops),
            source_digest=self.result_digest,
            result_digest=self.source_digest,
        )


class EditResult(BaseModel):
    """Committed document and its forward/inverse changes."""

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)
    document: CAEXFile
    changes: ChangeSet
    inverse: ChangeSet


class DocumentEdit:
    """Context manager that edits a deep copy and commits on clean exit."""

    def __init__(self, source: CAEXFile) -> None:
        self._source = source.model_copy(deep=True)
        self._working = source.model_copy(deep=True)
        self._result: EditResult | None = None

    def __enter__(self) -> CAEXFile:
        return self._working

    def __exit__(self, exc_type, exc, traceback) -> bool:
        if exc_type is None:
            changes = diff_documents(self._source, self._working)
            committed = changes.apply(self._source)
            self._result = EditResult(
                document=committed,
                changes=changes,
                inverse=changes.inverse(),
            )
        return False

    @property
    def result(self) -> EditResult:
        if self._result is None:
            raise ChangeSetError("Edit has not committed successfully")
        return self._result


def diff_documents(before: CAEXFile, after: CAEXFile) -> ChangeSet:
    """Return a deterministic change set between two canonical documents."""

    operations = diff_payloads(_document_payload(before), _document_payload(after))
    return ChangeSet(
        operations=operations,
        source_digest=document_digest(before),
        result_digest=document_digest(after),
    )


def diff_payloads(before: Any, after: Any) -> tuple[ChangeOperation, ...]:
    """Diff two JSON-compatible values using the shared RFC 6901 engine."""

    operations: list[ChangeOperation] = []
    _diff_values(before, after, "", operations)
    return tuple(operations)


def document_digest(document: CAEXFile) -> str:
    raw = json.dumps(
        _document_payload(document),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _document_payload(document: CAEXFile) -> dict[str, Any]:
    return document.to_aml_dict(include_change_mode=True, prune_empty=False)


def _diff_values(before: Any, after: Any, path: str, output: list[ChangeOperation]) -> None:
    if isinstance(before, dict) and isinstance(after, dict):
        for key in sorted(before.keys() - after.keys()):
            output.append(
                ChangeOperation(
                    op="remove",
                    path=_join(path, key),
                    before=deepcopy(before[key]),
                )
            )
        for key in sorted(after.keys() - before.keys()):
            output.append(
                ChangeOperation(
                    op="add",
                    path=_join(path, key),
                    after=deepcopy(after[key]),
                )
            )
        for key in sorted(before.keys() & after.keys()):
            _diff_values(before[key], after[key], _join(path, key), output)
        return

    if isinstance(before, list) and isinstance(after, list):
        common = min(len(before), len(after))
        for index in range(common):
            _diff_values(before[index], after[index], _join(path, str(index)), output)
        for index in range(len(before) - 1, len(after) - 1, -1):
            output.append(
                ChangeOperation(
                    op="remove",
                    path=_join(path, str(index)),
                    before=deepcopy(before[index]),
                )
            )
        for index in range(common, len(after)):
            output.append(
                ChangeOperation(
                    op="add",
                    path=_join(path, str(index)),
                    after=deepcopy(after[index]),
                )
            )
        return

    if before != after:
        output.append(
            ChangeOperation(
                op="replace",
                path=path,
                before=deepcopy(before),
                after=deepcopy(after),
            )
        )


def _apply_operation(root: Any, operation: ChangeOperation) -> None:
    parts = _pointer_parts(operation.path)
    if not parts:
        raise ChangeSetError("Root document replacement is not supported")
    parent = root
    for part in parts[:-1]:
        try:
            parent = parent[int(part)] if isinstance(parent, list) else parent[part]
        except (KeyError, IndexError, ValueError, TypeError) as exc:
            raise ChangeSetError(f"Invalid change path {operation.path!r}") from exc
    key = parts[-1]
    if isinstance(parent, list):
        try:
            index = int(key)
        except ValueError as exc:
            raise ChangeSetError(f"List path segment must be an integer: {key!r}") from exc
        if operation.op == "add":
            parent.insert(index, deepcopy(operation.after))
        elif operation.op == "remove":
            if index >= len(parent) or parent[index] != operation.before:
                raise ChangeSetError(f"Remove precondition failed at {operation.path}")
            parent.pop(index)
        else:
            if index >= len(parent) or parent[index] != operation.before:
                raise ChangeSetError(f"Replace precondition failed at {operation.path}")
            parent[index] = deepcopy(operation.after)
        return

    if not isinstance(parent, dict):
        raise ChangeSetError(f"Invalid change parent at {operation.path!r}")
    if operation.op == "add":
        if key in parent:
            raise ChangeSetError(f"Add target already exists at {operation.path}")
        parent[key] = deepcopy(operation.after)
    elif operation.op == "remove":
        if parent.get(key, object()) != operation.before:
            raise ChangeSetError(f"Remove precondition failed at {operation.path}")
        del parent[key]
    else:
        if parent.get(key, object()) != operation.before:
            raise ChangeSetError(f"Replace precondition failed at {operation.path}")
        parent[key] = deepcopy(operation.after)


def _pointer_parts(path: str) -> list[str]:
    if not path:
        return []
    if not path.startswith("/"):
        raise ChangeSetError(f"Invalid JSON Pointer {path!r}")
    return [part.replace("~1", "/").replace("~0", "~") for part in path[1:].split("/")]


def _join(path: str, part: str) -> str:
    escaped = str(part).replace("~", "~0").replace("/", "~1")
    return f"{path}/{escaped}"
