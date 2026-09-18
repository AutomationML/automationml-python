"""AutomationML and RDF/Turtle conversion.

This is the Python replacement for the hand-written ``AML2TTL.xslt`` export
(see ``docs/rdf-mapping-audit.md``). It follows the same shape as
``automationml.opcua``: a shared, declared :class:`~automationml.rdf_mapping.
RDFMappingProfile` drives both directions, unsupported constructs fail
explicitly instead of being silently dropped, and a round trip returns
inspectable, JSON-Pointer-addressed differences instead of a bare boolean.

Scope of this first version: CAEX file metadata, all four class-library
kinds (with inheritance via ``RefBaseClassPath`` / ``RefAttributeType``),
instance hierarchies, internal elements (recursively), attributes (typed
literals, nested attributes, constraints), external interfaces, internal
links, and role relationships (``RoleRequirements`` / ``SupportedRoleClass``,
including ``MappingObject`` payloads). AML constructs this SDK's own CAEX 3.0
model does not represent at all (Mirror objects, Facets) are out of scope
here the same way they are out of scope for the rest of the SDK. Anything
this profile could plausibly see but does not yet have a rule for raises
:class:`~automationml.rdf_mapping.RDFMappingUnsupported` rather than being
dropped silently, matching the "unsupported or ambiguous features fail
explicitly" stance the OPC UA mapper already established.

Every CAEX list this module walks is order-sensitive (attribute order,
sibling order, ...), so every child gets an explicit ``hasIndex`` alongside
its containment triple. RDF triples are an unordered set; without this, a
round trip could silently permute sibling order.
"""

from __future__ import annotations

from typing import Literal
from urllib.parse import quote

from pydantic import BaseModel, ConfigDict, JsonValue, computed_field
from rdflib import OWL, RDF, RDFS, XSD, Graph
from rdflib import Literal as RDFLiteral
from rdflib import Namespace, URIRef
from rdflib.collection import Collection

from .builders import (
    attribute as build_attribute,
    caex_file as build_caex_file,
    external_interface as build_external_interface,
    instance_hierarchy as build_instance_hierarchy,
    internal_element as build_internal_element,
    source_document as build_source_document,
)
from .models import (
    AdditionalInformation,
    Attribute,
    AttributeNameMapping,
    AttributeType,
    AttributeTypeLib,
    AttributeValueRequirement,
    CAEXFile,
    ExternalReference,
    InstanceHierarchy,
    InterfaceClass,
    InterfaceClassLib,
    InterfaceFamily,
    InterfaceIDMapping,
    InternalElement,
    InternalLink,
    MappingObject,
    NominalScaledType,
    OrdinalScaledType,
    RefSemantic,
    Revision,
    RoleClassLib,
    RoleFamily,
    RoleRequirements,
    SourceDocumentInformation,
    SourceObjectInformation,
    SupportedRoleClass,
    SystemUnitClass,
    SystemUnitClassLib,
    SystemUnitFamily,
    TextElement,
    UnknownType,
)
from .rdf_mapping import (
    DEFAULT_MAPPING_PROFILE,
    RDFMappingProfile,
    RDFMappingUnsupported,
)
from .validation import ReferenceIndex, ReferenceTarget

MAPPING_PROFILE_VERSION = f"{DEFAULT_MAPPING_PROFILE.name}-v{DEFAULT_MAPPING_PROFILE.version}"

_ClassKind = Literal["system_unit", "role", "interface", "attribute_type"]


class RDFConversionError(ValueError):
    """Raised when AutomationML/RDF conversion cannot produce a valid result."""


# ---------------------------------------------------------------------------
# Round-trip evidence (mirrors automationml.opcua's RoundTripDifference shape)
# ---------------------------------------------------------------------------


class RDFRoundTripDifference(BaseModel):
    """One stable, JSON-Pointer-addressed semantic difference."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str
    kind: Literal["added", "removed", "changed"]
    source_value: JsonValue | None = None
    recovered_value: JsonValue | None = None


class RDFRoundTripResult(BaseModel):
    """Validated evidence from an AML -> RDF -> AML semantic round trip."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    differences: tuple[RDFRoundTripDifference, ...]
    mapping_profile: str
    source_document: CAEXFile
    ttl: str
    recovered_document: CAEXFile

    @computed_field
    @property
    def semantically_equivalent(self) -> bool:
        """Whether the AutomationML semantic projections are equal."""

        return not self.differences

    def assert_equivalent(self) -> CAEXFile:
        """Return the recovered document or fail with a round-trip-specific error."""

        if self.differences:
            paths = ", ".join(item.path for item in self.differences[:3])
            suffix = "" if len(self.differences) <= 3 else ", ..."
            raise RDFConversionError(
                "The AML -> RDF -> AML round trip completed but changed "
                f"AutomationML semantics at {paths}{suffix}."
            )
        return self.recovered_document


def compare_aml_semantics(
    source: CAEXFile,
    recovered: CAEXFile,
) -> tuple[RDFRoundTripDifference, ...]:
    """Compare canonical CAEX semantics and return structured differences."""

    return _compare_json_values(
        source.to_aml_dict(include_change_mode=True),
        recovered.to_aml_dict(include_change_mode=True),
    )


def _compare_json_values(
    source: JsonValue,
    recovered: JsonValue,
    path: str = "",
) -> tuple[RDFRoundTripDifference, ...]:
    from .changes import diff_payloads

    return tuple(
        RDFRoundTripDifference(
            path=(f"{path}{operation.path}" or "/"),
            kind={"add": "added", "remove": "removed", "replace": "changed"}[
                operation.op
            ],
            source_value=operation.before,
            recovered_value=operation.after,
        )
        for operation in diff_payloads(source, recovered)
    )


def _json_pointer_segment(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


# ---------------------------------------------------------------------------
# Forward mapping: CAEXFile -> rdflib.Graph
# ---------------------------------------------------------------------------


def document_to_rdf_graph(
    document: CAEXFile,
    *,
    profile: RDFMappingProfile = DEFAULT_MAPPING_PROFILE,
) -> Graph:
    """Map a validated CAEX document directly to an RDF graph."""

    return _ForwardMapper(document, profile).build()


def document_to_ttl(
    document: CAEXFile,
    *,
    profile: RDFMappingProfile = DEFAULT_MAPPING_PROFILE,
) -> str:
    """Serialize a CAEX document as Turtle."""

    return document_to_rdf_graph(document, profile=profile).serialize(format="turtle")


class _ForwardMapper:
    def __init__(self, document: CAEXFile, profile: RDFMappingProfile) -> None:
        self.document = document
        self.profile = profile
        self.ns = Namespace(profile.base_uri)
        self.graph = Graph()
        self.index: ReferenceIndex = document.reference_index()
        # Every path-derived (ID-less) URI is seeded with the file name so
        # that graphs from two different documents merged into one store do
        # not collide just because both documents share a structural shape
        # (e.g. both have an unnamed-by-ID "InstanceHierarchy[0]").
        safe_name = quote(document.file_name or "document", safe="")
        self.root_path = f"$[{safe_name}]"

    # -- identity -----------------------------------------------------------

    def _mint(self, *, id: str | None, path: str) -> URIRef:
        return self.profile.mint_uri(id=id, path=path)

    def _mint_child(self, parent: URIRef, obj: object, kind: str, index: int) -> URIRef:
        return self._mint(id=getattr(obj, "id", None), path=f"{parent}/{kind}[{index}]")

    def _link(self, parent: URIRef, predicate: URIRef, child: URIRef, index: int) -> None:
        """Add a containment triple plus the sibling-order index it needs on replay."""

        self.graph.add((parent, predicate, child))
        self.graph.add((child, self.ns.hasIndex, RDFLiteral(index)))

    def _uri_for_target(self, target: ReferenceTarget | None, *, raw_path: str) -> URIRef:
        if target is not None:
            return self._mint(id=target.id, path=self.root_path + target.path[1:])
        if raw_path:
            # Not resolvable inside this document. AML permits several
            # legitimate reasons: an explicit alias@library/path into a file
            # this document does not embed, a plain reference into one of
            # AutomationML's own standard base libraries (e.g.
            # "AutomationMLBaseInterface", or "AutomationMLBaseAttributeType
            # Lib/Direction") that tooling is expected to know implicitly and
            # never inlines, or a genuine typo. This profile cannot tell
            # those apart from the path string alone, so -- unlike the
            # legacy XSLT, which emits a dangling or malformed URI here --
            # every case mints a stable, explicitly-tagged proxy node
            # carrying the raw path, rather than guessing or crashing.
            uri = self.profile.mint_external_class_uri(raw_path)
            if (uri, RDF.type, self.ns.ExternalClassProxy) not in self.graph:
                self.graph.add((uri, RDF.type, self.ns.ExternalClassProxy))
                self.graph.add((uri, self.ns.hasExternalClassPath, RDFLiteral(raw_path)))
            return uri
        raise RDFMappingUnsupported(
            "A class-path reference was empty; there is nothing to resolve "
            "or represent as an external proxy."
        )

    def _resolve_class(self, path: str, kind: _ClassKind) -> URIRef:
        resolver = {
            "system_unit": self.index.resolve_system_unit_class,
            "role": self.index.resolve_role_class,
            "interface": self.index.resolve_interface_class,
            "attribute_type": self.index.resolve_attribute_type,
        }[kind]
        return self._uri_for_target(resolver(path), raw_path=path)

    # -- entry point ----------------------------------------------------------

    def build(self) -> Graph:
        g, ns = self.graph, self.ns
        g.bind("aml", ns)
        g.bind("owl", OWL)

        mapping_result = URIRef(f"{self.profile.graph_uri}/MappingResult")
        g.add((mapping_result, RDF.type, OWL.Ontology))
        g.add((mapping_result, OWL.imports, URIRef(f"{self.profile.graph_uri}/AutomationML")))

        document = self.document
        file_uri = self._mint(id=None, path=self.root_path)
        g.add((file_uri, RDF.type, ns.CAEXFile))
        g.add((file_uri, ns.hasFileName, RDFLiteral(document.file_name)))
        g.add((file_uri, ns.hasSchemaVersion, RDFLiteral(document.schema_version)))
        g.add((file_uri, RDFS.label, RDFLiteral(document.file_name)))

        for version in document.superior_standard_versions:
            g.add((file_uri, ns.hasSuperiorStandardVersion, RDFLiteral(version)))

        for index, source in enumerate(document.source_document_information):
            self._map_source_document(file_uri, source, index)

        for index, reference in enumerate(document.external_references):
            self._map_external_reference(file_uri, reference, index)

        # Description, Version, Copyright, Revision, SourceObjectInformation
        # and AdditionalInformation of the file header.
        self._emit_common(file_uri, document, metadata_path=self.root_path)

        for index, lib in enumerate(document.attribute_type_libs):
            self._link(file_uri, ns.hasAttributeTypeLib, self._map_attribute_type_lib(lib, index), index)
        for index, lib in enumerate(document.interface_class_libs):
            self._link(file_uri, ns.hasInterfaceClassLib, self._map_interface_class_lib(lib, index), index)
        for index, lib in enumerate(document.role_class_libs):
            self._link(file_uri, ns.hasRoleClassLib, self._map_role_class_lib(lib, index), index)
        for index, lib in enumerate(document.system_unit_class_libs):
            self._link(file_uri, ns.hasSystemUnitClassLib, self._map_system_unit_class_lib(lib, index), index)
        for index, hierarchy in enumerate(document.instance_hierarchies):
            self._link(file_uri, ns.hasInstanceHierarchy, self._map_instance_hierarchy(hierarchy, index), index)

        return g

    # -- header -----------------------------------------------------------------

    def _map_source_document(
        self, file_uri: URIRef, source: SourceDocumentInformation, index: int
    ) -> None:
        g, ns = self.graph, self.ns
        origin_uri = self._mint(id=None, path=f"{self.root_path}.SourceDocumentInformation[{index}]")
        self._link(file_uri, ns.hasOrigin, origin_uri, index)
        g.add((origin_uri, RDF.type, ns.Origin))
        for field_name, predicate in (
            ("origin_name", ns.hasOriginName),
            ("origin_id", ns.hasOriginID),
            ("origin_vendor", ns.hasOriginVendor),
            ("origin_vendor_url", ns.hasOriginVendorURL),
            ("origin_version", ns.hasOriginVersion),
            ("origin_release", ns.hasOriginRelease),
            ("origin_project_id", ns.hasOriginProjectID),
            ("origin_project_title", ns.hasOriginProjectTitle),
        ):
            value = getattr(source, field_name)
            if value:
                g.add((origin_uri, predicate, RDFLiteral(value)))
        if source.last_writing_date_time:
            g.add((origin_uri, ns.hasLastWritingDateTime, RDFLiteral(source.last_writing_date_time.isoformat())))
        if source.origin_name:
            g.add((origin_uri, RDFS.label, RDFLiteral(source.origin_name)))

    def _map_external_reference(
        self, file_uri: URIRef, reference: "ExternalReference", index: int
    ) -> None:
        g, ns = self.graph, self.ns
        uri = self._mint(id=None, path=f"{self.root_path}.ExternalReference[{index}]")
        self._link(file_uri, ns.hasExternalReference, uri, index)
        g.add((uri, RDF.type, ns.ExternalReference))
        self._emit_common(uri, reference)
        g.add((uri, ns.hasPath, RDFLiteral(reference.path)))
        g.add((uri, ns.hasAlias, RDFLiteral(reference.file_alias)))

    def _map_additional_information(
        self, owner_uri: URIRef, info: "AdditionalInformation", index: int, metadata_path: str
    ) -> None:
        # AML leaves AdditionalInformation open-ended (association-specific
        # extensions, including arbitrary namespaced XML carried as ``$xml``).
        # Rather than hand-modeling every possible shape (as the legacy XSLT
        # does not even attempt), the whole element round-trips as one
        # canonical-AML-JSON literal.
        g, ns = self.graph, self.ns
        uri = self._mint(id=None, path=f"{metadata_path}.AdditionalInformation[{index}]")
        self._link(owner_uri, ns.hasAdditionalInformation, uri, index)
        g.add((uri, RDF.type, ns.AdditionalInformation))
        g.add((uri, ns.hasAdditionalInformationJson, RDFLiteral(info.to_aml_json(indent=None))))

    def _map_revision(self, owner_uri: URIRef, revision: Revision, index: int, metadata_path: str) -> None:
        g, ns = self.graph, self.ns
        uri = self._mint(id=None, path=f"{metadata_path}.Revision[{index}]")
        self._link(owner_uri, ns.hasRevision, uri, index)
        g.add((uri, RDF.type, ns.Revision))
        if revision.revision_date is not None:
            g.add((uri, ns.hasRevisionDate, RDFLiteral(revision.revision_date.isoformat(), datatype=XSD.dateTime)))
        for field_name, predicate in (
            ("old_version", ns.hasOldVersion),
            ("new_version", ns.hasNewVersion),
            ("author_name", ns.hasAuthorName),
            ("comment", ns.hasComment),
        ):
            value = getattr(revision, field_name)
            if value is not None:
                g.add((uri, predicate, RDFLiteral(value)))
        if revision.change_mode != "state":
            g.add((uri, ns.hasChangeMode, RDFLiteral(revision.change_mode)))

    def _map_source_object_information(
        self, owner_uri: URIRef, info: SourceObjectInformation, index: int, metadata_path: str
    ) -> None:
        g, ns = self.graph, self.ns
        uri = self._mint(id=None, path=f"{metadata_path}.SourceObjectInformation[{index}]")
        self._link(owner_uri, ns.hasSourceObjectInformation, uri, index)
        g.add((uri, RDF.type, ns.SourceObjectInformation))
        if info.value:
            g.add((uri, ns.hasValue, RDFLiteral(info.value)))
        if info.origin_id is not None:
            g.add((uri, ns.hasOriginID, RDFLiteral(info.origin_id)))
        if info.source_obj_id is not None:
            g.add((uri, ns.hasSourceObjID, RDFLiteral(info.source_obj_id)))
        if info.change_mode != "state":
            g.add((uri, ns.hasChangeMode, RDFLiteral(info.change_mode)))

    # -- common CAEX object fields -----------------------------------------------

    def _emit_common(self, uri: URIRef, obj: object, *, metadata_path: str | None = None) -> None:
        """Emit identity plus every CAEXBasicObject header field.

        Every CAEX object can carry Description, Version, Copyright,
        Revision, AdditionalInformation and SourceObjectInformation; none of
        them may be dropped silently.
        """

        g, ns = self.graph, self.ns
        metadata_path = metadata_path or str(uri)
        name = getattr(obj, "name", None)
        if name is not None:
            g.add((uri, ns.hasName, RDFLiteral(name)))
            g.add((uri, RDFS.label, RDFLiteral(name)))
        object_id = getattr(obj, "id", None)
        if object_id:
            g.add((uri, ns.hasID, RDFLiteral(object_id)))
        for field_name, predicate, json_predicate in (
            ("description", ns.hasDescription, ns.hasDescriptionJson),
            ("version", ns.hasVersion, ns.hasVersionJson),
            ("copyright", ns.hasCopyright, ns.hasCopyrightJson),
        ):
            text = getattr(obj, field_name, None)
            if text is None:
                continue
            if text.value:
                g.add((uri, predicate, RDFLiteral(text.value)))
            if not text.value or text.change_mode != "state":
                # The plain literal is what SPARQL consumers read; the JSON
                # literal preserves an empty element or its ChangeMode.
                g.add((uri, json_predicate, RDFLiteral(text.to_aml_json(indent=None, include_change_mode=True))))
        for index, revision in enumerate(getattr(obj, "revision", None) or ()):
            self._map_revision(uri, revision, index, metadata_path)
        for index, info in enumerate(getattr(obj, "additional_information", None) or ()):
            self._map_additional_information(uri, info, index, metadata_path)
        for index, info in enumerate(getattr(obj, "source_object_information", None) or ()):
            self._map_source_object_information(uri, info, index, metadata_path)
        change_mode = getattr(obj, "change_mode", None)
        if change_mode is not None and change_mode != "state":
            g.add((uri, ns.hasChangeMode, RDFLiteral(change_mode)))

    # -- class libraries and their definitions ------------------------------------

    def _map_attribute_type_lib(self, lib: AttributeTypeLib, index: int) -> URIRef:
        g, ns = self.graph, self.ns
        lib_uri = self._mint(id=lib.id, path=f"{self.root_path}.AttributeTypeLib[{index}]")
        g.add((lib_uri, RDF.type, ns.AttributeTypeLib))
        self._emit_common(lib_uri, lib)
        for item_index, item in enumerate(lib.attribute_types):
            self._link(
                lib_uri, ns.hasAttributeType, self._map_attribute_type_def(item, lib.name), item_index
            )
        return lib_uri

    def _map_attribute_type_def(self, item: AttributeType, parent_aml_path: str) -> URIRef:
        g, ns = self.graph, self.ns
        aml_path = f"{parent_aml_path}/{item.name}"
        uri = self._resolve_class(aml_path, "attribute_type")
        g.add((uri, RDF.type, ns.AttributeType))
        g.add((uri, ns.hasAmlPath, RDFLiteral(aml_path)))
        self._emit_common(uri, item)
        self._emit_attribute_fields(uri, item)
        if item.ref_attribute_type:
            g.add((uri, RDFS.subClassOf, self._resolve_class(item.ref_attribute_type, "attribute_type")))
        for index, child in enumerate(item.attributes):
            self._link(uri, ns.hasAttribute, self._map_attribute_instance(child, uri, index), index)
        for index, child in enumerate(item.attribute_types):
            self._link(uri, ns.hasAttributeType, self._map_attribute_type_def(child, aml_path), index)
        return uri

    def _map_interface_class_lib(self, lib: InterfaceClassLib, index: int) -> URIRef:
        g, ns = self.graph, self.ns
        lib_uri = self._mint(id=lib.id, path=f"{self.root_path}.InterfaceClassLib[{index}]")
        g.add((lib_uri, RDF.type, ns.InterfaceClassLib))
        self._emit_common(lib_uri, lib)
        for item_index, item in enumerate(lib.interface_classes):
            self._link(
                lib_uri, ns.hasInterfaceClass, self._map_interface_class_def(item, lib.name), item_index
            )
        return lib_uri

    def _map_interface_class_def(self, item: InterfaceFamily, parent_aml_path: str) -> URIRef:
        g, ns = self.graph, self.ns
        aml_path = f"{parent_aml_path}/{item.name}"
        uri = self._resolve_class(aml_path, "interface")
        g.add((uri, RDF.type, ns.InterfaceClass))
        g.add((uri, ns.hasAmlPath, RDFLiteral(aml_path)))
        self._emit_common(uri, item)
        if item.ref_base_class_path:
            g.add((uri, RDFS.subClassOf, self._resolve_class(item.ref_base_class_path, "interface")))
        for index, attribute in enumerate(item.attributes):
            self._link(uri, ns.hasAttribute, self._map_attribute_instance(attribute, uri, index), index)
        for index, interface in enumerate(item.external_interfaces):
            self._link(
                uri, ns.hasExternalInterface, self._map_external_interface(interface, uri, index), index
            )
        for index, child in enumerate(item.interface_classes):
            self._link(uri, ns.hasInterfaceClass, self._map_interface_class_def(child, aml_path), index)
        return uri

    def _map_role_class_lib(self, lib: RoleClassLib, index: int) -> URIRef:
        g, ns = self.graph, self.ns
        lib_uri = self._mint(id=lib.id, path=f"{self.root_path}.RoleClassLib[{index}]")
        g.add((lib_uri, RDF.type, ns.RoleClassLib))
        self._emit_common(lib_uri, lib)
        for item_index, item in enumerate(lib.role_classes):
            self._link(lib_uri, ns.hasRoleClass, self._map_role_class_def(item, lib.name), item_index)
        return lib_uri

    def _map_role_class_def(self, item: RoleFamily, parent_aml_path: str) -> URIRef:
        g, ns = self.graph, self.ns
        aml_path = f"{parent_aml_path}/{item.name}"
        uri = self._resolve_class(aml_path, "role")
        g.add((uri, RDF.type, ns.RoleClass))
        g.add((uri, ns.hasAmlPath, RDFLiteral(aml_path)))
        self._emit_common(uri, item)
        if item.ref_base_class_path:
            g.add((uri, RDFS.subClassOf, self._resolve_class(item.ref_base_class_path, "role")))
        for index, attribute in enumerate(item.attributes):
            self._link(uri, ns.hasAttribute, self._map_attribute_instance(attribute, uri, index), index)
        for index, interface in enumerate(item.external_interfaces):
            self._link(
                uri, ns.hasExternalInterface, self._map_external_interface(interface, uri, index), index
            )
        for index, child in enumerate(item.role_classes):
            self._link(uri, ns.hasRoleClass, self._map_role_class_def(child, aml_path), index)
        return uri

    def _map_system_unit_class_lib(self, lib: SystemUnitClassLib, index: int) -> URIRef:
        g, ns = self.graph, self.ns
        lib_uri = self._mint(id=lib.id, path=f"{self.root_path}.SystemUnitClassLib[{index}]")
        g.add((lib_uri, RDF.type, ns.SystemUnitClassLib))
        self._emit_common(lib_uri, lib)
        for item_index, item in enumerate(lib.system_unit_classes):
            self._link(
                lib_uri, ns.hasSystemUnitClass, self._map_system_unit_class_def(item, lib.name), item_index
            )
        return lib_uri

    def _map_system_unit_class_def(self, item: SystemUnitFamily, parent_aml_path: str) -> URIRef:
        g, ns = self.graph, self.ns
        aml_path = f"{parent_aml_path}/{item.name}"
        uri = self._resolve_class(aml_path, "system_unit")
        g.add((uri, RDF.type, ns.SystemUnitClass))
        g.add((uri, ns.hasAmlPath, RDFLiteral(aml_path)))
        self._emit_common(uri, item)
        if item.ref_base_class_path:
            g.add((uri, RDFS.subClassOf, self._resolve_class(item.ref_base_class_path, "system_unit")))
        for index, attribute in enumerate(item.attributes):
            self._link(uri, ns.hasAttribute, self._map_attribute_instance(attribute, uri, index), index)
        for index, interface in enumerate(item.external_interfaces):
            self._link(
                uri, ns.hasExternalInterface, self._map_external_interface(interface, uri, index), index
            )
        for index, role in enumerate(item.supported_role_classes):
            self._map_supported_role_class(role, uri, index)
        for index, element in enumerate(item.internal_elements):
            self._link(uri, ns.hasInternalElement, self._map_internal_element(element, uri, index), index)
        for index, link in enumerate(item.internal_links):
            self._map_internal_link(link, uri, index)
        for index, child in enumerate(item.system_unit_classes):
            self._link(uri, ns.hasSystemUnitClass, self._map_system_unit_class_def(child, aml_path), index)
        return uri

    # -- instance hierarchy ---------------------------------------------------------

    def _map_instance_hierarchy(self, hierarchy: InstanceHierarchy, index: int) -> URIRef:
        g, ns = self.graph, self.ns
        uri = self._mint(id=hierarchy.id, path=f"{self.root_path}.InstanceHierarchy[{index}]")
        g.add((uri, RDF.type, ns.InstanceHierarchy))
        self._emit_common(uri, hierarchy)
        for element_index, element in enumerate(hierarchy.internal_elements):
            self._link(
                uri, ns.hasInternalElement, self._map_internal_element(element, uri, element_index), element_index
            )
        return uri

    def _map_internal_element(self, element: InternalElement, parent: URIRef, index: int) -> URIRef:
        g, ns = self.graph, self.ns
        uri = self._mint_child(parent, element, "InternalElement", index)
        g.add((uri, RDF.type, ns.InternalElement))
        self._emit_common(uri, element)
        if element.ref_base_system_unit_path:
            class_uri = self._resolve_class(element.ref_base_system_unit_path, "system_unit")
            g.add((uri, ns.hasRefBaseSystemUnitClass, class_uri))
            g.add((uri, RDF.type, class_uri))
        for index, attribute in enumerate(element.attributes):
            self._link(uri, ns.hasAttribute, self._map_attribute_instance(attribute, uri, index), index)
        for index, interface in enumerate(element.external_interfaces):
            self._link(
                uri, ns.hasExternalInterface, self._map_external_interface(interface, uri, index), index
            )
        for index, role in enumerate(element.role_requirements):
            self._map_role_requirement(role, uri, index)
        for index, role in enumerate(element.supported_role_classes):
            self._map_supported_role_class(role, uri, index)
        for index, child in enumerate(element.internal_elements):
            self._link(uri, ns.hasInternalElement, self._map_internal_element(child, uri, index), index)
        for index, link in enumerate(element.internal_links):
            self._map_internal_link(link, uri, index)
        return uri

    # -- attributes -------------------------------------------------------------------

    def _emit_attribute_fields(self, uri: URIRef, attribute: Attribute) -> None:
        g, ns = self.graph, self.ns
        if attribute.unit:
            g.add((uri, ns.hasUnitName, RDFLiteral(attribute.unit)))
        data_type_rule = self.profile.data_types.from_aml(attribute.attribute_data_type)
        # hasDataType is the effective (defaulted) type for consumers;
        # hasAttributeDataType is the value exactly as authored, and is only
        # present when the AML Attribute actually declared one.
        g.add((uri, ns.hasDataType, RDFLiteral(data_type_rule.canonical_aml_type)))
        if attribute.attribute_data_type is not None:
            g.add((uri, ns.hasAttributeDataType, RDFLiteral(attribute.attribute_data_type)))
        if attribute.value is not None:
            # hasAttributeValue is the authoritative, always-round-trippable
            # copy: a plain string literal, deliberately NOT re-typed. RDF
            # libraries are free to re-render a typed xsd:double/xsd:float
            # literal's lexical form on a serialize/parse cycle (e.g. "36"
            # comes back as "36.0", or in scientific notation) even though
            # the numeric *value* is unchanged -- verified against rdflib
            # directly. That is a real loss for an AML Value string, which
            # is application data, not a number Turtle gets to reformat.
            # hasTypedAttributeValue carries the RDF-native typed literal
            # for SPARQL/type-aware consumers who want it, and is not read
            # back by this module's reverse mapper.
            g.add((uri, ns.hasAttributeValue, RDFLiteral(attribute.value)))
            g.add((uri, ns.hasTypedAttributeValue, RDFLiteral(attribute.value, datatype=data_type_rule.xsd_term)))
        if attribute.default_value is not None:
            g.add((uri, ns.hasDefaultValue, RDFLiteral(attribute.default_value)))
            g.add(
                (uri, ns.hasTypedDefaultValue, RDFLiteral(attribute.default_value, datatype=data_type_rule.xsd_term))
            )
        for index, semantic in enumerate(attribute.ref_semantic):
            semantic_uri = self._mint_child(uri, semantic, "RefSemantic", index)
            self._link(uri, ns.hasSemanticRef, semantic_uri, index)
            g.add((semantic_uri, RDF.type, ns.RefSemantic))
            self._emit_common(semantic_uri, semantic)
            g.add(
                (
                    semantic_uri,
                    ns.hasCorrespondingAttributePath,
                    RDFLiteral(semantic.corresponding_attribute_path),
                )
            )
        for index, constraint in enumerate(attribute.constraint):
            self._map_constraint(constraint, uri, index)

    def _map_attribute_instance(self, attribute: Attribute, parent: URIRef, index: int) -> URIRef:
        g, ns = self.graph, self.ns
        uri = self._mint_child(parent, attribute, "Attribute", index)
        g.add((uri, RDF.type, ns.Attribute))
        self._emit_common(uri, attribute)
        self._emit_attribute_fields(uri, attribute)
        if attribute.ref_attribute_type:
            type_uri = self._resolve_class(attribute.ref_attribute_type, "attribute_type")
            g.add((uri, ns.hasRefAttributeType, type_uri))
            g.add((uri, RDF.type, type_uri))
        for child_index, child in enumerate(attribute.attributes):
            self._link(uri, ns.hasAttribute, self._map_attribute_instance(child, uri, child_index), child_index)
        return uri

    def _map_constraint(self, constraint: AttributeValueRequirement, parent: URIRef, index: int) -> URIRef:
        g, ns = self.graph, self.ns
        uri = self._mint_child(parent, constraint, "Constraint", index)
        self._link(parent, ns.hasConstraint, uri, index)
        g.add((uri, RDF.type, ns.Constraint))
        self._emit_common(uri, constraint)
        if constraint.nominal_scaled_type is not None:
            g.add((uri, RDF.type, ns.NominalScaledConstraint))
            # An rdf:List, not a set of hasRequiredValue triples: AML's
            # NominalScaledType.RequiredValue is an ordered sequence, and
            # plain triples would let a round trip silently permute it.
            list_uri = self._mint_child(uri, constraint.nominal_scaled_type, "RequiredValueList", 0)
            g.add((uri, ns.hasRequiredValueList, list_uri))
            Collection(
                g,
                list_uri,
                [RDFLiteral(value) for value in constraint.nominal_scaled_type.required_values],
            )
        if constraint.ordinal_scaled_type is not None:
            g.add((uri, RDF.type, ns.OrdinalScaledConstraint))
            ordinal = constraint.ordinal_scaled_type
            if ordinal.required_value is not None:
                g.add((uri, ns.hasRequiredValue, RDFLiteral(ordinal.required_value)))
            if ordinal.required_min_value is not None:
                g.add((uri, ns.hasRequiredMinValue, RDFLiteral(ordinal.required_min_value)))
            if ordinal.required_max_value is not None:
                g.add((uri, ns.hasRequiredMaxValue, RDFLiteral(ordinal.required_max_value)))
        if constraint.unknown_type is not None:
            g.add((uri, RDF.type, ns.UnknownConstraint))
            if constraint.unknown_type.requirements is not None:
                g.add((uri, ns.hasRequirements, RDFLiteral(constraint.unknown_type.requirements)))
        return uri

    # -- interfaces and links -----------------------------------------------------------

    def _map_external_interface(self, interface: InterfaceClass, parent: URIRef, index: int) -> URIRef:
        g, ns = self.graph, self.ns
        uri = self._mint_child(parent, interface, "ExternalInterface", index)
        g.add((uri, RDF.type, ns.ExternalInterface))
        self._emit_common(uri, interface)
        if interface.ref_base_class_path:
            class_uri = self._resolve_class(interface.ref_base_class_path, "interface")
            g.add((uri, ns.hasRefBaseClass, class_uri))
            g.add((uri, RDF.type, class_uri))
        for attr_index, attribute in enumerate(interface.attributes):
            self._link(uri, ns.hasAttribute, self._map_attribute_instance(attribute, uri, attr_index), attr_index)
        for sub_index, sub_interface in enumerate(interface.external_interfaces):
            self._link(
                uri,
                ns.hasExternalInterface,
                self._map_external_interface(sub_interface, uri, sub_index),
                sub_index,
            )
        return uri

    def _map_internal_link(self, link: InternalLink, parent: URIRef, index: int) -> None:
        g, ns = self.graph, self.ns
        uri = self._mint_child(parent, link, "InternalLink", index)
        self._link(parent, ns.hasInternalLink, uri, index)
        g.add((uri, RDF.type, ns.InternalLink))
        self._emit_common(uri, link)
        g.add((uri, ns.hasRefPartnerSideA, RDFLiteral(link.ref_partner_side_a)))
        g.add((uri, ns.hasRefPartnerSideB, RDFLiteral(link.ref_partner_side_b)))
        g.add((uri, ns.hasSideA, self._resolve_partner(link.ref_partner_side_a)))
        g.add((uri, ns.hasSideB, self._resolve_partner(link.ref_partner_side_b)))
        g.add((self._resolve_partner(link.ref_partner_side_a), ns.isLinkedTo, self._resolve_partner(link.ref_partner_side_b)))

    def _resolve_partner(self, reference: str) -> URIRef:
        raw_owner_id, _, interface_name = reference.partition(":")
        # ReferenceIndex.resolve_id already ignores optional GUID braces.
        owner_id = raw_owner_id.strip()
        if not interface_name:
            target = self.index.resolve_id(owner_id)
            if target is None:
                raise RDFMappingUnsupported(
                    f"InternalLink partner reference {reference!r} does not "
                    "resolve to any CAEX object ID in this document."
                )
            return self._mint(id=target.id, path=self.root_path + target.path[1:])
        owner = self.index.resolve_id(owner_id)
        if owner is None or not hasattr(owner.obj, "external_interfaces"):
            raise RDFMappingUnsupported(
                f"InternalLink partner reference {reference!r} does not "
                "resolve to an owner with external interfaces in this document."
            )
        for position, interface in enumerate(owner.obj.external_interfaces):
            if interface.name == interface_name:
                if interface.id:
                    return self._mint(id=interface.id, path="")
                owner_uri = self._mint(id=owner.id, path=self.root_path + owner.path[1:])
                return self._mint_child(owner_uri, interface, "ExternalInterface", position)
        raise RDFMappingUnsupported(
            f"InternalLink partner reference {reference!r} names an "
            f"ExternalInterface {interface_name!r} that does not exist on "
            f"{owner_id!r}."
        )

    # -- role relationships -------------------------------------------------------------

    def _map_role_requirement(self, role: RoleRequirements, owner: URIRef, index: int) -> None:
        g, ns = self.graph, self.ns
        uri = self._mint_child(owner, role, "RoleRequirements", index)
        self._link(owner, ns.hasRoleRequirements, uri, index)
        g.add((uri, RDF.type, ns.RoleRequirements))
        self._emit_common(uri, role)
        role_uri = self._resolve_class(role.ref_base_role_class_path, "role")
        g.add((uri, ns.hasRefBaseRoleClass, role_uri))
        g.add((owner, RDF.type, role_uri))
        for index2, attribute in enumerate(role.attributes):
            self._link(uri, ns.hasAttribute, self._map_attribute_instance(attribute, uri, index2), index2)
        for index2, interface in enumerate(role.external_interfaces):
            self._link(
                uri, ns.hasExternalInterface, self._map_external_interface(interface, uri, index2), index2
            )
        if role.mapping_object is not None:
            self._map_mapping_object(role.mapping_object, uri)

    def _map_supported_role_class(self, role: SupportedRoleClass, owner: URIRef, index: int) -> None:
        g, ns = self.graph, self.ns
        uri = self._mint_child(owner, role, "SupportedRoleClass", index)
        self._link(owner, ns.hasSupportedRoleClass, uri, index)
        g.add((uri, RDF.type, ns.SupportedRoleClass))
        self._emit_common(uri, role)
        role_uri = self._resolve_class(role.ref_role_class_path, "role")
        g.add((uri, ns.hasRefRoleClass, role_uri))
        g.add((owner, RDF.type, role_uri))
        if role.mapping_object is not None:
            self._map_mapping_object(role.mapping_object, uri)

    def _map_mapping_object(self, mapping: MappingObject, owner: URIRef) -> None:
        g, ns = self.graph, self.ns
        uri = self._mint_child(owner, mapping, "MappingObject", 0)
        g.add((owner, ns.hasMappingObject, uri))
        g.add((uri, RDF.type, ns.MappingObject))
        self._emit_common(uri, mapping)
        for index, pair in enumerate(mapping.attribute_name_mapping):
            pair_uri = self._mint_child(uri, pair, "AttributeNameMapping", index)
            self._link(uri, ns.hasAttributeNameMapping, pair_uri, index)
            g.add((pair_uri, RDF.type, ns.AttributeNameMapping))
            self._emit_common(pair_uri, pair)
            g.add((pair_uri, ns.hasSystemUnitAttributeName, RDFLiteral(pair.system_unit_attribute_name)))
            g.add((pair_uri, ns.hasRoleAttributeName, RDFLiteral(pair.role_attribute_name)))
        for index, pair in enumerate(mapping.interface_id_mapping):
            pair_uri = self._mint_child(uri, pair, "InterfaceIDMapping", index)
            self._link(uri, ns.hasInterfaceIDMapping, pair_uri, index)
            g.add((pair_uri, RDF.type, ns.InterfaceIDMapping))
            self._emit_common(pair_uri, pair)
            g.add((pair_uri, ns.hasSystemUnitInterfaceID, RDFLiteral(pair.system_unit_interface_id)))
            g.add((pair_uri, ns.hasRoleInterfaceID, RDFLiteral(pair.role_interface_id)))


# ---------------------------------------------------------------------------
# Reverse mapping: rdflib.Graph -> CAEXFile
# ---------------------------------------------------------------------------


def rdf_graph_to_document(
    graph: Graph,
    *,
    profile: RDFMappingProfile = DEFAULT_MAPPING_PROFILE,
) -> CAEXFile:
    """Reconstruct a CAEX document from an RDF graph produced by this profile."""

    return _ReverseMapper(graph, profile).build()


def ttl_to_document(
    ttl: str | bytes,
    *,
    profile: RDFMappingProfile = DEFAULT_MAPPING_PROFILE,
) -> CAEXFile:
    """Parse Turtle text and reconstruct the CAEX document it encodes."""

    graph = Graph()
    graph.parse(data=ttl, format="turtle")
    return rdf_graph_to_document(graph, profile=profile)


def round_trip_ttl(
    document: CAEXFile,
    *,
    profile: RDFMappingProfile = DEFAULT_MAPPING_PROFILE,
) -> RDFRoundTripResult:
    """Exercise an AML -> Turtle -> AML semantic round trip.

    Mirrors ``round_trip_document`` in ``automationml.opcua``: the result
    retains the source document, the intervening Turtle text, and the
    recovered document so a failed or lossy mapping is inspectable rather
    than reduced to a Boolean.
    """

    ttl = document_to_ttl(document, profile=profile)
    recovered = ttl_to_document(ttl, profile=profile)
    return RDFRoundTripResult(
        differences=compare_aml_semantics(document, recovered),
        mapping_profile=f"{profile.name}-v{profile.version}",
        source_document=document,
        ttl=ttl,
        recovered_document=recovered,
    )


class _ReverseMapper:
    def __init__(self, graph: Graph, profile: RDFMappingProfile) -> None:
        self.graph = graph
        self.profile = profile
        self.ns = Namespace(profile.base_uri)

    # -- small graph-reading helpers ---------------------------------------------

    def _value(self, subject: URIRef, predicate: URIRef) -> str | None:
        value = self.graph.value(subject, predicate)
        return None if value is None else str(value)

    def _ordered(self, subject: URIRef, predicate: URIRef) -> list[URIRef]:
        children = list(self.graph.objects(subject, predicate))
        children.sort(key=lambda child: int(self.graph.value(child, self.ns.hasIndex) or 0))
        return children

    def _aml_path(self, uri: URIRef) -> str:
        path = self._value(uri, self.ns.hasAmlPath)
        if path is not None:
            return path
        external_path = self._value(uri, self.ns.hasExternalClassPath)
        if external_path is not None:
            return external_path
        raise RDFMappingUnsupported(
            f"RDF node {uri} has neither hasAmlPath nor hasExternalClassPath; "
            "it cannot be turned back into an AML class-path reference."
        )

    # -- entry point ---------------------------------------------------------------

    def build(self) -> CAEXFile:
        g, ns = self.graph, self.ns
        candidates = list(g.subjects(RDF.type, ns.CAEXFile))
        if len(candidates) != 1:
            raise RDFMappingUnsupported(
                f"Expected exactly one aml:CAEXFile node, found {len(candidates)}."
            )
        file_uri = candidates[0]

        origins = [
            self._map_source_document(uri) for uri in self._ordered(file_uri, ns.hasOrigin)
        ]
        document = build_caex_file(self._value(file_uri, ns.hasFileName) or "")
        # ``caex_file()`` is a convenience builder that fills in a default
        # SourceDocumentInformation and SuperiorStandardVersion when none is
        # given. Those defaults must not leak into a reconstruction: the
        # graph is authoritative, including when it encodes zero of either.
        document.source_document_information = origins
        document.superior_standard_versions = [
            str(value) for value in g.objects(file_uri, ns.hasSuperiorStandardVersion)
        ]
        document.schema_version = self._value(file_uri, ns.hasSchemaVersion) or "3.0"

        for reference_uri in self._ordered(file_uri, ns.hasExternalReference):
            document.external_references.append(self._map_external_reference(reference_uri))
        self._apply_common(document, file_uri)

        for lib_uri in self._ordered(file_uri, ns.hasAttributeTypeLib):
            document.attribute_type_libs.append(self._map_attribute_type_lib(lib_uri))
        for lib_uri in self._ordered(file_uri, ns.hasInterfaceClassLib):
            document.interface_class_libs.append(self._map_interface_class_lib(lib_uri))
        for lib_uri in self._ordered(file_uri, ns.hasRoleClassLib):
            document.role_class_libs.append(self._map_role_class_lib(lib_uri))
        for lib_uri in self._ordered(file_uri, ns.hasSystemUnitClassLib):
            document.system_unit_class_libs.append(self._map_system_unit_class_lib(lib_uri))
        for hierarchy_uri in self._ordered(file_uri, ns.hasInstanceHierarchy):
            document.instance_hierarchies.append(self._map_instance_hierarchy(hierarchy_uri))
        return document

    def _map_source_document(self, uri: URIRef) -> SourceDocumentInformation:
        ns = self.ns
        source = build_source_document(
            origin_name=self._value(uri, ns.hasOriginName) or "",
            origin_id=self._value(uri, ns.hasOriginID) or "",
        )
        source.origin_vendor = self._value(uri, ns.hasOriginVendor)
        source.origin_vendor_url = self._value(uri, ns.hasOriginVendorURL)
        source.origin_version = self._value(uri, ns.hasOriginVersion)
        source.origin_release = self._value(uri, ns.hasOriginRelease)
        source.origin_project_id = self._value(uri, ns.hasOriginProjectID)
        source.origin_project_title = self._value(uri, ns.hasOriginProjectTitle)
        last_writing = self._value(uri, ns.hasLastWritingDateTime)
        if last_writing:
            from datetime import datetime

            source.last_writing_date_time = datetime.fromisoformat(last_writing)
        return source

    def _map_external_reference(self, uri: URIRef) -> ExternalReference:
        ns = self.ns
        reference = ExternalReference(
            path=self._value(uri, ns.hasPath) or "",
            file_alias=self._value(uri, ns.hasAlias) or "",
        )
        self._apply_common(reference, uri)
        return reference

    def _map_additional_information(self, uri: URIRef) -> AdditionalInformation:
        payload = self._value(uri, self.ns.hasAdditionalInformationJson)
        if payload is None:
            return AdditionalInformation()
        return AdditionalInformation.from_aml_json(payload)

    # -- common fields --------------------------------------------------------------

    def _read_id_name(self, uri: URIRef) -> tuple[str | None, str | None]:
        return self._value(uri, self.ns.hasID), self._value(uri, self.ns.hasName)

    def _map_revision(self, uri: URIRef) -> Revision:
        ns = self.ns
        return Revision(
            revision_date=self._value(uri, ns.hasRevisionDate),
            old_version=self._value(uri, ns.hasOldVersion),
            new_version=self._value(uri, ns.hasNewVersion),
            author_name=self._value(uri, ns.hasAuthorName),
            comment=self._value(uri, ns.hasComment),
            change_mode=self._value(uri, ns.hasChangeMode) or "state",
        )

    def _map_source_object_information(self, uri: URIRef) -> SourceObjectInformation:
        ns = self.ns
        return SourceObjectInformation(
            value=self._value(uri, ns.hasValue) or "",
            origin_id=self._value(uri, ns.hasOriginID),
            source_obj_id=self._value(uri, ns.hasSourceObjID),
            change_mode=self._value(uri, ns.hasChangeMode) or "state",
        )

    def _apply_common(self, obj, uri: URIRef) -> None:
        ns = self.ns
        for field_name, predicate, json_predicate in (
            ("description", ns.hasDescription, ns.hasDescriptionJson),
            ("version", ns.hasVersion, ns.hasVersionJson),
            ("copyright", ns.hasCopyright, ns.hasCopyrightJson),
        ):
            payload = self._value(uri, json_predicate)
            if payload is not None:
                setattr(obj, field_name, TextElement.from_aml_json(payload))
                continue
            text = self._value(uri, predicate)
            if text is not None:
                setattr(obj, field_name, TextElement(value=text))
        obj.revision = [self._map_revision(item) for item in self._ordered(uri, ns.hasRevision)]
        obj.additional_information = [
            self._map_additional_information(item) for item in self._ordered(uri, ns.hasAdditionalInformation)
        ]
        obj.source_object_information = [
            self._map_source_object_information(item)
            for item in self._ordered(uri, ns.hasSourceObjectInformation)
        ]
        change_mode = self._value(uri, self.ns.hasChangeMode)
        if change_mode is not None:
            obj.change_mode = change_mode

    # -- class libraries -------------------------------------------------------------

    def _map_attribute_type_lib(self, uri: URIRef) -> AttributeTypeLib:
        ns = self.ns
        lib = AttributeTypeLib(id=self._value(uri, ns.hasID), name=self._value(uri, ns.hasName) or "")
        self._apply_common(lib, uri)
        for item_uri in self._ordered(uri, ns.hasAttributeType):
            lib.attribute_types.append(self._map_attribute_type_def(item_uri))
        return lib

    def _map_attribute_type_def(self, uri: URIRef) -> AttributeType:
        ns = self.ns
        item_id, name = self._read_id_name(uri)
        item = AttributeType(id=item_id, name=name or "")
        self._apply_common(item, uri)
        self._apply_attribute_fields(item, uri)
        parent = self.graph.value(uri, RDFS.subClassOf)
        if parent is not None:
            item.ref_attribute_type = self._aml_path(parent)
        for attr_uri in self._ordered(uri, ns.hasAttribute):
            item.attributes.append(self._map_attribute_instance(attr_uri))
        for child_uri in self._ordered(uri, ns.hasAttributeType):
            item.attribute_types.append(self._map_attribute_type_def(child_uri))
        return item

    def _map_interface_class_lib(self, uri: URIRef) -> InterfaceClassLib:
        ns = self.ns
        lib = InterfaceClassLib(id=self._value(uri, ns.hasID), name=self._value(uri, ns.hasName) or "")
        self._apply_common(lib, uri)
        for item_uri in self._ordered(uri, ns.hasInterfaceClass):
            lib.interface_classes.append(self._map_interface_class_def(item_uri))
        return lib

    def _map_interface_class_def(self, uri: URIRef) -> InterfaceFamily:
        ns = self.ns
        item_id, name = self._read_id_name(uri)
        item = InterfaceFamily(id=item_id, name=name or "")
        self._apply_common(item, uri)
        parent = self.graph.value(uri, RDFS.subClassOf)
        if parent is not None:
            item.ref_base_class_path = self._aml_path(parent)
        for attr_uri in self._ordered(uri, ns.hasAttribute):
            item.attributes.append(self._map_attribute_instance(attr_uri))
        for interface_uri in self._ordered(uri, ns.hasExternalInterface):
            item.external_interfaces.append(self._map_external_interface(interface_uri))
        for child_uri in self._ordered(uri, ns.hasInterfaceClass):
            item.interface_classes.append(self._map_interface_class_def(child_uri))
        return item

    def _map_role_class_lib(self, uri: URIRef) -> RoleClassLib:
        ns = self.ns
        lib = RoleClassLib(id=self._value(uri, ns.hasID), name=self._value(uri, ns.hasName) or "")
        self._apply_common(lib, uri)
        for item_uri in self._ordered(uri, ns.hasRoleClass):
            lib.role_classes.append(self._map_role_class_def(item_uri))
        return lib

    def _map_role_class_def(self, uri: URIRef) -> RoleFamily:
        ns = self.ns
        item_id, name = self._read_id_name(uri)
        item = RoleFamily(id=item_id, name=name or "")
        self._apply_common(item, uri)
        parent = self.graph.value(uri, RDFS.subClassOf)
        if parent is not None:
            item.ref_base_class_path = self._aml_path(parent)
        for attr_uri in self._ordered(uri, ns.hasAttribute):
            item.attributes.append(self._map_attribute_instance(attr_uri))
        for interface_uri in self._ordered(uri, ns.hasExternalInterface):
            item.external_interfaces.append(self._map_external_interface(interface_uri))
        for child_uri in self._ordered(uri, ns.hasRoleClass):
            item.role_classes.append(self._map_role_class_def(child_uri))
        return item

    def _map_system_unit_class_lib(self, uri: URIRef) -> SystemUnitClassLib:
        ns = self.ns
        lib = SystemUnitClassLib(id=self._value(uri, ns.hasID), name=self._value(uri, ns.hasName) or "")
        self._apply_common(lib, uri)
        for item_uri in self._ordered(uri, ns.hasSystemUnitClass):
            lib.system_unit_classes.append(self._map_system_unit_class_def(item_uri))
        return lib

    def _map_system_unit_class_def(self, uri: URIRef) -> SystemUnitFamily:
        ns = self.ns
        item_id, name = self._read_id_name(uri)
        item = SystemUnitFamily(id=item_id, name=name or "")
        self._apply_common(item, uri)
        parent = self.graph.value(uri, RDFS.subClassOf)
        if parent is not None:
            item.ref_base_class_path = self._aml_path(parent)
        for attr_uri in self._ordered(uri, ns.hasAttribute):
            item.attributes.append(self._map_attribute_instance(attr_uri))
        for interface_uri in self._ordered(uri, ns.hasExternalInterface):
            item.external_interfaces.append(self._map_external_interface(interface_uri))
        for role_uri in self._ordered(uri, ns.hasSupportedRoleClass):
            item.supported_role_classes.append(self._map_supported_role_class(role_uri))
        for element_uri in self._ordered(uri, ns.hasInternalElement):
            item.internal_elements.append(self._map_internal_element(element_uri))
        for link_uri in self._ordered(uri, ns.hasInternalLink):
            item.internal_links.append(self._map_internal_link(link_uri))
        for child_uri in self._ordered(uri, ns.hasSystemUnitClass):
            item.system_unit_classes.append(self._map_system_unit_class_def(child_uri))
        return item

    # -- instance hierarchy ----------------------------------------------------------

    def _map_instance_hierarchy(self, uri: URIRef) -> InstanceHierarchy:
        ns = self.ns
        hierarchy = build_instance_hierarchy(self._value(uri, ns.hasName) or "", id=self._value(uri, ns.hasID))
        self._apply_common(hierarchy, uri)
        for element_uri in self._ordered(uri, ns.hasInternalElement):
            hierarchy.internal_elements.append(self._map_internal_element(element_uri))
        return hierarchy

    def _map_internal_element(self, uri: URIRef) -> InternalElement:
        ns = self.ns
        element_id, name = self._read_id_name(uri)
        element = build_internal_element(name or "", id=element_id)
        self._apply_common(element, uri)
        class_uri = self.graph.value(uri, ns.hasRefBaseSystemUnitClass)
        if class_uri is not None:
            element.ref_base_system_unit_path = self._aml_path(class_uri)
        for attr_uri in self._ordered(uri, ns.hasAttribute):
            element.attributes.append(self._map_attribute_instance(attr_uri))
        for interface_uri in self._ordered(uri, ns.hasExternalInterface):
            element.external_interfaces.append(self._map_external_interface(interface_uri))
        for role_uri in self._ordered(uri, ns.hasRoleRequirements):
            element.role_requirements.append(self._map_role_requirement(role_uri))
        for role_uri in self._ordered(uri, ns.hasSupportedRoleClass):
            element.supported_role_classes.append(self._map_supported_role_class(role_uri))
        for child_uri in self._ordered(uri, ns.hasInternalElement):
            element.internal_elements.append(self._map_internal_element(child_uri))
        for link_uri in self._ordered(uri, ns.hasInternalLink):
            element.internal_links.append(self._map_internal_link(link_uri))
        return element

    # -- attributes --------------------------------------------------------------------

    def _apply_attribute_fields(self, attribute: Attribute, uri: URIRef) -> None:
        ns = self.ns
        attribute.unit = self._value(uri, ns.hasUnitName)
        attribute.attribute_data_type = self._value(uri, ns.hasAttributeDataType)
        value = self.graph.value(uri, ns.hasAttributeValue)
        if value is not None:
            attribute.value = str(value)
        default_value = self.graph.value(uri, ns.hasDefaultValue)
        if default_value is not None:
            attribute.default_value = str(default_value)
        for semantic_uri in self._ordered(uri, ns.hasSemanticRef):
            path = self._value(semantic_uri, ns.hasCorrespondingAttributePath)
            if path is not None:
                semantic = RefSemantic(corresponding_attribute_path=path)
                self._apply_common(semantic, semantic_uri)
                attribute.ref_semantic.append(semantic)
        for constraint_uri in self._ordered(uri, ns.hasConstraint):
            attribute.constraint.append(self._map_constraint(constraint_uri))

    def _map_attribute_instance(self, uri: URIRef) -> Attribute:
        ns = self.ns
        attr_id, name = self._read_id_name(uri)
        attribute = build_attribute(name or "", id=attr_id)
        self._apply_common(attribute, uri)
        self._apply_attribute_fields(attribute, uri)
        type_uri = self.graph.value(uri, ns.hasRefAttributeType)
        if type_uri is not None:
            attribute.ref_attribute_type = self._aml_path(type_uri)
        for child_uri in self._ordered(uri, ns.hasAttribute):
            attribute.attributes.append(self._map_attribute_instance(child_uri))
        return attribute

    def _map_constraint(self, uri: URIRef) -> AttributeValueRequirement:
        ns = self.ns
        types = set(self.graph.objects(uri, RDF.type))
        name = self._value(uri, ns.hasName) or ""
        constraint = AttributeValueRequirement(name=name)
        self._apply_common(constraint, uri)
        if ns.NominalScaledConstraint in types:
            list_uri = self.graph.value(uri, ns.hasRequiredValueList)
            values = list(Collection(self.graph, list_uri)) if list_uri is not None else []
            constraint.nominal_scaled_type = NominalScaledType(
                required_values=[str(v) for v in values]
            )
        elif ns.OrdinalScaledConstraint in types:
            constraint.ordinal_scaled_type = OrdinalScaledType(
                required_value=self._value(uri, ns.hasRequiredValue),
                required_min_value=self._value(uri, ns.hasRequiredMinValue),
                required_max_value=self._value(uri, ns.hasRequiredMaxValue),
            )
        elif ns.UnknownConstraint in types:
            constraint.unknown_type = UnknownType(requirements=self._value(uri, ns.hasRequirements))
        return constraint

    # -- interfaces and links ------------------------------------------------------------

    def _map_external_interface(self, uri: URIRef) -> InterfaceClass:
        ns = self.ns
        interface_id, name = self._read_id_name(uri)
        interface = build_external_interface(name or "", id=interface_id)
        self._apply_common(interface, uri)
        class_uri = self.graph.value(uri, ns.hasRefBaseClass)
        if class_uri is not None:
            interface.ref_base_class_path = self._aml_path(class_uri)
        for attr_uri in self._ordered(uri, ns.hasAttribute):
            interface.attributes.append(self._map_attribute_instance(attr_uri))
        for sub_uri in self._ordered(uri, ns.hasExternalInterface):
            interface.external_interfaces.append(self._map_external_interface(sub_uri))
        return interface

    def _map_internal_link(self, uri: URIRef) -> InternalLink:
        ns = self.ns
        link_id, name = self._read_id_name(uri)
        link = InternalLink(
            id=link_id,
            name=name or "",
            ref_partner_side_a=self._value(uri, ns.hasRefPartnerSideA) or "",
            ref_partner_side_b=self._value(uri, ns.hasRefPartnerSideB) or "",
        )
        self._apply_common(link, uri)
        return link

    # -- role relationships -----------------------------------------------------------

    def _map_role_requirement(self, uri: URIRef) -> RoleRequirements:
        ns = self.ns
        role_uri = self.graph.value(uri, ns.hasRefBaseRoleClass)
        role = RoleRequirements(ref_base_role_class_path=self._aml_path(role_uri) if role_uri is not None else "")
        self._apply_common(role, uri)
        for attr_uri in self._ordered(uri, ns.hasAttribute):
            role.attributes.append(self._map_attribute_instance(attr_uri))
        for interface_uri in self._ordered(uri, ns.hasExternalInterface):
            role.external_interfaces.append(self._map_external_interface(interface_uri))
        mapping_uri = self.graph.value(uri, ns.hasMappingObject)
        if mapping_uri is not None:
            role.mapping_object = self._map_mapping_object(mapping_uri)
        return role

    def _map_supported_role_class(self, uri: URIRef) -> SupportedRoleClass:
        ns = self.ns
        role_uri = self.graph.value(uri, ns.hasRefRoleClass)
        role = SupportedRoleClass(ref_role_class_path=self._aml_path(role_uri) if role_uri is not None else "")
        self._apply_common(role, uri)
        mapping_uri = self.graph.value(uri, ns.hasMappingObject)
        if mapping_uri is not None:
            role.mapping_object = self._map_mapping_object(mapping_uri)
        return role

    def _map_mapping_object(self, uri: URIRef) -> MappingObject:
        ns = self.ns
        mapping = MappingObject()
        self._apply_common(mapping, uri)
        for pair_uri in self._ordered(uri, ns.hasAttributeNameMapping):
            name_pair = AttributeNameMapping(
                system_unit_attribute_name=self._value(pair_uri, ns.hasSystemUnitAttributeName) or "",
                role_attribute_name=self._value(pair_uri, ns.hasRoleAttributeName) or "",
            )
            self._apply_common(name_pair, pair_uri)
            mapping.attribute_name_mapping.append(name_pair)
        for pair_uri in self._ordered(uri, ns.hasInterfaceIDMapping):
            id_pair = InterfaceIDMapping(
                system_unit_interface_id=self._value(pair_uri, ns.hasSystemUnitInterfaceID) or "",
                role_interface_id=self._value(pair_uri, ns.hasRoleInterfaceID) or "",
            )
            self._apply_common(id_pair, pair_uri)
            mapping.interface_id_mapping.append(id_pair)
        return mapping
