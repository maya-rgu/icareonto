#!/usr/bin/env python3
"""Generate reviewable OWL/Turtle modules from the iCARE Onto workbooks.

Requires Python 3.9+ and RDFLib 7.x. Never edits source workbooks.
"""
import argparse
import collections
import csv
from datetime import datetime, timezone
import hashlib
import json
import posixpath
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from rdflib import BNode, Graph, Literal, Namespace, RDF, RDFS, OWL, SKOS, URIRef, XSD
from rdflib.namespace import DCTERMS

BASE = "http://maya-project.eu/icareonto/"
IC = Namespace(BASE)
META = Namespace(BASE + "metadata#")
PROV = Namespace("http://www.w3.org/ns/prov#")
ROOT_IRI = URIRef(BASE.rstrip("/"))
META_IRI = URIRef(BASE + "metadata")
PROV_IRI = URIRef(BASE + "imports/prov-reference")
SKOS_IRI = URIRef(BASE + "imports/skos-reference")
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
EXTERNAL = {"owl": OWL, "rdf": RDF, "rdfs": RDFS, "skos": SKOS, "prov": PROV, "xsd": XSD, "dcterms": DCTERMS}
SKIP = {"Summary", "controlled vocabulary summary", "controlled vocabulary detail"}


def read_xlsx(path):
    """Read cell values and cached formula results without Excel dependencies."""
    sheets = {}
    with zipfile.ZipFile(path) as z:
        strings = []
        if "xl/sharedStrings.xml" in z.namelist():
            strings = ["".join(t.text or "" for t in s.findall(".//m:t", NS))
                       for s in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", NS)]
        rels = {r.attrib["Id"]: r.attrib["Target"]
                for r in ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))}
        for sheet in ET.fromstring(z.read("xl/workbook.xml")).findall("m:sheets/m:sheet", NS):
            rid = sheet.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
            target = rels[rid]
            target = target.lstrip("/") if target.startswith("/") else posixpath.normpath("xl/" + target)
            rows = []
            for row in ET.fromstring(z.read(target)).findall(".//m:sheetData/m:row", NS):
                values = {"_row": int(row.attrib["r"])}
                for cell in row.findall("m:c", NS):
                    col = re.sub(r"\d", "", cell.attrib["r"])
                    value = cell.find("m:v", NS)
                    if cell.attrib.get("t") == "inlineStr":
                        values[col] = "".join(t.text or "" for t in cell.findall(".//m:t", NS))
                    elif value is not None:
                        values[col] = strings[int(value.text)] if cell.attrib.get("t") == "s" else value.text or ""
                if len(values) > 1:
                    rows.append(values)
            sheets[sheet.attrib["name"]] = rows
    return sheets


def normalise(text):
    return re.sub(r"[^a-z0-9]", "", text.casefold())


def graph():
    g = Graph()
    for prefix, ns in {"icare": IC, "meta": META, "rdf": RDF, "rdfs": RDFS,
                       "owl": OWL, "skos": SKOS, "prov": PROV, "xsd": XSD, "dcterms": DCTERMS}.items():
        g.bind(prefix, ns)
    return g


def header(g, iri, title, description, version):
    g.add((iri, RDF.type, OWL.Ontology))
    g.add((iri, RDFS.label, Literal(title, lang="en")))
    g.add((iri, RDFS.comment, Literal(description, lang="en")))
    suffix = str(iri).removeprefix(BASE).replace("#", "") if str(iri) != str(ROOT_IRI) else "icareonto"
    g.add((iri, OWL.versionIRI, URIRef(BASE + "releases/" + version + "/" + suffix)))
    g.add((iri, OWL.versionInfo, Literal(version)))
    g.add((iri, META.reviewStatus, Literal("Draft")))


def write_tsv(path, fields, rows):
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def reference_imports(root, version):
    """Select named, relevant source axioms; retain original downloads unchanged.

    Full SKOS contains unused rdf:List modelling outside OWL 2 DL. The published
    PROV RDF contains ontology metadata OWLAPI reads as property/annotation punning.
    Import purpose-labelled subsets without those unrelated parts.
    """
    skos_source = Graph().parse(root / "imports/skos.rdf", format="xml")
    prov_source = Graph().parse(root / "imports/prov-o.ttl", format="turtle")
    annotation = {RDFS.label, RDFS.comment, RDFS.seeAlso, RDFS.isDefinedBy,
                  SKOS.definition, SKOS.prefLabel, SKOS.altLabel, SKOS.scopeNote, SKOS.note}
    structural = {RDF.type, RDFS.subClassOf, RDFS.subPropertyOf, RDFS.domain, RDFS.range,
                  OWL.inverseOf, OWL.disjointWith, OWL.propertyDisjointWith}
    skos_names = ("Concept ConceptScheme inScheme topConceptOf hasTopConcept broader narrower broaderTransitive "
                  "narrowerTransitive semanticRelation related mappingRelation exactMatch closeMatch broadMatch "
                  "narrowMatch relatedMatch prefLabel altLabel hiddenLabel definition note scopeNote changeNote "
                  "historyNote editorialNote example notation").split()
    definitions = [("skos-reference.ttl", SKOS_IRI, skos_source, {SKOS[n] for n in skos_names},
                    "SKOS reference subset", "https://www.w3.org/2009/08/skos-reference/skos.rdf"),
                   ("prov-reference.ttl", PROV_IRI, prov_source, {PROV.Agent, PROV.Entity, PROV.Collection, PROV.InstantaneousEvent},
                    "PROV-O reference subset", "https://www.w3.org/ns/prov-o.ttl")]
    out = {}
    for file, iri, original, terms, title, url in definitions:
        g = graph()
        header(g, iri, title, "Reference subset of W3C terms used by iCARE Onto. Term IRIs retain their external identity; this ontology provides the selected supporting axioms.", version)
        g.add((iri, RDFS.seeAlso, URIRef(url)))
        g.add((iri, OWL.imports, META_IRI))
        for subject in sorted(terms):
            for s, p, o in original.triples((subject, None, None)):
                if p in annotation and isinstance(o, (Literal, URIRef)):
                    g.add((s, p, o))
                elif p in structural and isinstance(o, URIRef):
                    if (str(o).startswith(str(SKOS)) or str(o).startswith(str(PROV))) and o not in terms:
                        raise ValueError(f"Subset closure requires missing term {o}")
                    g.add((s, p, o))
        # Official SKOS annotation declarations, also needed while parsing class annotations.
        for prop in annotation:
            if str(prop).startswith(str(SKOS)):
                g.add((prop, RDF.type, OWL.AnnotationProperty))
        g.serialize(root / "imports" / file, format="turtle")
        out["imports/" + file] = g
    return out


def build(args):
    root = args.output.resolve()
    for folder in ("modules", "alignments", "imports", "validation"):
        (root / folder).mkdir(parents=True, exist_ok=True)
    wb = read_xlsx(args.ontology)
    alignment = read_xlsx(args.alignments)
    cq = read_xlsx(args.cqs)
    modules, entities, owners, lookup = {}, {}, {}, collections.defaultdict(set)
    aliases_used, warnings, declarations = [], [], []
    for name, rows in wb.items():
        if name in SKIP:
            continue
        by_row = {r["_row"]: r for r in rows}
        title, iri, description = by_row[1]["A"], URIRef(by_row[2]["B"]), by_row[3]["B"]
        if str(iri) != BASE + name:
            raise ValueError(f"Module IRI mismatch: {name}: {iri}")
        if by_row[1].get("B") != name:
            warnings.append(f"{name}: sheet title identifier differs from the module IRI; module ownership follows sheet name and IRI.")
        modules[name] = {"iri": iri, "title": title, "description": description, "graph": graph(), "deps": set()}
        for r in rows:
            if r.get("A") in ("Object property", "Data property"):
                kind = "ObjectProperty" if r["A"] == "Object property" else "DatatypeProperty"
                ident, entity_iri, label, definition = r["B"], URIRef(r["C"]), r.get("D", r["B"]), r.get("F", "")
            elif r["_row"] >= 8 and r.get("B", "").startswith(BASE) and r.get("A"):
                kind = "Class"
                ident, entity_iri, label, definition = r["A"], URIRef(r["B"]), r.get("C", r["A"]), r.get("E", "")
            else:
                continue
            if entity_iri in entities:
                raise ValueError(f"Duplicate entity IRI: {entity_iri}")
            if str(entity_iri) != BASE + ident:
                warnings.append(f"{name}!{r['_row']}: identifier {ident} differs from IRI local name; IRI preserved.")
            e = dict(module=name, row=r, id=ident, iri=entity_iri, kind=kind, label=label, definition=definition)
            entities[entity_iri] = e
            owners[entity_iri] = name
            for key in (ident, label, str(entity_iri).removeprefix(BASE)):
                lookup[normalise(key)].add(entity_iri)
            declarations.append({"module": name, "kind": kind, "identifier": ident, "iri": str(entity_iri), "source_cell": f"{name}!A{r['_row']}"})
    # A workbook domain says "Education Attainment"; the actual class is EducationalAttainment.
    explicit_aliases = {"Education Attainment": "EducationalAttainment"}

    def resolve(text, module, purpose):
        text = text.strip()
        if text.startswith(("http://", "https://")):
            value = URIRef(text)
            if text.startswith(BASE) and value not in entities:
                raise ValueError(f"Unknown local IRI {text} ({purpose})")
        elif ":" in text:
            prefix, local = text.split(":", 1)
            if prefix in EXTERNAL:
                value = URIRef(str(EXTERNAL[prefix]) + local)
            elif prefix in modules:
                value = URIRef(BASE + local)
                if value not in entities or owners[value] != prefix:
                    raise ValueError(f"Wrong module/unknown reference {text} ({purpose})")
            else:
                raise ValueError(f"Unknown prefix: {text}")
        else:
            corrected = explicit_aliases.get(text, text)
            candidates = lookup[normalise(corrected)]
            if len(candidates) != 1:
                raise ValueError(f"Unresolved/ambiguous reference {text!r} ({module}: {purpose})")
            value = next(iter(candidates))
            if text in explicit_aliases:
                aliases_used.append({"module": module, "context": purpose, "source_text": text, "resolved_iri": str(value)})
        if value in owners and owners[value] != module:
            modules[module]["deps"].add(modules[owners[value]]["iri"])
        elif str(value).startswith(str(SKOS)):
            modules[module]["deps"].add(SKOS_IRI)
        elif str(value).startswith(str(PROV)):
            modules[module]["deps"].add(PROV_IRI)
        return value

    for e in entities.values():
        name, r, subject = e["module"], e["row"], e["iri"]
        g = modules[name]["graph"]
        g.add((subject, RDF.type, getattr(OWL, e["kind"])))
        g.add((subject, RDFS.label, Literal(e["label"], lang="en")))
        g.add((subject, RDFS.isDefinedBy, modules[name]["iri"]))
        if e["definition"]:
            g.add((subject, SKOS.definition, Literal(e["definition"], lang="en")))
        else:
            warnings.append(f"Missing definition: {name}:{e['id']}")
        alt = r.get("D" if e["kind"] == "Class" else "E", "")
        for label in re.split(r"[;\n]", alt):
            if label.strip() and label.strip() != e["label"]:
                g.add((subject, SKOS.altLabel, Literal(label.strip(), lang="en")))
        if e["kind"] == "Class":
            parent = r.get("F", "").strip()
            if parent:
                # Only unambiguous named parents are accepted; do not split "Access or Engagement Barrier".
                if ";" in parent or "\n" in parent:
                    raise ValueError(f"Multiple parents need explicit review: {subject}: {parent}")
                g.add((subject, RDFS.subClassOf, resolve(parent, name, e["id"] + " parent")))
        else:
            for col, pred in (("G", RDFS.domain), ("H", RDFS.range)):
                text = r.get(col, "").strip()
                if not text:
                    warnings.append(f"Missing {pred}: {subject}")
                    continue
                value = resolve(text, name, e["id"] + " " + col)
                if col == "H" and e["kind"] == "DatatypeProperty":
                    if not str(value).startswith(str(XSD)):
                        raise ValueError(f"Not an XSD datatype: {subject}: {value}")
                elif value in entities and entities[value]["kind"] != "Class":
                    raise ValueError(f"Non-class domain/range {subject}: {value}")
                g.add((subject, pred, value))

    vocab = [r for r in wb["controlled vocabulary detail"] if r.get("F", "").startswith(BASE)]
    vocab_ids, schemes = set(), {}
    summary = {r["A"]: set(x.strip() for x in r["B"].split(","))
               for r in wb["controlled vocabulary summary"] if r["_row"] > 1 and r.get("A")}
    actual_summary = collections.defaultdict(set)
    for r in vocab:
        name, category, value = r["J"], URIRef(r["B"]), URIRef(r["F"])
        if category not in entities or owners[category] != name or entities[category]["kind"] != "Class":
            raise ValueError(f"Unknown/wrongly owned vocabulary category: {category}")
        if value in vocab_ids or value in entities:
            raise ValueError(f"Value IRI repeated or collides with schema: {value}")
        if str(value) != BASE + r["C"]:
            raise ValueError(f"Value identifier/IRI mismatch: {r}")
        vocab_ids.add(value)
        actual_summary[r["A"]].add(r["C"])
        g = modules[name]["graph"]
        scheme = URIRef(r["H"])
        if scheme in entities or scheme in vocab_ids:
            raise ValueError(f"Concept-scheme IRI collision: {scheme}")
        schemes[scheme] = name
        g.add((scheme, RDF.type, OWL.NamedIndividual))
        g.add((scheme, RDF.type, SKOS.ConceptScheme))
        g.add((scheme, RDFS.label, Literal(entities[category]["label"] + " scheme", lang="en")))
        g.add((value, RDF.type, OWL.NamedIndividual))
        g.add((value, RDF.type, category))
        g.add((value, RDF.type, SKOS.Concept))
        g.add((value, SKOS.prefLabel, Literal(r["D"], lang="en")))
        g.add((value, RDFS.label, Literal(r["D"], lang="en")))
        g.add((value, SKOS.definition, Literal(r.get("E", ""), lang="en")))
        g.add((value, SKOS.inScheme, scheme))
        g.add((value, META.reviewStatus, Literal(r.get("I", ""))))
        g.add((value, RDFS.isDefinedBy, modules[name]["iri"]))
        modules[name]["deps"].add(SKOS_IRI)
    if dict(actual_summary) != summary:
        raise ValueError("Controlled vocabulary summary/detail mismatch")
    for r in vocab:
        g, value, scheme = modules[r["J"]]["graph"], URIRef(r["F"]), URIRef(r["H"])
        if r.get("G", "").strip():
            parent = URIRef(BASE + r["G"].strip())
            if parent not in vocab_ids:
                raise ValueError(f"Unknown broader concept: {parent}")
            if (parent, SKOS.inScheme, scheme) not in g:
                raise ValueError(f"Broader concept in different module/scheme: {parent}")
            g.add((value, SKOS.broader, parent))
        else:
            g.add((scheme, SKOS.hasTopConcept, value))
            g.add((value, SKOS.topConceptOf, scheme))

    # Dublin Core properties support bibliographic/resource metadata, including CQ-025 and CQ-051.
    metadata = graph()
    header(metadata, META_IRI, "iCARE Onto metadata", "Annotation vocabulary for ontology review status and descriptive, bibliographic, language and rights metadata for knowledge resources.", args.version)
    for prop, label in ((META.reviewStatus, "review status"),):
        metadata.add((prop, RDF.type, OWL.AnnotationProperty))
        metadata.add((prop, RDFS.label, Literal(label, lang="en")))
    for local in ("title", "creator", "contributor", "description", "identifier", "language", "publisher", "issued", "modified", "license", "rights", "bibliographicCitation", "source"):
        metadata.add((DCTERMS[local], RDF.type, OWL.AnnotationProperty))
        metadata.add((DCTERMS[local], RDFS.label, Literal(local, lang="en")))
    metadata.add((META_IRI, RDFS.seeAlso, URIRef("https://www.dublincore.org/specifications/dublin-core/dcmi-terms/")))
    for local in ("prefLabel", "altLabel", "definition"):
        metadata.add((SKOS[local], RDF.type, OWL.AnnotationProperty))
    # Preserve the source datatypes explicitly, including XSD datatypes outside
    # OWL 2's mandatory datatype map. Value-level support is reasoner-dependent.
    for dtype in (XSD.date, XSD.duration):
        metadata.add((dtype, RDF.type, RDFS.Datatype))
    metadata.serialize(root / "imports" / "metadata.ttl", format="turtle")
    references = reference_imports(root, args.version)

    # Approved semantic alignments only. FHIR and coding recommendations remain documentation.
    align_g = graph()
    align_iri = URIRef(BASE + "alignments")
    header(align_g, align_iri, "iCARE Onto external alignments", "Semantic relationships connecting iCARE Onto entities to external ontology concepts while preserving their domain-specific meaning.", args.version)
    align_g.add((align_iri, OWL.imports, META_IRI))
    approved, excluded, alignment_trace = [], [], []
    for r in alignment["Alignment Register"]:
        if not r.get("A", "").startswith("MAP-"):
            continue
        if r.get("M") != "Approved" or r.get("J") not in ("Ontology", "Terminology"):
            excluded.append({"mapping_id": r["A"], "status": r.get("M", ""), "category": r.get("J", ""), "reason": "Not an approved semantic relationship"})
            continue
        subject, target = URIRef(r["E"]), URIRef(r["I"])
        if subject not in entities:
            raise ValueError(f"Approved alignment has unknown local entity: {r['A']}")
        if r["K"] != "rdfs:subClassOf":
            raise ValueError(f"Approved relation needs an explicit implementation: {r['K']}")
        align_g.add((subject, RDFS.subClassOf, target))
        # The operational axiom retains semantic rationale; register IDs stay in a sidecar.
        axiom = BNode(hashlib.sha256((str(subject) + str(RDFS.subClassOf) + str(target)).encode()).hexdigest()[:20])
        for p, o in ((RDF.type, OWL.Axiom), (OWL.annotatedSource, subject),
                     (OWL.annotatedProperty, RDFS.subClassOf), (OWL.annotatedTarget, target),
                     (META.reviewStatus, Literal("Approved")),
                     (RDFS.comment, Literal(r["N"], lang="en")), (RDFS.seeAlso, URIRef(r["O"]))):
            align_g.add((axiom, p, o))
        align_g.add((align_iri, OWL.imports, modules[owners[subject]]["iri"]))
        if str(target).startswith(str(PROV)):
            align_g.add((align_iri, OWL.imports, PROV_IRI))
        approved.append(r["A"])
        alignment_trace.append({"mapping_id": r["A"], "source_iri": str(subject), "relation": str(RDFS.subClassOf), "target_iri": str(target), "source_workbook": args.alignments.name, "source_row": r["_row"]})
    align_g.serialize(root / "alignments" / "approved.ttl", format="turtle")

    catalogue = {str(ROOT_IRI): "icareonto.ttl", str(META_IRI): "imports/metadata.ttl",
                 str(SKOS_IRI): "imports/skos-reference.ttl", str(PROV_IRI): "imports/prov-reference.ttl",
                 str(align_iri): "alignments/approved.ttl"}
    top = graph()
    header(top, ROOT_IRI, "iCARE Onto v1 (draft)",
           "iCARE Onto provides the semantic foundation for the MAYA iCARE Health Hub, supporting adolescent and young adult cancer survivorship and cardiovascular health. "
           "Its modular model represents people and preferences, cancer treatment history, clinical profiles, measurements, cardiovascular risk, personalised care, lifestyle, social context, educational resources, conversational interaction, digital services, pilot settings and knowledge governance. "
           "It supports participant- and pilot-specific knowledge graphs, personalised educational support and evidence-grounded dialogue. "
           "This pre-release draft is under review toward iCARE Onto v1.", args.version)
    top.add((ROOT_IRI, OWL.imports, align_iri))
    top.add((ROOT_IRI, OWL.imports, META_IRI))
    module_counts = []
    for name, m in modules.items():
        g, iri = m["graph"], m["iri"]
        header(g, iri, m["title"], m["description"], args.version)
        g.add((iri, OWL.imports, META_IRI))
        for dep in sorted(m["deps"]):
            g.add((iri, OWL.imports, dep))
        path = "modules/" + name + ".ttl"
        catalogue[str(iri)] = path
        g.serialize(root / path, format="turtle")
        top.add((ROOT_IRI, OWL.imports, iri))
        module_counts.append({"module": name, "classes": sum(e["module"] == name and e["kind"] == "Class" for e in entities.values()),
                              "object_properties": sum(e["module"] == name and e["kind"] == "ObjectProperty" for e in entities.values()),
                              "data_properties": sum(e["module"] == name and e["kind"] == "DatatypeProperty" for e in entities.values()),
                              "controlled_values": sum(r["J"] == name for r in vocab), "triples": len(g)})
    top.serialize(root / "icareonto.ttl", format="turtle")
    all_graphs = {"icareonto.ttl": top, "imports/metadata.ttl": metadata, "alignments/approved.ttl": align_g}
    all_graphs.update({"modules/" + n + ".ttl": m["graph"] for n, m in modules.items()})
    all_graphs.update(references)
    for file, g in all_graphs.items():
        for dep in g.objects(None, OWL.imports):
            if str(dep) not in catalogue:
                raise ValueError(f"Unmapped import {dep} in {file}")
        # Parse the actual written file, not just its in-memory graph.
        parsed = Graph().parse(root / file, format="xml" if file.endswith(".rdf") else "turtle")
        if len(parsed) != len(g):
            raise ValueError(f"RDF round-trip triple count mismatch: {file}")
    catalog = ET.Element("catalog", {"xmlns": "urn:oasis:names:tc:entity:xmlns:xml:catalog", "prefer": "public"})
    for iri, path in sorted(list(catalogue.items())):
        ET.SubElement(catalog, "uri", {"name": iri, "uri": path})
    for file, g in all_graphs.items():
        for version in g.objects(None, OWL.versionIRI):
            if str(version) not in catalogue:
                catalogue[str(version)] = file
                ET.SubElement(catalog, "uri", {"name": str(version), "uri": file})
    ET.indent(catalog)
    ET.ElementTree(catalog).write(root / "catalog-v001.xml", encoding="utf-8", xml_declaration=True)
    write_tsv(root / "validation" / "import-map.tsv", ["iri", "file"], [{"iri": k, "file": v} for k, v in sorted(catalogue.items())])
    write_tsv(root / "validation" / "entity-manifest.tsv", ["module", "kind", "identifier", "iri", "source_cell"], declarations)
    write_tsv(root / "validation" / "module-counts.tsv", list(module_counts[0]), module_counts)
    write_tsv(root / "validation" / "excluded-alignments.tsv", ["mapping_id", "status", "category", "reason"], excluded)
    write_tsv(root / "validation" / "alignment-trace.tsv", ["mapping_id", "source_iri", "relation", "target_iri", "source_workbook", "source_row"], alignment_trace)
    write_tsv(root / "validation" / "controlled-value-provenance.tsv", ["iri", "module", "source_workbook", "source_cell"],
              [{"iri": r["F"], "module": r["J"], "source_workbook": args.ontology.name, "source_cell": f"controlled vocabulary detail!A{r['_row']}"} for r in vocab])
    write_tsv(root / "validation" / "reference-normalisations.tsv", ["module", "context", "source_text", "resolved_iri"], aliases_used)

    cq_rows = []
    term_ids = {e["id"] for e in entities.values()} | {r["C"] for r in vocab}
    for r in cq["Final CQs"]:
        if not re.fullmatch(r"CQ-\d+", r.get("A", "")):
            continue
        path = r["E"]
        tokens = re.findall(r"(?:[\w-]+:)?[A-Za-z][A-Za-z0-9]*", path)
        refs = [t for t in tokens if t.split(":")[-1] in term_ids or t.startswith("dcterms:")]
        missing = [t for t in tokens if (":" in t and t.split(":")[0] in modules and t.split(":")[-1] not in term_ids)
                   or (t[0].islower() and re.search(r"[A-Z]", t) and t not in term_ids and ":" not in t)]
        if missing:
            raise ValueError(f"CQ {r['A']} references unknown terms: {missing}")
        if not refs:
            raise ValueError(f"No recognised ontology path in {r['A']}")
        cq_rows.append({"cq_id": r["A"], "question": r["C"], "ontology_path": path, "recognised_terms": "; ".join(refs),
                        "check": "Referenced terms present; query execution not tested"})
    write_tsv(root / "validation" / "cq-term-coverage.tsv", list(cq_rows[0]), cq_rows)
    sources = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (args.ontology, args.alignments, args.cqs)}
    external_sources = [{"file": file, "source_url": url, "retrieved": "2026-10-30",
                         "sha256": hashlib.sha256((root / file).read_bytes()).hexdigest()}
                        for file, url in (("imports/skos.rdf", "https://www.w3.org/2009/08/skos-reference/skos.rdf"),
                                          ("imports/prov-o.ttl", "https://www.w3.org/ns/prov-o.ttl"))]
    datatypes = sorted({str(o) for g in all_graphs.values() for s, p, o in g.triples((None, RDFS.range, None)) if str(o).startswith(str(XSD))})
    report = {"release": args.release, "ontology_version": args.version, "review_status": "Draft", "target_release": "iCARE Onto v1",
              "runtime_provenance_policy": "Development filenames, sheet references and mapping-register identifiers are retained only in validation sidecars, not in the ontology graphs.",
              "sources_sha256": sources, "external_sources": external_sources, "module_count": len(modules),
              "schema_counts": dict(collections.Counter(e["kind"] for e in entities.values())), "controlled_values": len(vocab),
              "concept_schemes": len(schemes), "approved_alignments": approved, "excluded_alignment_count": len(excluded),
              "cq_terms_checked": len(cq_rows), "rdf_files_parsed": len(all_graphs), "unresolved_references": 0,
              "normalised_references": aliases_used, "warnings": warnings,
              "external_reference_policy": "Imports use labelled, source-derived SKOS and PROV-O reference subsets. Full downloaded sources are retained unmodified but are not imported.",
              "source_datatypes_preserved": datatypes,
              "limitations": ["CQ paths checked for term presence only; no participant instances or CQ query execution.",
                              "OWL domains/ranges are inference axioms, not required-field validation rules.",
                              "Workbook xsd:date and xsd:duration datatypes are preserved; check reasoner support.",
                              "Dublin Core metadata properties are locally declared as OWL annotation properties; dcterms:source can hold an evidence-resource IRI.",
                              "No unapproved cardinalities, disjointness, equivalence, enumeration closure or distinct-value axioms were added."]}
    (root / "validation" / "build-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("module_count", "schema_counts", "controlled_values", "concept_schemes", "cq_terms_checked", "unresolved_references", "warnings")}, indent=2))


if __name__ == "__main__":
    repo = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ontology", type=Path, default=repo / "sources/icareonto_review_workbook_v021126.xlsx")
    parser.add_argument("--alignments", type=Path, default=repo / "sources/icareonto_alignment_mapping_workbook_v301026_4.xlsx")
    parser.add_argument("--cqs", type=Path, default=repo / "sources/icareonto_final_consolidated_competency_questions_v5.xlsx")
    parser.add_argument("--output", type=Path, default=repo / "serialisation")
    parser.add_argument("--release", default=datetime.now(timezone.utc).date().isoformat(), help="Build date recorded in the development report; defaults to the current UTC date")
    parser.add_argument("--version", default="0.1.0-draft", help="Ontology pre-release version, independent of development-source revisions")
    build(parser.parse_args())
