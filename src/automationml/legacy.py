"""Version-detecting AML XML import and one-way CAEX 2.15 migration."""

from __future__ import annotations

import warnings
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from importlib.resources import files
from typing import Literal
from uuid import NAMESPACE_URL, uuid5
from xml.etree import ElementTree as ET

import xmlschema

from .exceptions import LegacyConversionError, LegacyConversionWarning
from .models import CAEXFile, InternalElement, RoleRequirements, SourceDocumentInformation

CAEX_NS = "http://www.dke.de/CAEX"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"


@dataclass(frozen=True, slots=True)
class MigrationIssue:
    severity: Literal["warning", "info"]
    code: str
    path: str
    message: str


@dataclass(frozen=True, slots=True)
class AMLImportResult:
    document: CAEXFile
    source_schema_version: str
    converted: bool
    issues: tuple[MigrationIssue, ...] = ()


def import_aml_xml(
    data: str | bytes,
    *,
    warn_legacy: bool = False,
) -> AMLImportResult:
    """Import CAEX 3.0 or atomically upgrade supported CAEX 2.15 input."""

    raw = data.encode("utf-8") if isinstance(data, str) else data
    from .xml import parse_xml_element

    try:
        root = parse_xml_element(raw)
    except (ET.ParseError, ValueError) as exc:
        raise LegacyConversionError(f"Invalid AML XML: {exc}") from exc
    if _local(root.tag) != "CAEXFile":
        raise LegacyConversionError(f"Expected CAEXFile root, got {_local(root.tag)!r}")

    version = root.get("SchemaVersion", "")
    namespace = _namespace(root.tag)
    if version != "2.15" and (version.startswith("3") or namespace == CAEX_NS):
        from .xml import loads

        return AMLImportResult(
            document=loads(raw),
            source_schema_version=version or "3.0",
            converted=False,
        )
    if version != "2.15":
        raise LegacyConversionError(
            f"Unsupported CAEX schema version {version!r}; expected 2.15 or 3.0"
        )

    try:
        _legacy_schema().validate(raw)
    except xmlschema.XMLSchemaValidationError as exc:
        raise LegacyConversionError(
            f"CAEX 2.15 input does not validate against the pinned schema: {exc.reason}"
        ) from exc

    upgraded, issues = _upgrade_215(root)
    from .xml import loads

    document = loads(ET.tostring(upgraded, encoding="utf-8"))
    result = AMLImportResult(
        document=document,
        source_schema_version="2.15",
        converted=True,
        issues=tuple(issues),
    )
    if warn_legacy:
        warnings.warn(
            "CAEX 2.15 input was upgraded to CAEX 3.0; use "
            "CAEXFile.import_aml_xml() to inspect migration diagnostics.",
            LegacyConversionWarning,
            stacklevel=3,
        )
    return result


def upgrade_legacy_model(document: CAEXFile) -> CAEXFile:
    """Canonicalize a semantically reconstructed CAEX 2.15 model to 3.0."""

    if document.schema_version != "2.15":
        return document
    upgraded = document.model_copy(deep=True)
    upgraded.schema_version = "3.0"
    if not upgraded.source_document_information:
        upgraded.source_document_information.append(
            SourceDocumentInformation(
                origin_name="CAEX 2.15 import",
                origin_id="automationml-python-legacy-import",
                origin_version="1",
                last_writing_date_time=datetime(1970, 1, 1, tzinfo=timezone.utc),
            )
        )
    for model in _walk_model_objects(upgraded):
        if not isinstance(model, InternalElement) or not model.supported_role_classes:
            continue
        existing = {item.ref_base_role_class_path for item in model.role_requirements}
        for supported in model.supported_role_classes:
            if supported.ref_role_class_path not in existing:
                model.role_requirements.append(
                    RoleRequirements(
                        ref_base_role_class_path=supported.ref_role_class_path,
                        mapping_object=supported.mapping_object.model_copy(deep=True)
                        if supported.mapping_object is not None
                        else None,
                    )
                )
        model.supported_role_classes = []
    return upgraded


@lru_cache(maxsize=1)
def _legacy_schema() -> xmlschema.XMLSchema:
    schema = (
        files("automationml")
        .joinpath("resources", "caex", "CAEX_ClassModel_V2.15.xsd")
        .read_text(encoding="utf-8")
    )
    return xmlschema.XMLSchema(schema)


def _upgrade_215(root: ET.Element) -> tuple[ET.Element, list[MigrationIssue]]:
    issues: list[MigrationIssue] = []
    root.set("SchemaVersion", "3.0")
    root.attrib.pop(f"{{{XSI_NS}}}noNamespaceSchemaLocation", None)
    root.set(
        f"{{{XSI_NS}}}schemaLocation",
        f"{CAEX_NS} CAEX_ClassModel_V.3.0.xsd",
    )

    source_documents = _extract_writer_headers(root, issues)
    if not source_documents:
        source_documents.append(
            _source_document_element(
                {
                    "OriginName": "CAEX 2.15 import",
                    "OriginID": "automationml-python-legacy-import",
                    "OriginVersion": "1",
                    "LastWritingDateTime": "1970-01-01T00:00:00+00:00",
                }
            )
        )
        issues.append(
            MigrationIssue(
                severity="warning",
                code="synthesized-source-document-information",
                path="/CAEXFile",
                message="The legacy file had no WriterHeader; deterministic source metadata was added.",
            )
        )
    insert_at = 0
    while insert_at < len(root) and _local(root[insert_at].tag) in {
        "Description",
        "Version",
        "Revision",
        "Copyright",
        "AdditionalInformation",
        "SourceObjectInformation",
        "SuperiorStandardVersion",
    }:
        insert_at += 1
    for source in reversed(source_documents):
        root.insert(insert_at, source)

    _convert_legacy_roles_and_mappings(root, issues)
    _clean_mirror_objects(root, issues)
    _convert_internal_link_partners(root, issues)
    _namespace_caex_tree(root)
    issues.append(
        MigrationIssue(
            severity="info",
            code="schema-upgraded",
            path="/CAEXFile/@SchemaVersion",
            message="CAEX 2.15 was upgraded to CAEX 3.0.",
        )
    )
    return root, issues


def _extract_writer_headers(
    root: ET.Element,
    issues: list[MigrationIssue],
) -> list[ET.Element]:
    result: list[ET.Element] = []
    for additional in list(root):
        if _local(additional.tag) != "AdditionalInformation":
            continue
        writers = [child for child in additional if _local(child.tag) == "WriterHeader"]
        if not writers:
            continue
        for writer in writers:
            values = {_local(child.tag): (child.text or "").strip() for child in writer}
            last_write = values.get("LastWritingDateTime") or "1970-01-01T00:00:00+00:00"
            try:
                datetime.fromisoformat(last_write.replace("Z", "+00:00"))
            except ValueError:
                last_write = "1970-01-01T00:00:00+00:00"
                issues.append(
                    MigrationIssue(
                        severity="warning",
                        code="invalid-writer-date",
                        path="/CAEXFile/AdditionalInformation/WriterHeader/LastWritingDateTime",
                        message="An invalid WriterHeader date was replaced with the migration epoch.",
                    )
                )
            result.append(
                _source_document_element(
                    {
                        "OriginName": values.get("WriterName") or "Unknown legacy writer",
                        "OriginID": values.get("WriterID") or "unknown-legacy-writer",
                        "OriginVendor": values.get("WriterVendor"),
                        "OriginVendorURL": values.get("WriterVendorURL"),
                        "OriginVersion": values.get("WriterVersion") or "unknown",
                        "OriginRelease": values.get("WriterRelease"),
                        "LastWritingDateTime": last_write,
                        "OriginProjectTitle": values.get("WriterProjectTitle"),
                        "OriginProjectID": values.get("WriterProjectID"),
                    }
                )
            )
            if writer.tail and writer.tail.strip():
                position = list(additional).index(writer)
                if position:
                    previous = list(additional)[position - 1]
                    previous.tail = (previous.tail or "") + writer.tail
                else:
                    additional.text = (additional.text or "") + writer.tail
            additional.remove(writer)
        if (
            not list(additional)
            and not additional.attrib
            and not (additional.text or "").strip()
        ):
            root.remove(additional)
    if result:
        issues.append(
            MigrationIssue(
                severity="info",
                code="writer-header-converted",
                path="/CAEXFile/SourceDocumentInformation",
                message=f"Converted {len(result)} legacy WriterHeader record(s).",
            )
        )
    return result


def _source_document_element(values: dict[str, str | None]) -> ET.Element:
    return ET.Element(
        "SourceDocumentInformation",
        {name: value for name, value in values.items() if value not in (None, "")},
    )


def _convert_legacy_roles_and_mappings(
    root: ET.Element,
    issues: list[MigrationIssue],
) -> None:
    role_classes = _role_class_index(root)
    converted = 0
    for internal in (item for item in root.iter() if _local(item.tag) == "InternalElement"):
        requirements = [child for child in internal if _local(child.tag) == "RoleRequirements"]
        by_role = {item.get("RefBaseRoleClassPath"): item for item in requirements}
        supported = [child for child in internal if _local(child.tag) == "SupportedRoleClass"]
        for role in supported:
            role_path = role.get("RefRoleClassPath")
            if not role_path:
                raise LegacyConversionError("SupportedRoleClass without RefRoleClassPath cannot be upgraded")
            requirement = by_role.get(role_path)
            if requirement is None:
                requirement = ET.Element("RoleRequirements", {"RefBaseRoleClassPath": role_path})
                internal.append(requirement)
                by_role[role_path] = requirement
            _materialize_role_members(
                root, internal, requirement, role_path, role_classes, issues
            )
            mapping = next((child for child in role if _local(child.tag) == "MappingObject"), None)
            if mapping is not None:
                _merge_mapping(requirement, mapping, internal)
            internal.remove(role)
            converted += 1

        legacy_mapping = next(
            (child for child in internal if _local(child.tag) == "MappingObject"), None
        )
        if legacy_mapping is not None:
            if not requirements and not by_role:
                raise LegacyConversionError(
                    f"InternalElement {internal.get('Name')!r} has a MappingObject but no role target"
                )
            target = requirements[0] if requirements else next(iter(by_role.values()))
            _merge_mapping(target, legacy_mapping, internal)
            internal.remove(legacy_mapping)
            converted += 1
    if converted:
        issues.append(
            MigrationIssue(
                severity="info",
                code="legacy-role-mapping-converted",
                path="/CAEXFile//InternalElement",
                message=f"Converted {converted} legacy role or mapping construct(s).",
            )
        )


def _merge_mapping(requirement: ET.Element, source: ET.Element, owner: ET.Element) -> None:
    target = next((child for child in requirement if _local(child.tag) == "MappingObject"), None)
    if target is None:
        target = ET.SubElement(requirement, "MappingObject")
    for item in list(source):
        tag = _local(item.tag)
        if tag == "AttributeNameMapping":
            item.set("SystemUnitAttributeName", _canonical_attribute_path(item.get("SystemUnitAttributeName", "")))
            item.set("RoleAttributeName", _canonical_attribute_path(item.get("RoleAttributeName", "")))
            target.append(item)
        elif tag == "InterfaceNameMapping":
            system_name = item.get("SystemUnitInterfaceName", "")
            role_name = item.get("RoleInterfaceName", "")
            system_id = _interface_id(owner, system_name, create=True)
            role_id = _interface_id(requirement, role_name)
            if not system_id or not role_id:
                raise LegacyConversionError(
                    f"InterfaceNameMapping {system_name!r}->{role_name!r} cannot be resolved to IDs"
                )
            converted = ET.Element(
                "InterfaceIDMapping",
                {"SystemUnitInterfaceID": system_id, "RoleInterfaceID": role_id},
            )
            target.append(converted)


def _interface_id(owner: ET.Element, path: str, *, create: bool = False) -> str | None:
    parts = [part for part in path.replace(".", "/").split("/") if part]
    matches: list[ET.Element] = []

    def visit(element: ET.Element, names: tuple[str, ...]) -> None:
        for child in element:
            name = child.get("Name")
            child_names = (*names, name) if name else names
            if _local(child.tag) == "ExternalInterface" and (
                not parts or list(child_names[-len(parts) :]) == parts
            ):
                matches.append(child)
            visit(child, child_names)

    visit(owner, ())
    if len(matches) > 1:
        raise LegacyConversionError(
            f"Interface path {path!r} is ambiguous during migration"
        )
    if not matches:
        return None
    interface = matches[0]
    identifier = interface.get("ID")
    if identifier is None and create:
        identifier = str(
            uuid5(
                NAMESPACE_URL,
                f"legacy-interface:{owner.get('ID', owner.get('Name', ''))}:{path}",
            )
        )
        interface.set("ID", identifier)
    return identifier


def _role_class_index(root: ET.Element) -> dict[str, ET.Element]:
    result: dict[str, ET.Element] = {}
    for library in (item for item in root if _local(item.tag) == "RoleClassLib"):
        library_name = library.get("Name", "")

        def register(parent: ET.Element, prefix: str) -> None:
            for role in parent:
                if _local(role.tag) != "RoleClass":
                    continue
                path = f"{prefix}/{role.get('Name', '')}"
                result[path] = role
                register(role, path)

        register(library, library_name)
    return result


def _materialize_role_members(
    root: ET.Element,
    owner: ET.Element,
    requirement: ET.Element,
    role_path: str,
    role_classes: dict[str, ET.Element],
    issues: list[MigrationIssue],
) -> None:
    local_path = role_path.split("@", 1)[-1]
    role = role_classes.get(local_path)
    if role is None:
        return
    chain: list[ET.Element] = []
    seen: set[str] = set()
    current_path = local_path
    while role is not None:
        if current_path in seen:
            raise LegacyConversionError(
                f"RoleClass inheritance cycle at {current_path!r}"
            )
        seen.add(current_path)
        chain.append(role)
        base_path = role.get("RefBaseClassPath")
        if not base_path:
            break
        current_path = base_path.split("@", 1)[-1]
        role = role_classes.get(current_path)
        if role is None:
            if "@" in base_path or base_path.startswith("["):
                break
            # The document references a RoleClass that it does not carry, which
            # is normal for files that rely on the standard AutomationML
            # libraries. Migration stays non-destructive: inherited members are
            # materialized as far as the chain is known, the gap is reported,
            # and semantic validation still flags the unresolved reference.
            issues.append(
                MigrationIssue(
                    severity="warning",
                    code="unresolved-base-role-class",
                    path=f"/CAEXFile//RoleClass[@Name='{current_path}']",
                    message=(
                        f"Base RoleClass {base_path!r} is not defined in this "
                        f"document; inherited members of {role_path!r} were "
                        "materialized only from the resolvable part of the "
                        "inheritance chain."
                    ),
                )
            )
            break

    effective: dict[tuple[str, str], ET.Element] = {}
    order: list[tuple[str, str]] = []
    for definition in reversed(chain):
        for child in definition:
            kind = _local(child.tag)
            if kind not in {"Attribute", "ExternalInterface"}:
                continue
            key = (kind, child.get("Name", ""))
            if key not in effective:
                order.append(key)
            effective[key] = child

    existing = {
        (_local(child.tag), child.get("Name", ""))
        for child in requirement
        if _local(child.tag) in {"Attribute", "ExternalInterface"}
    }
    id_mapping: dict[str, str] = {}
    copies: list[ET.Element] = []
    for key in order:
        if key in existing:
            continue
        copied = deepcopy(effective[key])
        copies.append(copied)
        for item in copied.iter():
            old_id = item.get("ID")
            if old_id or _local(item.tag) == "ExternalInterface":
                new_id = str(
                    uuid5(
                        NAMESPACE_URL,
                        ":".join(
                            (
                                root.get("FileName", ""),
                                owner.get("ID", owner.get("Name", "")),
                                role_path,
                                _local(item.tag),
                                item.get("Name", ""),
                                old_id or "",
                            )
                        ),
                    )
                )
                if old_id:
                    id_mapping[old_id] = new_id
                item.set("ID", new_id)
    for copied in copies:
        for item in copied.iter():
            for attribute, value in list(item.attrib.items()):
                if value in id_mapping:
                    item.set(attribute, id_mapping[value])
        requirement.append(copied)


def _canonical_attribute_path(value: str) -> str:
    return "/".join(part for part in value.replace(".", "/").split("/") if part)


def _clean_mirror_objects(
    root: ET.Element,
    issues: list[MigrationIssue],
) -> None:
    """Apply the original C# upgrader's CAEX 3.0 mirror normalization.

    A legacy mirror is an InternalElement whose RefBaseSystemUnitPath resolves
    to another InternalElement ID.  CAEX 3.0 keeps the mirror empty: legacy
    attributes, interfaces, and child elements are moved to the master unless
    the master already has a same-named member.
    """

    elements = [item for item in root.iter() if _local(item.tag) == "InternalElement"]
    masters = {item.get("ID"): item for item in elements if item.get("ID")}
    normalized = 0
    moved = 0
    for mirror in elements:
        master = masters.get(mirror.get("RefBaseSystemUnitPath"))
        if master is None or master is mirror:
            continue
        changed = False
        for kind in ("InternalElement", "ExternalInterface", "Attribute"):
            existing_names = {
                child.get("Name")
                for child in master
                if _local(child.tag) == kind
            }
            for child in [item for item in mirror if _local(item.tag) == kind]:
                mirror.remove(child)
                changed = True
                if child.get("Name") not in existing_names:
                    master.append(child)
                    existing_names.add(child.get("Name"))
                    moved += 1
        if changed:
            normalized += 1
    if normalized:
        issues.append(
            MigrationIssue(
                severity="info",
                code="mirror-content-normalized",
                path="/CAEXFile//InternalElement",
                message=(
                    f"Normalized {normalized} legacy mirror object(s) and moved "
                    f"{moved} unique member(s) to their master objects."
                ),
            )
        )


def _convert_internal_link_partners(
    root: ET.Element,
    issues: list[MigrationIssue],
) -> None:
    interfaces: dict[tuple[str, str], str] = {}
    generated = 0
    for owner in (item for item in root.iter() if _local(item.tag) == "InternalElement"):
        owner_id = owner.get("ID")
        if not owner_id:
            continue
        for interface in owner:
            if _local(interface.tag) != "ExternalInterface":
                continue
            interface_id = interface.get("ID")
            if not interface_id:
                interface_id = str(
                    uuid5(
                        NAMESPACE_URL,
                        f"{root.get('FileName', '')}:{owner_id}:{interface.get('Name', '')}",
                    )
                )
                interface.set("ID", interface_id)
                generated += 1
            interfaces[(owner_id.strip("{}"), interface.get("Name", ""))] = interface_id

    converted = 0
    for link in (item for item in root.iter() if _local(item.tag) == "InternalLink"):
        for field in ("RefPartnerSideA", "RefPartnerSideB"):
            value = link.get(field)
            if not value or value in interfaces.values():
                continue
            if ":" not in value:
                raise LegacyConversionError(f"InternalLink partner {value!r} cannot be upgraded")
            owner_id, name = value.split(":", 1)
            resolved = interfaces.get((owner_id.strip("{}"), name))
            if resolved is None:
                raise LegacyConversionError(f"InternalLink partner {value!r} cannot be resolved")
            link.set(field, resolved)
            converted += 1
    if converted or generated:
        issues.append(
            MigrationIssue(
                severity="info",
                code="internal-link-partners-converted",
                path="/CAEXFile//InternalLink",
                message=(
                    f"Converted {converted} legacy link endpoint(s) and generated "
                    f"{generated} missing interface ID(s)."
                ),
            )
        )


def _namespace_caex_tree(element: ET.Element, *, in_additional: bool = False) -> None:
    local = _local(element.tag)
    if not in_additional and not _namespace(element.tag):
        element.tag = f"{{{CAEX_NS}}}{local}"
    child_extension = in_additional or local == "AdditionalInformation"
    for child in element:
        _namespace_caex_tree(child, in_additional=child_extension)


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _namespace(tag: str) -> str:
    return tag[1:].split("}", 1)[0] if tag.startswith("{") else ""


def _walk_model_objects(value):
    from .models import AmlModel

    if isinstance(value, AmlModel):
        yield value
        for field_name in type(value).model_fields:
            yield from _walk_model_objects(getattr(value, field_name))
    elif isinstance(value, list):
        for item in value:
            yield from _walk_model_objects(item)
