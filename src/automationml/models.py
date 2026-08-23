"""JSON-first AutomationML CAEX 3.0 domain models.

The public Python API uses readable snake_case field names. JSON import/export uses
the canonical CAEX/AML names through Pydantic aliases, for example
``instance_hierarchies`` <-> ``InstanceHierarchy``.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .exceptions import CAEXValidationError

if TYPE_CHECKING:
    from .opcua import OPCUARoundTripResult
    from .opcua_nodeset import UANodeSet
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

    value: str = Field(
        default="",
        alias="value",
        description="Text content of the XML element.",
    )
    change_mode: ChangeMode = Field(
        default=ChangeMode.STATE,
        alias="ChangeMode",
        description="Optional CAEX change state.",
    )


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

    aml_version: str | None = Field(default=None, alias="aml_version")
    document_versions: str | None = Field(default=None, alias="document_versions")


class SourceObjectInformation(TextElement):
    """Source object metadata attached to a CAEX object."""

    origin_id: str | None = Field(default=None, alias="OriginID")
    source_obj_id: str | None = Field(default=None, alias="SourceObjID")


class Revision(AmlModel):
    """Revision entry in a CAEX header."""

    change_mode: ChangeMode = Field(default=ChangeMode.STATE, alias="ChangeMode")
    revision_date: datetime | None = Field(default=None, alias="RevisionDate")
    old_version: str | None = Field(default=None, alias="OldVersion")
    new_version: str | None = Field(default=None, alias="NewVersion")
    author_name: str | None = Field(default=None, alias="AuthorName")
    comment: str | None = Field(default=None, alias="Comment")


class CAEXBasicObject(AmlModel):
    """Base CAEX object carrying header data and change state."""

    description: TextElement | None = Field(
        default=None,
        alias="Description",
        description="Textual description for CAEX objects.",
    )
    version: TextElement | None = Field(
        default=None,
        alias="Version",
        description="Organizational version information.",
    )
    revision: list[Revision] = Field(
        default_factory=list,
        alias="Revision",
        description="Revision history entries.",
    )
    copyright: TextElement | None = Field(default=None, alias="Copyright")
    additional_information: list[AdditionalInformation] = Field(
        default_factory=list,
        alias="AdditionalInformation",
    )
    source_object_information: list[SourceObjectInformation] = Field(
        default_factory=list,
        alias="SourceObjectInformation",
    )
    change_mode: ChangeMode = Field(
        default=ChangeMode.STATE,
        alias="ChangeMode",
        description="Optional CAEX change state.",
    )


class CAEXObject(CAEXBasicObject):
    """Named CAEX object with an optional identifier."""

    id: str | None = Field(
        default=None,
        alias="ID",
        description="Optional unique identifier of the CAEX object.",
    )
    name: str = Field(
        alias="Name",
        description="Required CAEX object name.",
    )


class SourceDocumentInformation(AmlModel):
    """Information about a source document that contributed to the CAEX file."""

    origin_name: str | None = Field(default=None, alias="OriginName")
    origin_id: str | None = Field(default=None, alias="OriginID")
    origin_vendor: str | None = Field(default=None, alias="OriginVendor")
    origin_vendor_url: str | None = Field(default=None, alias="OriginVendorURL")
    origin_version: str | None = Field(default=None, alias="OriginVersion")
    origin_release: str | None = Field(default=None, alias="OriginRelease")
    last_writing_date_time: datetime | None = Field(
        default=None,
        alias="LastWritingDateTime",
    )
    origin_project_title: str | None = Field(default=None, alias="OriginProjectTitle")
    origin_project_id: str | None = Field(default=None, alias="OriginProjectID")


class ExternalReference(CAEXBasicObject):
    """Alias definition for an external CAEX file."""

    path: str = Field(alias="Path")
    file_alias: str = Field(alias="Alias")


class AttributeNameMapping(CAEXBasicObject):
    """Mapping between system-unit and role attributes."""

    system_unit_attribute_name: str = Field(alias="SystemUnitAttributeName")
    role_attribute_name: str = Field(alias="RoleAttributeName")


class InterfaceIDMapping(CAEXBasicObject):
    """Mapping between system-unit and role interface IDs."""

    system_unit_interface_id: str = Field(alias="SystemUnitInterfaceID")
    role_interface_id: str = Field(alias="RoleInterfaceID")


class MappingObject(CAEXBasicObject):
    """Host object for CAEX attribute and interface mappings."""

    attribute_name_mapping: list[AttributeNameMapping] = Field(
        default_factory=list,
        alias="AttributeNameMapping",
    )
    interface_id_mapping: list[InterfaceIDMapping] = Field(
        default_factory=list,
        alias="InterfaceIDMapping",
    )


class OrdinalScaledType(AmlModel):
    """Ordinal value constraint."""

    required_max_value: str | None = Field(default=None, alias="RequiredMaxValue")
    required_value: str | None = Field(default=None, alias="RequiredValue")
    required_min_value: str | None = Field(default=None, alias="RequiredMinValue")


class NominalScaledType(AmlModel):
    """Nominal value constraint."""

    required_values: list[str] = Field(default_factory=list, alias="RequiredValue")


class UnknownType(AmlModel):
    """Free-form value requirement."""

    requirements: str | None = Field(default=None, alias="Requirements")


class AttributeValueRequirement(CAEXBasicObject):
    """Constraint for an attribute value."""

    name: str = Field(alias="Name")
    ordinal_scaled_type: OrdinalScaledType | None = Field(
        default=None,
        alias="OrdinalScaledType",
    )
    nominal_scaled_type: NominalScaledType | None = Field(
        default=None,
        alias="NominalScaledType",
    )
    unknown_type: UnknownType | None = Field(default=None, alias="UnknownType")

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

    corresponding_attribute_path: str = Field(alias="CorrespondingAttributePath")


class Attribute(CAEXObject):
    """CAEX attribute instance."""

    default_value: str | None = Field(default=None, alias="DefaultValue")
    value: str | None = Field(default=None, alias="Value")
    ref_semantic: list[RefSemantic] = Field(
        default_factory=list,
        alias="RefSemantic",
    )
    constraint: list[AttributeValueRequirement] = Field(
        default_factory=list,
        alias="Constraint",
    )
    attributes: list[Attribute] = Field(default_factory=list, alias="Attribute")
    unit: str | None = Field(default=None, alias="Unit")
    attribute_data_type: str | None = Field(default=None, alias="AttributeDataType")
    ref_attribute_type: str | None = Field(default=None, alias="RefAttributeType")


class AttributeType(Attribute):
    """Attribute type definition inside an AttributeTypeLib."""

    attribute_types: list[AttributeType] = Field(
        default_factory=list,
        alias="AttributeType",
    )


class InterfaceClass(CAEXObject):
    """Interface class or external interface."""

    attributes: list[Attribute] = Field(default_factory=list, alias="Attribute")
    external_interfaces: list[InterfaceClass] = Field(
        default_factory=list,
        alias="ExternalInterface",
    )
    ref_base_class_path: str | None = Field(default=None, alias="RefBaseClassPath")


class InterfaceFamily(InterfaceClass):
    """Hierarchical interface class definition."""

    interface_classes: list[InterfaceFamily] = Field(
        default_factory=list,
        alias="InterfaceClass",
    )


class RoleClass(CAEXObject):
    """Role class definition."""

    attributes: list[Attribute] = Field(default_factory=list, alias="Attribute")
    external_interfaces: list[InterfaceClass] = Field(
        default_factory=list,
        alias="ExternalInterface",
    )
    ref_base_class_path: str | None = Field(default=None, alias="RefBaseClassPath")


class RoleFamily(RoleClass):
    """Hierarchical role class definition."""

    role_classes: list[RoleFamily] = Field(default_factory=list, alias="RoleClass")


class SupportedRoleClass(CAEXBasicObject):
    """Role class supported by a system unit class."""

    ref_role_class_path: str = Field(alias="RefRoleClassPath")
    mapping_object: MappingObject | None = Field(default=None, alias="MappingObject")


class InternalLink(CAEXObject):
    """Relationship between internal interfaces."""

    ref_partner_side_a: str = Field(alias="RefPartnerSideA")
    ref_partner_side_b: str = Field(alias="RefPartnerSideB")


class SystemUnitClass(CAEXObject):
    """System unit class definition."""

    attributes: list[Attribute] = Field(default_factory=list, alias="Attribute")
    external_interfaces: list[InterfaceClass] = Field(
        default_factory=list,
        alias="ExternalInterface",
    )
    internal_elements: list[InternalElement] = Field(
        default_factory=list,
        alias="InternalElement",
    )
    supported_role_classes: list[SupportedRoleClass] = Field(
        default_factory=list,
        alias="SupportedRoleClass",
    )
    internal_links: list[InternalLink] = Field(
        default_factory=list,
        alias="InternalLink",
    )


class RoleRequirements(CAEXBasicObject):
    """Role requirements attached to an internal element."""

    attributes: list[Attribute] = Field(default_factory=list, alias="Attribute")
    external_interfaces: list[InterfaceClass] = Field(
        default_factory=list,
        alias="ExternalInterface",
    )
    mapping_object: MappingObject | None = Field(default=None, alias="MappingObject")
    ref_base_role_class_path: str = Field(alias="RefBaseRoleClassPath")


class InternalElement(SystemUnitClass):
    """Hierarchical object instance in an InstanceHierarchy or SystemUnitClass."""

    role_requirements: list[RoleRequirements] = Field(
        default_factory=list,
        alias="RoleRequirements",
    )
    ref_base_system_unit_path: str | None = Field(
        default=None,
        alias="RefBaseSystemUnitPath",
    )


class SystemUnitFamily(SystemUnitClass):
    """Hierarchical SystemUnitClass tree entry."""

    system_unit_classes: list[SystemUnitFamily] = Field(
        default_factory=list,
        alias="SystemUnitClass",
    )
    ref_base_class_path: str | None = Field(default=None, alias="RefBaseClassPath")


class InstanceHierarchy(CAEXObject):
    """Root element for a system hierarchy of object instances."""

    internal_elements: list[InternalElement] = Field(
        default_factory=list,
        alias="InternalElement",
    )


class InterfaceClassLib(CAEXObject):
    """Container for interface class definitions."""

    interface_classes: list[InterfaceFamily] = Field(
        default_factory=list,
        alias="InterfaceClass",
    )


class RoleClassLib(CAEXObject):
    """Container for role class definitions."""

    role_classes: list[RoleFamily] = Field(default_factory=list, alias="RoleClass")


class SystemUnitClassLib(CAEXObject):
    """Container for system unit class definitions."""

    system_unit_classes: list[SystemUnitFamily] = Field(
        default_factory=list,
        alias="SystemUnitClass",
    )


class AttributeTypeLib(CAEXObject):
    """Container for attribute type definitions."""

    attribute_types: list[AttributeType] = Field(
        default_factory=list,
        alias="AttributeType",
    )


class CAEXFile(CAEXBasicObject):
    """Root AutomationML CAEX 3.0 document."""

    superior_standard_versions: list[str] = Field(
        default_factory=list,
        alias="SuperiorStandardVersion",
    )
    source_document_information: list[SourceDocumentInformation] = Field(
        default_factory=list,
        alias="SourceDocumentInformation",
    )
    external_references: list[ExternalReference] = Field(
        default_factory=list,
        alias="ExternalReference",
    )
    instance_hierarchies: list[InstanceHierarchy] = Field(
        default_factory=list,
        alias="InstanceHierarchy",
    )
    interface_class_libs: list[InterfaceClassLib] = Field(
        default_factory=list,
        alias="InterfaceClassLib",
    )
    role_class_libs: list[RoleClassLib] = Field(
        default_factory=list,
        alias="RoleClassLib",
    )
    system_unit_class_libs: list[SystemUnitClassLib] = Field(
        default_factory=list,
        alias="SystemUnitClassLib",
    )
    attribute_type_libs: list[AttributeTypeLib] = Field(
        default_factory=list,
        alias="AttributeTypeLib",
    )
    schema_version: str = Field(
        default="3.0",
        alias="SchemaVersion",
        description="CAEX schema version. CAEX 3.0 documents use fixed value 3.0.",
    )
    file_name: str = Field(alias="FileName")

    def reference_index(self) -> ReferenceIndex:
        """Return an index for resolving in-document AML paths and IDs."""

        from .validation import ReferenceIndex

        return ReferenceIndex.from_document(self)

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
        mapper: Literal["python", "xslt"] = "python",
    ) -> str:
        """Convert the document to an OPC UA UANodeSet XML document."""

        from .opcua import document_to_nodeset

        return document_to_nodeset(
            self,
            pretty=pretty,
            include_roundtrip=include_roundtrip,
            publication_date=publication_date,
            mapper=mapper,
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
        mapper: Literal["python", "xslt"] = "python",
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
            mapper=mapper,
        )

    @classmethod
    def from_aml_xml(cls, data: str | bytes) -> CAEXFile:
        """Parse CAEX XML into a JSON-first model."""

        from .xml import loads

        return loads(data)

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


for model in (
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
