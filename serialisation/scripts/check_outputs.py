#!/usr/bin/env python3
"""Independently reconcile saved RDF files with source cells and import catalogue."""
import collections
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from rdflib import Graph, RDF, RDFS, OWL, SKOS, Literal, URIRef
from rdflib.compare import isomorphic

from serialise_ontology import read_xlsx, BASE

root = Path(__file__).resolve().parents[1]
repo = root.parent / "sources"
report = json.loads((root / "validation/build-report.json").read_text())
ontology_source = next(name for name in report["sources_sha256"] if name.startswith("icareonto_review_workbook_"))
source = read_xlsx(repo / ontology_source)
graphs = {p.stem: Graph().parse(p, format="turtle") for p in sorted((root / "modules").glob("*.ttl"))}
checks = []


def check(condition, message):
    if not condition:
        raise AssertionError(message)
    checks.append(message)


for filename, expected in report["sources_sha256"].items():
    check(hashlib.sha256((repo / filename).read_bytes()).hexdigest() == expected, "Source unchanged: " + filename)

expected = {"Class": set(), "ObjectProperty": set(), "DatatypeProperty": set()}
for module, g in graphs.items():
    for r in source[module]:
        if r.get("A") in ("Object property", "Data property"):
            kind = "ObjectProperty" if r["A"] == "Object property" else "DatatypeProperty"
            subject, label, definition = URIRef(r["C"]), r.get("D", r["B"]), r.get("F", "")
        elif r["_row"] >= 8 and r.get("B", "").startswith(BASE) and r.get("A"):
            kind = "Class"
            subject, label, definition = URIRef(r["B"]), r.get("C", r["A"]), r.get("E", "")
        else:
            continue
        expected[kind].add(subject)
        check((subject, RDF.type, getattr(OWL, kind)) in g, f"Declaration: {module}:{subject}")
        check((subject, RDFS.label, Literal(label, lang="en")) in g, f"Label: {module}:{subject}")
        if definition:
            check((subject, SKOS.definition, Literal(definition, lang="en")) in g, f"Definition: {module}:{subject}")
        if kind == "DatatypeProperty":
            dtype = URIRef("http://www.w3.org/2001/XMLSchema#" + r["H"].split(":", 1)[1])
            check((subject, RDFS.range, dtype) in g, f"Datatype preserved: {module}:{subject}")
        if kind in ("ObjectProperty", "DatatypeProperty"):
            check(len(list(g.objects(subject, RDFS.domain))) == 1 and len(list(g.objects(subject, RDFS.range))) == 1,
                  f"Single source domain/range: {module}:{subject}")

merged = Graph()
for g in graphs.values():
    merged += g
for kind, iris in expected.items():
    actual = {s for s in merged.subjects(RDF.type, getattr(OWL, kind)) if str(s).startswith(BASE)}
    check(actual == iris, "Complete schema set: " + kind)
    check(sum(len({s for s in g.subjects(RDF.type, getattr(OWL, kind)) if str(s).startswith(BASE)}) for g in graphs.values()) == len(iris),
          "Single module ownership: " + kind)

values = [r for r in source["controlled vocabulary detail"] if r.get("F", "").startswith(BASE)]
for r in values:
    g, subject = graphs[r["J"]], URIRef(r["F"])
    check((subject, RDF.type, URIRef(r["B"])) in g, "Controlled class membership: " + r["C"])
    check((subject, SKOS.prefLabel, Literal(r["D"], lang="en")) in g, "Controlled label: " + r["C"])
    check((subject, SKOS.definition, Literal(r.get("E", ""), lang="en")) in g, "Controlled definition: " + r["C"])
    check((subject, SKOS.inScheme, URIRef(r["H"])) in g, "Controlled scheme: " + r["C"])
    if r.get("G"):
        check((subject, SKOS.broader, URIRef(BASE + r["G"])) in g, "Controlled hierarchy: " + r["C"])

catalogue = {e.attrib["name"]: e.attrib["uri"] for e in ET.parse(root / "catalog-v001.xml").getroot()}
for iri, relative in catalogue.items():
    check((root / relative).is_file(), "Catalogue target exists: " + iri)
all_graphs = dict(graphs)
for path in [root / "icareonto.ttl", root / "alignments/approved.ttl", root / "imports/metadata.ttl", root / "imports/skos-reference.ttl", root / "imports/prov-reference.ttl"]:
    all_graphs[path.name] = Graph().parse(path, format="turtle")
for name, g in all_graphs.items():
    for dep in g.objects(None, OWL.imports):
        check(str(dep) in catalogue, "Catalogue resolves import: " + name + ":" + str(dep))
    # Independently round-trip through RDF/XML, as consumed by OWL tools.
    check(isomorphic(g, Graph().parse(data=g.serialize(format="xml"), format="xml")), "RDF/XML round-trip: " + name)
    check(not any(str(p).endswith(("#sourceWorkbook", "#sourceCell", "#mappingIdentifier"))
                  or (isinstance(o, Literal) and re.search(r"workbook|\.xlsx\b|v301026", str(o), re.I))
                  for s, p, o in g), "No development-source references in ontology: " + name)
    check(not any((subject, RDFS.comment, definition) in g
                  for subject, definition in g.subject_objects(SKOS.definition)),
          "No duplicated definition/comment text: " + name)
    for ontology in g.subjects(RDF.type, OWL.Ontology):
        check((ontology, OWL.versionInfo, Literal(report["ontology_version"])) in g,
              "Ontology version matches release: " + str(ontology))
        check(any("/releases/" + report["ontology_version"] + "/" in str(v) for v in g.objects(ontology, OWL.versionIRI)),
              "Version IRI matches release: " + str(ontology))

align = all_graphs["approved.ttl"]
check(len(list(align.subjects(RDF.type, OWL.Axiom))) == len(report["approved_alignments"]), "Approved mappings reconciled")
for name, g in graphs.items():
    for predicate in (OWL.equivalentClass, OWL.equivalentProperty, OWL.disjointWith, OWL.cardinality, OWL.oneOf):
        check(not list(g.triples((None, predicate, None))), "No inferred design additions: " + name + ":" + str(predicate))

result = {"checks_passed": len(checks), "source_schema_counts": {k: len(v) for k, v in expected.items()},
          "controlled_values_checked": len(values), "module_count": len(graphs),
          "catalogue_targets_checked": len(catalogue), "result": "PASS"}
(root / "validation/source-reconciliation.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
