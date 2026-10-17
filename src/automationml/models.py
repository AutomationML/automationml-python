"""JSON-first AutomationML CAEX 3.0 domain models.

The public Python API uses readable snake_case field names. JSON import/export uses
the canonical CAEX/AML names through Pydantic aliases, for example
``instance_hierarchies`` <-> ``InstanceHierarchy``.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from enum import Enum
from typing import TYPE_CHECKING, Annotated, Any, Callable, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .exceptions import CAEXValidationError

if TYPE_CHECKING:
    from rdflib import Graph

    from .opcua import OPCUARoundTripResult
    from .opcua_nodeset import UANodeSet
    from .changes import DocumentEdit
    from .legacy import AMLImportResult
    from .query import CAEXQuery
    from .rdf import RDFRoundTripResult
    from .rdf_mapping import RDFMappingProfile
    from .validation import CAEXIssue, ReferenceIndex


class ChangeMode(str, Enum):
    """CAEX change state for an element."""

    STATE = "state"
    CREATE = "create"
    DELETE = "delete"
    CHANGE = "change"


def _clean_aml_payload(value: Any, *, include_change_mode: bool) -> Any:
    if isinstance(value, list):
        cleaned = [
            _clean_aml_payload(item, include_change_mode=include_change_mode)
            for item in value
        ]
        return [item for item in cleaned if item not in ({}, [], None)]

    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for key, item in value.items():
            next_item = _clean_aml_payload(
                item, include_change_mode=include_change_mode
            )
            if next_item in ({}, [], None):
                continue
            if (
                key == "ChangeMode"
                and next_item == ChangeMode.STATE.value
                and not include_change_mode
            ):
                continue
            cleaned[key] = next_item
        return cleaned

    return value


class AmlModel(BaseModel):
    """Base model with AML JSON helpers."""

    model_config = ConfigDict(
        populate_by_name=True,
        extra="forbid",
        validate_assignment=True,
        use_enum_values=True,
    )

    def to_aml_dict(
        self,
        *,
        include_change_mode: bool = False,
        prune_empty: bool = True,
    ) -> dict[str, Any]:
        """Return canonical AML JSON with CAEX/PascalCase keys."""

        data = self.model_dump(by_alias=True, mode="json", exclude_none=True)
        if prune_empty:
            data = _clean_aml_payload(
                data, include_change_mode=include_change_mode
            )
        return data

    def to_aml_json(
        self,
        *,
        indent: int | None = 2,
        include_change_mode: bool = False,
        prune_empty: bool = True,
    ) -> str:
        """Serialize to readable AML JSON."""

        return json.dumps(
            self.to_aml_dict(
                include_change_mode=include_change_mode,
                prune_empty=prune_empty,
            ),
            indent=indent,
            ensure_ascii=False,
        )

    @classmethod
    def from_aml_dict(cls, data: dict[str, Any]) -> Self:
        """Validate an AML JSON dictionary into a model."""

        return cls.model_validate(data)

    @classmethod
    def from_aml_json(cls, data: str | bytes) -> Self:
        """Validate an AML JSON string into a model."""

        return cls.model_validate_json(data)


class TextElement(AmlModel):
    """Simple CAEX text element with an optional ChangeMode attribute."""

    value: Annotated[
        str, Field(alias="value", description="Text content of the XML element.")
    ] = ""
    change_mode: Annotated[
        ChangeMode, Field(alias="ChangeMode", description="Optional CAEX change state.")
    ] = ChangeMode.STATE


class XmlExtensionNode(AmlModel):
    """Namespace-aware XML element stored inside ``AdditionalInformation``.

    Names use ElementTree's expanded-name form (``{namespace}local``). ``text``
    is the content before the first child and every child's ``tail`` is the
    content immediately following that child, which preserves mixed-content
    ordering without preserving insignificant lexical formatting.
    """

    name: Annotated[str, Field(alias="Name")]
    attributes: Annotated[
        dict[str, str], Field(alias="Attributes")
    ] = Field(default_factory=dict)
    text: Annotated[str | None, Field(alias="Text")] = None
    tail: Annotated[str | None, Field(alias="Tail")] = None
    children: Annotated[
        list[XmlExtensionNode], Field(alias="Children")
    ] = Field(default_factory=list)


class XmlExtensionPayload(AmlModel):
    """Non-trivial XML content carried by ``AdditionalInformation``."""

    attributes: Annotated[
        dict[str, str], Field(alias="Attributes")
    ] = Field(default_factory=dict)
    children: Annotated[
        list[XmlExtensionNode], Field(alias="Children")
    ] = Field(default_factory=list)


class AdditionalInformation(TextElement):
    """Auxiliary object information.

    CAEX 3.0 leaves this element open. The SDK keeps common AutomationML fields
    explicit while allowing association-specific extensions.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        extra="allow",
        validate_assignment=True,
        use_enum_values=True,
    )

    aml_version: Annotated[str | None, Field(alias="AutomationMLVersion")] = None
    document_versions: Annotated[str | None, Field(alias="DocumentVersions")] = None
    xml: Annotated[XmlExtensionPayload | None, Field(alias="$xml")] = None


class SourceObjectInformation(TextElement):
    """Source object metadata attached to a CAEX object."""

    origin_id: Annotated[str | None, Field(alias="OriginID")] = None
    source_obj_id: Annotated[str | None, Field(alias="SourceObjID")] = None


class Revision(AmlModel):
    """Revision entry in a CAEX header."""

    change_mode: Annotated[ChangeMode, Field(alias="ChangeMode")] = ChangeMode.STATE
    revision_date: Annotated[datetime | None, Field(alias="RevisionDate")] = None
    old_version: Annotated[str | None, Field(alias="OldVersion")] = None
    new_version: Annotated[str | None, Field(alias="NewVersion")] = None
    author_name: Annotated[str | None, Field(alias="AuthorName")] = None
    comment: Annotated[str | None, Field(alias="Comment")] = None


class CAEXBasicObject(AmlModel):
    """Base CAEX object carrying header data and change state."""

    description: Annotated[
        TextElement | None,
        Field(alias="Description", description="Textual description for CAEX objects."),
    ] = None
    version: Annotated[
        TextElement | None,
        Field(alias="Version", description="Organizational version information."),
    ] = None
    revision: Annotated[
        list[Revision], Field(alias="Revision", description="Revision history entries.")
    ] = Field(default_factory=list)
    copyright: Annotated[TextElement | None, Field(alias="Copyright")] = None
    additional_information: Annotated[
        list[AdditionalInformation], Field(alias="AdditionalInformation")
    ] = Field(default_factory=list)
    source_object_information: Annotated[
        list[SourceObjectInformation], Field(alias="SourceObjectInformation")
    ] = Field(default_factory=list)
    change_mode: Annotated[
        ChangeMode, Field(alias="ChangeMode", description="Optional CAEX change state.")
    ] = ChangeMode.STATE


class CAEXObject(CAEXBasicObject):
    """Named CAEX object with an optional identifier."""

    id: Annotated[
        str | None,
        Field(alias="ID", description="Optional unique identifier of the CAEX object."),
    ] = None
    name: Annotated[str, Field(alias="Name", description="Required CAEX object name.")]


class SourceDocumentInformation(AmlModel):
    """Information about a source document that contributed to the CAEX file."""

    origin_name: Annotated[str | None, Field(alias="OriginName")] = None
    origin_id: Annotated[str | None, Field(alias="OriginID")] = None
    origin_vendor: Annotated[str | None, Field(alias="OriginVendor")] = None
    origin_vendor_url: Annotated[str | None, Field(alias="OriginVendorURL")] = None
    origin_version: Annotated[str | None, Field(alias="OriginVersion")] = None
    origin_release: Annotated[str | None, Field(alias="OriginRelease")] = None
    last_writing_date_time: Annotated[
        datetime | None, Field(alias="LastWritingDateTime")
    ] = None
    origin_project_title: Annotated[
        str | None, Field(alias="OriginProjectTitle")
    ] = None
    origin_project_id: Annotated[str | None, Field(alias="OriginProjectID")] = None


class ExternalReference(CAEXBasicObject):
    """Alias definition for an external CAEX file."""

    path: Annotated[str, Field(alias="Path")]
    file_alias: Annotated[str, Field(alias="Alias")]


class AttributeNameMapping(CAEXBasicObject):
    """Mapping between system-unit and role attributes."""

    system_unit_attribute_name: Annotated[str, Field(alias="SystemUnitAttributeName")]
    role_attribute_name: Annotated[str, Field(alias="RoleAttributeName")]


class InterfaceIDMapping(CAEXBasicObject):
    """Mapping between system-unit and role interface IDs."""

    system_unit_interface_id: Annotated[str, Field(alias="SystemUnitInterfaceID")]
    role_interface_id: Annotated[str, Field(alias="RoleInterfaceID")]


class MappingObject(CAEXBasicObject):
    """Host object for CAEX attribute and interface mappings."""

    attribute_name_mapping: Annotated[
        list[AttributeNameMapping], Field(alias="AttributeNameMapping")
    ] = Field(default_factory=list)
    interface_id_mapping: Annotated[
        list[InterfaceIDMapping], Field(alias="InterfaceIDMapping")
    ] = Field(default_factory=list)


class OrdinalScaledType(AmlModel):
    """Ordinal value constraint."""

    required_max_value: Annotated[str | None, Field(alias="RequiredMaxValue")] = None
    required_value: Annotated[str | None, Field(alias="RequiredValue")] = None
    required_min_value: Annotated[str | None, Field(alias="RequiredMinValue")] = None


class NominalScaledType(AmlModel):
    """Nominal value constraint."""

    required_values: Annotated[
        list[str], Field(alias="RequiredValue")
    ] = Field(default_factory=list)


class UnknownType(AmlModel):
    """Free-form value requirement."""

    requirements: Annotated[str | None, Field(alias="Requirements")] = None


class AttributeValueRequirement(CAEXBasicObject):
    """Constraint for an attribute value."""

    name: Annotated[str, Field(alias="Name")]
    ordinal_scaled_type: Annotated[
        OrdinalScaledType | None, Field(alias="OrdinalScaledType")
    ] = None
    nominal_scaled_type: Annotated[
        NominalScaledType | None, Field(alias="NominalScaledType")
    ] = None
    unknown_type: Annotated[UnknownType | None, Field(alias="UnknownType")] = None

    @model_validator(mode="after")
    def _warn_about_multiple_constraint_shapes(self) -> Self:
        choices = [
            self.ordinal_scaled_type,
            self.nominal_scaled_type,
            self.unknown_type,
        ]
        if sum(choice is not None for choice in choices) > 1:
            raise ValueError(
                "AttributeValueRequirement may use only one of "
                "OrdinalScaledType, NominalScaledType, or UnknownType."
            )
        return self


class RefSemantic(CAEXBasicObject):
    """Semantic reference for an attribute."""

    corresponding_attribute_path: Annotated[
        str, Field(alias="CorrespondingAttributePath")
    ]


class Attribute(CAEXObject):
    """CAEX attribute instance."""

    default_value: Annotated[str | None, Field(alias="DefaultValue")] = None
    value: Annotated[str | None, Field(alias="Value")] = None
    ref_semantic: Annotated[
        list[RefSemantic], Field(alias="RefSemantic")
    ] = Field(default_factory=list)
    constraint: Annotated[
        list[AttributeValueRequirement], Field(alias="Constraint")
    ] = Field(default_factory=list)
    attributes: Annotated[
        list[Attribute], Field(alias="Attribute")
    ] = Field(default_factory=list)
    unit: Annotated[str | None, Field(alias="Unit")] = None
    attribute_data_type: Annotated[str | None, Field(alias="AttributeDataType")] = None
    ref_attribute_type: Annotated[str | None, Field(alias="RefAttributeType")] = None


class AttributeType(Attribute):
    """Attribute type definition inside an AttributeTypeLib."""

    attribute_types: Annotated[
        list[AttributeType], Field(alias="AttributeType")
    ] = Field(default_factory=list)


class InterfaceClass(CAEXObject):
    """Interface class or external interface."""

    attributes: Annotated[
        list[Attribute], Field(alias="Attribute")
    ] = Field(default_factory=list)
    external_interfaces: Annotated[
        list[InterfaceClass], Field(alias="ExternalInterface")
    ] = Field(default_factory=list)
    ref_base_class_path: Annotated[str | None, Field(alias="RefBaseClassPath")] = None


class InterfaceFamily(InterfaceClass):
    """Hierarchical interface class definition."""

    interface_classes: Annotated[
        list[InterfaceFamily], Field(alias="InterfaceClass")
    ] = Field(default_factory=list)


class RoleClass(CAEXObject):
    """Role class definition."""

    attributes: Annotated[
        list[Attribute], Field(alias="Attribute")
    ] = Field(default_factory=list)
    external_interfaces: Annotated[
        list[InterfaceClass], Field(alias="ExternalInterface")
    ] = Field(default_factory=list)
    ref_base_class_path: Annotated[str | None, Field(alias="RefBaseClassPath")] = None


class RoleFamily(RoleClass):
    """Hierarchical role class definition."""

    role_classes: Annotated[
        list[RoleFamily], Field(alias="RoleClass")
    ] = Field(default_factory=list)


class SupportedRoleClass(CAEXBasicObject):
    """Role class supported by a system unit class."""

    ref_role_class_path: Annotated[str, Field(alias="RefRoleClassPath")]
    mapping_object: Annotated[MappingObject | None, Field(alias="MappingObject")] = None


class InternalLink(CAEXObject):
    """Relationship between internal interfaces."""

    ref_partner_side_a: Annotated[str, Field(alias="RefPartnerSideA")]
    ref_partner_side_b: Annotated[str, Field(alias="RefPartnerSideB")]


class SystemUnitClass(CAEXObject):
    """System unit class definition."""

    attributes: Annotated[
        list[Attribute], Field(alias="Attribute")
    ] = Field(default_factory=list)
    external_interfaces: Annotated[
        list[InterfaceClass], Field(alias="ExternalInterface")
    ] = Field(default_factory=list)
    internal_elements: Annotated[
        list[InternalElement], Field(alias="InternalElement")
    ] = Field(default_factory=list)
    supported_role_classes: Annotated[
        list[SupportedRoleClass], Field(alias="SupportedRoleClass")
    ] = Field(default_factory=list)
    internal_links: Annotated[
        list[InternalLink], Field(alias="InternalLink")
    ] = Field(default_factory=list)


class RoleRequirements(CAEXBasicObject):
    """Role requirements attached to an internal element."""

    attributes: Annotated[
        list[Attribute], Field(alias="Attribute")
    ] = Field(default_factory=list)
    external_interfaces: Annotated[
        list[InterfaceClass], Field(alias="ExternalInterface")
    ] = Field(default_factory=list)
    mapping_object: Annotated[MappingObject | None, Field(alias="MappingObject")] = None
    ref_base_role_class_path: Annotated[str, Field(alias="RefBaseRoleClassPath")]


class InternalElement(SystemUnitClass):
    """Hierarchical object instance in an InstanceHierarchy or SystemUnitClass."""

    role_requirements: Annotated[
        list[RoleRequirements], Field(alias="RoleRequirements")
    ] = Field(default_factory=list)
    ref_base_system_unit_path: Annotated[
        str | None, Field(alias="RefBaseSystemUnitPath")
    ] = None


class SystemUnitFamily(SystemUnitClass):
    """Hierarchical SystemUnitClass tree entry."""

    system_unit_classes: Annotated[
        list[SystemUnitFamily], Field(alias="SystemUnitClass")
    ] = Field(default_factory=list)
    ref_base_class_path: Annotated[str | None, Field(alias="RefBaseClassPath")] = None


class InstanceHierarchy(CAEXObject):
    """Root element for a system hierarchy of object instances."""

    internal_elements: Annotated[
        list[InternalElement], Field(alias="InternalElement")
    ] = Field(default_factory=list)


class InterfaceClassLib(CAEXObject):
    """Container for interface class definitions."""

    interface_classes: Annotated[
        list[InterfaceFamily], Field(alias="InterfaceClass")
    ] = Field(default_factory=list)


class RoleClassLib(CAEXObject):
    """Container for role class definitions."""

    role_classes: Annotated[
        list[RoleFamily], Field(alias="RoleClass")
    ] = Field(default_factory=list)


class SystemUnitClassLib(CAEXObject):
    """Container for system unit class definitions."""

    system_unit_classes: Annotated[
        list[SystemUnitFamily], Field(alias="SystemUnitClass")
    ] = Field(default_factory=list)


class AttributeTypeLib(CAEXObject):
    """Container for attribute type definitions."""

    attribute_types: Annotated[
        list[AttributeType], Field(alias="AttributeType")
    ] = Field(default_factory=list)


class CAEXFile(CAEXBasicObject):
    """Root AutomationML CAEX 3.0 document."""

    superior_standard_versions: Annotated[
        list[str], Field(alias="SuperiorStandardVersion")
    ] = Field(default_factory=list)
    source_document_information: Annotated[
        list[SourceDocumentInformation], Field(alias="SourceDocumentInformation")
    ] = Field(default_factory=list)
    external_references: Annotated[
        list[ExternalReference], Field(alias="ExternalReference")
    ] = Field(default_factory=list)
    instance_hierarchies: Annotated[
        list[InstanceHierarchy], Field(alias="InstanceHierarchy")
    ] = Field(default_factory=list)
    interface_class_libs: Annotated[
        list[InterfaceClassLib], Field(alias="InterfaceClassLib")
    ] = Field(default_factory=list)
    role_class_libs: Annotated[
        list[RoleClassLib], Field(alias="RoleClassLib")
    ] = Field(default_factory=list)
    system_unit_class_libs: Annotated[
        list[SystemUnitClassLib], Field(alias="SystemUnitClassLib")
    ] = Field(default_factory=list)
    attribute_type_libs: Annotated[
        list[AttributeTypeLib], Field(alias="AttributeTypeLib")
    ] = Field(default_factory=list)
    schema_version: Annotated[
        str,
        Field(
            alias="SchemaVersion",
            description="CAEX schema version. CAEX 3.0 documents use fixed value 3.0.",
        ),
    ] = "3.0"
    file_name: Annotated[str, Field(alias="FileName")]

    def reference_index(self) -> ReferenceIndex:
        """Return an index for resolving in-document AML paths and IDs."""

        from .validation import ReferenceIndex

        return ReferenceIndex.from_document(self)

    def query(self, *, externals: dict[str, CAEXFile] | None = None) -> CAEXQuery:
        """Build a fresh immutable query snapshot for this document."""

        from .query import CAEXQuery

        return CAEXQuery.from_document(self, externals=externals)

    def instantiate_system_unit_class(
        self,
        path: str,
        *,
        name: str,
        id: str | None = None,
        id_factory: Callable[[], str] | None = None,
    ) -> InternalElement:
        """Materialize a SystemUnitClass and its inheritance as an instance."""

        from .instantiation import instantiate_system_unit_class

        return instantiate_system_unit_class(
            self,
            path,
            name=name,
            id=id,
            id_factory=id_factory,
        )

    def edit(self) -> DocumentEdit:
        """Create a non-mutating transactional edit context."""

        from .changes import DocumentEdit

        return DocumentEdit(self)

    def caex_validation_issues(
        self,
        *,
        strict_xsd: bool = False,
    ) -> list[CAEXIssue]:
        """Return structured CAEX conformance and semantic issues."""

        from .validation import validate_caex_document

        return validate_caex_document(self, strict_xsd=strict_xsd)

    def caex_issues(self, *, strict_xsd: bool = False) -> list[str]:
        """Return human-readable CAEX conformance issues."""

        return [
            f"{issue.path}: {issue.message}"
            for issue in self.caex_validation_issues(strict_xsd=strict_xsd)
        ]

    def assert_caex_valid(self, *, strict_xsd: bool = False) -> None:
        """Raise if the document violates the selected CAEX conformance level."""

        issues = self.caex_issues(strict_xsd=strict_xsd)
        if issues:
            raise CAEXValidationError("; ".join(issues))

    def to_aml_xml(self, **kwargs: Any) -> str:
        """Serialize the document to CAEX XML."""

        from .xml import dumps

        return dumps(self, **kwargs)

    def to_opcua_nodeset_xml(
        self,
        *,
        pretty: bool = True,
        include_roundtrip: bool = False,
        publication_date: date | datetime | str | None = None,
    ) -> str:
        """Convert the document to an OPC UA UANodeSet XML document."""

        from .opcua import document_to_nodeset

        return document_to_nodeset(
            self,
            pretty=pretty,
            include_roundtrip=include_roundtrip,
            publication_date=publication_date,
        )

    def to_opcua_nodeset(
        self,
        *,
        publication_date: date | datetime | str | None = None,
    ) -> UANodeSet:
        """Build the validated Python OPC UA graph without serializing XML."""

        from .opcua import document_to_nodeset_model

        return document_to_nodeset_model(
            self,
            publication_date=publication_date,
        )

    def round_trip_opcua(
        self,
        *,
        pretty: bool = True,
        publication_date: date | datetime | str | None = None,
    ) -> OPCUARoundTripResult:
        """Run and inspect a semantic AML -> OPC UA -> AML round trip.

        The original AML is deliberately not embedded in the NodeSet. Call
        ``result.assert_equivalent()`` when semantic preservation is required.
        """

        from .opcua import round_trip_document

        return round_trip_document(
            self,
            pretty=pretty,
            publication_date=publication_date,
        )

    @classmethod
    def from_aml_xml(cls, data: str | bytes) -> CAEXFile:
        """Parse CAEX XML, automatically upgrading CAEX 2.15 to CAEX 3.0."""

        from .legacy import import_aml_xml

        return import_aml_xml(data, warn_legacy=True).document

    @classmethod
    def import_aml_xml(cls, data: str | bytes) -> AMLImportResult:
        """Parse AML XML and return import or legacy-migration diagnostics."""

        from .legacy import import_aml_xml

        return import_aml_xml(data)

    @classmethod
    def from_opcua_nodeset_xml(
        cls,
        data: str | bytes,
        *,
        prefer_embedded_source: bool = True,
    ) -> CAEXFile:
        """Convert a UANodeSet through source recovery or semantic mapping."""

        from .opcua import nodeset_to_document

        return nodeset_to_document(
            data,
            prefer_embedded_source=prefer_embedded_source,
        )

    @classmethod
    def from_opcua_nodeset(cls, nodeset: UANodeSet) -> CAEXFile:
        """Map a typed OPC UA graph directly to canonical AutomationML."""

        from .opcua import nodeset_to_document

        return nodeset_to_document(
            nodeset,
            prefer_embedded_source=False,
        )

    def to_rdf_graph(
        self,
        *,
        profile: RDFMappingProfile | None = None,
    ) -> Graph:
        """Build the validated Python RDF graph without serializing Turtle."""

        from .rdf import DEFAULT_MAPPING_PROFILE, document_to_rdf_graph

        return document_to_rdf_graph(self, profile=profile or DEFAULT_MAPPING_PROFILE)

    def to_ttl(
        self,
        *,
        profile: RDFMappingProfile | None = None,
    ) -> str:
        """Convert the document to Turtle (RDF) text.

        This is the Python replacement for the legacy ``AML2TTL.xslt``
        export; see ``docs/rdf-mapping-audit.md`` for why. The default
        profile reproduces the legacy stylesheet's target namespace.
        """

        from .rdf import DEFAULT_MAPPING_PROFILE, document_to_ttl

        return document_to_ttl(self, profile=profile or DEFAULT_MAPPING_PROFILE)

    def round_trip_ttl(
        self,
        *,
        profile: RDFMappingProfile | None = None,
    ) -> RDFRoundTripResult:
        """Run and inspect a semantic AML -> Turtle -> AML round trip.

        Call ``result.assert_equivalent()`` when semantic preservation is
        required; ``result.differences`` gives JSON-Pointer-addressed detail
        when it is not.
        """

        from .rdf import DEFAULT_MAPPING_PROFILE, round_trip_ttl

        return round_trip_ttl(self, profile=profile or DEFAULT_MAPPING_PROFILE)

    @classmethod
    def from_ttl(
        cls,
        data: str | bytes,
        *,
        profile: RDFMappingProfile | None = None,
    ) -> CAEXFile:
        """Parse Turtle text produced by this profile back into a CAEX document."""

        from .rdf import DEFAULT_MAPPING_PROFILE, ttl_to_document

        return ttl_to_document(data, profile=profile or DEFAULT_MAPPING_PROFILE)

    @classmethod
    def from_rdf_graph(
        cls,
        graph: Graph,
        *,
        profile: RDFMappingProfile | None = None,
    ) -> CAEXFile:
        """Reconstruct a CAEX document from an already-parsed RDF graph."""

        from .rdf import DEFAULT_MAPPING_PROFILE, rdf_graph_to_document

        return rdf_graph_to_document(graph, profile=profile or DEFAULT_MAPPING_PROFILE)


for model in (
    XmlExtensionNode,
    Attribute,
    AttributeType,
    InterfaceClass,
    InterfaceFamily,
    RoleClass,
    RoleFamily,
    SystemUnitClass,
    InternalElement,
    SystemUnitFamily,
    InstanceHierarchy,
):
    model.model_rebuild()
