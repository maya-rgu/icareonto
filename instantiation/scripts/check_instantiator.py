#!/usr/bin/env python3
"""Check fillable inputs, progressive enrichment and ontology-checked refreshes."""
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from rdflib import Graph, Literal, RDF, URIRef, XSD
import generate_kg as w


class InstantiatorChecks(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(prefix="maya-instantiator-")
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name) / "generated"
        self.pilot = w.read_json(w.ROOT / "examples/pilot-es-demo.json")
        self.person = w.read_json(w.ROOT / "examples/participant-es-001.json")
        self.node = URIRef(w.DEFAULT_BASE + "people/" + self.person["participant_id"])

    def run_record(self, kind, record):
        return w.instantiate(kind, record, self.output)

    def setup_pilot(self):
        return self.run_record("pilot", self.pilot)

    def graph(self):
        return Graph().parse(self.output / "participants" / (self.person["participant_id"] + ".ttl"))

    def hashes(self):
        return {str(p.relative_to(self.output)): w.digest(p.read_bytes()) for p in self.output.rglob("*") if p.is_file()}

    def reject(self, kind, record, text):
        before = self.hashes()
        with self.assertRaisesRegex(w.InputError, text):
            self.run_record(kind, record)
        self.assertEqual(self.hashes(), before)

    def template_person(self):
        record = w.read_json(w.ROOT / "templates/participant.json")
        for key in ("recorded_at", "source", "participant_id", "study_id", "site_id"):
            record[key] = self.person[key]
        for key in ("id", "enrolled_at", "status"):
            record["enrolment"][key] = self.person["enrolment"][key]
        return record

    def test_required_placeholders_prevent_publication(self):
        for kind in ("pilot", "participant"):
            self.reject(kind, w.read_json(w.ROOT / f"templates/{kind}.json"), "Input validation failed")

    def test_pilot_template_can_leave_phases_and_arms_unknown(self):
        record = w.read_json(w.ROOT / "templates/pilot.json")
        record.update(recorded_at=self.pilot["recorded_at"], source=self.pilot["source"])
        record["study"].update(id=self.pilot["study"]["id"], name=self.pilot["study"]["name"])
        record["site"] = deepcopy(self.pilot["site"])
        self.assertEqual(self.run_record("pilot", record)["status"], "CREATED")
        graph = Graph().parse(self.output / "pilots/es-demo-01.ttl")
        self.assertFalse(list(graph.triples((None, w.IC.pilotStudyHasPhase, None))))
        self.assertFalse(list(graph.triples((None, w.IC.pilotStudyHasArm, None))))

    def test_participant_template_leaves_unknown_information_unasserted(self):
        self.setup_pilot()
        self.run_record("participant", self.template_person())
        graph = self.graph()
        self.assertIn((self.node, w.IC.personIdentifier, Literal("es-demo-aya-001", datatype=XSD.string)), graph)
        for prop in (w.IC.personHasPreference, w.IC.ageInYears, w.IC.personHasAttribute):
            self.assertFalse(list(graph.triples((self.node, prop, None))))
        self.assertFalse(list(graph.subjects(RDF.type, w.IC.ConsentRecord)))
        self.assertFalse(any(isinstance(value, Literal) and "<" in str(value) for value in graph.objects()))

    def test_participant_requires_a_registered_pilot(self):
        self.reject("participant", self.template_person(), "pilot must be generated")

    def test_wrong_study_site_pair_is_rejected(self):
        self.setup_pilot()
        record = self.template_person(); record["study_id"] = "other-study"
        self.reject("participant", record, "pair does not match")

    def test_progressive_enrichment_preserves_identity_and_archives_previous_graph(self):
        self.setup_pilot(); record = self.template_person()
        self.run_record("participant", record)
        old_path = self.output / "participants/es-demo-aya-001.ttl"
        previous = old_path.read_bytes()
        record["preferences"]["language_tag"] = "en-GB"
        record["preferences"]["detail_level"] = "detailed"
        record["age_years"] = 27
        record["recorded_at"] = "2026-11-04T10:00:00Z"
        self.assertEqual(self.run_record("participant", record)["status"], "REPLACED_SEED")
        graph = self.graph()
        self.assertEqual(set(graph.subjects(RDF.type, w.IC.Person)), {self.node})
        age = next(graph.objects(self.node, w.IC.ageInYears))
        self.assertEqual(age.datatype, XSD.decimal)
        self.assertEqual(age.toPython(), 27)
        self.assertEqual({str(v) for v in graph.objects(None, w.IC.preferredLanguageTag)}, {"en-GB"})
        self.assertEqual(set(graph.objects(None, w.IC.informationPreferenceHasDetailLevel)), {w.IC.DetailedInformation})
        self.assertEqual((self.output / f"history/participant/es-demo-aya-001/{w.digest(previous)}.ttl").read_bytes(), previous)

    def test_unchanged_input_keeps_seed_bytes(self):
        self.setup_pilot(); self.run_record("participant", self.person)
        path = self.output / "participants/es-demo-aya-001.ttl"; before = path.read_bytes()
        self.assertEqual(self.run_record("participant", self.person)["status"], "UNCHANGED")
        self.assertEqual(path.read_bytes(), before)

    def test_snapshot_omission_removes_old_optional_assertions(self):
        self.setup_pilot(); self.run_record("participant", self.person)
        self.run_record("participant", self.template_person())
        self.assertFalse(list(self.graph().triples((self.node, w.IC.personHasPreference, None))))
        self.assertFalse(list(self.graph().triples((self.node, w.IC.ageInYears, None))))

    def test_optional_placeholder_is_not_published(self):
        self.setup_pilot(); record = self.template_person()
        record["preferences"]["language_tag"] = "<preferred language when known>"
        self.run_record("participant", record)
        self.assertFalse(list(self.graph().objects(None, w.IC.preferredLanguageTag)))

    def test_filled_invalid_optional_value_is_rejected(self):
        self.setup_pilot(); record = self.template_person()
        record["preferences"]["detail_level"] = "invented-level"
        self.reject("participant", record, "detail_level")

    def test_unknown_field_is_rejected_even_when_null(self):
        self.setup_pilot(); record = self.template_person(); record["made_up_field"] = None
        self.reject("participant", record, "Additional properties")

    def test_incomplete_supplied_consent_record_is_rejected(self):
        self.setup_pilot(); record = self.template_person()
        record["consent"] = {"id": "consent-1", "status": "granted", "valid_from": None}
        self.reject("participant", record, "valid_from")

    def test_participant_cannot_be_silently_reassigned(self):
        self.setup_pilot(); self.run_record("participant", self.person)
        site = deepcopy(self.pilot); site["site"]["id"] = "second-site"
        self.run_record("pilot", site)
        record = deepcopy(self.person); record["site_id"] = "second-site"
        self.reject("participant", record, "cannot replace enrolment identity")

    def test_pilot_refresh_updates_shared_context_without_rewriting_participants(self):
        self.setup_pilot(); self.run_record("participant", self.person)
        before = (self.output / "participants/es-demo-aya-001.ttl").read_bytes()
        record = deepcopy(self.pilot); record["site"]["name"] = "Updated demonstration site"
        self.assertEqual(self.run_record("pilot", record)["status"], "REPLACED_SEED")
        self.assertEqual((self.output / "participants/es-demo-aya-001.ttl").read_bytes(), before)
        graph = self.graph() + Graph().parse(self.output / "pilots/es-demo-01.ttl")
        rows = list(graph.query((w.ROOT / "queries/enrolment-context.rq").read_text()))
        self.assertEqual({str(row.siteName) for row in rows}, {"Updated demonstration site"})

    def test_pilot_refresh_cannot_remove_a_referenced_arm(self):
        self.setup_pilot(); self.run_record("participant", self.person)
        record = deepcopy(self.pilot); record["study"]["arms"] = None
        self.reject("pilot", record, "range mismatch")

    def test_refresh_rejects_a_property_absent_from_the_loaded_ontology(self):
        self.setup_pilot()
        schema, paths = w.schema_package(w.DEFAULT_SCHEMA)
        schema.remove((w.IC.personIdentifier, None, None))
        with patch.object(w, "schema_package", return_value=(schema, paths)):
            self.reject("participant", self.template_person(), "Undeclared predicate")

    def test_refresh_rejects_a_controlled_value_with_an_incompatible_ontology_type(self):
        self.setup_pilot()
        schema, paths = w.schema_package(w.DEFAULT_SCHEMA)
        schema.remove((w.IC.BriefInformation, RDF.type, w.IC.InformationDetailLevelValue))
        # Remove all category assertions, leaving the named individual declared.
        schema.remove((w.IC.BriefInformation, RDF.type, None))
        schema.add((w.IC.BriefInformation, RDF.type, w.OWL.NamedIndividual))
        with patch.object(w, "schema_package", return_value=(schema, paths)):
            self.reject("participant", self.person, "range mismatch")

    def test_named_command_accepts_the_same_file_for_creation_and_refresh(self):
        self.setup_pilot(); path = Path(self.temp.name) / "participant.json"
        record = self.template_person(); path.write_bytes(w.canonical(record))
        command = [sys.executable, str(w.ROOT / "kg-instantiator.py"), "participant", "--input", str(path), "--output", str(self.output)]
        first = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(json.loads(first.stdout)["status"], "CREATED")
        record["preferences"]["language_tag"] = "es-ES"; path.write_bytes(w.canonical(record))
        second = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(json.loads(second.stdout)["status"], "REPLACED_SEED")
        self.assertEqual({str(v) for v in self.graph().objects(None, w.IC.preferredLanguageTag)}, {"es-ES"})


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(InstantiatorChecks)
    names = [test.id().split(".")[-1] for test in suite]
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    failed = {test.id().split(".")[-1] for test, _ in result.failures + result.errors}
    cases = [{"name": name, "status": "FAIL" if name in failed else "PASS"} for name in names] if result.testsRun else []
    report = {"run_date": datetime.now(timezone.utc).date().isoformat(), "status": "PASS" if result.wasSuccessful() else "FAIL",
              "checks": result.testsRun, "failures": len(result.failures), "errors": len(result.errors), "cases": cases,
              "scope": "Fictional JSON inputs and temporary outputs; existing delivered graphs and the ontology are unchanged."}
    folder = w.ROOT / "reports"; folder.mkdir(exist_ok=True)
    (folder / "instantiator-checks.json").write_bytes(w.canonical(report))
    (folder / "INSTANTIATOR_CHECKS.md").write_text(
        "# KG Instantiator checks\n\n" + f"{result.testsRun} checks; {len(result.failures)} failures; {len(result.errors)} errors. Result: **{report['status']}**.\n\n" + report["scope"] +
        "\n\nRepeat: `python instantiation/scripts/check_instantiator.py`\n\n| Check | Result |\n|---|---|\n" +
        "".join(f"| {case['name'].removeprefix('test_').replace('_', ' ')} | {case['status']} |\n" for case in cases))
    print(json.dumps({k:v for k,v in report.items() if k != "cases"}, indent=2))
    raise SystemExit(0 if result.wasSuccessful() else 1)
