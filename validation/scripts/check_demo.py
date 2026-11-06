#!/usr/bin/env python3
"""Check fixture terms, explicit types, literal values, imports and sample CQs."""
import json
import xml.etree.ElementTree as ET
from collections import Counter
from decimal import Decimal
from pathlib import Path

from rdflib import Graph, Literal, RDF, RDFS, OWL, URIRef

ROOT = Path(__file__).resolve().parents[1]
BASE = "http://maya-project.eu/icareonto/"
DEMO = "https://example.org/maya/demo/es/"
g = Graph().parse(ROOT / "demo_spain_aya.ttl", format="turtle")
schema = Graph()
catalogue = {e.attrib["name"]: (ROOT / e.attrib["uri"]).resolve()
             for e in ET.parse(ROOT / "catalog-v001.xml").getroot()}
for path in set(catalogue.values()):
    assert path.is_file(), path
    if path != (ROOT / "demo_spain_aya.ttl").resolve():
        schema += Graph().parse(path, format="turtle")
for imported in g.objects(None, OWL.imports):
    assert str(imported) in catalogue, imported
combined = schema + g
classes = set(schema.subjects(RDF.type, OWL.Class))
object_props = set(schema.subjects(RDF.type, OWL.ObjectProperty))
data_props = set(schema.subjects(RDF.type, OWL.DatatypeProperty))
annotations = set(schema.subjects(RDF.type, OWL.AnnotationProperty))


def ancestors(cls):
    found, pending = {cls}, [cls]
    while pending:
        current = pending.pop()
        for parent in schema.objects(current, RDFS.subClassOf):
            if isinstance(parent, URIRef) and parent not in found:
                found.add(parent)
                pending.append(parent)
    return found


def explicitly_compatible(node, cls):
    return cls == OWL.Thing or any(cls in ancestors(t) for t in combined.objects(node, RDF.type))


errors = []
for s, p, o in g:
    if p == RDF.type and str(o).startswith(BASE) and o not in classes:
        errors.append(f"Unknown class: {o}")
    if str(p).startswith(BASE) and p not in object_props | data_props | annotations:
        errors.append(f"Unknown local predicate: {p}")
    if isinstance(o, URIRef) and str(o).startswith(BASE):
        if not list(schema.triples((o, None, None))):
            errors.append(f"Unknown local object: {o}")
    if p in object_props | data_props:
        for domain in schema.objects(p, RDFS.domain):
            if not explicitly_compatible(s, domain):
                errors.append(f"Subject not explicitly compatible with source domain: {s}, {p}, {domain}")
        if p in object_props:
            if not isinstance(o, URIRef):
                errors.append(f"Object property has literal value: {s}, {p}")
            for range_ in schema.objects(p, RDFS.range):
                if not explicitly_compatible(o, range_):
                    errors.append(f"Object not explicitly compatible with source range: {s}, {p}, {o}, {range_}")
        else:
            if not isinstance(o, Literal):
                errors.append(f"Data property has resource value: {s}, {p}")
            elif o.value is None:
                errors.append(f"Invalid literal lexical form: {o.n3()}")
            else:
                for range_ in schema.objects(p, RDFS.range):
                    if o.datatype != range_:
                        errors.append(f"Datatype mismatch: {p}, {o.n3()}, expected {range_}")
for s in {s for s in g.subjects() if str(s).startswith(DEMO)}:
    if (s, RDF.type, OWL.NamedIndividual) not in g:
        errors.append(f"Missing individual declaration: {s}")
results = []
for case in json.loads((ROOT / "tests/expected_results.json").read_text())["cases"]:
    query = (ROOT / "queries" / (case["id"] + ".rq")).read_text()
    bindings = [row.asdict() for row in combined.query(query)]
    actual = [{str(k): str(v) for k, v in row.items()} for row in bindings]
    numeric_columns = case.get("numeric_datatypes", {})
    def normalise(rows):
        normalised = []
        for row in rows:
            row = dict(row)
            for key in numeric_columns:
                if key in row:
                    row[key] = str(Decimal(row[key]).normalize())
            normalised.append(json.dumps(row, sort_keys=True))
        return Counter(normalised)
    types_match = all(str(row[key].datatype) == dtype for row in bindings for key, dtype in numeric_columns.items() if key in row)
    passed = types_match and normalise(actual) == normalise(case["expected"])
    results.append({"id": case["id"], "status": "PASS" if passed else "FAIL", "expected": case["expected"], "actual": actual})
report = {"term_and_explicit_type_errors": errors, "query_mode": "SPARQL over explicit schema + fixture triples, without inference",
          "cq_cases_tested": sum(r["id"].startswith("CQ-") for r in results),
          "additional_scenario_cases": sum(not r["id"].startswith("CQ-") for r in results),
          "passed": sum(r["status"] == "PASS" for r in results), "failed": sum(r["status"] == "FAIL" for r in results),
          "results": results, "all_78_cqs_tested": False}
(ROOT / "validation/query-results.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({k: v for k, v in report.items() if k != "results"}, indent=2))
if errors or report["failed"]:
    raise SystemExit(1)
