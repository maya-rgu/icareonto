#!/usr/bin/env python3
"""Regression checks of clinical sections, linked updates and JSON-LD exports."""
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import unittest

from rdflib import Dataset, Graph, Literal, RDF, URIRef, XSD
from rdflib.compare import isomorphic
import generate_kg as w
import section_records as s


class SectionChecks(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(prefix="maya-section-check-")
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name) / "generated"
        self.pilot = w.read_json(w.ROOT / "examples/pilot-es-demo.json")
        self.person = w.read_json(w.ROOT / "examples/participant-es-full.json")
        self.schema, _ = w.schema_package(w.DEFAULT_SCHEMA)
        w.instantiate("pilot", self.pilot, self.output)
        self.root = w.DEFAULT_BASE + "people/es-demo-aya-full"

    def run_record(self, record=None):
        return w.instantiate("participant", record if record is not None else self.person, self.output)

    def graph(self):
        return Graph().parse(self.output / "participants/es-demo-aya-full.ttl")

    def node(self, name):
        return URIRef(self.root + "/records/" + name)

    def record(self, name, data=None):
        return next(r for group in (data or self.person)["sections"].values() for r in group.get("records", []) if r["id"] == name)

    def hashes(self):
        return {str(p.relative_to(self.output)): w.digest(p.read_bytes()) for p in self.output.rglob("*") if p.is_file()}

    def reject(self, data, text):
        before = self.hashes()
        with self.assertRaisesRegex(w.InputError, text):
            self.run_record(data)
        self.assertEqual(before, self.hashes())

    def test_clinical_profile_is_queryable_from_the_participant(self):
        self.run_record()
        rows = list(self.graph().query("""
          PREFIX i: <http://maya-project.eu/icareonto/>
          SELECT ?name WHERE { ?person i:personIdentifier ?identifier ;
            i:personHasClinicalProfile/i:clinicalProfileIncludesRecord ?record .
            FILTER(STR(?identifier) = "es-demo-aya-full")
            ?record i:conditionRecordRecordsCondition/i:conditionName ?name }
        """))
        self.assertEqual([str(row.name) for row in rows], ["Hypertension"])

    def test_cancer_diagnosis_and_exposure_remain_connected(self):
        self.run_record()
        rows = list(self.graph().query("""
          PREFIX i: <http://maya-project.eu/icareonto/>
          SELECT ?diagnosis ?dose ?unit WHERE {
            ?p i:hasCancerDiagnosis ?d ; i:personHasCancerTreatmentHistory/i:cancerTreatmentHistoryHasRecord ?r .
            ?d i:cancerTypeName ?diagnosis . ?r i:treatmentRecordTreatsDiagnosis ?d ; i:treatmentRecordIndicatesExposure ?e .
            ?e i:cumulativeDrugDose ?dose ; i:cumulativeDrugDoseUnit ?unit }
        """))
        self.assertEqual([(str(r.diagnosis), r.dose.toPython(), str(r.unit)) for r in rows], [("Fictional Hodgkin lymphoma history", 200, "mg/m2")])

    def test_risk_input_connects_to_exposure_and_measurement(self):
        self.run_record()
        rows = list(self.graph().query("""
          PREFIX i: <http://maya-project.eu/icareonto/>
          SELECT ?score ?category ?value WHERE {
            ?p i:personHasRiskProfile ?profile . ?profile i:riskProfileIncludesRiskEstimate ?estimate .
            ?estimate i:riskScore ?score ; i:riskEstimateHasCategory ?category .
            ?execution i:modelExecutionGeneratesRiskProfile ?profile ; i:modelExecutionUsesInput ?input .
            ?input i:modelInputIncludesExposure ?exposure ; i:modelInputDerivedFromObservation ?observation .
            ?exposure a i:AnthracyclineExposure .
            ?observation i:observationHasQuantityValue/i:quantityNumericValue ?value }
        """))
        self.assertEqual([(float(r.score), str(r.category), float(r.value)) for r in rows], [(0.12, str(w.IC.ModerateRisk), 126.0)])

    def test_published_query_files_return_the_specified_answers(self):
        self.run_record(); graph = self.graph()
        def query(name):
            return list(graph.query((w.ROOT / "queries" / name).read_text()))
        self.assertEqual([(str(r.conditionName), str(r.status)) for r in query("clinical-conditions.rq")], [("Hypertension", str(w.IC.ActiveClinicalStatus))])
        self.assertEqual([(str(r.cancer), float(r.dose), str(r.unit)) for r in query("treatment-exposures.rq")], [("Fictional Hodgkin lymphoma history", 200.0, "mg/m2")])
        self.assertEqual([(float(r.score), str(r.category)) for r in query("risk-input-context.rq")], [(0.12, str(w.IC.ModerateRisk))])
        self.assertEqual([(str(r.prescriptionId), float(r.prescribedMinutes), float(r.performedMinutes)) for r in query("prescribed-and-performed-exercise.rq")], [("fictional-prescription-001", 30.0, 20.0)])

    def test_query_files_exclude_another_participants_similar_records(self):
        self.run_record(); other = deepcopy(self.person); other["participant_id"] = "another-person"
        self.record("hypertension", other)["properties"]["conditionName"] = "Other participant condition"
        w.instantiate("participant", other, self.output)
        graph = self.graph() + Graph().parse(self.output / "participants/another-person.ttl")
        query = (w.ROOT / "queries/clinical-conditions.rq").read_text()
        self.assertEqual([str(r.conditionName) for r in graph.query(query)], ["Hypertension"])
        self.assertEqual(list(graph.query(query.replace('"es-demo-aya-full"', '"unknown-person"'))), [])

    def test_prescribed_and_performed_exercise_have_separate_expected_values(self):
        self.run_record()
        rows = list(self.graph().query("""
          PREFIX i: <http://maya-project.eu/icareonto/>
          SELECT ?prescribed ?performed WHERE {
            ?care i:carePlanIntendedFor ?person ; i:carePlanIncludesActivity ?intervention .
            ?intervention i:exerciseInterventionHasPrescription ?prescription ; i:activityRealisedBy ?actual .
            ?prescription i:exercisePrescriptionIncludesActivity/i:durationMinutes ?prescribed .
            ?actual i:performedSessionRealises/i:plannedSessionFollowsPrescription ?prescription ;
              i:performedSessionIncludesActivity/i:durationMinutes ?performed }
        """))
        self.assertEqual([(float(r.prescribed), float(r.performed)) for r in rows], [(30.0, 20.0)])

    def test_performed_update_does_not_rewrite_prescription(self):
        self.run_record(); record = deepcopy(self.person)
        self.record("performed-walking", record)["properties"]["durationMinutes"] = 25
        record["recorded_at"] = "2026-11-05T10:00:00Z"
        self.assertEqual(self.run_record(record)["status"], "REPLACED_SEED")
        graph = self.graph()
        self.assertEqual(float(next(graph.objects(self.node("prescribed-walking"), w.IC.durationMinutes))), 30)
        self.assertEqual(float(next(graph.objects(self.node("performed-walking"), w.IC.durationMinutes))), 25)
        self.assertEqual(set(graph.objects(self.node("performed-session"), w.IC.performedSessionRealises)), {self.node("planned-session")})

    def test_new_observation_is_added_without_losing_history(self):
        self.run_record(); record = deepcopy(self.person)
        record["sections"]["measurements"]["records"].extend([
            {"id": "bp-result-2", "type": "ObservationResult", "properties": {"observationHasQuantityValue": {"ref": "bp-quantity-2"}}},
            {"id": "bp-quantity-2", "type": "QuantityValue", "properties": {"quantityNumericValue": 124, "quantityValueHasUnit": {"ref": "mmhg"}}}
        ])
        self.record("bp-event", record)["properties"]["measurementEventHasOutput"] = [{"ref": "bp-result"}, {"ref": "bp-result-2"}]
        self.run_record(record)
        self.assertEqual({float(v) for v in self.graph().objects(None, w.IC.quantityNumericValue)}, {124, 126})

    def test_forward_and_cross_section_references_are_resolved(self):
        self.run_record(); graph = self.graph()
        self.assertIn((self.node("model-input"), w.IC.modelInputIncludesExposure, self.node("anthracycline-exposure")), graph)
        self.assertIn((self.node("exercise-intervention"), w.IC.exerciseInterventionHasPrescription, self.node("exercise-prescription")), graph)

    def test_duplicate_record_ids_across_groups_are_rejected(self):
        record = deepcopy(self.person)
        record["sections"]["exercise"]["records"].append(deepcopy(self.record("clinical-profile")))
        self.reject(record, "Duplicate section record ID")

    def test_unresolved_reference_does_not_replace_existing_graph(self):
        self.run_record(); record = deepcopy(self.person)
        self.record("clinical-profile", record)["properties"]["clinicalProfileIncludesRecord"] = {"ref": "missing-record"}
        self.reject(record, "Unresolved section reference")

    def test_wrong_reference_type_is_rejected(self):
        record = deepcopy(self.person)
        self.record("clinical-profile", record)["properties"]["clinicalProfileIncludesRecord"] = {"ref": "mmhg"}
        self.reject(record, "range mismatch")

    def test_property_on_wrong_subject_type_is_rejected(self):
        record = deepcopy(self.person)
        self.record("clinical-profile", record)["properties"]["durationMinutes"] = 30
        self.reject(record, "domain mismatch")

    def test_unknown_class_is_rejected(self):
        record = deepcopy(self.person); self.record("clinical-profile", record)["type"] = "InventedClinicalProfile"
        self.reject(record, "Unknown ontology Class")

    def test_unknown_property_is_rejected_even_when_null(self):
        record = deepcopy(self.person); self.record("clinical-profile", record)["properties"]["inventedProperty"] = None
        self.reject(record, "Unknown ontology property")

    def test_unknown_controlled_value_is_rejected(self):
        record = deepcopy(self.person); self.record("risk-estimate", record)["properties"]["riskEstimateHasCategory"] = {"term": "InventedRisk"}
        self.reject(record, "Unknown ontology NamedIndividual")

    def test_wrong_controlled_value_category_is_rejected(self):
        record = deepcopy(self.person); self.record("risk-estimate", record)["properties"]["riskEstimateHasCategory"] = {"term": "AerobicExercise"}
        self.reject(record, "range mismatch")

    def test_invalid_date_and_numeric_value_are_rejected(self):
        for name, prop, value in [("cancer-diagnosis", "diagnosisDate", "2022-02-30"), ("risk-estimate", "riskScore", "high"), ("review-time", "timepointDateTime", "2026-11-01T09:00:00")]:
            record = deepcopy(self.person); self.record(name, record)["properties"][prop] = value
            self.reject(record, "incompatible with ontology datatype")

    def test_all_deployed_datatypes_are_supported_without_loss_of_type(self):
        samples = {
            XSD.string: "LVEF <50% is a textual example", XSD.decimal: 1.25,
            XSD.nonNegativeInteger: 0, XSD.positiveInteger: 1, XSD.boolean: False,
            XSD.dateTime: "2026-11-04T10:00:00Z", XSD.date: "2022-03-12",
            XSD.language: "es-ES", XSD.anyURI: "http://unitsofmeasure.org", XSD.duration: "PT30M"
        }
        actual = {v for p in self.schema.subjects(RDF.type, w.OWL.DatatypeProperty) for v in self.schema.objects(p, w.RDFS.range)}
        self.assertEqual(actual, set(samples))
        for datatype, value in samples.items():
            self.assertEqual(s.literal(value, datatype, w.FORMATS).datatype, datatype)
        for datatype, value in [(XSD.boolean, "false"), (XSD.positiveInteger, 0), (XSD.nonNegativeInteger, -1), (XSD.decimal, True), (XSD.duration, "P"), (XSD.anyURI, "http://[")]:
            with self.assertRaises(s.SectionError): s.literal(value, datatype, w.FORMATS)

    def test_unknown_valid_property_value_remains_unasserted(self):
        record = deepcopy(self.person); self.record("prescribed-walking", record)["properties"]["distanceValue"] = None
        self.run_record(record)
        self.assertFalse(list(self.graph().objects(self.node("prescribed-walking"), w.IC.distanceValue)))

    def test_clinical_comparison_text_is_not_mistaken_for_a_placeholder(self):
        record = deepcopy(self.person); self.record("fatigue", record)["properties"]["symptomName"] = "Example note: LVEF <50%"
        self.run_record(record)
        self.assertEqual({str(v) for v in self.graph().objects(self.node("fatigue"), w.IC.symptomName)}, {"Example note: LVEF <50%"})

    def test_jsonld_preserves_the_exact_participant_graph(self):
        self.run_record()
        exported = Graph().parse(self.output / "participants/es-demo-aya-full.jsonld", format="json-ld")
        self.assertTrue(isomorphic(self.graph(), exported))

    def test_jsonld_preserves_exact_named_graphs(self):
        self.run_record()
        trig = Dataset().parse(self.output / "dataset.trig", format="trig")
        jsonld = Dataset().parse(self.output / "dataset.jsonld", format="json-ld")
        self.assertEqual(set(trig.quads()), set(jsonld.quads()))

    def test_repeated_processing_is_stable_in_turtle_and_jsonld(self):
        self.run_record(); before = self.hashes()
        self.assertEqual(self.run_record()["status"], "UNCHANGED")
        after = self.hashes()
        for path, value in before.items():
            if path not in ("validation/generation-report.json", "validation/shacl-report.ttl"):
                self.assertEqual(value, after[path], path)

    def test_manually_altered_jsonld_is_rejected(self):
        self.run_record(); path = self.output / "participants/es-demo-aya-full.jsonld"
        path.write_text(path.read_text() + "\n")
        self.reject(self.person, "JSON-LD missing or edited")

    def test_pilot_can_instantiate_additional_typed_records(self):
        pilot = deepcopy(self.pilot)
        pilot["sections"] = {"common": {"records": [{"id": "pilot-source", "type": "DataSource", "properties": {"dataSourceDescription": "Fictional shared pilot source"}}]}}
        w.instantiate("pilot", pilot, self.output)
        graph = Graph().parse(self.output / "pilots/es-demo-01.ttl")
        self.assertIn((URIRef(w.DEFAULT_BASE + "sites/es-demo-01/records/pilot-source"), RDF.type, w.IC.DataSource), graph)

    def test_reference_covers_every_deployed_local_class_and_property(self):
        reference = s.ontology_reference(self.schema)
        classes = {str(v) for v in self.schema.subjects(RDF.type, w.OWL.Class) if str(v).startswith(str(w.IC))}
        props = {str(v) for cat in [w.OWL.ObjectProperty, w.OWL.DatatypeProperty] for v in self.schema.subjects(RDF.type, cat) if str(v).startswith(str(w.IC))}
        self.assertEqual({r["iri"] for r in reference["classes"]}, classes)
        self.assertEqual({r["iri"] for r in reference["properties"]}, props)

    def test_new_sections_can_be_added_later_without_changing_existing_record_ids(self):
        initial = deepcopy(self.person)
        initial["sections"].pop("cv_risk")
        self.run_record(initial)
        before = self.graph()
        self.run_record()
        after = self.graph()
        self.assertIn((self.node("clinical-profile"), RDF.type, w.IC.ClinicalProfile), before)
        self.assertIn((self.node("clinical-profile"), RDF.type, w.IC.ClinicalProfile), after)
        self.assertIn((self.node("risk-profile"), RDF.type, w.IC.RiskProfile), after)

    def test_removing_a_still_referenced_record_is_rejected(self):
        self.run_record(); record = deepcopy(self.person)
        record["sections"]["common"]["records"] = [r for r in record["sections"]["common"]["records"] if r["id"] != "review-time"]
        self.reject(record, "Unresolved section reference")

    def test_changed_ontology_rebuilds_unchanged_json_in_both_formats(self):
        self.run_record()
        # This hypothetical model change is confined to a temporary package.
        # The authoritative ontology and its declared date representation stay intact.
        package = Path(self.temp.name) / "ontology-copy"
        shutil.copytree(w.DEFAULT_SCHEMA, package)
        module = package / "modules/cancer-history.ttl"
        graph = Graph().parse(module)
        graph.set((w.IC.diagnosisDate, w.RDFS.range, XSD.string))
        module.write_text(graph.serialize(format="turtle"))
        report = w.instantiate("participant", self.person, self.output, schema_dir=package)
        self.assertEqual(report["status"], "REPLACED_SEED")
        actual = self.graph()
        self.assertEqual(next(actual.objects(self.node("cancer-diagnosis"), w.IC.diagnosisDate)).datatype, XSD.string)
        self.assertTrue(isomorphic(actual, Graph().parse(self.output / "participants/es-demo-aya-full.jsonld", format="json-ld")))


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(SectionChecks)
    names = [test.id().split(".")[-1] for test in suite]
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    failed = {test.id().split(".")[-1] for test, _ in result.failures + result.errors}
    cases = [{"name": name, "status": "FAIL" if name in failed else "PASS"} for name in names] if result.testsRun else []
    report = {"run_date": datetime.now(timezone.utc).date().isoformat(), "status": "PASS" if result.wasSuccessful() else "FAIL",
              "checks": result.testsRun, "failures": len(result.failures), "errors": len(result.errors), "cases": cases,
              "scope": "Fictional clinical inputs and temporary outputs. Expected query answers are independently specified. No clinical efficacy or predictive validity is established."}
    folder = w.ROOT / "reports"; folder.mkdir(exist_ok=True)
    (folder / "section-checks.json").write_bytes(w.canonical(report))
    (folder / "SECTION_CHECKS.md").write_text(
        "# Grouped knowledge records and JSON-LD checks\n\n" + f"{result.testsRun} checks; {len(result.failures)} failures; {len(result.errors)} errors. Result: **{report['status']}**.\n\n" + report["scope"] +
        "\n\nRepeat: `python instantiation/scripts/check_sections.py`\n\n| Check | Result |\n|---|---|\n" +
        "".join(f"| {case['name'].removeprefix('test_').replace('_', ' ')} | {case['status']} |\n" for case in cases))
    print(json.dumps({k:v for k,v in report.items() if k != "cases"}, indent=2))
    raise SystemExit(0 if result.wasSuccessful() else 1)
