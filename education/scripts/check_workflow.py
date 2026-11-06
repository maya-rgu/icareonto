#!/usr/bin/env python3
"""Exercise publication, withdrawal, identity, matching and failure controls.

Tests use temporary output directories and a fixed reviewed-metadata fixture.
The real workbook is read only; expected resource IDs are authored constants.
"""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import DCTERMS
import education_resources as e

EXPECTED = {f"MAYA-EDU-{n:04}" for n in [4, 5, 7, 8, 9, 10, 11, 12, 13, 17, 18, 19, 20, 21, 23, 30]}
FIXTURE = e.ROOT / "tests/fixtures/reviewed-rows.json"


class WorkflowChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema, _, cls.schema_hash = e.load_schema(e.REPO / "serialisation")
        cls.vocab = e.Vocabulary(cls.schema)
        fixture = e.read_json(FIXTURE)
        cls.raw, cls.epoch = fixture["records"], fixture["epoch_1904"]
        cls.headers = fixture["headers"]
        cls.records, cls.excluded, cls.audit = e.prepare_records(cls.raw, cls.vocab, e.DEFAULT_BASE, cls.epoch)
        cls.request = e.read_json(e.ROOT / "examples/spanish-cardiovascular.json")

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="maya-education-check-")
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name) / "generated"

    def prepare(self, rows):
        return e.prepare_records(rows, self.vocab, e.DEFAULT_BASE, self.epoch)

    def publish(self, rows=None, **kwargs):
        # Hold the reviewed collection fixed while testing additions and failures.
        with patch.object(e, "worksheet_records", return_value=(deepcopy(self.raw if rows is None else rows), self.epoch)):
            return e.build_release(output=self.output, **kwargs)

    def fixture_workbook(self):
        # Reconstruct cell positions to exercise header discovery independently
        # of future row additions or column moves in the live curation workbook.
        def column(index):
            value = ""
            while index:
                index, digit = divmod(index - 1, 26)
                value = chr(65 + digit) + value
            return value
        columns = {column(i): name for i, name in enumerate(self.headers, 1)}
        rows = [{"_row": 5, **columns}]
        rows.extend({"_row": row["_row"], **{col: row.get(name, "") for col, name in columns.items()}} for row in self.raw)
        return {"Release resources": rows}

    def catalogue(self):
        return {"records": deepcopy(self.records), "ontology_sha256": self.schema_hash, "release_id": "test"}

    def ids(self, request=None, catalogue=None):
        result = e.select_resources(request or self.request, catalogue or self.catalogue())
        return [r["id"] for r in result["matches"]]

    def test_exact_initial_resource_set(self):
        self.assertEqual({r["id"] for r in self.records}, EXPECTED)
        self.assertEqual([r["id"] for r in self.excluded], ["MAYA-EDU-0014"])

    def test_approved_and_complete_are_both_required(self):
        rows = deepcopy(self.raw)
        for i, (status, complete) in enumerate([("Approved", "To complete"), ("On hold", "Complete"), ("Not reviewed", "Complete")], 100):
            row = deepcopy(rows[0]); row.update({"Resource ID": f"MAYA-EDU-{i:04}", "Curation status": status, "Completion status": complete})
            rows.append(row)
        self.assertEqual({r["id"] for r in self.prepare(rows)[0]}, EXPECTED)

    def test_new_approved_id_is_automatically_published(self):
        self.publish()
        rows = deepcopy(self.raw)
        row = deepcopy(rows[0]); row.update({"Resource ID": "MAYA-EDU-0100", "Resource title": "Additional reviewed resource", "_row": 301})
        rows.insert(0, row)
        report = self.publish(rows)
        self.assertEqual(report["added"], ["MAYA-EDU-0100"])
        self.assertEqual(len(e.load_release(self.output)["records"]), 17)
        self.assertIn("MAYA-EDU-0100", {r["id"] for r in e.load_release(self.output)["records"]})
        template = next(t for t in e.load_release(self.output)["activity_templates"] if t["id"] == "EDU-CV-FOLLOWUP")
        self.assertIn("MAYA-EDU-0100", template["candidate_resource_ids"])

    def test_reordering_keeps_resource_identities(self):
        self.assertEqual({r["id"]: r["iri"] for r in self.prepare(list(reversed(self.raw)))[0]}, {r["id"]: r["iri"] for r in self.records})

    def test_columns_are_located_by_header(self):
        workbook = self.fixture_workbook()
        rows = workbook["Release resources"]
        for row in rows:
            row["A"], row["Z"] = row.get("Z", ""), row.get("A", "")
        with patch.object(e, "read_xlsx", return_value=workbook):
            reordered, _ = e.worksheet_records(e.DEFAULT_WORKBOOK, "Release resources")
        self.assertEqual({r["id"] for r in self.prepare(reordered)[0]}, EXPECTED)

    def test_configurable_sheet_and_shifted_header_row(self):
        workbook = self.fixture_workbook()
        rows = workbook.pop("Release resources")
        for row in rows:
            row["_row"] += 3
        workbook["Reviewed collection"] = rows
        with patch.object(e, "read_xlsx", return_value=workbook):
            found, _ = e.worksheet_records(e.DEFAULT_WORKBOOK, "Reviewed collection")
        self.assertEqual({r["id"] for r in self.prepare(found)[0]}, EXPECTED)

    def test_missing_column_fails(self):
        workbook = self.fixture_workbook()
        header = next(r for r in workbook["Release resources"] if r.get("A") == "Resource ID")
        del header[next(k for k, v in header.items() if v == "Completion status")]
        with patch.object(e, "read_xlsx", return_value=workbook), self.assertRaises(e.InputError):
            e.worksheet_records(e.DEFAULT_WORKBOOK, "Release resources")

    def test_duplicate_id_fails_without_replacing_current_release(self):
        self.publish(); pointer = (self.output / "current.json").read_bytes()
        with self.assertRaises(e.InputError):
            self.publish(self.raw + [deepcopy(self.raw[0])])
        self.assertEqual((self.output / "current.json").read_bytes(), pointer)

    def test_failed_initial_write_can_be_retried(self):
        write = e.atomic_write
        def fail(path, content):
            if Path(path).name == "catalogue.ttl":
                raise OSError("Simulated interrupted export")
            return write(path, content)
        with patch.object(e, "atomic_write", side_effect=fail), self.assertRaises(OSError):
            self.publish()
        self.assertFalse((self.output / "current.json").exists())
        self.assertFalse(list(self.output.parent.glob(".maya-education-pending-*")))
        self.assertEqual(self.publish()["included_count"], 16)

    def test_withdrawal_removes_current_but_preserves_history(self):
        first = self.publish()
        rows = deepcopy(self.raw); rows[0]["Curation status"] = "On hold"
        second = self.publish(rows)
        self.assertEqual(second["removed"], ["MAYA-EDU-0004"])
        self.assertNotIn("MAYA-EDU-0004", {r["id"] for r in e.load_release(self.output)["records"]})
        history = e.read_json(Path(first["release_directory"]) / "catalogue.json")
        self.assertIn("MAYA-EDU-0004", {r["id"] for r in history["records"]})

    def test_update_preserves_iri_and_removes_old_url(self):
        self.publish()
        rows = deepcopy(self.raw); rows[0]["Resource URL"] = "https://example.org/reviewed-replacement"
        report = self.publish(rows)
        self.assertEqual(report["updated"], ["MAYA-EDU-0004"])
        record = next(r for r in e.load_release(self.output)["records"] if r["id"] == "MAYA-EDU-0004")
        self.assertEqual(record["iri"], e.DEFAULT_BASE + "resources/MAYA-EDU-0004")
        g = Graph().parse(Path(report["release_directory"]) / "catalogue.ttl")
        self.assertEqual(set(g.objects(URIRef(record["iri"]), DCTERMS.source)), {URIRef("https://example.org/reviewed-replacement")})

    def test_repeated_build_is_unchanged(self):
        first = self.publish(); pointer = (self.output / "current.json").read_bytes()
        second = self.publish()
        self.assertEqual(second["result"], "UNCHANGED")
        self.assertEqual(second["release_id"], first["release_id"])
        self.assertEqual((self.output / "current.json").read_bytes(), pointer)

    def test_unknown_need_is_not_fuzzily_mapped(self):
        rows = deepcopy(self.raw); rows[0]["Health-literacy needs addressed"] = "Needs a better explanation"
        with self.assertRaises(e.InputError): self.prepare(rows)

    def test_wrong_vocabulary_category_is_rejected(self):
        rows = deepcopy(self.raw); rows[0]["Health-literacy needs addressed"] = "Nutrition"
        with self.assertRaises(e.InputError): self.prepare(rows)

    def test_unknown_stage_is_rejected(self):
        rows = deepcopy(self.raw); rows[0]["Cancer journey stage(s)"] = "Unreviewed stage"
        with self.assertRaises(e.InputError): self.prepare(rows)

    def test_empty_required_annotation_is_rejected(self):
        rows = deepcopy(self.raw); rows[0]["Ontology topic(s)"] = ""
        with self.assertRaises(e.InputError): self.prepare(rows)

    def test_language_claims_need_verified_values(self):
        rows = deepcopy(self.raw); rows[0]["Language(s)"] = "134 Languages"
        with self.assertRaises(e.InputError): self.prepare(rows)

    def test_multiple_values_split_on_semicolons_not_commas(self):
        self.assertEqual(e.split_values("Digital health, privacy and trust; Nutrition"), ["Digital health, privacy and trust", "Nutrition"])
        self.assertEqual(self.vocab.resolve("Digital health, privacy and trust", "ResourceTopic"), str(e.IC.DigitalHealthPrivacyAndTrust))

    def test_review_dates_preserve_excel_epochs(self):
        self.assertEqual(e.review_date("46329"), "2026-11-03")
        self.assertEqual(e.review_date("1", True), "1904-01-02")
        self.assertEqual(e.review_date("2026-11-03"), "2026-11-03")
        with self.assertRaises(e.InputError): e.review_date("60")

    def test_unresolved_permission_is_not_released(self):
        rows = deepcopy(self.raw); rows[0]["Permitted MAYA use"] = "Permission Required Before Use"
        with self.assertRaises(e.InputError): self.prepare(rows)

    def test_email_like_url_is_rejected(self):
        rows = deepcopy(self.raw); rows[0]["Resource URL"] = "http://info@example.org"
        with self.assertRaises(e.InputError): self.prepare(rows)

    def test_empty_release_requires_explicit_flag(self):
        rows = deepcopy(self.raw)
        for row in rows: row["Curation status"] = "On hold"
        with self.assertRaises(e.InputError): self.publish(rows)
        self.publish(rows, allow_empty=True)
        self.assertEqual(e.load_release(self.output)["records"], [])

    def test_namespace_cannot_change_in_existing_deployment(self):
        self.publish()
        with self.assertRaises(e.InputError): self.publish(base="https://example.org/different/")

    def test_custom_namespace_is_preserved(self):
        self.publish(base="https://example.org/reviewed-education/")
        self.assertTrue(all(r["iri"].startswith("https://example.org/reviewed-education/resources/") for r in e.load_release(self.output)["records"]))

    def test_tampered_managed_file_is_rejected(self):
        report = self.publish()
        path = Path(report["release_directory"]) / "catalogue.ttl"
        path.write_text(path.read_text() + "\n# manual edit\n")
        with self.assertRaises(e.InputError): e.load_release(self.output)

    def test_existing_old_release_is_verified_before_reactivation(self):
        first = self.publish()
        rows = deepcopy(self.raw); rows[0]["Curation status"] = "On hold"
        self.publish(rows); pointer = (self.output / "current.json").read_bytes()
        path = Path(first["release_directory"]) / "catalogue.ttl"
        path.write_text(path.read_text() + "\n# manual edit\n")
        with self.assertRaises(e.InputError): self.publish()
        self.assertEqual((self.output / "current.json").read_bytes(), pointer)

    def test_spanish_cardiovascular_expected_match(self):
        self.assertEqual(self.ids(), ["MAYA-EDU-0004"])

    def test_preferred_complexity_is_not_required_complexity(self):
        result = e.select_resources(self.request, self.catalogue())
        self.assertFalse(result["matches"][0]["preference_matches"]["complexities"])
        self.assertEqual(result["match_count"], 1)

    def test_language_and_topic_filters_have_no_automatic_fallback(self):
        request = deepcopy(self.request); request["language"] = "pl"
        result = e.select_resources(request, self.catalogue())
        self.assertEqual(result["status"], "NO_SUITABLE_RESOURCE")
        self.assertEqual(result["unmatched_needs"], [str(e.IC.InformationComprehensionSupportNeed)])

    def test_audience_excludes_caregiver_only_resources(self):
        request = deepcopy(self.request)
        request.update(audience="CaregiverAudience", language="es", topics=["MentalHealthAndEmotionalWellbeing"], needs=["SocialSupportNeed"])
        self.assertEqual(self.ids(request), ["MAYA-EDU-0012"])

    def test_registration_is_visible_and_can_be_excluded(self):
        request = e.read_json(e.ROOT / "examples/english-nutrition.json")
        result = e.select_resources(request, self.catalogue())
        self.assertEqual([r["id"] for r in result["matches"]], ["MAYA-EDU-0023"])
        self.assertTrue(result["matches"][0]["requires_registration_or_access_check"])
        request["include_registration_required"] = False
        self.assertEqual(self.ids(request), [])

    def test_required_accessibility_is_not_inferred(self):
        request = deepcopy(self.request); request["required_accessibility"] = ["ScreenReaderCompatible"]
        self.assertEqual(self.ids(request), [])

    def test_journey_stage_excludes_nonmatching_resource(self):
        request = e.read_json(e.ROOT / "examples/english-nutrition.json"); request["journey_stage"] = "Before treatment"
        self.assertEqual(self.ids(request), [])

    def test_invalid_request_and_unknown_term_fail(self):
        request = deepcopy(self.request); request["unexpected"] = True
        with self.assertRaises(e.InputError): self.ids(request)
        request = deepcopy(self.request); request["topics"] = ["UnknownTopic"]
        with self.assertRaises(e.InputError): self.ids(request)

    def test_stale_ontology_is_rejected(self):
        catalogue = self.catalogue(); catalogue["ontology_sha256"] = "outdated"
        with self.assertRaises(e.InputError): self.ids(catalogue=catalogue)

    def test_shacl_rejects_missing_resource_url(self):
        g = e.catalogue_graph(self.records, e.DEFAULT_BASE)
        g.remove((URIRef(self.records[0]["iri"]), DCTERMS.source, None))
        with self.assertRaises(e.InputError): e.validate_graph(g, self.schema)

    def test_sparql_returns_independent_expected_answer(self):
        g = e.catalogue_graph(self.records, e.DEFAULT_BASE)
        rows = g.query((e.ROOT / "queries/spanish-cardiovascular.rq").read_text())
        self.assertEqual([str(row.id) for row in rows], ["MAYA-EDU-0004"])

    def test_demo_links_real_resource_to_synthetic_draft_intervention(self):
        self.publish()
        report = e.demonstration(self.request, "EDU-CV-FOLLOWUP", self.output)
        self.assertEqual(report["selected_resource_ids"], ["MAYA-EDU-0004"])
        self.assertEqual(report["activity_status"], "Draft")
        g = Graph().parse(self.output / "demo/participant-education.ttl")
        self.assertEqual(set(g.objects(None, e.IC.healthLiteracyInterventionUsesResource)), {URIRef(e.DEFAULT_BASE + "resources/MAYA-EDU-0004")})
        self.assertFalse(list(g.triples((None, e.IC.activityRealisedBy, None))))

    def test_demo_does_not_publish_real_participant_data(self):
        self.publish(); request = deepcopy(self.request); request["synthetic"] = False
        with self.assertRaises(e.InputError): e.demonstration(request, "EDU-CV-FOLLOWUP", self.output)
        self.assertFalse((self.output / "demo").exists())

    def test_activity_does_not_infer_an_unidentified_need(self):
        self.publish(); request = deepcopy(self.request); request["needs"] = ["SelfManagementSupportNeed"]
        with self.assertRaises(e.InputError): e.demonstration(request, "EDU-CV-FOLLOWUP", self.output)
        self.assertFalse((self.output / "demo").exists())


if __name__ == "__main__":
    original_hash = hashlib.sha256(e.DEFAULT_WORKBOOK.read_bytes()).hexdigest()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(WorkflowChecks)
    test_names = [test.id().split(".")[-1] for test in suite]
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    assert hashlib.sha256(e.DEFAULT_WORKBOOK.read_bytes()).hexdigest() == original_hash, "Source workbook was modified"
    failed = {test.id().split(".")[-1] for test, _ in result.failures}
    errored = {test.id().split(".")[-1] for test, _ in result.errors}
    skipped = {test.id().split(".")[-1] for test, _ in result.skipped}
    test_cases = [{"name": name, "status": "FAIL" if name in failed else "ERROR" if name in errored else "SKIP" if name in skipped else "PASS"} for name in test_names] if result.testsRun else []
    report = {"run_date": datetime.now(timezone.utc).date().isoformat(), "checks_run": result.testsRun,
              "failures": len(result.failures), "errors": len(result.errors), "source_workbook_unchanged": True,
              "fixture": str(FIXTURE.relative_to(e.REPO)), "fixture_sha256": e.digest(FIXTURE.read_bytes()), "test_cases": test_cases,
              "result": "PASS" if result.wasSuccessful() else "FAIL"}
    folder = e.ROOT / "reports"; folder.mkdir(exist_ok=True)
    (folder / "workflow-checks.json").write_bytes(e.canonical(report))
    (folder / "WORKFLOW_CHECKS.md").write_text(
        "# Educational resource workflow checks\n\n" + f"{report['checks_run']} checks; {report['failures']} failures; {report['errors']} errors. Result: **{report['result']}**.\n\n"
        "Tests exercise new approved IDs, status gating, withdrawal, stable IRIs, repeat processing, header and sheet independence, vocabulary validation, dates, permissions, release integrity, participant matching and a synthetic educational activity.\n\n"
        "Expected matches are authored resource IDs. The fixed reviewed-metadata fixture and temporary output directories keep these regression checks independent of later additions to the live collection. The source workbook is unchanged. These are technical checks, not evaluation of educational outcomes or clinical suitability.\n\n"
        "Repeat from the project root: `python education/scripts/check_workflow.py` (with dependencies from `education/requirements.txt`).\n\n"
        "| Test | Result |\n|---|---|\n" + "".join(f"| {case['name'].removeprefix('test_').replace('_', ' ')} | {case['status']} |\n" for case in test_cases))
    print(json.dumps({k: v for k, v in report.items() if k != "test_cases"}, indent=2))
    raise SystemExit(0 if result.wasSuccessful() else 1)
