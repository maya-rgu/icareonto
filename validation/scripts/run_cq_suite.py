#!/usr/bin/env python3
"""Execute the full CQ suite and write reproducible JSON, TSV and Markdown reports."""
import collections
import csv
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from rdflib import Graph, Literal, Namespace, RDF, RDFS, OWL, URIRef, XSD

KG = Path(__file__).resolve().parents[1]
SUITE = KG / "cq-tests"
REPORTS = KG / "reports"
REPORTS.mkdir(exist_ok=True)
IC = Namespace("http://maya-project.eu/icareonto/")
PREFIXES = {"icare": str(IC), "demo": "https://example.org/maya/demo/es/", "test": "https://example.org/maya/demo/cq-tests/"}
config = json.loads((SUITE / "cases.json").read_text())
catalogue = {e.attrib["name"]: (SUITE / e.attrib["uri"]).resolve() for e in ET.parse(SUITE / "catalog-v001.xml").getroot()}
schema, data = Graph(), Graph()
hashes = {}
import_errors = []
for path in sorted(set(catalogue.values())):
    if not path.is_file():
        raise FileNotFoundError(path)
    parsed = Graph().parse(path, format="turtle")
    relative = str(path.relative_to(KG.parent))
    hashes[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    for imported in parsed.objects(None, OWL.imports):
        if str(imported) not in catalogue:
            import_errors.append(f"Unmapped import: {imported} in {relative}")
    if path in ((KG / "demo_spain_aya.ttl").resolve(), (SUITE / "coverage.ttl").resolve()):
        data += parsed
    else:
        schema += parsed
combined = schema + data
classes = set(schema.subjects(RDF.type, OWL.Class))
object_props = set(schema.subjects(RDF.type, OWL.ObjectProperty))
data_props = set(schema.subjects(RDF.type, OWL.DatatypeProperty))
annotations = set(schema.subjects(RDF.type, OWL.AnnotationProperty))


def expand(text):
    if ":" in text:
        prefix, rest = text.split(":", 1)
        if prefix in PREFIXES:
            return PREFIXES[prefix] + rest
    return text


def ancestors(cls):
    seen, todo = {cls}, [cls]
    while todo:
        for parent in schema.objects(todo.pop(), RDFS.subClassOf):
            if isinstance(parent, URIRef) and parent not in seen:
                seen.add(parent)
                todo.append(parent)
    return seen


def compatible(node, cls):
    return cls == OWL.Thing or any(cls in ancestors(t) for t in combined.objects(node, RDF.type))


errors = list(import_errors)
for s, p, o in data:
    if p == RDF.type and str(o).startswith(str(IC)) and o not in classes:
        errors.append(f"Undeclared class: {o}")
    if str(p).startswith(str(IC)) and p not in object_props | data_props | annotations:
        errors.append(f"Undeclared local property: {p}")
    if isinstance(o, URIRef) and str(o).startswith(str(IC)) and not list(schema.triples((o, None, None))):
        errors.append(f"Unrecognised ontology object: {o}")
    if p in object_props | data_props:
        for domain in schema.objects(p, RDFS.domain):
            if not compatible(s, domain):
                errors.append(f"Explicit subject type does not satisfy source domain: {s} {p} ({domain})")
        if p in object_props:
            if not isinstance(o, URIRef):
                errors.append(f"Non-resource object for {p}: {o}")
            for range_ in schema.objects(p, RDFS.range):
                if not compatible(o, range_):
                    errors.append(f"Explicit object type does not satisfy source range: {s} {p} {o} ({range_})")
        elif not isinstance(o, Literal) or o.value is None:
            errors.append(f"Invalid data-property literal: {s} {p} {o}")
        else:
            for range_ in schema.objects(p, RDFS.range):
                if o.datatype != range_:
                    errors.append(f"Literal datatype mismatch: {s} {p} {o.n3()}")


def expected_term(value, key, case):
    expanded = expand(value)
    if expanded.startswith(("http://", "https://")):
        return URIRef(expanded)
    dtype = case.get("datatypes", {}).get(key)
    if key in case.get("numeric", []):
        dtype = str(XSD.decimal)
    return Literal(value, datatype=URIRef(dtype) if dtype else XSD.string)


def canonical(term):
    if isinstance(term, URIRef):
        return ("iri", str(term))
    if term is None:
        return ("unbound",)
    if isinstance(term, Literal):
        if term.datatype in (XSD.decimal, XSD.integer, XSD.nonNegativeInteger, XSD.positiveInteger, XSD.float, XSD.double):
            return ("number", str(term.datatype), str(Decimal(str(term)).normalize()))
        if term.datatype == XSD.dateTime:
            parsed = datetime.fromisoformat(str(term).replace("Z", "+00:00"))
            if parsed.tzinfo is not None:
                parsed = parsed.astimezone(timezone.utc)
            return ("datetime", parsed.isoformat())
        return ("literal", str(term), str(term.datatype or XSD.string), term.language)
    return ("other", str(term))


def canonical_rows(rows):
    return [tuple(sorted((k, canonical(v)) for k, v in row.items())) for row in rows]


def display(term):
    if term is None:
        return None
    text = str(term)
    for prefix, ns in PREFIXES.items():
        if text.startswith(ns):
            return prefix + ":" + text[len(ns):]
    return text


results = []
for case in config["cases"]:
    query_file = SUITE / case["query_file"]
    query = query_file.read_text()
    expected = [{k: expected_term(v, k, case) for k, v in row.items()} for row in case["expected"]]
    target = combined
    if case.get("remove_triples"):
        target = Graph() + combined
        for triple in case["remove_triples"]:
            target.remove(tuple(URIRef(expand(value)) for value in triple))
    actual, exception = [], None
    try:
        actual = [{str(k): v for k, v in row.asdict().items()} for row in target.query(query)]
        wanted, returned = canonical_rows(expected), canonical_rows(actual)
        matched = wanted == returned if case.get("ordered") else collections.Counter(wanted) == collections.Counter(returned)
        for forbidden in case.get("forbidden", []):
            ban = {k: expected_term(v, k, case) for k, v in forbidden.items()}
            if canonical_rows([ban])[0] in returned:
                matched = False
    except Exception as exc:
        matched = False
        exception = f"{type(exc).__name__}: {exc}"
    status = "ERROR" if exception else "PASS" if matched else "NEEDS REVIEW" if case.get("review_issue") else "FAIL"
    record = {k: v for k, v in case.items() if k not in ("expected", "forbidden")}
    record.update(status=status, comparison="MATCH" if matched else "MISMATCH", expected=[{k: display(v) for k, v in row.items()} for row in expected],
                  actual=[{k: display(v) for k, v in row.items()} for row in actual], error=exception,
                  query_sha256=hashlib.sha256(query.encode()).hexdigest())
    results.append(record)

canonical_results = [r for r in results if r["id"].startswith("CQ-")]
controls = [r for r in results if r["id"].startswith("CTRL-")]
counts = dict(collections.Counter(r["status"] for r in canonical_results))
ids = {r["id"] for r in canonical_results}
if ids != {f"CQ-{i:03d}" for i in range(1, 79)} or len(canonical_results) != 78:
    errors.append("Canonical CQ identifiers are missing, duplicated or unexpected")
if any(not r["expected"] for r in canonical_results):
    errors.append("A canonical test has an empty oracle and could pass vacuously")
register = KG.parent / "sources" / config["source_register"]
if hashlib.sha256(register.read_bytes()).hexdigest() != config["source_sha256"]:
    errors.append("CQ register changed after suite generation")
owl_path = REPORTS / "cq-owlapi-report.json"
owl = json.loads(owl_path.read_text()) if owl_path.exists() else None
report = {
    "run_date": datetime.now(timezone.utc).date().isoformat(), "ontology_version": config["ontology_version"], "source_register": config["source_register"],
    "source_register_sha256": config["source_sha256"], "query_engine": "RDFLib SPARQL 1.1",
    "query_semantics": "Explicit RDF union; subclass traversal is expressed using SPARQL property paths. No OWL inference is materialised for query execution.",
    "fixture_scope": "Original Spanish survivor graph plus a separate synthetic coverage supplement and four controls",
    "canonical_cqs_executed": len(canonical_results), "canonical_status_counts": counts,
    "controls_executed": len(controls), "control_status_counts": dict(collections.Counter(r["status"] for r in controls)),
    "source_type_and_import_errors": errors, "inputs_sha256": hashes,
    "suite_spec_sha256": hashlib.sha256((SUITE / "cases.json").read_bytes()).hexdigest(),
    "owl_validation": None if owl is None else {"in_owl2_dl": owl["owl2_dl_profile"]["in_profile"], "profile_violations": len(owl["owl2_dl_profile"]["violations"]), "imports_closure_size": owl["imports_closure_size"], "reasoner": owl["reasoner"]},
    "overall": "COMPLETE_WITH_REVIEW_ITEMS" if counts.get("NEEDS REVIEW") else "PASS",
    "results": results,
    "limitations": ["One authored positive scenario per canonical CQ, plus four controls; this is not exhaustive validation over all possible instance data.",
                    "The fixture, thresholds, clinical conditions, evidence and scores are fictional. No clinical validity, prediction accuracy or real instrument validation is established.",
                    "CQ-019 follows the revised topic wording; CQ-051 uses the explicit validation-evidence relation and excludes background-only citations.",
                    "Trigger queries retrieve authored associations, not execution traces or clinical causal inference.",
                    "Required-field validation and full FHIR transformation testing are outside this suite."]
}
if errors or any(r["status"] in ("FAIL", "ERROR") for r in results):
    report["overall"] = "FAILED_CHECKS"
(REPORTS / "cq-results.json").write_text(json.dumps(report, indent=2) + "\n")
fields = ["id", "theme", "question", "status", "comparison", "expected", "actual", "review_issue", "scope", "query_file", "primary_basis", "stakeholder_cq_ids", "proposal_cq_ids"]
with (REPORTS / "cq-results.tsv").open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fields, delimiter="\t", extrasaction="ignore")
    writer.writeheader()
    for record in results:
        row = dict(record)
        row["expected"] = json.dumps(row["expected"], ensure_ascii=False)
        row["actual"] = json.dumps(row["actual"], ensure_ascii=False)
        writer.writerow(row)


def md(text):
    return str(text).replace("|", "\\|").replace("\n", " ")


lines = ["# iCARE Onto competency-question validation report", "",
         f"**Ontology:** 0.1.0-draft, under review toward iCARE Onto v1. **Test date:** {report['run_date']}.", "",
         f"All **78 consolidated CQs were executed**. **{counts.get('PASS', 0)}** matched their authored expected answers; **{counts.get('NEEDS REVIEW', 0)}** require modelling/scope review. The **{len(controls)} additional controls** " + ("all passed." if all(r['status'] == 'PASS' for r in controls) else "include failures; see the results."), "",
         "CQ-019 follows the corrected question wording and includes mixed-topic resources addressing nutrition. CQ-051 uses the new validation-evidence relation and excludes a general background citation. These changes follow the revised source specifications; expected answers remain separately authored constants.", "",
         "## Method", "",
         "The canonical CQ register supplies the question wording, expected answer type, suggested ontology path, modules and original proposal/stakeholder CQ identifiers. Each canonical CQ has one executable SPARQL query and a separately authored, nonempty expected result. Expected answers are constants in the suite definition; they are not calculated from actual query output.", "",
         "The query dataset is the explicit union of the ontology imports, the existing fictional Spanish survivor graph, and a separate synthetic coverage supplement. SPARQL subclass property paths handle declared class hierarchies; no reasoning engine materialises new facts during query execution. Ordered results are checked for CQ-043. Other answers use exact unordered multisets, including exclusion of extra results. IRIs, numeric datatypes/value equality, language tags and timezone-normalised date-time values are checked.", "",
         "The Spanish survivor graph and ontology are unchanged by these tests. Added coverage data include two risk-factor contributions, clinical and social records, an interval-based observation, out-of-window observations, nutrition/adherence examples, another fictional person, a mixed-topic resource and separate validation/background evidence sources.", "",
         "Fixture preflight checks declared terms, import resolution, datatype lexical forms and explicit compatibility with ontology domains/ranges. These checks report mismatches instead of relying on OWL domain/range inference to assign convenient types.", "",
         f"Preflight errors: **{len(errors)}**.", ""]
if owl:
    v = report["owl_validation"]
    lines += ["## OWL consistency", "", f"Protégé's OWLAPI loads **{v['imports_closure_size']} documents** for the complete test entry. OWL 2 DL profile violations: **{v['profile_violations']}**. HermiT consistency: **{v['reasoner']['consistent']}**. Unsatisfiable named classes: **{len(v['reasoner'].get('unsatisfiable_named_classes', []))}**.", "",
              "Consistency is checked separately from expected query answers. It does not establish clinical correctness or prove every CQ can be answered.", ""]
else:
    lines += ["## OWL consistency", "", "OWLAPI/HermiT validation report has not yet been generated for this coverage fixture.", ""]
lines += ["## Items requiring review", ""]
for r in canonical_results:
    if r["status"] != "PASS":
        lines += ["### " + r["id"] + " — " + r.get("question", ""), "", r.get("review_issue", r.get("error") or "Unexpected answer mismatch."), "",
                  "Expected: `" + json.dumps(r["expected"]) + "`", "", "Returned: `" + json.dumps(r["actual"]) + "`", ""]
lines += (["No outstanding query-answer review items in this run.", ""] if all(r["status"] == "PASS" for r in canonical_results) else [])
lines += ["The suite tests the current source CQ wording and ontology relations. Unexpected missing or additional answers are reported as mismatches.", "",
          "## Interpretation choices", "",
          "- CQ-001 enumerates represented risk-factor instances. CQ-015, CQ-029 and CQ-035 enumerate local named subclasses. CQ-060 and CQ-061 enumerate the supplied controlled concepts.",
          "- CQ-039 uses AnthropometricParameter typing. CQ-040 and CQ-046 identify body-composition variables through BodyCompositionProtocol membership. This interpretation is recorded with the cases.",
          "- Systolic/diastolic variables are explicitly typed as PhysiologicalParameter in the supplement because VitalSign is currently a sibling class in the supplied hierarchy. BMI is explicitly typed as both DerivedParameter and AnthropometricParameter. No schema axioms were changed.",
          "- CQ-043 uses a half-open UTC window, includes point observations inside it and intervals overlapping it, and checks chronological ordering. A point exactly at the upper bound is excluded.",
          "- CQ-063 and CQ-064 distinguish prescribed and performed ExerciseActivity instances (20 versus 18 minutes).",
          "- CQ-073–CQ-078 retrieve authored trigger associations. They do not demonstrate execution of a warning rule or causal initiation of an activity.", "",
          "## Results by theme", "", "| Theme | Executed | Pass | Needs review | Fail/error |", "|---|---:|---:|---:|---:|"]
themes = {}
for r in canonical_results:
    themes.setdefault(r["theme"], []).append(r)
for theme, rows in themes.items():
    c = collections.Counter(r["status"] for r in rows)
    lines.append(f"| {md(theme)} | {len(rows)} | {c['PASS']} | {c['NEEDS REVIEW']} | {c['FAIL'] + c['ERROR']} |")
lines += ["", "## Per-CQ results", "", "The JSON and TSV reports contain complete expected and actual bindings, source identifiers, query hashes, and test-scope notes.", "",
          "| CQ | Question | Status | Expected/actual rows | Query |", "|---|---|---|---|---|"]
for r in canonical_results:
    lines.append(f"| {r['id']} | {md(r['question'])} | {r['status']} | {len(r['expected'])}/{len(r['actual'])} | [SPARQL](../cq-tests/{r['query_file']}) |")
lines += ["", "## Additional controls", "", "| Control | Purpose | Result |", "|---|---|---|"]
for r in controls:
    lines.append(f"| {r['id']} | {md(r.get('scope', ''))} | {r['status']} |")
lines += ["", "## Reproduction and limits", "", "Run the commands in [the suite README](../cq-tests/README.md). Query files, authored cases and fixture are versionable text assets. Input-file and query SHA-256 hashes are included in `cq-results.json`.", "",
          "Coverage here means all canonical CQs have been exercised with at least one specified scenario. It is not exhaustive testing of all parameter combinations, clinical meanings or data-quality conditions. Empty results under an unknown-participant control indicate no matching assertion in this dataset, not proof that a clinical fact is false.", ""]
(REPORTS / "CQ_VALIDATION_REPORT.md").write_text("\n".join(lines), encoding="utf-8")
print(json.dumps({k: report[k] for k in ("canonical_cqs_executed", "canonical_status_counts", "controls_executed", "control_status_counts", "source_type_and_import_errors", "overall")}, indent=2))
for r in canonical_results:
    if r["status"] != "PASS":
        print(r["id"], r["status"], "expected", r["expected"], "actual", r["actual"], r.get("error") or "")
if report["overall"] == "FAILED_CHECKS":
    raise SystemExit(1)
