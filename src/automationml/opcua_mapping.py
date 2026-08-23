"""Shared, validated rules for the AutomationML/OPC UA mapping profile.

The forward and reverse converters deliberately depend on the same immutable
profile object.  A rule which cannot be expressed in both directions belongs
here with an explicit canonical inverse or ambiguity policy; it must not be
hidden in an XML serializer.
"""

from __future__ import annotations

from typing import Literal, Self
from uuid import NAMESPACE_URL, uuid5

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class UnsupportedDataTypeError(ValueError):
    """Raised when the strict profile has no loss-aware datatype rule."""


class MappingRuleError(ValueError):
    """Raised when no unambiguous shared mapping rule applies."""


def normalize_partner_reference(value: str) -> str:
    """Canonicalize optional UUID braces without changing AML endpoint syntax."""

    owner, separator, interface = value.partition(":")
    normalized_owner = owner.strip().strip("{}")
    if separator:
        return f"{normalized_owner}:{interface}"
    return normalized_owner


def canonical_internal_link_identity(
    partner_a: str,
    partner_b: str,
) -> tuple[str, str]:
    """Generate the strict profile's stable link name and UUID from direction."""

    source = normalize_partner_reference(partner_a)
    target = normalize_partner_reference(partner_b)
    identifier = uuid5(
        NAMESPACE_URL,
        f"urn:automationml:internal-link:{source}->{target}",
    )
    return f"InternalLink_{identifier.hex[:8]}", str(identifier)


class _MappingModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, validate_default=True)


class DataTypeRule(_MappingModel):
    """One many-to-one AML datatype mapping with a canonical inverse."""

    aml_types: tuple[str, ...]
    canonical_aml_type: str
    ua_alias: str
    ua_node_id: str
    scalar_type: str

    @field_validator("aml_types")
    @classmethod
    def _require_unique_aml_types(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            raise ValueError("A datatype rule requires at least one AML datatype.")
        if len(value) != len(set(value)):
            raise ValueError("A datatype rule cannot repeat AML datatypes.")
        return value

    @model_validator(mode="after")
    def _validate_canonical_inverse(self) -> Self:
        if self.canonical_aml_type not in self.aml_types:
            raise ValueError(
                "canonical_aml_type must be one of the rule's aml_types."
            )
        return self


class DataTypeRegistry(_MappingModel):
    """Bidirectional datatype lookup used by both conversion directions."""

    rules: tuple[DataTypeRule, ...]
    default_aml_type: str = "xs:string"

    @model_validator(mode="after")
    def _validate_registry(self) -> Self:
        aml_types = [name for rule in self.rules for name in rule.aml_types]
        ua_aliases = [rule.ua_alias for rule in self.rules]
        ua_node_ids = [rule.ua_node_id for rule in self.rules]
        scalar_types = [rule.scalar_type for rule in self.rules]
        for label, values in (
            ("AML datatype", aml_types),
            ("OPC UA alias", ua_aliases),
            ("OPC UA NodeId", ua_node_ids),
            ("OPC UA scalar element", scalar_types),
        ):
            duplicates = sorted({item for item in values if values.count(item) > 1})
            if duplicates:
                raise ValueError(f"Duplicate {label} rules: {', '.join(duplicates)}")
        if self.default_aml_type not in aml_types:
            raise ValueError("default_aml_type must be registered.")
        return self

    def from_aml(self, aml_type: str | None) -> DataTypeRule:
        """Return the forward rule, defaulting an omitted AML type to String."""

        requested = aml_type or self.default_aml_type
        for rule in self.rules:
            if requested in rule.aml_types:
                return rule
        raise UnsupportedDataTypeError(
            f"No strict OPC UA mapping exists for AML datatype {requested!r}."
        )

    def from_ua(self, ua_type: str) -> DataTypeRule:
        """Return the reverse rule for a built-in alias or expanded NodeId."""

        for rule in self.rules:
            if ua_type in {rule.ua_alias, rule.ua_node_id}:
                return rule
        raise UnsupportedDataTypeError(
            f"No strict AutomationML mapping exists for OPC UA datatype {ua_type!r}."
        )


RoleOwner = Literal["InternalElement", "SystemUnitClass"]
RoleRelationship = Literal["RoleRequirements", "SupportedRoleClass"]


class RoleReferenceRule(_MappingModel):
    """Contextual inverse for the companion model's native role edge."""

    owner: RoleOwner
    relationship: RoleRelationship
    reference_type: str = "HasAMLRoleReference"
    aml_path_field: Literal["RefBaseRoleClassPath", "RefRoleClassPath"]

    @model_validator(mode="after")
    def _validate_path_field(self) -> Self:
        expected = (
            "RefBaseRoleClassPath"
            if self.relationship == "RoleRequirements"
            else "RefRoleClassPath"
        )
        if self.aml_path_field != expected:
            raise ValueError(
                f"{self.relationship} must use AML field {expected!r}."
            )
        return self


class AMLUAMappingProfile(_MappingModel):
    """The executable strict-implicit mapping contract."""

    name: str = "strict-implicit"
    version: str = "1"
    data_types: DataTypeRegistry
    default_value_property: str = "DefaultValue"
    unit_property: str = "Unit"
    role_references: tuple[RoleReferenceRule, ...]

    @model_validator(mode="after")
    def _validate_role_rules(self) -> Self:
        owners = [rule.owner for rule in self.role_references]
        if len(owners) != len(set(owners)):
            raise ValueError("Each role-reference owner needs one canonical inverse.")
        return self

    def role_rule(
        self,
        owner: RoleOwner,
        relationship: RoleRelationship | None = None,
    ) -> RoleReferenceRule:
        """Find the one native role rule valid for an owner context."""

        matches = [
            rule
            for rule in self.role_references
            if rule.owner == owner
            and (relationship is None or rule.relationship == relationship)
        ]
        if len(matches) != 1:
            detail = f"{owner}/{relationship}" if relationship else owner
            raise MappingRuleError(
                f"No unique native role-reference rule exists for {detail}."
            )
        return matches[0]


DEFAULT_DATA_TYPE_REGISTRY = DataTypeRegistry(
    rules=(
        DataTypeRule(
            aml_types=("xs:boolean",),
            canonical_aml_type="xs:boolean",
            ua_alias="Boolean",
            ua_node_id="i=1",
            scalar_type="Boolean",
        ),
        DataTypeRule(
            aml_types=("xs:byte",),
            canonical_aml_type="xs:byte",
            ua_alias="SByte",
            ua_node_id="i=2",
            scalar_type="SByte",
        ),
        DataTypeRule(
            aml_types=("xs:unsignedByte",),
            canonical_aml_type="xs:unsignedByte",
            ua_alias="Byte",
            ua_node_id="i=3",
            scalar_type="Byte",
        ),
        DataTypeRule(
            aml_types=("xs:short",),
            canonical_aml_type="xs:short",
            ua_alias="Int16",
            ua_node_id="i=4",
            scalar_type="Int16",
        ),
        DataTypeRule(
            aml_types=("xs:unsignedShort",),
            canonical_aml_type="xs:unsignedShort",
            ua_alias="UInt16",
            ua_node_id="i=5",
            scalar_type="UInt16",
        ),
        DataTypeRule(
            aml_types=("xs:int", "xs:integer"),
            canonical_aml_type="xs:int",
            ua_alias="Int32",
            ua_node_id="i=6",
            scalar_type="Int32",
        ),
        DataTypeRule(
            aml_types=("xs:unsignedInt",),
            canonical_aml_type="xs:unsignedInt",
            ua_alias="UInt32",
            ua_node_id="i=7",
            scalar_type="UInt32",
        ),
        DataTypeRule(
            aml_types=("xs:long",),
            canonical_aml_type="xs:long",
            ua_alias="Int64",
            ua_node_id="i=8",
            scalar_type="Int64",
        ),
        DataTypeRule(
            aml_types=("xs:unsignedLong", "xs:positiveInteger"),
            canonical_aml_type="xs:unsignedLong",
            ua_alias="UInt64",
            ua_node_id="i=9",
            scalar_type="UInt64",
        ),
        DataTypeRule(
            aml_types=("xs:float",),
            canonical_aml_type="xs:float",
            ua_alias="Float",
            ua_node_id="i=10",
            scalar_type="Float",
        ),
        DataTypeRule(
            aml_types=("xs:double",),
            canonical_aml_type="xs:double",
            ua_alias="Double",
            ua_node_id="i=11",
            scalar_type="Double",
        ),
        DataTypeRule(
            aml_types=("xs:string", "xs:ID", "xs:token", "xs:anyURI"),
            canonical_aml_type="xs:string",
            ua_alias="String",
            ua_node_id="i=12",
            scalar_type="String",
        ),
        DataTypeRule(
            aml_types=("xs:dateTime", "xs:date"),
            canonical_aml_type="xs:dateTime",
            ua_alias="DateTime",
            ua_node_id="i=13",
            scalar_type="DateTime",
        ),
        DataTypeRule(
            aml_types=("xs:base64Binary",),
            canonical_aml_type="xs:base64Binary",
            ua_alias="ByteString",
            ua_node_id="i=15",
            scalar_type="ByteString",
        ),
    )
)


DEFAULT_MAPPING_PROFILE = AMLUAMappingProfile(
    data_types=DEFAULT_DATA_TYPE_REGISTRY,
    role_references=(
        RoleReferenceRule(
            owner="InternalElement",
            relationship="RoleRequirements",
            aml_path_field="RefBaseRoleClassPath",
        ),
        RoleReferenceRule(
            owner="SystemUnitClass",
            relationship="SupportedRoleClass",
            aml_path_field="RefRoleClassPath",
        ),
    ),
)
