#!/usr/bin/env python3
"""Validate readable enrolment inputs and generate iCARE Onto instance graphs.

The generate() function is the reusable entry point for a later form/backend.
No network access or graph-store connection is used.
"""
import argparse
from copy import deepcopy
import hashlib
import json
import os
from datetime import datetime
from decimal import Decimal
from pathlib import Path
import re
import tempfile
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from jsonschema import Draft202012Validator, FormatChecker
from pyshacl import validate as validate_shapes
from rdflib import Dataset, Graph, Literal, Namespace, RDF, RDFS, OWL, URIRef, XSD
from rdflib.namespace import DCTERMS

try:
    from . import section_records
except ImportError:
    import section_records

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA = ROOT.parent / "serialisation"
DEFAULT_BASE = "https://example.org/maya/instantiation/"
IC = Namespace("http://maya-project.eu/icareonto/")
ONTOLOGY = URIRef("http://maya-project.eu/icareonto")
SH = Namespace("http://www.w3.org/ns/shacl#")
GENERATOR_VERSION = "1.1"
STATUS = {"screening": "ScreeningEnrolmentStatus", "enrolled": "EnrolledStatus", "active": "ActiveEnrolmentStatus", "completed": "CompletedEnrolmentStatus", "withdrawn": "WithdrawnEnrolmentStatus"}
CONSENT = {"pending": "ConsentPending", "granted": "ConsentGranted", "refused": "ConsentRefused", "withdrawn": "ConsentWithdrawn", "expired": "ConsentExpired"}
PREFERENCES = {
    "language_tag": ("LanguagePreference", "preferredLanguageTag", None),
    "detail_level": ("InformationPreference", "informationPreferenceHasDetailLevel", {"brief": "BriefInformation", "detailed": "DetailedInformation"}),
    "communication_channel": ("CommunicationPreference", "preferredCommunicationChannel", {"smart_mirror": "SmartMirrorChannel", "mobile_app": "MobileAppChannel", "email": "EmailChannel", "sms": "SMSChannel", "telephone": "TelephoneChannel", "in_person": "InPersonChannel"}),
    "contact_time": ("ContactPreference", "preferredContactTime", {"morning": "MorningTimeOfDay", "afternoon": "AfternoonTimeOfDay", "evening": "EveningTimeOfDay", "night": "NightTimeOfDay", "any_time": "AnyTimeOfDay"})
}


class InputError(ValueError):
    """A failed input, reference or graph check; outputs have not been published."""


def canonical(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode()


def digest(content):
    return hashlib.sha256(content).hexdigest()


def read_json(path):
    """Read input without silently discarding duplicate keys or non-finite numbers."""
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise InputError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result
    def constant(value):
        raise InputError(f"Non-finite number is not valid input JSON: {value}")
    return json.loads(Path(path).read_text(), object_pairs_hook=pairs, parse_constant=constant)


def stamp(value):
    return datetime.fromisoformat(value.upper().replace("Z", "+00:00"))


FORMATS = FormatChecker()


@FORMATS.checks("date-time")
def offset_datetime(value):
    # jsonschema's built-in date-time checker needs an optional dependency.
    # Enforce this profile explicitly, including mandatory seconds and offset.
    if not isinstance(value, str):
        return True  # The schema's type constraint reports non-string input.
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[Zz]|[+-](?:[01]\d|2[0-3]):[0-5]\d)", value):
        return False
    try:
        return stamp(value).utcoffset() is not None
    except ValueError:
        return False


def input_schema(kind):
    """Inline the local shared schema so validation never fetches a remote file."""
    spec = read_json(ROOT / "schemas" / f"{kind}.schema.json")
    sections = read_json(ROOT / "schemas/sections.schema.json")
    spec["properties"]["sections"] = {k: v for k, v in sections.items() if k not in ("$schema", "$defs")}
    spec.setdefault("$defs", {}).update(sections["$defs"])
    return spec


def validate_input(kind, data):
    """Validate the field contract, then check dates and cross-field consistency."""
    spec = input_schema(kind)
    Draft202012Validator.check_schema(spec)
    errors = sorted(Draft202012Validator(spec, format_checker=FORMATS).iter_errors(data), key=lambda e: str(list(e.absolute_path)))
    if errors:
        raise InputError("Input validation failed:\n" + "\n".join(f"  {'.'.join(map(str, e.absolute_path)) or '$'}: {e.message}" for e in errors))

    def walk(value, path="$"):
        if isinstance(value, str):
            if not value.strip() or re.fullmatch(r"<[^<>]+>", value.strip()):
                raise InputError(f"{path}: blank text or an unresolved placeholder")
        elif isinstance(value, dict):
            for key, item in value.items():
                walk(item, f"{path}.{key}")
        elif isinstance(value, list):
            for index, item in enumerate(value):
                walk(item, f"{path}[{index}]")
    walk(data)
    if kind == "pilot":
        locale = data["site"]["locale"]
        try:
            ZoneInfo(locale["time_zone"])
        except (ZoneInfoNotFoundError, ValueError):
            raise InputError("site.locale.time_zone: unknown IANA time zone") from None
        if locale["language_tag"].split("-")[-1] != locale["country_code"]:
            raise InputError("site.locale: locale country suffix must match country_code")
        groups = [data["study"].get("phases", []), data["study"].get("arms", [])]
    else:
        groups = [data.get("attributes", [])]
        if stamp(data["enrolment"]["enrolled_at"]) > stamp(data["recorded_at"]):
            raise InputError("enrolment.enrolled_at: must not be later than recorded_at for an initial enrolment")
        consent = data.get("consent", {})
        if "valid_until" in consent and stamp(consent["valid_until"]) <= stamp(consent["valid_from"]):
            raise InputError("consent.valid_until: must be later than valid_from")
    for group in groups:
        ids = [item["id"] for item in group]
        if len(ids) != len(set(ids)):
            raise InputError("Repeated record identifier in phases, arms or attributes")


def schema_package(folder):
    """Load local catalogue targets and check that ontology imports resolve offline."""
    folder = Path(folder).resolve()
    catalogue = ET.parse(folder / "catalog-v001.xml").getroot()
    paths = {e.attrib["name"]: (folder / e.attrib["uri"]).resolve() for e in catalogue if "name" in e.attrib}
    graph = Graph()
    for path in sorted(set(paths.values())):
        graph += Graph().parse(path, format="turtle")
    for iri in graph.objects(None, OWL.imports):
        if str(iri) not in paths:
            raise InputError(f"Unresolved ontology import: {iri}")
    return graph, paths


class Builder:
    def __init__(self, base, graph_iri, data):
        self.base, self.graph_iri = base, URIRef(graph_iri)
        self.g = Graph()
        for prefix, namespace in (("icare", IC), ("inst", Namespace(base)), ("owl", OWL), ("xsd", XSD), ("dcterms", DCTERMS)):
            self.g.bind(prefix, namespace)
        self.g.add((self.graph_iri, RDF.type, OWL.Ontology))
        self.g.add((self.graph_iri, OWL.imports, ONTOLOGY))
        self.g.add((self.graph_iri, DCTERMS.source, URIRef(base + "input-records/sha256-" + digest(canonical(data)))))
        self.g.add((self.graph_iri, DCTERMS.description, Literal(data["source"])))
        self.g.add((self.graph_iri, DCTERMS.issued, Literal(data["recorded_at"], datatype=XSD.dateTime)))
        self.g.add((self.graph_iri, OWL.versionInfo, Literal(f"KG Instantiation profile {GENERATOR_VERSION}")))

    def node(self, path, cls, label=None):
        iri = URIRef(self.base + path)
        self.g.add((iri, RDF.type, OWL.NamedIndividual))
        self.g.add((iri, RDF.type, IC[cls]))
        if label:
            self.g.add((iri, RDFS.label, Literal(label)))
        return iri

    def rel(self, subject, prop, object_):
        self.g.add((subject, IC[prop], object_))

    def val(self, subject, prop, value, datatype=XSD.string):
        self.g.add((subject, IC[prop], Literal(value, datatype=datatype)))

    def time(self, path, value):
        node = self.node(path, "Timepoint")
        self.val(node, "timepointDateTime", value, XSD.dateTime)
        return node


def build_pilot(data, base):
    """Create shared study/site entities with stable identifiers for later enrolments."""
    site_id, study_id = data["site"]["id"], data["study"]["id"]
    b = Builder(base, base + "graphs/pilots/" + site_id, data)
    study = b.node("studies/" + study_id, "PilotStudy", data["study"]["name"])
    site = b.node("sites/" + site_id, "PilotSite", data["site"]["name"])
    b.g.add((site, DCTERMS.identifier, Literal(site_id)))
    b.g.add((study, DCTERMS.identifier, Literal(study_id)))
    b.rel(study, "pilotStudyHasPilotSite", site)
    locale = b.node("sites/" + site_id + "/locale", "Locale")
    b.rel(site, "pilotSiteHasLocale", locale)
    for key, prop in (("language_tag", "localeTag"), ("country_code", "localeCountryCode"), ("time_zone", "localeTimeZoneIdentifier")):
        b.val(locale, prop, data["site"]["locale"][key], XSD.language if key == "language_tag" else XSD.string)
    for key, cls, prop in (("phases", "PilotPhase", "pilotStudyHasPhase"), ("arms", "StudyArm", "pilotStudyHasArm")):
        for item in data["study"].get(key, []):
            child = b.node(f"studies/{study_id}/{key}/{item['id']}", cls, item["name"])
            b.rel(study, prop, child)
    return b


def build_participant(data, base, pilot):
    """Create a participant seed linked to the existing pilot, using supplied data."""
    pid, sid, study_id = data["participant_id"], data["site_id"], data["study_id"]
    site, study = URIRef(base + "sites/" + sid), URIRef(base + "studies/" + study_id)
    if (study, IC.pilotStudyHasPilotSite, site) not in pilot:
        raise InputError("study_id/site_id: pair does not match the registered pilot setup")
    b = Builder(base, base + "graphs/participants/" + pid, data)
    b.g.add((b.graph_iri, OWL.imports, URIRef(base + "graphs/pilots/" + sid)))
    root = "people/" + pid
    person = b.node(root, "Person", pid)
    b.val(person, "personIdentifier", pid)
    recorded = b.time(root + "/seed-recorded-at", data["recorded_at"])
    source = b.node(root + "/seed-source", "DataSource")
    b.val(source, "dataSourceIdentifier", "sha256-" + digest(canonical(data)))
    b.val(source, "dataSourceDescription", data["source"])
    logical = b.node(root + "/knowledge-graph", "ParticipantKnowledgeGraph")
    b.rel(logical, "participantKnowledgeGraphAboutPerson", person)
    b.g.add((logical, DCTERMS.source, source))
    for role in ["StudyParticipantRole"] + ([{"cancer_survivor": "CancerSurvivorRole", "aya_cancer_survivor": "AYACancerSurvivorRole"}[data["survivor_role"]]] if "survivor_role" in data else []):
        b.rel(person, "personHasRole", b.node(root + "/roles/" + role, role))
    if "age_years" in data:
        b.val(person, "ageInYears", Decimal(str(data["age_years"])), XSD.decimal)
        b.g.add((person, RDFS.comment, Literal("Age is a snapshot at the seed's recorded_at time.")))
    enrolment_path = root + "/enrolments/" + data["enrolment"]["id"]
    enrolment = b.node(enrolment_path, "ParticipantEnrolment")
    for prop, object_ in (("participantEnrolmentForPerson", person), ("participantEnrolmentAtSite", site), ("participantEnrolmentInStudy", study), ("participantEnrolmentHasStatus", IC[STATUS[data["enrolment"]["status"]]])):
        b.rel(enrolment, prop, object_)
    period = b.node(enrolment_path + "/period", "TimeInterval")
    b.rel(enrolment, "participantEnrolmentValidDuring", period)
    b.rel(period, "intervalStartsAt", b.time(enrolment_path + "/start", data["enrolment"]["enrolled_at"]))
    for field, key, prop, membership in (("phase_id", "phases", "participantEnrolmentInPhase", "pilotStudyHasPhase"), ("arm_id", "arms", "participantEnrolmentAssignedToArm", "pilotStudyHasArm")):
        if field in data["enrolment"]:
            object_ = URIRef(base + f"studies/{study_id}/{key}/" + data["enrolment"][field])
            if (study, IC[membership], object_) not in pilot:
                raise InputError(f"enrolment.{field}: not declared in the site's study setup")
            b.rel(enrolment, prop, object_)
    for key, value in data.get("preferences", {}).items():
        cls, prop, choices = PREFERENCES[key]
        preference = b.node(root + "/preferences/" + key, cls)
        b.rel(person, "personHasPreference", preference)
        b.rel(preference, "preferenceRecordedAt", recorded)
        b.g.add((preference, DCTERMS.source, source))
        if choices is None:
            b.val(preference, prop, value, XSD.language)
        else:
            b.rel(preference, prop, IC[choices[value]])
    for item in data.get("attributes", []):
        attribute = b.node(root + "/attributes/" + item["id"], "PersonAttribute")
        b.rel(person, "personHasAttribute", attribute)
        b.val(attribute, "personAttributeName", item["name"])
        b.val(attribute, "personAttributeValue", item["value"])
        b.rel(attribute, "personAttributeRecordedAt", recorded)
        b.rel(attribute, "personAttributeHasSource", source)
    if "consent" in data:
        item = data["consent"]
        path = root + "/consents/" + item["id"]
        record = b.node(path, "ConsentRecord")
        if item["status"] != "pending":
            b.rel(record, "consentRecordGrantedBy", person)
        b.rel(record, "consentRecordAppliesToKnowledgeGraph", logical)
        b.rel(record, "consentRecordHasStatus", IC[CONSENT[item["status"]]])
        b.g.add((record, DCTERMS.source, source))
        # A status record is not asserted to have been independently verified.
        b.rel(record, "hasVerificationStatus", IC.Unverified)
        interval = b.node(path + "/period", "TimeInterval")
        b.rel(record, "consentRecordValidDuring", interval)
        b.rel(interval, "intervalStartsAt", b.time(path + "/start", item["valid_from"]))
        if "valid_until" in item:
            b.rel(interval, "intervalEndsAt", b.time(path + "/end", item["valid_until"]))
    return b


def validate_graphs(graphs, schema):
    """Check declared terms and explicit types before applying the SHACL profile."""
    data = Graph()
    for graph in graphs:
        data += graph
    combined = data + schema
    errors = []
    classes = set(schema.subjects(RDF.type, OWL.Class))
    objects = set(schema.subjects(RDF.type, OWL.ObjectProperty))
    literals = set(schema.subjects(RDF.type, OWL.DatatypeProperty))
    annotations = set(schema.subjects(RDF.type, OWL.AnnotationProperty))
    def compatible(node, cls):
        return cls == OWL.Thing or any(t == cls or cls in schema.transitive_objects(t, RDFS.subClassOf) for t in combined.objects(node, RDF.type))
    for subject, prop, value in data:
        if prop == RDF.type and str(value).startswith(str(IC)) and value not in classes:
            errors.append(f"Undeclared class: {value}")
        if str(prop).startswith(str(IC)) and prop not in objects | literals | annotations:
            errors.append(f"Undeclared predicate: {prop}")
        if isinstance(value, URIRef) and str(value).startswith(str(IC)) and not any(schema.triples((value, None, None))):
            errors.append(f"Undeclared ontology value: {value}")
        if prop in objects | literals:
            for domain in schema.objects(prop, RDFS.domain):
                if not compatible(subject, domain):
                    errors.append(f"Explicit domain mismatch: {subject}, {prop}")
            if prop in objects:
                if not isinstance(value, URIRef):
                    errors.append(f"Object property requires an IRI: {prop}")
                for range_ in schema.objects(prop, RDFS.range):
                    if not compatible(value, range_):
                        errors.append(f"Explicit range mismatch: {subject}, {prop}, {value}")
            else:
                if not isinstance(value, Literal) or value.value is None:
                    errors.append(f"Invalid literal: {subject}, {prop}")
                elif any(value.datatype != range_ for range_ in schema.objects(prop, RDFS.range)):
                    errors.append(f"Wrong datatype: {prop}")
    # Shared study/phase/arm identifiers must not acquire competing names.
    for cls in (IC.PilotStudy, IC.PilotPhase, IC.StudyArm):
        for node in data.subjects(RDF.type, cls):
            if len(set(data.objects(node, RDFS.label))) > 1:
                errors.append(f"Conflicting labels for shared study entity: {node}")
    if errors:
        raise InputError("Graph validation failed:\n" + "\n".join(sorted(set(errors))))
    shapes = Graph().parse(ROOT / "shapes/enrolment.shacl.ttl", format="turtle")
    # Supply an explicit union: pySHACL's ont_graph inoculation recursively
    # clones interconnected named resources in this modular ontology.
    # No inferred instance types or OWL rules are materialised here.
    conforms, report, text = validate_shapes(combined, shacl_graph=shapes, inference="none", do_owl_imports=False)
    if not conforms:
        raise InputError("SHACL validation failed:\n" + text)
    return data, report


def atomic_write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as file:
        temporary = Path(file.name)
        try:
            file.write(content)
            file.flush()
            os.fsync(file.fileno())
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    os.replace(temporary, path)


def prepare_template(kind, data):
    """Omit unknown optional values from a fillable JSON record.

    Required placeholders and unknown field names are retained so normal schema
    validation reports them. No supplied value is coerced or mapped by guessing.
    """
    if kind not in ("pilot", "participant"):
        raise InputError("kind must be pilot or participant")
    root = input_schema(kind)
    missing = object()

    def clean(value, spec):
        if "$ref" in spec:
            target = root
            for part in spec["$ref"].removeprefix("#/").split("/"):
                target = target[part]
            spec = target
        if value is None or isinstance(value, str) and (not value.strip() or re.fullmatch(r"<[^<>]+>", value.strip())):
            return missing
        if isinstance(value, dict) and spec.get("type") == "object":
            result = {}
            for key, item in value.items():
                if key not in spec.get("properties", {}):
                    result[key] = deepcopy(item)
                    continue
                prepared = clean(item, spec["properties"][key])
                if prepared is not missing:
                    result[key] = prepared
                elif key in spec.get("required", []):
                    result[key] = deepcopy(item)
            return result if result else missing
        if isinstance(value, list) and spec.get("type") == "array":
            # Empty optional collections mean no assertions in this snapshot.
            if not value:
                return missing
            result = [clean(item, spec.get("items", {})) for item in value]
            return [deepcopy(original) if prepared is missing else prepared for original, prepared in zip(value, result)]
        return deepcopy(value)

    prepared = clean(data, root)
    return deepcopy(data) if prepared is missing else prepared


def instantiate(kind, data, output=ROOT / "generated", schema_dir=DEFAULT_SCHEMA, base=DEFAULT_BASE):
    """Create or refresh a graph from its current JSON snapshot.

    A new snapshot replaces this managed seed, not separately maintained clinical
    graphs. generate() validates the complete graph set before any publication.
    """
    return generate(kind, prepare_template(kind, data), output, schema_dir, base, replace_seed=True)


def generate(kind, data, output=ROOT / "generated", schema_dir=DEFAULT_SCHEMA, base=DEFAULT_BASE, replace_seed=False):
    """Generate one managed seed. Validates the whole managed set before publishing.

    Returns a JSON-serialisable report. This local prototype has one writer;
    callers must serialise writes if later exposed as a service.
    """
    if kind not in ("pilot", "participant"):
        raise InputError("kind must be pilot or participant")
    validate_input(kind, data)
    parsed = urlsplit(base)
    if parsed.scheme not in ("https", "http") or not parsed.netloc or parsed.query or parsed.fragment or re.search(r"\s|[<>]", base) or not base.endswith("/"):
        raise InputError("base must be an absolute HTTP(S) namespace ending in /, without query, fragment or whitespace")
    output, schema_dir = Path(output).resolve(), Path(schema_dir).resolve()
    if output == schema_dir or schema_dir in output.parents or output in schema_dir.parents:
        raise InputError("Output must be separate from the ontology package")
    registry_path = output / "validation/registry.json"
    if not registry_path.exists() and output.exists() and any(output.iterdir()):
        raise InputError("Output folder is nonempty and has no generator registry; choose a new folder")
    registry = read_json(registry_path) if registry_path.exists() else {"generator_version": GENERATOR_VERSION, "base_iri": base, "entries": {}}
    if registry["base_iri"] != base:
        raise InputError("base differs from this output deployment; choose a different output folder")
    registry["generator_version"] = GENERATOR_VERSION
    schema, ontology_paths = schema_package(schema_dir)
    schema_hashes = {iri: digest(path.read_bytes()) for iri, path in sorted(ontology_paths.items())}
    ontology_hash = digest(canonical(schema_hashes))
    mapping_files = [Path(__file__), Path(section_records.__file__), *sorted((ROOT / "schemas").glob("*.json")), ROOT / "shapes/enrolment.shacl.ttl"]
    mapping_hash = digest(canonical({path.relative_to(ROOT).as_posix(): digest(path.read_bytes()) for path in mapping_files}))
    graphs = {}
    # Detect manual changes to managed files before constructing replacement output.
    for key, entry in registry["entries"].items():
        path = (output / entry["file"]).resolve()
        if output not in path.parents or not path.is_file() or digest(path.read_bytes()) != entry["sha256"]:
            raise InputError(f"Managed seed missing or edited outside the generator: {key}")
        graphs[key] = Graph().parse(path, format="turtle")
        if "jsonld_file" in entry:
            jsonld_path = (output / entry["jsonld_file"]).resolve()
            if output not in jsonld_path.parents or not jsonld_path.is_file() or digest(jsonld_path.read_bytes()) != entry["jsonld_sha256"]:
                raise InputError(f"Managed JSON-LD missing or edited outside the generator: {key}")
    identifier = data["site"]["id"] if kind == "pilot" else data["participant_id"]
    key = kind + ":" + identifier
    if kind == "pilot":
        builder = build_pilot(data, base)
    else:
        pilot_key = "pilot:" + data["site_id"]
        if pilot_key not in graphs:
            raise InputError("site_id: pilot must be generated in this output folder before participant enrolment")
        builder = build_participant(data, base, graphs[pilot_key])
    try:
        section_records.add_sections(builder, data, schema, kind, FORMATS)
    except section_records.SectionError as error:
        raise InputError(str(error)) from error
    previous = registry["entries"].get(key)
    # Canonical input hashes make repeated enrolment idempotent despite JSON key order.
    input_hash = digest(canonical(data))
    unchanged = previous is not None and previous["input_sha256"] == input_hash and previous.get("ontology_sha256") == ontology_hash and previous.get("mapping_sha256") == mapping_hash
    if previous and not unchanged and not replace_seed:
        raise InputError("This seed already exists with different input. Use --replace-seed for an intentional seed correction; the previous seed will be archived.")
    if previous and kind == "participant":
        old_person = next(graphs[key].subjects(IC.personIdentifier, Literal(identifier, datatype=XSD.string)))
        old_enrolment = next(graphs[key].subjects(IC.participantEnrolmentForPerson, old_person))
        new_enrolment = next(builder.g.subjects(IC.participantEnrolmentForPerson, old_person))
        if old_enrolment != new_enrolment or previous["site_id"] != data["site_id"] or previous["study_id"] != data["study_id"]:
            raise InputError("Seed correction cannot replace enrolment identity, study or site. Additional enrolments require an explicit history/update workflow.")
    # Normalise the RDF lexical forms through the canonical storage format once.
    # In particular, Turtle writes integral decimals as 27.0 rather than 27;
    # JSON-LD must preserve the same terms on the first run and on every refresh.
    builder.g = Graph().parse(data=builder.g.serialize(format="turtle"), format="turtle")
    graphs[key] = builder.g
    union, shape_report = validate_graphs(graphs.values(), schema)
    relative = f"{'pilots' if kind == 'pilot' else 'participants'}/{identifier}.ttl"
    content = builder.g.serialize(format="turtle").encode()
    if not previous and (output / relative).exists():
        raise InputError("Refusing to replace a file not owned by the generator")
    if previous and not unchanged:
        archive = output / "history" / kind / identifier / previous["sha256"]
        atomic_write(archive.with_suffix(".ttl"), (output / relative).read_bytes())
        atomic_write(archive.with_suffix(".json"), canonical(previous))
    if not unchanged:
        atomic_write(output / relative, content)
    else:
        content = (output / relative).read_bytes()
    entry = {"kind": kind, "id": identifier, "iri": str(builder.graph_iri), "file": relative, "sha256": digest(content), "input_sha256": input_hash,
             "ontology_sha256": ontology_hash, "mapping_sha256": mapping_hash}
    if kind == "participant":
        entry.update(site_id=data["site_id"], study_id=data["study_id"])
    registry["entries"][key] = entry
    # JSON-LD is a second serialisation of the same assertions, not a parallel
    # source of clinical facts. Export every managed graph, including older seeds.
    for key_, graph in graphs.items():
        entry_ = registry["entries"][key_]
        jsonld_file = str(Path(entry_["file"]).with_suffix(".jsonld"))
        jsonld_content = section_records.jsonld_bytes(graph, schema)
        atomic_write(output / jsonld_file, jsonld_content)
        entry_["jsonld_file"] = jsonld_file
        entry_["jsonld_sha256"] = digest(jsonld_content)
    root_iri = URIRef(base + "graphs/dataset")
    dataset_entry = Graph()
    dataset_entry.add((root_iri, RDF.type, OWL.Ontology))
    dataset_entry.add((root_iri, OWL.imports, ONTOLOGY))
    dataset_entry.add((root_iri, RDFS.label, Literal("iCARE generated initialisation graphs")))
    for entry_ in registry["entries"].values():
        dataset_entry.add((root_iri, OWL.imports, URIRef(entry_["iri"])))
    paths = dict(ontology_paths)
    paths.update({entry_["iri"]: output / entry_["file"] for entry_ in registry["entries"].values()})
    paths[str(root_iri)] = output / "dataset.ttl"
    for graph in list(graphs.values()) + [dataset_entry]:
        for imported in graph.objects(None, OWL.imports):
            if str(imported) not in paths:
                raise InputError(f"Unresolved generated import: {imported}")
    atomic_write(output / "dataset.ttl", dataset_entry.serialize(format="turtle").encode())
    # Turtle provides an import entry; TriG preserves each instance graph separately.
    dataset = Dataset()
    for key_, graph in graphs.items():
        named = dataset.graph(URIRef(registry["entries"][key_]["iri"]))
        for triple in graph:
            named.add(triple)
    atomic_write(output / "dataset.trig", section_records.trig_bytes(dataset))
    atomic_write(output / "dataset.jsonld", section_records.jsonld_bytes(dataset, schema))
    # Adjacent catalogues also support opening an individual seed directly.
    for directory in (output, output / "pilots", output / "participants"):
        catalogue = ET.Element("catalog", {"xmlns": "urn:oasis:names:tc:entity:xmlns:xml:catalog", "prefer": "public"})
        for iri, path in sorted(paths.items()):
            ET.SubElement(catalogue, "uri", {"name": iri, "uri": Path(os.path.relpath(path, directory)).as_posix()})
        ET.indent(catalogue)
        atomic_write(directory / "catalog-v001.xml", ET.tostring(catalogue, encoding="utf-8", xml_declaration=True) + b"\n")
    atomic_write(output / "validation/import-map.tsv", ("iri\tfile\n" + "".join(f"{iri}\t{Path(os.path.relpath(path, output)).as_posix()}\n" for iri, path in sorted(paths.items()))).encode())
    atomic_write(output / "validation/shacl-report.ttl", shape_report.serialize(format="turtle").encode())
    report = {
        "status": "UNCHANGED" if unchanged else "REPLACED_SEED" if previous else "CREATED",
        "input_kind": kind, "input_id": identifier, "file": relative, "generator_version": GENERATOR_VERSION,
        "input_sha256": input_hash, "base_iri": base,
        "ontology_sha256": ontology_hash, "mapping_sha256": mapping_hash,
        "pilot_graphs": sum(e["kind"] == "pilot" for e in registry["entries"].values()),
        "participant_graphs": sum(e["kind"] == "participant" for e in registry["entries"].values()),
        "instance_triples_in_union": len(union), "input_schema_valid": True,
        "term_and_explicit_type_errors": [], "shacl_conforms": True,
        "ontology_version": str(next(schema.objects(ONTOLOGY, OWL.versionInfo))),
        "ontology_files_sha256": schema_hashes,
        "owl_reasoner": "Not run by generator; use the separate OWLAPI/HermiT validator."
    }
    atomic_write(output / "validation/generation-report.json", canonical(report))
    # Registry is the last file committed. Individual file writes are atomic;
    # interruption midway is detected by hashes, not a multi-file transaction.
    atomic_write(registry_path, canonical(registry))
    return report


def main(refresh=False):
    parser = argparse.ArgumentParser(description="KG Instantiator: validate pilot/participant JSON and create or refresh ontology-based knowledge graphs." if refresh else __doc__)
    parser.add_argument("kind", choices=("pilot", "participant"))
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "generated")
    parser.add_argument("--schema-dir", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--base-iri", default=DEFAULT_BASE)
    parser.add_argument("--replace-seed", action="store_true", help="Correct this managed seed and archive its previous version; never merge clinical events")
    parser.add_argument("--refresh", action="store_true", default=refresh, help="Read a fillable current-record template, omit unknown optional values, and create or refresh its graph with history")
    args = parser.parse_args()
    try:
        data = read_json(args.input)
        report = instantiate(args.kind, data, args.output, args.schema_dir, args.base_iri) if args.refresh else generate(args.kind, data, args.output, args.schema_dir, args.base_iri, args.replace_seed)
    except (InputError, OSError, json.JSONDecodeError, ET.ParseError) as error:
        parser.exit(2, f"ERROR: {error}\n")
    print(json.dumps({key: report[key] for key in ("status", "file", "pilot_graphs", "participant_graphs", "shacl_conforms")}, indent=2))


if __name__ == "__main__":
    main()
