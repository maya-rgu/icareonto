#!/usr/bin/env python3
"""Exercise KG initialisation, shared context and rejected-input behaviour."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import xml.etree.ElementTree as ET

from rdflib import Dataset, Graph, Literal, RDF, URIRef, XSD

import generate_kg as w


def main():
    cases = []
    def check(identifier, condition, detail):
        if not condition:
            raise AssertionError(identifier + ": " + detail)
        cases.append({"id": identifier, "status": "PASS", "detail": detail})

    pilot = w.read_json(w.ROOT / "examples/pilot-es-demo.json")
    first = w.read_json(w.ROOT / "examples/participant-es-001.json")
    second = w.read_json(w.ROOT / "examples/participant-es-002.json")
    base, ic = w.DEFAULT_BASE, w.IC
    person = URIRef(base + "people/es-demo-aya-001")
    other = URIRef(base + "people/es-demo-aya-002")
    site = URIRef(base + "sites/es-demo-01")
    with TemporaryDirectory(prefix="icareonto-input-workflow-") as temp:
        # Keep every test enrolment and intentional failure outside the delivered graphs.
        output = Path(temp) / "generated"
        def fingerprint():
            return {str(p.relative_to(output)): w.digest(p.read_bytes()) for p in output.rglob("*") if p.is_file()} if output.exists() else {}
        def rejected(identifier, kind, data, expected_text, replace=False):
            before = fingerprint()
            try:
                w.generate(kind, data, output, replace_seed=replace)
            except w.InputError as error:
                check(identifier, expected_text in str(error) and before == fingerprint(), "Rejected without changing published files: " + expected_text)
            else:
                raise AssertionError(identifier + ": invalid input accepted")

        rejected("UNREGISTERED-PILOT", "participant", first, "pilot must be generated")
        check("CREATE-PILOT", w.generate("pilot", pilot, output)["status"] == "CREATED", "Pilot setup generated and validated")
        check("CREATE-FIRST", w.generate("participant", first, output)["status"] == "CREATED", "First enrolment generated and validated")
        check("CREATE-SECOND", w.generate("participant", second, output)["status"] == "CREATED", "Second enrolment references the same site")
        pilot_graph = Graph().parse(output / "pilots/es-demo-01.ttl")
        g1 = Graph().parse(output / "participants/es-demo-aya-001.ttl")
        g2 = Graph().parse(output / "participants/es-demo-aya-002.ttl")
        union = pilot_graph + g1 + g2
        query = """
          PREFIX i: <http://maya-project.eu/icareonto/>
          SELECT ?person ?language WHERE {
            ?e i:participantEnrolmentForPerson ?person ; i:participantEnrolmentAtSite ?site .
            ?site i:pilotSiteHasLocale ?locale .
            ?locale i:localeCountryCode ?country . FILTER(STR(?country) = "ES")
            ?person i:personHasPreference ?p . ?p i:preferredLanguageTag ?language .
          }
        """
        actual = {(str(row.person), str(row.language)) for row in union.query(query)}
        check("SHARED-SITE-QUERY", actual == {(str(person), "es-ES"), (str(other), "en-GB")}, "Combined query returns two distinct participant language preferences at the Spanish site")
        check("NO-SITE-COPY", (site, RDF.type, ic.PilotSite) not in g1 and (site, RDF.type, ic.PilotSite) not in g2 and len(set(union.subjects(RDF.type, ic.PilotSite))) == 1, "Site is defined once and referenced by both participant graphs")
        check("CONTROLLED-VALUES", (URIRef(str(person) + "/preferences/detail_level"), ic.informationPreferenceHasDetailLevel, ic.BriefInformation) in g1 and any(g1.triples((None, ic.participantEnrolmentHasStatus, ic.ActiveEnrolmentStatus))), "Readable values map to existing ontology individuals")
        check("OPTIONAL-OMISSION", not any(g2.triples((None, RDF.type, ic.ConsentRecord))) and not any(g2.triples((other, ic.ageInYears, None))) and not any(g2.triples((None, RDF.type, ic.AYACancerSurvivorRole))), "Omitted age, consent and survivor role are not invented")
        check("SOURCE-TIME", any(g1.triples((None, ic.preferenceRecordedAt, None))) and any(g1.triples((None, ic.personAttributeHasSource, None))), "Preference/attribute provenance and times are represented")
        rows = [{str(key): str(value) for key, value in row.asdict().items()} for row in union.query((w.ROOT / "queries/enrolment-context.rq").read_text())]
        expected_rows = [
            {"participantId": "es-demo-aya-001", "siteName": "Fictional Spanish demonstration site", "siteLocale": "es-ES", "preferredLanguage": "es-ES", "status": str(ic.ActiveEnrolmentStatus)},
            {"participantId": "es-demo-aya-002", "siteName": "Fictional Spanish demonstration site", "siteLocale": "es-ES", "preferredLanguage": "en-GB", "status": str(ic.EnrolledStatus)}
        ]
        check("DOCUMENTED-QUERY", rows == expected_rows, "The supplied enrolment-context query returns the exact independently specified participant/site answers")
        age = next(g1.objects(person, ic.ageInYears))
        check("AGE-TYPE", age.datatype == XSD.decimal and age.toPython() == 27, "Age retains decimal datatype and the supplied numeric value")
        before = fingerprint()
        report = w.generate("participant", first, output)
        after = fingerprint()
        stable = all(before[name] == after[name] for name in before if name != "validation/generation-report.json" and name != "validation/shacl-report.ttl")
        check("REPEAT-IDENTITY", report["status"] == "UNCHANGED" and stable and len(set(union.subjects(RDF.type, ic.Person))) == 2, "Repeated input preserves managed seed bytes, graph identities and participant count")
        dataset = Dataset().parse(output / "dataset.trig", format="trig")
        named_ids = {str(graph.identifier) for graph in dataset.graphs() if len(graph)}
        check("NAMED-GRAPHS", named_ids == {base + "graphs/pilots/es-demo-01", base + "graphs/participants/es-demo-aya-001", base + "graphs/participants/es-demo-aya-002"}, "TriG preserves exactly three separate instance graphs")
        first_graph_iri = URIRef(base + "graphs/participants/es-demo-aya-001")
        check("TRIG-ROUNDTRIP", set(dataset.quads((None, None, None, first_graph_iri))) == {(s, p, o, first_graph_iri) for s, p, o in g1}, "Participant named graph survives RDF serialisation")
        for folder in (output, output / "pilots", output / "participants"):
            mapping = {e.attrib["name"]: (folder / e.attrib["uri"]).resolve() for e in ET.parse(folder / "catalog-v001.xml").getroot()}
            check("CATALOGUE-" + folder.name.upper(), all(path.is_file() for path in mapping.values()) and all(str(i) in mapping for g in (g1, g2, pilot_graph) for i in g.objects(None, w.OWL.imports)), "All catalogue targets and seed imports resolve locally")

        mutations = [
            ("MISSING-ID", lambda d: d.pop("participant_id"), "participant_id"),
            ("UNKNOWN-FIELD", lambda d: d.update(unknown_field="x"), "Additional properties"),
            ("BAD-STATUS", lambda d: d["enrolment"].update(status="invented"), "status"),
            ("MISSING-OFFSET", lambda d: d.update(recorded_at="2026-10-15T10:00:00"), "date-time"),
            ("BAD-DATE", lambda d: d["enrolment"].update(enrolled_at="2026-02-30T10:00:00Z"), "date-time"),
            ("FUTURE-ENROLMENT", lambda d: d["enrolment"].update(enrolled_at="2027-10-15T10:00:00Z"), "later than recorded_at"),
            ("PLACEHOLDER", lambda d: d.update(participant_id="<participant-id>"), "participant_id"),
            ("BAD-AGE", lambda d: d.update(age_years=-1), "age_years"),
            ("NULL-OPTIONAL", lambda d: d.update(age_years=None), "age_years"),
            ("UNKNOWN-SITE", lambda d: d.update(site_id="unknown"), "pilot must be generated"),
            ("WRONG-STUDY", lambda d: d.update(study_id="other-study"), "pair does not match"),
            ("UNKNOWN-PHASE", lambda d: d["enrolment"].update(phase_id="unknown"), "phase_id"),
            ("UNKNOWN-ARM", lambda d: d["enrolment"].update(arm_id="unknown"), "arm_id"),
            ("DUPLICATE-ATTRIBUTE", lambda d: d["attributes"].append(deepcopy(d["attributes"][0])), "Repeated record identifier"),
            ("CONSENT-INTERVAL", lambda d: d["consent"].update(valid_until="2026-10-14T10:00:00Z"), "later than valid_from")
        ]
        for identifier, mutation, message in mutations:
            changed = deepcopy(first)
            mutation(changed)
            rejected(identifier, "participant", changed, message)
        bad_pilot = deepcopy(pilot)
        bad_pilot["site"]["locale"]["time_zone"] = "Unknown/Zone"
        rejected("INVALID-ZONE", "pilot", bad_pilot, "unknown IANA time zone")
        bad_pilot = deepcopy(pilot)
        bad_pilot["site"]["locale"]["country_code"] = "IT"
        rejected("LOCALE-COUNTRY", "pilot", bad_pilot, "country suffix")
        bad_pilot = deepcopy(pilot)
        bad_pilot["study"]["phases"].append(deepcopy(bad_pilot["study"]["phases"][0]))
        rejected("DUPLICATE-PHASE", "pilot", bad_pilot, "Repeated record identifier")
        bad_pilot = deepcopy(pilot)
        bad_pilot["study"]["arms"] = [bad_pilot["study"]["arms"][1]]
        rejected("REMOVE-REFERENCED-ARM", "pilot", bad_pilot, "Explicit range mismatch", replace=True)
        conflicting = deepcopy(pilot)
        conflicting["site"]["id"] = "second-site"
        conflicting["site"]["name"] = "Fictional second site"
        conflicting["study"]["name"] = "A conflicting name for the same study ID"
        rejected("CONFLICTING-SHARED-STUDY", "pilot", conflicting, "Conflicting labels")
        participant_hashes = {p.name: w.digest(p.read_bytes()) for p in (output / "participants").glob("*.ttl")}
        changed_pilot = deepcopy(pilot)
        changed_pilot["site"]["name"] = "Corrected fictional Spanish site name"
        correction = w.generate("pilot", changed_pilot, output, replace_seed=True)
        check("PILOT-CORRECTION", correction["status"] == "REPLACED_SEED" and participant_hashes == {p.name: w.digest(p.read_bytes()) for p in (output / "participants").glob("*.ttl")}, "Site correction updates the shared seed without rewriting participant files")
        linked = Graph().parse(output / "pilots/es-demo-01.ttl") + g1 + g2
        new_rows = list(linked.query((w.ROOT / "queries/enrolment-context.rq").read_text()))
        check("SHARED-CORRECTION-QUERY", len(new_rows) == 2 and all(str(row.siteName) == "Corrected fictional Spanish site name" for row in new_rows), "Both participants see the corrected site information through the existing links")
        changed = deepcopy(first)
        changed["preferences"]["detail_level"] = "detailed"
        rejected("UNINTENTIONAL-REPLACEMENT", "participant", changed, "--replace-seed")
        old_hash = w.digest((output / "participants/es-demo-aya-001.ttl").read_bytes())
        report = w.generate("participant", changed, output, replace_seed=True)
        changed_graph = Graph().parse(output / "participants/es-demo-aya-001.ttl")
        check("EXPLICIT-CORRECTION", report["status"] == "REPLACED_SEED" and (URIRef(str(person) + "/preferences/detail_level"), ic.informationPreferenceHasDetailLevel, ic.DetailedInformation) in changed_graph and (output / f"history/participant/es-demo-aya-001/{old_hash}.ttl").is_file(), "Intentional preference correction keeps person identity and archives the previous seed")
        changed["enrolment"]["id"] = "different-enrolment"
        rejected("NO-SILENT-REENROLMENT", "participant", changed, "cannot replace enrolment identity", replace=True)
        minimal = {key: deepcopy(first[key]) for key in ("schema_version", "recorded_at", "source", "participant_id", "study_id", "site_id", "enrolment")}
        minimal["participant_id"] = "minimal-person"
        w.generate("participant", minimal, output)
        minimal_graph = Graph().parse(output / "participants/minimal-person.ttl")
        check("NO-PREFERENCE-DEFAULT", not any(minimal_graph.triples((None, ic.preferredLanguageTag, None))) and not any(minimal_graph.triples((None, ic.personHasPreference, None))), "Missing participant preferences remain unasserted despite the site's Spanish locale")
        pending = deepcopy(minimal)
        pending["participant_id"] = "pending-person"
        pending["consent"] = {"id": "pending", "status": "pending", "valid_from": pending["recorded_at"]}
        w.generate("participant", pending, output)
        pending_graph = Graph().parse(output / "participants/pending-person.ttl")
        check("PENDING-CONSENT", any(pending_graph.triples((None, ic.consentRecordHasStatus, ic.ConsentPending))) and not any(pending_graph.triples((None, ic.consentRecordGrantedBy, None))), "Pending consent does not assert that a grant decision was supplied")
        before = fingerprint()
        try:
            w.generate("participant", second, output, base="https://example.org/other/")
        except w.InputError as error:
            check("NAMESPACE-PROTECTION", "base differs" in str(error) and fingerprint() == before, "An existing deployment cannot silently switch its instance namespace")
        else:
            raise AssertionError("Namespace change accepted")
        schema, _ = w.schema_package(w.DEFAULT_SCHEMA)
        broken = Graph() + g1
        broken.remove((person, ic.personIdentifier, None))
        try:
            w.validate_graphs([pilot_graph, broken], schema)
        except w.InputError as error:
            check("SHACL-MISSING-IDENTIFIER", "SHACL validation failed" in str(error), "Graph-level missing required identifier is rejected independently of input validation")
        else:
            raise AssertionError("Broken graph accepted")
        broken = Graph() + pilot_graph
        broken.remove((site, RDF.type, ic.PilotSite))
        try:
            w.validate_graphs([broken, g1], schema)
        except w.InputError as error:
            check("EXPLICIT-TYPE-CHECK", "range mismatch" in str(error), "Missing explicit site type is rejected rather than inferred to repair the graph")
        else:
            raise AssertionError("Missing site type accepted")
        before = fingerprint()
        bad_path = Path(temp) / "bad.json"
        bad_path.write_text('{"schema_version":"1.0","schema_version":"1.0"}')
        command = subprocess.run([sys.executable, str(w.ROOT / "scripts/generate_kg.py"), "participant", "--input", str(bad_path), "--output", str(output)], text=True, capture_output=True)
        check("CLI-INVALID-JSON", command.returncode == 2 and "Duplicate JSON key" in command.stderr and before == fingerprint(), "CLI returns nonzero without publishing outputs for duplicate JSON keys")
        seed_path = output / "participants/es-demo-aya-001.ttl"
        seed_path.write_text(seed_path.read_text() + "\n# outside edit\n")
        rejected("EXTERNAL-EDIT", "participant", second, "edited outside the generator")

    report = {"status": "PASS", "checks": len(cases), "cases": cases, "scope": "Temporary fictional outputs; no modification of supplied examples, existing KG fixtures or ontology."}
    destination = w.ROOT / "reports"
    destination.mkdir(exist_ok=True)
    (destination / "workflow-checks.json").write_bytes(w.canonical(report))
    lines = ["# KG initialisation workflow checks", "", f"All **{len(cases)} checks passed**.", "", report["scope"], "", "| Check | Result | Purpose |", "|---|---|---|"]
    lines.extend(f"| {case['id']} | PASS | {case['detail']} |" for case in cases)
    (destination / "WORKFLOW_CHECKS.md").write_text("\n".join(lines) + "\n")
    print(json.dumps({"status": "PASS", "checks": len(cases)}, indent=2))


if __name__ == "__main__":
    main()
