"""Pluggable and filesystem-safe resolution of AML ExternalReferences."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .legacy import AMLImportResult, import_aml_xml
from .merge import MergePolicy, MergeResult, merge_documents
from .models import CAEXFile, ExternalReference


@dataclass(frozen=True, slots=True)
class ResolvedDocument:
    identity: str
    import_result: AMLImportResult


class ExternalReferenceResolver(Protocol):
    def resolve(
        self,
        reference: ExternalReference,
        *,
        owner: CAEXFile,
    ) -> ResolvedDocument: ...


@dataclass(frozen=True, slots=True)
class ResolutionIssue:
    code: str
    alias: str
    path: str
    message: str


@dataclass(frozen=True, slots=True)
class ResolutionResult:
    documents: dict[str, CAEXFile]
    imports: dict[str, AMLImportResult]
    issues: tuple[ResolutionIssue, ...]

    @property
    def succeeded(self) -> bool:
        return not self.issues


class FileSystemResolver:
    """Resolve references below one explicit filesystem root."""

    def __init__(self, base_directory: str | Path, *, allow_absolute: bool = False) -> None:
        self.base_directory = Path(base_directory).resolve()
        self.allow_absolute = allow_absolute

    def resolve(
        self,
        reference: ExternalReference,
        *,
        owner: CAEXFile,
    ) -> ResolvedDocument:
        requested = Path(reference.path)
        if requested.is_absolute() and not self.allow_absolute:
            raise ValueError(f"Absolute external path is not allowed: {requested}")
        target = requested.resolve() if requested.is_absolute() else (self.base_directory / requested).resolve()
        if not self.allow_absolute and not target.is_relative_to(self.base_directory):
            raise ValueError(f"External path escapes resolver root: {reference.path}")
        if not target.is_file():
            raise FileNotFoundError(target)
        result = import_aml_xml(target.read_bytes())
        return ResolvedDocument(identity=str(target), import_result=result)


def resolve_external_references(
    document: CAEXFile,
    resolver: ExternalReferenceResolver,
    *,
    recursive: bool = False,
    max_depth: int = 16,
) -> ResolutionResult:
    if max_depth < 1:
        raise ValueError("max_depth must be at least 1")
    documents: dict[str, CAEXFile] = {}
    imports: dict[str, AMLImportResult] = {}
    identities: dict[str, str] = {}
    issues: list[ResolutionIssue] = []

    def visit(owner: CAEXFile, depth: int, ancestry: tuple[str, ...]) -> None:
        if depth > max_depth:
            issues.append(
                ResolutionIssue(
                    code="maximum-depth-exceeded",
                    alias="",
                    path=owner.file_name,
                    message=f"External reference depth exceeded {max_depth}.",
                )
            )
            return
        local_aliases: set[str] = set()
        for reference in owner.external_references:
            alias = reference.file_alias
            if alias in local_aliases:
                issues.append(
                    ResolutionIssue(
                        code="duplicate-alias",
                        alias=alias,
                        path=reference.path,
                        message=f"External alias {alias!r} occurs more than once in {owner.file_name!r}.",
                    )
                )
                continue
            local_aliases.add(alias)
            try:
                resolved = resolver.resolve(reference, owner=owner)
            except (OSError, ValueError) as exc:
                issues.append(
                    ResolutionIssue(
                        code="resolution-failed",
                        alias=alias,
                        path=reference.path,
                        message=str(exc),
                    )
                )
                continue
            if resolved.identity in ancestry:
                issues.append(
                    ResolutionIssue(
                        code="reference-cycle",
                        alias=alias,
                        path=reference.path,
                        message=f"External reference cycle includes {resolved.identity!r}.",
                    )
                )
                continue
            previous = identities.get(alias)
            if previous is not None and previous != resolved.identity:
                issues.append(
                    ResolutionIssue(
                        code="alias-conflict",
                        alias=alias,
                        path=reference.path,
                        message=f"Alias {alias!r} resolves to multiple documents.",
                    )
                )
                continue
            identities[alias] = resolved.identity
            documents[alias] = resolved.import_result.document
            imports[alias] = resolved.import_result
            if recursive:
                visit(
                    resolved.import_result.document,
                    depth + 1,
                    (*ancestry, resolved.identity),
                )

    visit(document, 1, ())
    return ResolutionResult(
        documents=documents,
        imports=imports,
        issues=tuple(issues),
    )


def resolve_and_merge(
    document: CAEXFile,
    reference: ExternalReference,
    resolver: ExternalReferenceResolver,
    *,
    policy: MergePolicy | None = None,
) -> MergeResult:
    resolved = resolver.resolve(reference, owner=document)
    return merge_documents(document, resolved.import_result.document, policy=policy)
