#!/usr/bin/env python3
"""Publish reviewed resource metadata and select educational signposts offline.

build_release() and select_resources() are the reusable backend entry points.
Source workbooks and external educational content are never modified/downloaded.
"""
import argparse
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET
from zipfile import ZipFile

from jsonschema import Draft202012Validator
from pyshacl import validate as shacl_validate
from rdflib import Dataset, Graph, Literal, Namespace, OWL, RDF, RDFS, SKOS, URIRef, XSD
from rdflib.namespace import DCTERMS

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
sys.path.insert(0, str(REPO / "serialisation/scripts"))
from serialise_ontology import read_xlsx

IC = Namespace("http://maya-project.eu/icareonto/")
META = Namespace("http://maya-project.eu/icareonto/education/metadata#")
ONTOLOGY = URIRef("http://maya-project.eu/icareonto")
DEFAULT_BASE = "http://maya-project.eu/icareonto/education/"
DEFAULT_WORKBOOK = REPO / "sources/MAYA_consolidated_educational_resources_v20261101.xlsx"
STAGES = ["Before treatment", "During treatment", "After treatment / survivorship"]
# Each entry connects an application field to its worksheet heading, controlled
# vocabulary class and RDF relationship. Keep all three mappings together.
FIELDS = {
    "audiences": ("MAYA Target audience", "ResourceAudienceType", "knowledgeResourceHasAudience"),
    "topics": ("Ontology topic(s)", "ResourceTopic", "knowledgeResourceHasTopic"),
    "needs": ("Health-literacy needs addressed", "HealthLiteracyNeedType", "healthLiteracyResourceAddressesNeed"),
    "formats": ("Resource format", "ResourceFormat", "knowledgeResourceHasFormat"),
    "complexities": ("Literacy complexity", "ContentComplexityLevel", "knowledgeResourceHasComplexityLevel"),
    "accessibility": ("Accessibility features", "AccessibilityFeature", "knowledgeResourceHasAccessibilityFeature"),
    "purposes": ("Resource purpose(s)", "ResourcePurpose", "knowledgeResourceHasPurpose"),
}
REQUIRED = ["Resource ID", "Resource title", "Curation status", "Completion status", "Resource URL", "Language(s)",
            "Cancer journey stage(s)", "Provider / author", "Description excerpt", "Access conditions", "Permitted MAYA use",
            "Reviewer", "Review date"] + [v[0] for v in FIELDS.values() if v[0] != "Accessibility features"]
ALIASES = {"targetaudience": "MAYA Target audience", "resourcepurpose": "Resource purpose(s)"}
LANGUAGES = {"english": "en", "spanish": "es", "german": "de", "french": "fr", "italian": "it", "portuguese": "pt",
             "romanian": "ro", "polish": "pl", "finnish": "fi", "greek": "el", "catalan": "ca"}
APP_PROPERTIES = ["journeyStage", "resourceRole", "accessConditions", "reviewedBy", "reviewedOn", "resourceDateText",
                  "applicabilityNotes", "learningObjective", "learningStep", "reflectionPrompt",
                  "templateStatus", "identificationMethod", "isSynthetic", "curationStatus", "completionStatus"]


class InputError(ValueError):
    pass


# Stable JSON ordering makes hashes and comparisons independent of dictionary order.
def canonical(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def digest(data):
    return hashlib.sha256(data).hexdigest()


# Reject duplicate keys instead of silently accepting the last occurrence.
def read_json(path):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise InputError(f"Duplicate JSON key: {key}")
            out[key] = value
        return out
    def bad_constant(value):
        raise InputError(f"Non-finite JSON number: {value}")
    return json.loads(Path(path).read_text(), object_pairs_hook=pairs, parse_constant=bad_constant)


def norm(value):
    return re.sub(r"[^a-z0-9]", "", str(value).casefold())


# A comma can belong to a label, such as "Digital health, privacy and trust".
# Only semicolons separate multiple annotations in a worksheet cell.
def split_values(value):
    return list(dict.fromkeys(v.strip() for v in str(value or "").split(";") if v.strip()))


def http_url(value):
    p = urlsplit(value)
    return p.scheme in ("https", "http") and bool(p.hostname) and not p.username and not p.password and not re.search(r"\s|[<>]", value)


# Write a complete temporary file, then replace the destination in one operation.
def atomic_write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as f:
        temp = Path(f.name)
        try:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        except BaseException:
            temp.unlink(missing_ok=True)
            raise
    os.replace(temp, path)


# Load the ontology through its local import catalogue, with no network requests.
# The combined file hash later detects a resource release using another ontology.
def load_schema(folder):
    folder = Path(folder).resolve()
    paths = {e.attrib["name"]: (folder / e.attrib["uri"]).resolve()
             for e in ET.parse(folder / "catalog-v001.xml").getroot()}
    schema = Graph()
    hashes = {}
    for path in sorted(set(paths.values())):
        if not path.is_relative_to(folder):
            raise InputError("Ontology catalogue must resolve inside its package")
        schema += Graph().parse(path, format="turtle")
        hashes[path.relative_to(folder).as_posix()] = digest(path.read_bytes())
    for imported in schema.objects(None, OWL.imports):
        if str(imported) not in paths:
            raise InputError(f"Unresolved ontology import: {imported}")
    return schema, paths, digest(canonical(hashes))


class Vocabulary:
    def __init__(self, schema):
        self.schema = schema
        self.index = {}
        # Index labels and identifiers within their own vocabulary category.
        # For example, a resource topic must not be accepted as a literacy need.
        for _, cls, _ in FIELDS.values():
            lookup = defaultdict(set)
            for node in schema.subjects(RDF.type, IC[cls]):
                for value in [str(node), str(node).removeprefix(str(IC)), *schema.objects(node, SKOS.prefLabel), *schema.objects(node, RDFS.label)]:
                    lookup[norm(value)].add(str(node))
            self.index[cls] = lookup

    def resolve(self, value, cls):
        candidates = self.index[cls].get(norm(value), set())
        if len(candidates) != 1:
            raise InputError(f"Unknown or ambiguous {cls} value: {value!r}")
        return next(iter(candidates))


# Find the header by its text rather than assuming fixed column letters or rows.
def worksheet_records(path, sheet):
    workbook = read_xlsx(path)
    if sheet not in workbook:
        raise InputError(f"Worksheet not found: {sheet}")
    header_rows = [r for r in workbook[sheet] if any(norm(v) == "resourceid" for k, v in r.items() if k != "_row")]
    if len(header_rows) != 1:
        raise InputError("Expected one Resource ID header row")
    header = header_rows[0]
    known = {norm(h): h for h in REQUIRED + ["Accessibility features", "Resource role", "Publication / last updated", "Applicability review notes", "Source record ID", "Source reference"]}
    cols = {}
    for col, text in header.items():
        if col == "_row":
            continue
        key = ALIASES.get(norm(text), known.get(norm(text), str(text).strip()))
        if key in cols.values():
            raise InputError(f"Duplicate column header: {key}")
        cols[col] = key
    missing = sorted(set(REQUIRED) - set(cols.values()))
    if missing:
        raise InputError("Missing columns: " + ", ".join(missing))
    records = []
    for row in workbook[sheet]:
        if row["_row"] <= header["_row"]:
            continue
        rec = {key: str(row.get(col, "")).strip() for col, key in cols.items()}
        if any(rec.get(k) for k in ["Resource ID", "Resource title", "Curation status", "Completion status"]):
            records.append({"_row": row["_row"], **rec})
    # Excel workbooks can use either the 1900 or 1904 date system.
    with ZipFile(path) as z:
        prop = ET.fromstring(z.read("xl/workbook.xml")).find("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}workbookPr")
        epoch_1904 = prop is not None and prop.get("date1904") in ("1", "true")
    return records, epoch_1904


# Convert an ISO date or Excel serial without inventing a publication date.
# Excel's fictitious 29 February 1900 (serial 60) is deliberately rejected.
def review_date(value, epoch_1904=False):
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        pass
    try:
        serial = Decimal(value)
        if not serial.is_finite() or serial != serial.to_integral_value() or serial < 1 or (not epoch_1904 and serial == 60):
            raise ValueError()
        base = date(1904, 1, 1) if epoch_1904 else date(1899, 12, 30)
        if not epoch_1904 and serial < 60:
            base = date(1899, 12, 31)
        return (base + timedelta(days=int(serial))).isoformat()
    except (ValueError, InvalidOperation, OverflowError):
        raise InputError(f"Invalid review date: {value!r}") from None


def language_tag(value):
    value = LANGUAGES.get(value.casefold(), value)
    if not re.fullmatch(r"[a-zA-Z]{2,3}(?:-[a-zA-Z0-9]{2,8})*", value):
        raise InputError(f"Use a verified language name or BCP 47 tag, not {value!r}")
    return value.lower()


# Turn eligible worksheet rows into the shared JSON/RDF representation.
# Keep the original fields alongside the interpreted metadata for traceability.
def prepare_records(raw, vocabulary, base, epoch_1904=False):
    records, excluded, audit = [], [], []
    seen = set()
    for row in raw:
        rid = row.get("Resource ID", "")
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9._-]{0,127}", rid):
            raise InputError(f"Row {row['_row']}: invalid/missing Resource ID")
        if rid in seen:
            raise InputError(f"Duplicate Resource ID: {rid}")
        seen.add(rid)
        # Both decisions are required. Held or unfinished rows never reach the catalogue.
        if row.get("Curation status", "").casefold() != "approved" or row.get("Completion status", "").casefold() != "complete":
            excluded.append({"id": rid, "curation_status": row.get("Curation status"), "completion_status": row.get("Completion status")})
            continue
        for key in REQUIRED:
            if not row.get(key):
                raise InputError(f"{rid}: approved/complete entry has no {key}")
        if not http_url(row["Resource URL"]):
            raise InputError(f"{rid}: invalid HTTP(S) resource URL")
        stages = []
        for stage in split_values(row["Cancer journey stage(s)"]):
            matching = [s for s in STAGES if norm(s) == norm(stage)]
            if matching:
                stages.extend(matching)
            else:
                raise InputError(f"{rid}: unknown journey stage: {stage}")
        if not stages:
            raise InputError(f"{rid}: at least one of the three journey stages is required")
        # Identity depends on the Resource ID, so edits to a title, URL or row
        # position do not create a different resource in the knowledge graph.
        r = {"id": rid, "iri": base + "resources/" + rid, "title": row["Resource title"], "url": row["Resource URL"],
             "description": row["Description excerpt"], "provider": row["Provider / author"], "languages": sorted({language_tag(v) for v in split_values(row["Language(s)"])}),
             "journey_stages": sorted(set(stages)), "resource_role": row.get("Resource role", ""),
             "access_conditions": row["Access conditions"], "permitted_use": row["Permitted MAYA use"], "delivery_mode": "signpost",
             "reviewer": row["Reviewer"], "review_date": review_date(row["Review date"], epoch_1904),
             "resource_date_text": row.get("Publication / last updated", ""), "applicability_notes": row.get("Applicability review notes", ""),
             "curation_status": "Approved", "completion_status": "Complete"}
        if r["access_conditions"] not in ("Public", "Restricted"):
            raise InputError(f"{rid}: access conditions must be reviewed as Public or Restricted")
        if r["permitted_use"] not in ("Link / Signpost Only", "Reuse / Adapt Permitted"):
            raise InputError(f"{rid}: permitted use is unresolved")
        for key, (field, cls, _) in FIELDS.items():
            values = []
            for value in split_values(row.get(field, "")):
                # Every supplied term must resolve within its ontology vocabulary.
                values.append(vocabulary.resolve(value, cls))
            r[key] = sorted(set(values))
        if len(r["complexities"]) != 1:
            raise InputError(f"{rid}: exactly one reviewed complexity is required")
        records.append(r)
        audit.append({"id": rid, "source_row": row["_row"], "original_fields": row})
    return sorted(records, key=lambda r: r["id"]), excluded, audit


def new_graph(iri, label, imports):
    g = Graph()
    for prefix, ns in [("icare", IC), ("edu", META), ("owl", OWL), ("dcterms", DCTERMS), ("xsd", XSD)]:
        g.bind(prefix, ns)
    g.add((URIRef(iri), RDF.type, OWL.Ontology))
    g.add((URIRef(iri), RDFS.label, Literal(label, lang="en")))
    for imported in imports:
        g.add((URIRef(iri), OWL.imports, URIRef(imported)))
    for prop in APP_PROPERTIES:
        g.add((META[prop], RDF.type, OWL.AnnotationProperty))
    return g


def instance(g, iri, cls, label):
    node = URIRef(iri)
    g.add((node, RDF.type, OWL.NamedIndividual))
    g.add((node, RDF.type, IC[cls]))
    g.add((node, RDFS.label, Literal(label)))
    return node


# Build the resource RDF: descriptive values are annotations, while controlled
# classifications link each resource to the existing ontology individuals.
def catalogue_graph(records, base):
    g = new_graph(base + "graphs/resources", "MAYA reviewed educational resource catalogue", [ONTOLOGY])
    for r in records:
        n = instance(g, r["iri"], "HealthLiteracyResource", r["title"])
        if r["resource_role"] in ("Direct Educational Resource", "Both"):
            g.add((n, RDF.type, IC.EducationalResource))
        for predicate, value in [(DCTERMS.identifier, r["id"]), (DCTERMS.title, r["title"]), (DCTERMS.description, r["description"]),
                                 (DCTERMS.publisher, r["provider"]), (DCTERMS.rights, r["permitted_use"]), (META.accessConditions, r["access_conditions"]),
                                 (META.resourceRole, r["resource_role"]), (META.reviewedBy, r["reviewer"]), (META.applicabilityNotes, r["applicability_notes"]),
                                 (META.resourceDateText, r["resource_date_text"]), (META.curationStatus, "Approved"),
                                 (META.completionStatus, "Complete")]:
            if value:
                g.add((n, predicate, Literal(value)))
        g.add((n, DCTERMS.source, URIRef(r["url"])))
        g.add((n, META.reviewedOn, Literal(r["review_date"], datatype=XSD.date)))
        for language in r["languages"]:
            g.add((n, DCTERMS.language, Literal(language, datatype=XSD.language)))
        for stage in r["journey_stages"]:
            g.add((n, META.journeyStage, Literal(stage)))
        for key, (_, _, prop) in FIELDS.items():
            for value in r[key]:
                g.add((n, IC[prop], URIRef(value)))
    return g


# Create shared draft interventions and goals. These are templates, so this
# function does not assert that a participant has received or completed an activity.
def activity_graph(templates, records, vocabulary, base):
    g = new_graph(base + "graphs/activities", "MAYA draft educational activity templates", [base + "graphs/resources"])
    available = {r["id"]: r for r in records}
    result = []
    seen = set()
    for t in templates:
        if t.get("status") != "Draft" or not re.fullmatch(r"[A-Za-z0-9_-]+", t["id"]):
            raise InputError("Learning templates need stable IDs and explicit Draft status")
        if t["id"] in seen:
            raise InputError(f"Duplicate activity template: {t['id']}")
        seen.add(t["id"])
        for key in ["title", "learning_objective", "needs", "topics", "audiences", "journey_stages", "steps", "reflection_prompts"]:
            if not t.get(key):
                raise InputError(f"Activity template {t['id']} has no {key}")
        needs = [vocabulary.resolve(n, "HealthLiteracyNeedType") for n in t["needs"]]
        topics = [vocabulary.resolve(n, "ResourceTopic") for n in t["topics"]]
        audiences = [vocabulary.resolve(n, "ResourceAudienceType") for n in t["audiences"]]
        if not set(t["journey_stages"]).issubset(STAGES):
            raise InputError(f"Activity template {t['id']} has an unknown journey stage")
        # Templates use annotation criteria so newly reviewed resources can join automatically.
        ids = [rid for rid, r in sorted(available.items()) if set(needs) & set(r["needs"]) and set(topics) & set(r["topics"])
               and set(audiences) & set(r["audiences"]) and set(t["journey_stages"]) & set(r["journey_stages"])]
        if not ids:
            continue
        entry = {**t, "needs": needs, "topics": topics, "candidate_resource_ids": ids, "iri": base + "activity-templates/" + t["id"]}
        result.append(entry)
        n = instance(g, entry["iri"], "HealthLiteracyIntervention", t["title"])
        g.add((n, RDF.type, IC.EducationActivity))
        goal = instance(g, entry["iri"] + "/goal", "Goal", t["learning_objective"])
        g.add((goal, IC.goalDescriptionText, Literal(t["learning_objective"], datatype=XSD.string)))
        g.add((n, IC.activityContributesToGoal, goal))
        g.add((n, META.templateStatus, Literal("Draft")))
        g.add((n, META.learningObjective, Literal(t["learning_objective"])))
        for key, prop in [("steps", META.learningStep), ("reflection_prompts", META.reflectionPrompt)]:
            for index, text in enumerate(t[key], 1):
                g.add((n, prop, Literal(f"{index}. {text}")))
        for need in needs:
            g.add((n, IC.healthLiteracyInterventionAddressesNeed, URIRef(need)))
        for rid in ids:
            g.add((n, IC.healthLiteracyInterventionUsesResource, URIRef(available[rid]["iri"])))
    return g, result


# Check ontology terms, domains, ranges and datatypes first. SHACL then checks
# the catalogue's required fields; OWL alone does not enforce required fields.
def validate_graph(data, schema):
    combined = schema + data
    classes = set(schema.subjects(RDF.type, OWL.Class))
    obj = set(schema.subjects(RDF.type, OWL.ObjectProperty))
    dat = set(schema.subjects(RDF.type, OWL.DatatypeProperty))
    ann = set(schema.subjects(RDF.type, OWL.AnnotationProperty))
    def compatible(node, wanted):
        todo = list(combined.objects(node, RDF.type)); seen = set()
        while todo:
            cls = todo.pop()
            if cls == wanted:
                return True
            if cls not in seen:
                seen.add(cls); todo.extend(schema.objects(cls, RDFS.subClassOf))
        return False
    for s, p, o in data:
        if p == RDF.type and str(o).startswith(str(IC)) and o not in classes:
            raise InputError(f"Unknown ontology class: {o}")
        if str(p).startswith(str(IC)) and not str(p).startswith(str(META)) and p not in obj | dat | ann:
            raise InputError(f"Unknown ontology property: {p}")
        if p in obj | dat:
            for domain in schema.objects(p, RDFS.domain):
                if not compatible(s, domain):
                    raise InputError(f"Incompatible property domain: {s} {p}")
            if p in obj:
                for range_ in schema.objects(p, RDFS.range):
                    if not isinstance(o, URIRef) or not compatible(o, range_):
                        raise InputError(f"Incompatible property range: {p} {o}")
            elif not isinstance(o, Literal) or o.value is None or any(o.datatype != r for r in schema.objects(p, RDFS.range)):
                raise InputError(f"Invalid typed value: {p} {o}")
    conforms, report, text = shacl_validate(combined, shacl_graph=Graph().parse(ROOT / "shapes/resources.shacl.ttl"), inference="none", do_owl_imports=False)
    if not conforms:
        raise InputError("Resource SHACL validation failed:\n" + text)
    return report


def write_catalogue(paths, directory):
    root = ET.Element("catalog", {"xmlns": "urn:oasis:names:tc:entity:xmlns:xml:catalog", "prefer": "public"})
    for iri, path in sorted(paths.items()):
        ET.SubElement(root, "uri", {"name": str(iri), "uri": Path(os.path.relpath(path, directory)).as_posix()})
    ET.indent(root)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True) + b"\n"


def build_release(workbook=DEFAULT_WORKBOOK, sheet="Release resources", output=ROOT / "generated", ontology_dir=REPO / "serialisation",
                  base=DEFAULT_BASE, activities=ROOT / "activities.json", allow_empty=False):
    # 1. Check the destination and read the saved inputs and previous release.
    workbook, output, ontology_dir = Path(workbook).resolve(), Path(output).resolve(), Path(ontology_dir).resolve()
    if not http_url(base) or not base.endswith("/") or urlsplit(base).query or urlsplit(base).fragment:
        raise InputError("base must be an HTTP(S) namespace ending in /, without query or fragment")
    if output == ontology_dir or ontology_dir in output.parents or output in ontology_dir.parents:
        raise InputError("Output must be separate from the ontology package")
    pointer = output / "current.json"
    if output.exists() and any(output.iterdir()) and not pointer.is_file():
        raise InputError("Output is nonempty without a managed current.json; choose a new directory")
    previous = load_release(output) if pointer.is_file() else None
    if previous and previous["base_iri"] != base:
        raise InputError("base differs from this deployment; choose a new output directory")
    input_hash = digest(workbook.read_bytes())
    schema, ontology_paths, schema_hash = load_schema(ontology_dir)
    vocabulary = Vocabulary(schema)
    raw, epoch = worksheet_records(workbook, sheet)
    template_data = read_json(activities)
    # 2. Filter and normalise the worksheet, then construct and validate the RDF.
    records, excluded, audit = prepare_records(raw, vocabulary, base, epoch)
    if not records and not allow_empty:
        raise InputError("No approved and complete resources; use --allow-empty for an intentional empty release")
    cg = catalogue_graph(records, base)
    ag, active_templates = activity_graph(template_data, records, vocabulary, base)
    shape_report = validate_graph(cg + ag, schema)
    payload = {"profile_version": "1.1", "base_iri": base, "ontology_sha256": schema_hash, "records": records, "activity_templates": active_templates}
    # 3. Derive a release identifier from the inputs and implementation. This also
    # records script changes, including comments, in the next release's provenance.
    profile_hash = digest(canonical({name: digest(path.read_bytes()) for name, path in {
        "generator": Path(__file__), "resource_shapes": ROOT / "shapes/resources.shacl.ttl",
        "selection_schema": ROOT / "schemas/selection.schema.json"}.items()}))
    fingerprint = digest(canonical({"catalogue": payload, "workbook_sha256": input_hash, "sheet": sheet,
                                    "templates": template_data, "profile_sha256": profile_hash}))
    release_id = fingerprint[:24]
    # Compare by Resource ID to report additions, updates and withdrawals.
    old = {r["id"]: r for r in previous["records"]} if previous else {}
    new = {r["id"]: r for r in records}
    report = {"release_id": release_id, "source_workbook": workbook.name, "source_sha256": input_hash, "source_sheet": sheet,
              "ontology_sha256": schema_hash, "profile_sha256": profile_hash, "included_count": len(records), "excluded": excluded,
              "added": sorted(set(new) - set(old)), "removed": sorted(set(old) - set(new)),
              "updated": sorted(rid for rid in set(old) & set(new) if canonical(old[rid]) != canonical(new[rid])),
              "validation": "PASS", "activity_template_status": "Draft", "full_text_downloaded": False}
    release = output / "releases" / release_id
    # dataset.ttl is an import entry point. The resource and activity assertions
    # remain in catalogue.ttl and activity-templates.ttl, rather than being copied here.
    entry = new_graph(base + "dataset", "MAYA educational resources and draft learning activities", [base + "graphs/resources", base + "graphs/activities"])
    paths = {**ontology_paths, base + "graphs/resources": release / "catalogue.ttl", base + "graphs/activities": release / "activity-templates.ttl", base + "dataset": release / "dataset.ttl"}
    # TriG packages both sets of assertions together while preserving graph names.
    # The ordinary JSON output is for application code; it is not JSON-LD.
    dataset = Dataset()
    for iri, g in [(base + "graphs/resources", cg), (base + "graphs/activities", ag)]:
        for triple in g:
            dataset.graph(URIRef(iri)).add(triple)
    files = {"catalogue.json": canonical(payload), "catalogue.ttl": cg.serialize(format="turtle").encode(),
             "activity-templates.ttl": ag.serialize(format="turtle").encode(), "dataset.ttl": entry.serialize(format="turtle").encode(),
             "dataset.trig": dataset.serialize(format="trig").encode(), "catalog-v001.xml": write_catalogue(paths, release),
             "validation/shacl-report.ttl": shape_report.serialize(format="turtle").encode(),
             "validation/import-map.tsv": ("iri\tfile\n" + "".join(f"{iri}\t{Path(os.path.relpath(path, release)).as_posix()}\n" for iri, path in sorted(paths.items()))).encode(),
             "validation/source-records.json": canonical(audit), "validation/build-report.json": canonical(report)}
    # 4. Stage a complete release before publication. If Excel saves new content
    # during processing, or writing fails, the current release is retained.
    if digest(workbook.read_bytes()) != input_hash:
        raise InputError("Source workbook changed during processing; save and retry")
    if not release.exists():
        output.parent.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix=".maya-education-pending-", dir=output.parent))
        try:
            for relative, content in files.items():
                atomic_write(staging / relative, content)
            manifest = {"release_id": release_id, "files": {name: digest(content) for name, content in files.items()}}
            atomic_write(staging / "manifest.json", canonical(manifest))
            verify_release_folder(staging)
            release.parent.mkdir(parents=True, exist_ok=True)
            os.rename(staging, release)
        finally:
            if staging.exists():
                shutil.rmtree(staging)
    else:
        manifest = read_json(release / "manifest.json")
        if read_json(release / "catalogue.json") != payload:
            raise InputError("Release identifier collision")
    verify_release_folder(release)
    # One atomic pointer publishes the fully written immutable release.
    pointer_data = {"release_id": release_id, "manifest_sha256": digest((release / "manifest.json").read_bytes())}
    if pointer.is_file() and read_json(pointer) == pointer_data:
        load_release(output)
        return {**report, "result": "UNCHANGED", "release_directory": str(release), "added": [], "removed": [], "updated": []}
    atomic_write(pointer, canonical(pointer_data))
    load_release(output)
    return {**report, "result": "PUBLISHED", "release_directory": str(release)}


# Validate saved bytes against the manifest, including before reactivating history.
def verify_release_folder(folder):
    manifest = read_json(folder / "manifest.json")
    for relative, expected in manifest["files"].items():
        path = (folder / relative).resolve()
        if not path.is_relative_to(folder) or not path.is_file() or digest(path.read_bytes()) != expected:
            raise InputError(f"Published release file missing or modified: {relative}")
    return manifest


# current.json identifies the active snapshot; older releases remain historical.
def load_release(output=ROOT / "generated"):
    output = Path(output).resolve()
    pointer = read_json(output / "current.json")
    rid = pointer["release_id"]
    if not re.fullmatch(r"[a-f0-9]{24}", rid):
        raise InputError("Invalid release pointer")
    folder = output / "releases" / rid
    if digest((folder / "manifest.json").read_bytes()) != pointer["manifest_sha256"]:
        raise InputError("Release manifest was modified")
    verify_release_folder(folder)
    data = read_json(folder / "catalogue.json")
    return {**data, "release_id": rid, "release_directory": str(folder)}


def select_resources(request, catalogue, ontology_dir=REPO / "serialisation"):
    # Validate the request and require a catalogue built with the deployed ontology.
    spec = read_json(ROOT / "schemas/selection.schema.json")
    errors = sorted(Draft202012Validator(spec).iter_errors(request), key=lambda e: str(list(e.absolute_path)))
    if errors:
        raise InputError("Invalid selection request: " + "; ".join(e.message for e in errors))
    if not all(request["need_identification"][k].strip() for k in ("method", "source")):
        raise InputError("Need identification method and source must contain text")
    schema, _, schema_hash = load_schema(ontology_dir)
    if schema_hash != catalogue["ontology_sha256"]:
        raise InputError("Catalogue predates the deployed ontology; rebuild it before selection")
    vocab = Vocabulary(schema)
    needs = {vocab.resolve(n, "HealthLiteracyNeedType") for n in request["needs"]}
    topics = {vocab.resolve(n, "ResourceTopic") for n in request["topics"]}
    audience = vocab.resolve(request["audience"], "ResourceAudienceType")
    preferred = {key: {vocab.resolve(v, FIELDS[key][1]) for v in request.get("preferred_" + key, [])} for key in ["formats", "complexities"]}
    accessibility = {vocab.resolve(v, "AccessibilityFeature") for v in request.get("required_accessibility", [])}
    language = language_tag(request["language"])
    matches = []
    # Apply eligibility conditions before considering presentation preferences.
    # Multiple requested needs/topics use an "at least one match" rule in each group.
    for r in catalogue["records"]:
        if r["curation_status"] != "Approved" or r["completion_status"] != "Complete":
            continue
        if request["journey_stage"] not in r["journey_stages"] or audience not in r["audiences"]:
            continue
        if not any(tag == language or ("-" not in tag and language.split("-")[0] == tag) for tag in r["languages"]):
            continue
        if r["access_conditions"] == "Restricted" and not request.get("include_registration_required", True):
            continue
        if not needs.intersection(r["needs"]) or not topics.intersection(r["topics"]) or not accessibility.issubset(r["accessibility"]):
            continue
        # Preferences affect ordering and are reported explicitly. A required
        # accessibility feature, in contrast, must have passed the filter above.
        preference_matches = {k: bool(v & set(r[k])) for k, v in preferred.items() if v}
        matches.append({**r, "matched_needs": sorted(needs & set(r["needs"])), "matched_topics": sorted(topics & set(r["topics"])),
                        "preference_matches": preference_matches, "requires_registration_or_access_check": r["access_conditions"] == "Restricted",
                        "selection_explanation": "Matches recorded need, topic, audience, journey stage and language; any required accessibility features are annotated."})
    # Use Resource ID to break ties predictably and return gaps without substituting
    # an unrelated resource. Selection itself does not save participant requests.
    matches.sort(key=lambda r: (-sum(r["preference_matches"].values()), r["id"]))
    return {"release_id": catalogue["release_id"], "match_count": len(matches), "matches": matches,
            "unmatched_needs": sorted(needs - {n for r in matches for n in r["matched_needs"]}),
            "status": "MATCHES_FOUND" if matches else "NO_SUITABLE_RESOURCE", "delivery_mode": "signpost"}


def demonstration(request, activity_id, output=ROOT / "generated", ontology_dir=REPO / "serialisation"):
    # Reuse the operational selector, then connect its results to a fictional
    # participant, identified need, draft care plan, intervention and learning goal.
    catalogue = load_release(output)
    selection = select_resources(request, catalogue, ontology_dir)
    template = next((t for t in catalogue["activity_templates"] if t["id"] == activity_id), None)
    if template is None:
        raise InputError("Unknown or unavailable activity template")
    selected = [r for r in selection["matches"] if r["id"] in template["candidate_resource_ids"]]
    if not selected:
        raise InputError("No selected resource is suitable for this activity template")
    targeted_needs = set(template["needs"]) & {n for r in selected for n in r["matched_needs"]}
    targeted_topics = set(template["topics"]) & {n for r in selected for n in r["matched_topics"]}
    if not targeted_needs or not targeted_topics or request["journey_stage"] not in template["journey_stages"]:
        raise InputError("The identified need, requested topic and journey stage must match the activity template")
    if not request.get("synthetic"):
        raise InputError("The demo command requires an explicitly synthetic profile; use select() for operational requests")
    base = catalogue["base_iri"] + "demo/"
    g = new_graph(base + "graph", "Fictional participant education example using real resource metadata", [catalogue["base_iri"] + "dataset"])
    g.add((URIRef(base + "graph"), META.isSynthetic, Literal(True)))
    person = instance(g, base + "participant", "Person", "Fictional AYA survivor")
    language = instance(g, base + "language", "LanguagePreference", "Supplied demonstration language preference")
    g.add((person, IC.personHasPreference, language))
    g.add((language, IC.preferredLanguageTag, Literal(language_tag(request["language"]), datatype=XSD.language)))
    event = instance(g, base + "needs-identification", "MeasurementEvent", "Fictional support-needs identification")
    result = instance(g, base + "needs-result", "ObservationResult", "Fictional identified support needs")
    g.add((person, IC.personParticipatesInMeasurement, event))
    g.add((event, IC.measurementEventHasOutput, result))
    g.add((event, META.identificationMethod, Literal(request["need_identification"]["method"])))
    g.add((result, DCTERMS.description, Literal(request["need_identification"]["source"])))
    for need in {n for r in selected for n in r["matched_needs"]}:
        g.add((result, IC.healthLiteracyResultIdentifiesNeed, URIRef(need)))
    plan = instance(g, base + "care-plan", "CarePlan", "Draft demonstration education plan")
    g.add((plan, IC.carePlanIntendedFor, person))
    g.add((plan, IC.carePlanHasStatus, IC.DraftCarePlan))
    activity = instance(g, base + "intervention", "HealthLiteracyIntervention", template["title"])
    g.add((activity, RDF.type, IC.EducationActivity))
    g.add((plan, IC.carePlanIncludesActivity, activity))
    g.add((activity, META.templateStatus, Literal("Draft")))
    g.add((activity, DCTERMS.source, URIRef(template["iri"])))
    goal = instance(g, base + "goal", "Goal", template["learning_objective"])
    g.add((goal, IC.goalDescriptionText, Literal(template["learning_objective"], datatype=XSD.string)))
    g.add((plan, IC.carePlanHasGoal, goal))
    g.add((activity, IC.activityContributesToGoal, goal))
    for need in targeted_needs:
        g.add((activity, IC.healthLiteracyInterventionAddressesNeed, URIRef(need)))
    for r in selected:
        g.add((activity, IC.healthLiteracyInterventionUsesResource, URIRef(r["iri"])))
    schema, paths, _ = load_schema(ontology_dir)
    release = Path(catalogue["release_directory"])
    source = Graph().parse(release / "catalogue.ttl") + Graph().parse(release / "activity-templates.ttl")
    validate_graph(g + source, schema)
    folder = Path(output).resolve() / "demo"
    for iri, filename in [(catalogue["base_iri"] + "graphs/resources", "catalogue.ttl"), (catalogue["base_iri"] + "graphs/activities", "activity-templates.ttl"), (catalogue["base_iri"] + "dataset", "dataset.ttl")]:
        paths[iri] = release / filename
    paths[base + "graph"] = folder / "participant-education.ttl"
    atomic_write(folder / "participant-education.ttl", g.serialize(format="turtle").encode())
    atomic_write(folder / "catalog-v001.xml", write_catalogue(paths, folder))
    atomic_write(folder / "validation/import-map.tsv", ("iri\tfile\n" + "".join(f"{iri}\t{Path(os.path.relpath(path, folder)).as_posix()}\n" for iri, path in sorted(paths.items()))).encode())
    response = {"synthetic": True, "release_id": catalogue["release_id"], "activity_id": activity_id, "activity_status": "Draft",
                "selected_resource_ids": [r["id"] for r in selected], "learning_objective": template["learning_objective"],
                "steps": template["steps"], "reflection_prompts": template["reflection_prompts"],
                "scope": "Technical demonstration; no intervention delivery, completed learning or improved literacy is asserted."}
    atomic_write(folder / "selection.json", canonical(selection))
    atomic_write(folder / "learning-activity.json", canonical(response))
    return response


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build", help="Publish a validated snapshot of approved and complete worksheet entries")
    build.add_argument("--workbook", type=Path, default=DEFAULT_WORKBOOK)
    build.add_argument("--sheet", default="Release resources")
    build.add_argument("--base-iri", default=DEFAULT_BASE)
    build.add_argument("--activities", type=Path, default=ROOT / "activities.json")
    build.add_argument("--allow-empty", action="store_true")
    select = sub.add_parser("select", help="Return matching resource metadata and links")
    select.add_argument("--request", type=Path, required=True)
    demo = sub.add_parser("demo", help="Build a fictional participant education example")
    demo.add_argument("--request", type=Path, default=ROOT / "examples/spanish-cardiovascular.json")
    demo.add_argument("--activity", default="EDU-CV-FOLLOWUP")
    for cmd in [build, select, demo]:
        cmd.add_argument("--output", type=Path, default=ROOT / "generated")
        cmd.add_argument("--ontology-dir", type=Path, default=REPO / "serialisation")
    args = parser.parse_args()
    try:
        if args.command == "build":
            result = build_release(args.workbook, args.sheet, args.output, args.ontology_dir, args.base_iri, args.activities, args.allow_empty)
        elif args.command == "select":
            result = select_resources(read_json(args.request), load_release(args.output), args.ontology_dir)
        else:
            result = demonstration(read_json(args.request), args.activity, args.output, args.ontology_dir)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (InputError, KeyError, OSError, ET.ParseError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
