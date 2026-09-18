"""Semantic validation and reference resolution for CAEX documents."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from .models import (
    Attribute,
    AttributeType,
    CAEXFile,
    CAEXObject,
    InstanceHierarchy,
    InterfaceClass,
    InterfaceFamily,
    InternalElement,
    InternalLink,
    RoleClass,
    RoleFamily,
    RoleRequirements,
    SupportedRoleClass,
    SystemUnitClass,
    SystemUnitFamily,
)

IssueSeverity = Literal["error", "warning"]


@dataclass(frozen=True, slots=True)
class CAEXIssue:
    """Structured semantic issue found in a CAEX document."""

    severity: IssueSeverity
    path: str
    message: str
    code: str
    target: str | None = None
    suggestion: str | None = None

    def to_dict(self) -> dict[str, str]:
        """Return a JSON-serializable issue payload."""

        data = {
            "severity": self.severity,
            "path": self.path,
            "message": self.message,
            "code": self.code,
        }
        if self.target is not None:
            data["target"] = self.target
        if self.suggestion is not None:
            data["suggestion"] = self.suggestion
        return data


@dataclass(frozen=True, slots=True)
class ReferenceTarget:
    """Resolved AML object address for path and ID lookups."""

    kind: str
    name: str
    path: str
    aml_path: str
    id: str | None = None
    obj: Any = field(default=None, compare=False, repr=False)


@dataclass(frozen=True, slots=True)
class _ClassMemberExpectation:
    name: str
    source_class_path: str
    inherited: bool
    ref_base_class_path: str | None = None


def canonical_id(value: str) -> str:
    """Return the comparison key for a CAEX ``ID``.

    AML tooling (notably the AutomationML Editor) writes GUID IDs wrapped in
    braces (``{0f3c...}``) while other producers and CAEX 3.0 references often
    omit them. Both spellings identify the same object. The SDK keeps every ID
    exactly as authored, so documents round-trip unchanged, and uses this key
    only when *comparing* or *looking up* IDs.
    """

    stripped = value.strip()
    if len(stripped) >= 2 and stripped[0] == "{" and stripped[-1] == "}":
        return stripped[1:-1].strip()
    return stripped


def canonical_partner_reference(value: str) -> str:
    """Canonicalize an InternalLink partner (``ID`` or ``ID:InterfaceName``)."""

    owner, separator, interface = value.partition(":")
    if separator:
        return f"{canonical_id(owner)}:{interface}"
    return canonical_id(owner)


class ReferenceIndex:
    """Index of AML paths and IDs that can be referenced inside a CAEX file.

    ``ids`` is keyed by the IDs exactly as written. Lookups through
    :meth:`resolve_id` / :meth:`targets_for_id` ignore optional GUID braces,
    see :func:`canonical_id`.
    """

    def __init__(self) -> None:
        self.system_unit_class_paths: dict[str, list[ReferenceTarget]] = {}
        self.role_class_paths: dict[str, list[ReferenceTarget]] = {}
        self.interface_class_paths: dict[str, list[ReferenceTarget]] = {}
        self.attribute_type_paths: dict[str, list[ReferenceTarget]] = {}
        self.ids: dict[str, list[ReferenceTarget]] = {}
        self._ids_by_canonical: dict[str, list[ReferenceTarget]] = {}

    @classmethod
    def from_document(cls, document: CAEXFile) -> ReferenceIndex:
        """Build a reference index from all in-document definitions."""

        index = cls()
        index._build(document)
        return index

    def resolve_system_unit_class(self, path: str) -> ReferenceTarget | None:
        return _single_target(self.system_unit_class_paths.get(path))

    def resolve_role_class(self, path: str) -> ReferenceTarget | None:
        return _single_target(self.role_class_paths.get(path))

    def resolve_interface_class(self, path: str) -> ReferenceTarget | None:
        return _single_target(self.interface_class_paths.get(path))

    def resolve_attribute_type(self, path: str) -> ReferenceTarget | None:
        return _single_target(self.attribute_type_paths.get(path))

    def targets_for_id(self, id_value: str) -> list[ReferenceTarget]:
        """Return every object whose ID matches, ignoring optional braces."""

        return list(self._ids_by_canonical.get(canonical_id(id_value), ()))

    def resolve_id(self, id_value: str) -> ReferenceTarget | None:
        return _single_target(self._ids_by_canonical.get(canonical_id(id_value)))

    def duplicate_issues(self) -> list[CAEXIssue]:
        """Return issues for duplicate IDs and duplicate class paths."""

        issues: list[CAEXIssue] = []
        issues.extend(
            self._duplicate_path_issues(
                self.system_unit_class_paths,
                code="duplicate-system-unit-class-path",
                target_kind="SystemUnitClass",
            )
        )
        issues.extend(
            self._duplicate_path_issues(
                self.role_class_paths,
                code="duplicate-role-class-path",
                target_kind="RoleClass",
            )
        )
        issues.extend(
            self._duplicate_path_issues(
                self.interface_class_paths,
                code="duplicate-interface-class-path",
                target_kind="InterfaceClass",
            )
        )
        issues.extend(
            self._duplicate_path_issues(
                self.attribute_type_paths,
                code="duplicate-attribute-type-path",
                target_kind="AttributeType",
            )
        )
        for targets in self._ids_by_canonical.values():
            if len(targets) <= 1:
                continue
            for target in targets:
                id_value = target.id or ""
                issues.append(
                    CAEXIssue(
                        severity="error",
                        path=f"{target.path}.ID",
                        message=f"ID '{id_value}' is used by multiple CAEX objects.",
                        code="duplicate-id",
                        target=id_value,
                        suggestion="Use a globally unique ID for every CAEX object.",
                    )
                )
        return issues

    def _build(self, document: CAEXFile) -> None:
        self._register_id(document, "$", "CAEXFile")

        for lib_index, library in enumerate(document.system_unit_class_libs):
            lib_path = f"$.SystemUnitClassLib[{lib_index}]"
            self._register_id(library, lib_path, "SystemUnitClassLib")
            for class_index, item in enumerate(library.system_unit_classes):
                self._register_system_unit_family(
                    item,
                    f"{lib_path}.SystemUnitClass[{class_index}]",
                    _join_aml_path(library.name, item.name),
                )

        for lib_index, library in enumerate(document.role_class_libs):
            lib_path = f"$.RoleClassLib[{lib_index}]"
            self._register_id(library, lib_path, "RoleClassLib")
            for class_index, item in enumerate(library.role_classes):
                self._register_role_family(
                    item,
                    f"{lib_path}.RoleClass[{class_index}]",
                    _join_aml_path(library.name, item.name),
                )

        for lib_index, library in enumerate(document.interface_class_libs):
            lib_path = f"$.InterfaceClassLib[{lib_index}]"
            self._register_id(library, lib_path, "InterfaceClassLib")
            for class_index, item in enumerate(library.interface_classes):
                self._register_interface_family(
                    item,
                    f"{lib_path}.InterfaceClass[{class_index}]",
                    _join_aml_path(library.name, item.name),
                )

        for lib_index, library in enumerate(document.attribute_type_libs):
            lib_path = f"$.AttributeTypeLib[{lib_index}]"
            self._register_id(library, lib_path, "AttributeTypeLib")
            for type_index, item in enumerate(library.attribute_types):
                self._register_attribute_type(
                    item,
                    f"{lib_path}.AttributeType[{type_index}]",
                    _join_aml_path(library.name, item.name),
                )

        for hierarchy_index, hierarchy in enumerate(document.instance_hierarchies):
            hierarchy_path = f"$.InstanceHierarchy[{hierarchy_index}]"
            self._register_id(hierarchy, hierarchy_path, "InstanceHierarchy")
            for element_index, element in enumerate(hierarchy.internal_elements):
                self._register_internal_element(
                    element,
                    f"{hierarchy_path}.InternalElement[{element_index}]",
                    _join_aml_path(hierarchy.name, element.name),
                )

    def _register_system_unit_family(
        self,
        item: SystemUnitFamily,
        path: str,
        aml_path: str,
    ) -> None:
        self._register_path(
            self.system_unit_class_paths,
            aml_path,
            item,
            path,
            "SystemUnitClass",
        )
        self._register_system_unit_like(item, path, aml_path, "SystemUnitClass")
        for child_index, child in enumerate(item.system_unit_classes):
            self._register_system_unit_family(
                child,
                f"{path}.SystemUnitClass[{child_index}]",
                _join_aml_path(aml_path, child.name),
            )

    def _register_role_family(
        self,
        item: RoleFamily,
        path: str,
        aml_path: str,
    ) -> None:
        self._register_path(
            self.role_class_paths,
            aml_path,
            item,
            path,
            "RoleClass",
        )
        self._register_role_like(item, path, aml_path, "RoleClass")
        for child_index, child in enumerate(item.role_classes):
            self._register_role_family(
                child,
                f"{path}.RoleClass[{child_index}]",
                _join_aml_path(aml_path, child.name),
            )

    def _register_interface_family(
        self,
        item: InterfaceFamily,
        path: str,
        aml_path: str,
    ) -> None:
        self._register_path(
            self.interface_class_paths,
            aml_path,
            item,
            path,
            "InterfaceClass",
        )
        self._register_interface_like(item, path, aml_path, "InterfaceClass")
        for child_index, child in enumerate(item.interface_classes):
            self._register_interface_family(
                child,
                f"{path}.InterfaceClass[{child_index}]",
                _join_aml_path(aml_path, child.name),
            )

    def _register_attribute_type(
        self,
        item: AttributeType,
        path: str,
        aml_path: str,
    ) -> None:
        self._register_path(
            self.attribute_type_paths,
            aml_path,
            item,
            path,
            "AttributeType",
        )
        self._register_attribute_like(item, path, aml_path, "AttributeType")
        for child_index, child in enumerate(item.attribute_types):
            self._register_attribute_type(
                child,
                f"{path}.AttributeType[{child_index}]",
                _join_aml_path(aml_path, child.name),
            )

    def _register_system_unit_like(
        self,
        item: SystemUnitClass,
        path: str,
        aml_path: str,
        kind: str,
    ) -> None:
        self._register_id(item, path, kind, aml_path)
        for attr_index, attribute in enumerate(item.attributes):
            self._register_attribute_like(
                attribute,
                f"{path}.Attribute[{attr_index}]",
                _join_aml_path(aml_path, attribute.name),
                "Attribute",
            )
        for interface_index, interface in enumerate(item.external_interfaces):
            self._register_interface_like(
                interface,
                f"{path}.ExternalInterface[{interface_index}]",
                _join_aml_path(aml_path, interface.name),
                "ExternalInterface",
            )
        for link_index, link in enumerate(item.internal_links):
            self._register_id(
                link,
                f"{path}.InternalLink[{link_index}]",
                "InternalLink",
                _join_aml_path(aml_path, link.name),
            )
        for element_index, element in enumerate(item.internal_elements):
            self._register_internal_element(
                element,
                f"{path}.InternalElement[{element_index}]",
                _join_aml_path(aml_path, element.name),
            )

    def _register_internal_element(
        self,
        item: InternalElement,
        path: str,
        aml_path: str,
    ) -> None:
        self._register_system_unit_like(item, path, aml_path, "InternalElement")
        for requirement_index, requirement in enumerate(item.role_requirements):
            requirement_path = f"{path}.RoleRequirements[{requirement_index}]"
            self._register_role_requirement(requirement, requirement_path, aml_path)

    def _register_role_like(
        self,
        item: RoleClass,
        path: str,
        aml_path: str,
        kind: str,
    ) -> None:
        self._register_id(item, path, kind, aml_path)
        for attr_index, attribute in enumerate(item.attributes):
            self._register_attribute_like(
                attribute,
                f"{path}.Attribute[{attr_index}]",
                _join_aml_path(aml_path, attribute.name),
                "Attribute",
            )
        for interface_index, interface in enumerate(item.external_interfaces):
            self._register_interface_like(
                interface,
                f"{path}.ExternalInterface[{interface_index}]",
                _join_aml_path(aml_path, interface.name),
                "ExternalInterface",
            )

    def _register_interface_like(
        self,
        item: InterfaceClass,
        path: str,
        aml_path: str,
        kind: str,
    ) -> None:
        self._register_id(item, path, kind, aml_path)
        for attr_index, attribute in enumerate(item.attributes):
            self._register_attribute_like(
                attribute,
                f"{path}.Attribute[{attr_index}]",
                _join_aml_path(aml_path, attribute.name),
                "Attribute",
            )
        for interface_index, interface in enumerate(item.external_interfaces):
            self._register_interface_like(
                interface,
                f"{path}.ExternalInterface[{interface_index}]",
                _join_aml_path(aml_path, interface.name),
                "ExternalInterface",
            )

    def _register_attribute_like(
        self,
        item: Attribute,
        path: str,
        aml_path: str,
        kind: str,
    ) -> None:
        self._register_id(item, path, kind, aml_path)
        for attr_index, child in enumerate(item.attributes):
            self._register_attribute_like(
                child,
                f"{path}.Attribute[{attr_index}]",
                _join_aml_path(aml_path, child.name),
                "Attribute",
            )

    def _register_role_requirement(
        self,
        requirement: RoleRequirements,
        path: str,
        aml_path: str,
    ) -> None:
        for attr_index, attribute in enumerate(requirement.attributes):
            self._register_attribute_like(
                attribute,
                f"{path}.Attribute[{attr_index}]",
                _join_aml_path(aml_path, "RoleRequirements", attribute.name),
                "Attribute",
            )
        for interface_index, interface in enumerate(requirement.external_interfaces):
            self._register_interface_like(
                interface,
                f"{path}.ExternalInterface[{interface_index}]",
                _join_aml_path(aml_path, "RoleRequirements", interface.name),
                "ExternalInterface",
            )

    def _register_path(
        self,
        registry: dict[str, list[ReferenceTarget]],
        aml_path: str,
        obj: CAEXObject,
        path: str,
        kind: str,
    ) -> None:
        target = ReferenceTarget(
            kind=kind,
            name=obj.name,
            path=path,
            aml_path=aml_path,
            id=obj.id,
            obj=obj,
        )
        registry.setdefault(aml_path, []).append(target)

    def _register_id(
        self,
        obj: Any,
        path: str,
        kind: str,
        aml_path: str | None = None,
    ) -> None:
        id_value = getattr(obj, "id", None)
        if not id_value:
            return
        target = ReferenceTarget(
            kind=kind,
            name=getattr(obj, "name", kind),
            path=path,
            aml_path=aml_path or path,
            id=id_value,
            obj=obj,
        )
        self.ids.setdefault(id_value, []).append(target)
        self._ids_by_canonical.setdefault(canonical_id(id_value), []).append(target)

    def _duplicate_path_issues(
        self,
        registry: dict[str, list[ReferenceTarget]],
        *,
        code: str,
        target_kind: str,
    ) -> list[CAEXIssue]:
        issues: list[CAEXIssue] = []
        for aml_path, targets in registry.items():
            if len(targets) <= 1:
                continue
            for target in targets:
                issues.append(
                    CAEXIssue(
                        severity="error",
                        path=target.path,
                        message=(
                            f"{target_kind} path '{aml_path}' is defined "
                            "more than once."
                        ),
                        code=code,
                        target=aml_path,
                        suggestion=(
                            "Rename one class or move it under a unique library path."
                        ),
                    )
                )
        return issues


def validate_caex_document(
    document: CAEXFile,
    *,
    strict_xsd: bool = False,
) -> list[CAEXIssue]:
    """Return structured CAEX conformance and semantic validation issues."""

    index = ReferenceIndex.from_document(document)
    issues: list[CAEXIssue] = []

    if document.schema_version != "3.0":
        issues.append(
            CAEXIssue(
                severity="error",
                path="$.SchemaVersion",
                message="SchemaVersion must be '3.0' for CAEX 3.0.",
                code="invalid-schema-version",
                target=document.schema_version,
                suggestion="Set SchemaVersion to '3.0'.",
            )
        )
    if not document.file_name:
        issues.append(
            CAEXIssue(
                severity="error",
                path="$.FileName",
                message="FileName is required.",
                code="missing-file-name",
                suggestion="Set FileName to the AML document file name.",
            )
        )
    if strict_xsd and not document.source_document_information:
        issues.append(
            CAEXIssue(
                severity="error",
                path="$.SourceDocumentInformation",
                message="SourceDocumentInformation is required by the CAEX 3.0 XSD.",
                code="missing-source-document-information",
                suggestion="Add at least one SourceDocumentInformation entry.",
            )
        )
    for item_index, source in enumerate(document.source_document_information):
        prefix = f"$.SourceDocumentInformation[{item_index}]"
        if strict_xsd:
            if not source.origin_name:
                issues.append(_required_issue(f"{prefix}.OriginName"))
            if not source.origin_id:
                issues.append(_required_issue(f"{prefix}.OriginID"))
            if not source.origin_version:
                issues.append(_required_issue(f"{prefix}.OriginVersion"))
            if source.last_writing_date_time is None:
                issues.append(_required_issue(f"{prefix}.LastWritingDateTime"))

    issues.extend(index.duplicate_issues())
    _validate_instance_hierarchies(document, index, issues)
    _validate_system_unit_class_libs(document, index, issues)
    _validate_role_class_libs(document, index, issues)
    _validate_interface_class_libs(document, index, issues)
    _validate_attribute_type_libs(document, index, issues)
    return issues


def _validate_instance_hierarchies(
    document: CAEXFile,
    index: ReferenceIndex,
    issues: list[CAEXIssue],
) -> None:
    for hierarchy_index, hierarchy in enumerate(document.instance_hierarchies):
        path = f"$.InstanceHierarchy[{hierarchy_index}]"
        for element_index, element in enumerate(hierarchy.internal_elements):
            _validate_internal_element(
                element,
                f"{path}.InternalElement[{element_index}]",
                index,
                issues,
            )


def _validate_system_unit_class_libs(
    document: CAEXFile,
    index: ReferenceIndex,
    issues: list[CAEXIssue],
) -> None:
    for lib_index, library in enumerate(document.system_unit_class_libs):
        path = f"$.SystemUnitClassLib[{lib_index}]"
        for class_index, item in enumerate(library.system_unit_classes):
            _validate_system_unit_family(
                item,
                f"{path}.SystemUnitClass[{class_index}]",
                index,
                issues,
            )


def _validate_role_class_libs(
    document: CAEXFile,
    index: ReferenceIndex,
    issues: list[CAEXIssue],
) -> None:
    for lib_index, library in enumerate(document.role_class_libs):
        path = f"$.RoleClassLib[{lib_index}]"
        for class_index, item in enumerate(library.role_classes):
            _validate_role_family(
                item,
                f"{path}.RoleClass[{class_index}]",
                index,
                issues,
            )


def _validate_interface_class_libs(
    document: CAEXFile,
    index: ReferenceIndex,
    issues: list[CAEXIssue],
) -> None:
    for lib_index, library in enumerate(document.interface_class_libs):
        path = f"$.InterfaceClassLib[{lib_index}]"
        for class_index, item in enumerate(library.interface_classes):
            _validate_interface_family(
                item,
                f"{path}.InterfaceClass[{class_index}]",
                index,
                issues,
            )


def _validate_attribute_type_libs(
    document: CAEXFile,
    index: ReferenceIndex,
    issues: list[CAEXIssue],
) -> None:
    for lib_index, library in enumerate(document.attribute_type_libs):
        path = f"$.AttributeTypeLib[{lib_index}]"
        for type_index, item in enumerate(library.attribute_types):
            _validate_attribute_type(
                item,
                f"{path}.AttributeType[{type_index}]",
                index,
                issues,
            )


def _validate_system_unit_family(
    item: SystemUnitFamily,
    path: str,
    index: ReferenceIndex,
    issues: list[CAEXIssue],
) -> None:
    if item.ref_base_class_path:
        issue = _expect_reference(
            index.resolve_system_unit_class(item.ref_base_class_path),
            path=f"{path}.RefBaseClassPath",
            value=item.ref_base_class_path,
            code="unresolved-system-unit-class-reference",
            target_kind="SystemUnitClass",
            suggestion="Define the referenced SystemUnitClass or update RefBaseClassPath.",
        )
        if issue:
            issues.append(issue)
    _validate_system_unit_like(item, path, index, issues)
    for child_index, child in enumerate(item.system_unit_classes):
        _validate_system_unit_family(
            child,
            f"{path}.SystemUnitClass[{child_index}]",
            index,
            issues,
        )


def _validate_internal_element(
    item: InternalElement,
    path: str,
    index: ReferenceIndex,
    issues: list[CAEXIssue],
) -> None:
    system_unit_target: ReferenceTarget | None = None
    if item.ref_base_system_unit_path:
        system_unit_target = index.resolve_system_unit_class(
            item.ref_base_system_unit_path
        )
        issue = _expect_reference(
            system_unit_target,
            path=f"{path}.RefBaseSystemUnitPath",
            value=item.ref_base_system_unit_path,
            code="unresolved-system-unit-class-reference",
            target_kind="SystemUnitClass",
            suggestion=(
                "Define the referenced SystemUnitClass or update "
                "RefBaseSystemUnitPath."
            ),
        )
        if issue:
            issues.append(issue)
    if system_unit_target is not None:
        _validate_internal_element_realizes_system_unit_class(
            item,
            path,
            system_unit_target,
            index,
            issues,
        )
    _validate_system_unit_like(item, path, index, issues)
    for requirement_index, requirement in enumerate(item.role_requirements):
        _validate_role_requirements(
            requirement,
            f"{path}.RoleRequirements[{requirement_index}]",
            index,
            issues,
        )


def _validate_internal_element_realizes_system_unit_class(
    item: InternalElement,
    path: str,
    system_unit_target: ReferenceTarget,
    index: ReferenceIndex,
    issues: list[CAEXIssue],
) -> None:
    expected_attributes = _system_unit_attribute_expectations(
        system_unit_target,
        index,
    )
    actual_attribute_names = {attribute.name for attribute in item.attributes}
    for expected in expected_attributes:
        if expected.name in actual_attribute_names:
            continue
        issues.append(
            CAEXIssue(
                severity="warning",
                path=f"{path}.Attribute",
                message=(
                    f"InternalElement '{item.name}' does not materialize "
                    f"attribute '{expected.name}' from SystemUnitClass "
                    f"'{expected.source_class_path}'."
                ),
                code=(
                    "missing-inherited-attribute"
                    if expected.inherited
                    else "missing-class-attribute"
                ),
                target=expected.name,
                suggestion=(
                    "Add the attribute to the InternalElement when the instance "
                    "is expected to carry the referenced class shape."
                ),
            )
        )

    expected_interfaces = _system_unit_interface_expectations(
        system_unit_target,
        index,
    )
    actual_interface_names = {
        interface.name for interface in item.external_interfaces
    }
    for expected in expected_interfaces:
        if expected.name in actual_interface_names:
            continue
        issues.append(
            CAEXIssue(
                severity="warning",
                path=f"{path}.ExternalInterface",
                message=(
                    f"InternalElement '{item.name}' does not materialize "
                    f"ExternalInterface '{expected.name}' from SystemUnitClass "
                    f"'{expected.source_class_path}'."
                ),
                code=(
                    "missing-inherited-interface"
                    if expected.inherited
                    else "missing-class-interface"
                ),
                target=expected.name,
                suggestion=(
                    "Add the ExternalInterface to the InternalElement when the "
                    "instance should realize the referenced class interface set."
                ),
            )
        )


def _validate_system_unit_like(
    item: SystemUnitClass,
    path: str,
    index: ReferenceIndex,
    issues: list[CAEXIssue],
) -> None:
    for attr_index, attribute in enumerate(item.attributes):
        _validate_attribute(
            attribute,
            f"{path}.Attribute[{attr_index}]",
            index,
            issues,
        )
    for interface_index, interface in enumerate(item.external_interfaces):
        _validate_interface_like(
            interface,
            f"{path}.ExternalInterface[{interface_index}]",
            index,
            issues,
        )
    for role_index, role in enumerate(item.supported_role_classes):
        _validate_supported_role_class(
            role,
            f"{path}.SupportedRoleClass[{role_index}]",
            index,
            issues,
        )
    for link_index, link in enumerate(item.internal_links):
        _validate_internal_link(
            link,
            f"{path}.InternalLink[{link_index}]",
            item,
            issues,
        )
    for element_index, element in enumerate(item.internal_elements):
        _validate_internal_element(
            element,
            f"{path}.InternalElement[{element_index}]",
            index,
            issues,
        )


def _system_unit_attribute_expectations(
    target: ReferenceTarget,
    index: ReferenceIndex,
) -> list[_ClassMemberExpectation]:
    expectations: dict[str, _ClassMemberExpectation] = {}
    for source in _system_unit_class_chain(target, index):
        source_obj = source.obj
        if not isinstance(source_obj, SystemUnitClass):
            continue
        inherited = source.aml_path != target.aml_path
        for attribute in source_obj.attributes:
            expectations[attribute.name] = _ClassMemberExpectation(
                name=attribute.name,
                source_class_path=source.aml_path,
                inherited=inherited,
                ref_base_class_path=attribute.ref_attribute_type,
            )
    return list(expectations.values())


def _system_unit_interface_expectations(
    target: ReferenceTarget,
    index: ReferenceIndex,
) -> list[_ClassMemberExpectation]:
    expectations: dict[str, _ClassMemberExpectation] = {}
    for source in _system_unit_class_chain(target, index):
        source_obj = source.obj
        if not isinstance(source_obj, SystemUnitClass):
            continue
        inherited = source.aml_path != target.aml_path
        for interface in source_obj.external_interfaces:
            expectations[interface.name] = _ClassMemberExpectation(
                name=interface.name,
                source_class_path=source.aml_path,
                inherited=inherited,
                ref_base_class_path=interface.ref_base_class_path,
            )
    return list(expectations.values())


def _system_unit_class_chain(
    target: ReferenceTarget,
    index: ReferenceIndex,
    seen: set[str] | None = None,
) -> list[ReferenceTarget]:
    seen = set(seen or ())
    if target.aml_path in seen:
        return [target]
    seen.add(target.aml_path)
    target_obj = target.obj
    if (
        isinstance(target_obj, SystemUnitFamily)
        and target_obj.ref_base_class_path
    ):
        base_target = index.resolve_system_unit_class(
            target_obj.ref_base_class_path
        )
        if base_target is not None:
            return [
                *_system_unit_class_chain(base_target, index, seen),
                target,
            ]
    return [target]


def _validate_supported_role_class(
    item: SupportedRoleClass,
    path: str,
    index: ReferenceIndex,
    issues: list[CAEXIssue],
) -> None:
    issue = _expect_reference(
        index.resolve_role_class(item.ref_role_class_path),
        path=f"{path}.RefRoleClassPath",
        value=item.ref_role_class_path,
        code="unresolved-role-class-reference",
        target_kind="RoleClass",
        suggestion="Define the referenced RoleClass or update RefRoleClassPath.",
    )
    if issue:
        issues.append(issue)


def _validate_role_requirements(
    item: RoleRequirements,
    path: str,
    index: ReferenceIndex,
    issues: list[CAEXIssue],
) -> None:
    issue = _expect_reference(
        index.resolve_role_class(item.ref_base_role_class_path),
        path=f"{path}.RefBaseRoleClassPath",
        value=item.ref_base_role_class_path,
        code="unresolved-role-class-reference",
        target_kind="RoleClass",
        suggestion="Define the referenced RoleClass or update RefBaseRoleClassPath.",
    )
    if issue:
        issues.append(issue)
    for attr_index, attribute in enumerate(item.attributes):
        _validate_attribute(
            attribute,
            f"{path}.Attribute[{attr_index}]",
            index,
            issues,
        )
    for interface_index, interface in enumerate(item.external_interfaces):
        _validate_interface_like(
            interface,
            f"{path}.ExternalInterface[{interface_index}]",
            index,
            issues,
        )


def _validate_role_family(
    item: RoleFamily,
    path: str,
    index: ReferenceIndex,
    issues: list[CAEXIssue],
) -> None:
    if item.ref_base_class_path:
        issue = _expect_reference(
            index.resolve_role_class(item.ref_base_class_path),
            path=f"{path}.RefBaseClassPath",
            value=item.ref_base_class_path,
            code="unresolved-role-class-reference",
            target_kind="RoleClass",
            suggestion="Define the referenced RoleClass or update RefBaseClassPath.",
        )
        if issue:
            issues.append(issue)
    _validate_role_like(item, path, index, issues)
    for child_index, child in enumerate(item.role_classes):
        _validate_role_family(
            child,
            f"{path}.RoleClass[{child_index}]",
            index,
            issues,
        )


def _validate_role_like(
    item: RoleClass,
    path: str,
    index: ReferenceIndex,
    issues: list[CAEXIssue],
) -> None:
    for attr_index, attribute in enumerate(item.attributes):
        _validate_attribute(
            attribute,
            f"{path}.Attribute[{attr_index}]",
            index,
            issues,
        )
    for interface_index, interface in enumerate(item.external_interfaces):
        _validate_interface_like(
            interface,
            f"{path}.ExternalInterface[{interface_index}]",
            index,
            issues,
        )


def _validate_interface_family(
    item: InterfaceFamily,
    path: str,
    index: ReferenceIndex,
    issues: list[CAEXIssue],
) -> None:
    if item.ref_base_class_path:
        issue = _expect_reference(
            index.resolve_interface_class(item.ref_base_class_path),
            path=f"{path}.RefBaseClassPath",
            value=item.ref_base_class_path,
            code="unresolved-interface-class-reference",
            target_kind="InterfaceClass",
            suggestion=(
                "Define the referenced InterfaceClass or update RefBaseClassPath."
            ),
        )
        if issue:
            issues.append(issue)
    _validate_interface_like(item, path, index, issues)
    for child_index, child in enumerate(item.interface_classes):
        _validate_interface_family(
            child,
            f"{path}.InterfaceClass[{child_index}]",
            index,
            issues,
        )


def _validate_interface_like(
    item: InterfaceClass,
    path: str,
    index: ReferenceIndex,
    issues: list[CAEXIssue],
) -> None:
    if item.ref_base_class_path:
        issue = _expect_reference(
            index.resolve_interface_class(item.ref_base_class_path),
            path=f"{path}.RefBaseClassPath",
            value=item.ref_base_class_path,
            code="unresolved-interface-class-reference",
            target_kind="InterfaceClass",
            suggestion=(
                "Define the referenced InterfaceClass or update RefBaseClassPath."
            ),
        )
        if issue:
            issues.append(issue)
    for attr_index, attribute in enumerate(item.attributes):
        _validate_attribute(
            attribute,
            f"{path}.Attribute[{attr_index}]",
            index,
            issues,
        )
    for interface_index, interface in enumerate(item.external_interfaces):
        _validate_interface_like(
            interface,
            f"{path}.ExternalInterface[{interface_index}]",
            index,
            issues,
        )


def _validate_attribute_type(
    item: AttributeType,
    path: str,
    index: ReferenceIndex,
    issues: list[CAEXIssue],
) -> None:
    _validate_attribute(item, path, index, issues)
    for child_index, child in enumerate(item.attribute_types):
        _validate_attribute_type(
            child,
            f"{path}.AttributeType[{child_index}]",
            index,
            issues,
        )


def _validate_attribute(
    item: Attribute,
    path: str,
    index: ReferenceIndex,
    issues: list[CAEXIssue],
) -> None:
    if item.ref_attribute_type:
        issue = _expect_reference(
            index.resolve_attribute_type(item.ref_attribute_type),
            path=f"{path}.RefAttributeType",
            value=item.ref_attribute_type,
            code="unresolved-attribute-type-reference",
            target_kind="AttributeType",
            suggestion="Define the referenced AttributeType or update RefAttributeType.",
        )
        if issue:
            issues.append(issue)
    for child_index, child in enumerate(item.attributes):
        _validate_attribute(
            child,
            f"{path}.Attribute[{child_index}]",
            index,
            issues,
        )


def _validate_internal_link(
    item: InternalLink,
    path: str,
    owner: SystemUnitClass,
    issues: list[CAEXIssue],
) -> None:
    partner_references = _external_interface_partner_references(owner)
    for alias, value in (
        ("RefPartnerSideA", item.ref_partner_side_a),
        ("RefPartnerSideB", item.ref_partner_side_b),
    ):
        if canonical_partner_reference(value) in partner_references:
            continue
        issues.append(
            CAEXIssue(
                severity="error",
                path=f"{path}.{alias}",
                message=(
                    f"InternalLink partner '{value}' does not match an "
                    "ExternalInterface in the owning element tree."
                ),
                code="unresolved-internal-link-partner",
                target=value,
                suggestion=(
                    "Use '<InternalElement ID>:<ExternalInterface Name>' for "
                    "an interface below the same owning element."
                ),
            )
        )


def _external_interface_partner_references(owner: SystemUnitClass) -> set[str]:
    references = {
        canonical_id(interface.id)
        for interface in owner.external_interfaces
        if interface.id is not None
    }
    for element in owner.internal_elements:
        if element.id is not None:
            references.update(
                f"{canonical_id(element.id)}:{interface.name}"
                for interface in element.external_interfaces
            )
        references.update(_external_interface_partner_references(element))
    return references


def _expect_reference(
    target: ReferenceTarget | None,
    *,
    path: str,
    value: str,
    code: str,
    target_kind: str,
    suggestion: str,
) -> CAEXIssue | None:
    if target is not None:
        return None
    return CAEXIssue(
        severity="error",
        path=path,
        message=f"Unresolved {target_kind} reference '{value}'.",
        code=code,
        target=value,
        suggestion=suggestion,
    )


def _required_issue(path: str) -> CAEXIssue:
    return CAEXIssue(
        severity="error",
        path=path,
        message=f"{path.rsplit('.', 1)[-1]} is required.",
        code="missing-required-xsd-field",
        suggestion="Provide this field when strict XSD validation is enabled.",
    )


def _join_aml_path(*parts: str) -> str:
    return "/".join(part.strip("/") for part in parts if part)


def _single_target(targets: list[ReferenceTarget] | None) -> ReferenceTarget | None:
    if not targets or len(targets) != 1:
        return None
    return targets[0]
