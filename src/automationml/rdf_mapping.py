"""Shared, validated rules for the AutomationML/RDF (Turtle) mapping profile.

This mirrors the design of ``opcua_mapping.py``: the forward and reverse
converters in :mod:`automationml.rdf` depend on one immutable profile object
instead of re-deriving identity, datatype, or ordering rules ad hoc while
walking a tree. A rule that cannot be expressed in both directions belongs
here with an explicit canonical choice; it must not be hidden inside a
serializer.

This profile is the Python replacement for the hand-written ``AML2TTL.xslt``
export used by the ``AML-FD4AML`` effort. See
``docs/rdf-mapping-audit.md`` for the audit that motivated it. The default
namespace intentionally matches the legacy stylesheet's target
(``https://w3id.org/hsu-aut/AutomationML``) for continuity; callers who want
a project-local vocabulary instead should construct their own
:class:`RDFMappingProfile`.
"""

from __future__ import annotations

from typing import Self
from uuid import NAMESPACE_URL, uuid5

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from rdflib import XSD
from rdflib.term import URIRef


class RDFMappingUnsupported(ValueError):
    """Raised when a document uses a construct outside the strict profile.

    Mirrors the OPC UA mapper's "unsupported or ambiguous features fail
    explicitly" stance instead of the legacy XSLT's silent catch-all
    (``<xsl:template match="@*|*"/>``), which drops anything it does not
    recognize without any signal.
    """


class _MappingModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, validate_default=True)


class XSDDataTypeRule(_MappingModel):
    """One many-to-one AML datatype mapping with a canonical inverse.

    Shaped like ``opcua_mapping.DataTypeRule`` on purpose: the same
    many-to-one problem (several AML XSD spellings collapse to one RDF
    datatype) needs the same "declare the inverse, don't infer it" answer.
    """

    aml_types: tuple[str, ...]
    canonical_aml_type: str
    xsd_term: URIRef

    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)

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
            raise ValueError("canonical_aml_type must be one of the rule's aml_types.")
        return self


class XSDDataTypeRegistry(_MappingModel):
    """Bidirectional AML-datatype <-> RDF-literal-datatype lookup."""

    rules: tuple[XSDDataTypeRule, ...]
    default_aml_type: str = "xs:string"

    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)

    @model_validator(mode="after")
    def _validate_registry(self) -> Self:
        aml_types = [name for rule in self.rules for name in rule.aml_types]
        duplicates = sorted({item for item in aml_types if aml_types.count(item) > 1})
        if duplicates:
            raise ValueError(f"Duplicate AML datatype rules: {', '.join(duplicates)}")
        if self.default_aml_type not in aml_types:
            raise ValueError("default_aml_type must be registered.")
        return self

    def from_aml(self, aml_type: str | None) -> XSDDataTypeRule:
        """Return the forward rule, defaulting an omitted AttributeDataType to String."""

        requested = aml_type or self.default_aml_type
        for rule in self.rules:
            if requested in rule.aml_types:
                return rule
        # An unrecognized AttributeDataType is not a reason to fail the whole
        # export: AML permits application-specific type strings. Round-trip
        # through the canonical string type rather than raising, and let
        # validation elsewhere flag the unusual AttributeDataType if needed.
        return XSDDataTypeRule(
            aml_types=(requested,),
            canonical_aml_type=requested,
            xsd_term=XSD.string,
        )

    def from_xsd(self, term: URIRef) -> str:
        """Return the canonical AML AttributeDataType for an RDF literal datatype."""

        for rule in self.rules:
            if rule.xsd_term == term:
                return rule.canonical_aml_type
        return self.default_aml_type


# Unlike the OPC UA profile, RDF has a native literal datatype for every XSD
# built-in type AML uses, so no AML spelling has to be collapsed into another
# one: each rule is one-to-one and the authored AttributeDataType survives a
# round trip unchanged (xs:integer stays xs:integer, xs:token stays xs:token).
_ONE_TO_ONE_XSD_TYPES = (
    "boolean",
    "byte",
    "unsignedByte",
    "short",
    "unsignedShort",
    "int",
    "unsignedInt",
    "long",
    "unsignedLong",
    "integer",
    "positiveInteger",
    "nonNegativeInteger",
    "negativeInteger",
    "nonPositiveInteger",
    "decimal",
    "float",
    "double",
    "string",
    "normalizedString",
    "token",
    "language",
    "Name",
    "NCName",
    "ID",
    "IDREF",
    "anyURI",
    "QName",
    "dateTime",
    "date",
    "time",
    "duration",
    "gYear",
    "gYearMonth",
    "gMonth",
    "gMonthDay",
    "gDay",
    "base64Binary",
    "hexBinary",
)

DEFAULT_XSD_DATA_TYPE_REGISTRY = XSDDataTypeRegistry(
    rules=tuple(
        XSDDataTypeRule(
            aml_types=(f"xs:{name}",),
            canonical_aml_type=f"xs:{name}",
            xsd_term=URIRef(f"{XSD}{name}"),
        )
        for name in _ONE_TO_ONE_XSD_TYPES
    )
)


class RDFMappingProfile(_MappingModel):
    """The executable AML <-> RDF mapping contract.

    ``graph_uri`` / ``base_uri`` control the target vocabulary. The defaults
    reproduce the legacy XSLT's namespace for drop-in continuity; a project
    that wants its own vocabulary instead of ``hsu-aut``'s should build a
    profile with a different ``graph_uri``.
    """

    name: str = "python-semantic"
    version: str = "1"
    graph_uri: str = "http://www.w3id.org/hsu-aut"
    data_types: XSDDataTypeRegistry = DEFAULT_XSD_DATA_TYPE_REGISTRY

    @property
    def base_uri(self) -> str:
        return f"{self.graph_uri}/AutomationML#"

    def mint_uri(self, *, id: str | None, path: str) -> URIRef:
        """Mint a stable node URI.

        An explicit CAEX ``ID`` is used directly when present. Otherwise a
        UUIDv5 is derived from the object's structural path (the same
        ``$.Foo[0].Bar[1]``-shaped path :class:`~automationml.validation.
        ReferenceIndex` already computes), so two independent runs over an
        unchanged document mint the same URI for the same object without
        ever concatenating mutable ``Name`` values into the URI itself. This
        is the fix for the legacy XSLT's non-IRI-safe, rename-sensitive
        URI construction (``createUri`` / name-path ``refPath``).

        Renaming an object, or reordering its unnamed siblings, changes its
        minted URI when it has no ``ID`` -- exactly like the OPC UA profile
        treats sibling order as non-semantic only when identity is
        otherwise pinned. Give CAEX objects a stable ``ID`` when they must
        survive reordering across an export/import cycle.
        """

        if id:
            # AML tooling is inconsistent about whether a CAEX ID is written
            # with UUID braces (``{...}``); both spellings identify the same
            # object, so both must mint the same URI. IDs are otherwise
            # IRI-safe UUIDs, so no further percent-encoding is needed here
            # -- unlike the legacy XSLT, arbitrary ``Name`` text is never
            # substring into a URI in this profile.
            cleaned = id.strip().strip("{}")
            return URIRef(f"{self.base_uri}{cleaned}")
        digest = uuid5(NAMESPACE_URL, f"urn:automationml:rdf-node:{path}")
        return URIRef(f"{self.base_uri}p-{digest}")

    def mint_external_class_uri(self, raw_path: str) -> URIRef:
        """Mint a stable proxy URI for a class path this document cannot resolve.

        AML allows ``alias@library/path`` references into an external file
        that is not part of the document being converted (see
        ``9_ExtInt_IntLink.aml``'s ``BaseInterfaceClassLib@...`` references).
        Rather than silently emitting a dangling or malformed URI (as the
        legacy XSLT's ``locateElem`` fallback does), such a path is mapped to
        a stable proxy node tagged with the raw path, mirroring how the OPC
        UA profile represents an unresolved external class as a proxy
        carrying ``AMLExternalClassPath`` instead of pretending it is local.
        """

        digest = uuid5(NAMESPACE_URL, f"urn:automationml:rdf-external-class:{raw_path}")
        return URIRef(f"{self.base_uri}external-{digest}")


DEFAULT_MAPPING_PROFILE = RDFMappingProfile()
