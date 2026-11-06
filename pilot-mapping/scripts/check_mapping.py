#!/usr/bin/env python3
"""Check retrieval provenance, review boundaries and profile-linked generation."""
from copy import deepcopy
import json
import math
from pathlib import Path
from tempfile import TemporaryDirectory

from rdflib import Graph, RDF, URIRef

import pilot_mapping as pm
from evaluate_mapping import evaluate


def main():
    needs = pm.kg.read_json(pm.ROOT / "examples/pilot-needs.json")
    fixtures = pm.ROOT / "tests/fixtures"
    ranking_path = fixtures / "rankings.json"
    ranking = pm.kg.read_json(ranking_path)
    profile = pm.kg.read_json(fixtures / "pilot-profile.json")
    decisions = pm.kg.read_json(pm.ROOT / "examples/demo-review-decisions.json")
    reference = pm.kg.read_json(pm.ROOT / "tests/reference-mappings.json")
    # References evaluate retrieval; review decisions separately control profile selection.
    pilot = pm.kg.read_json(pm.ROOT.parent / "instantiation/examples/pilot-es-demo.json")
    participants = [pm.kg.read_json(pm.ROOT.parent / "instantiation/examples" / name) for name in ("participant-es-001.json", "participant-es-002.json")]
    cases = []
    def check(name, result, detail):
        if not result:
            raise AssertionError(name + ": " + detail)
        cases.append({"id": name, "status": "PASS", "detail": detail})
    def rejected(name, function, text):
        try:
            function()
        except pm.kg.InputError as error:
            check(name, text in str(error), "Rejected: " + text)
        else:
            raise AssertionError(name + ": invalid request accepted")
    schema, catalogue = pm.verify_rankings(ranking, needs, pm.kg.DEFAULT_SCHEMA)
    check("FULL-CANDIDATES", len(catalogue) == 283 and all(len(r["candidates"]) == 283 for r in ranking["requirements"]), "Every requirement ranks all 283 local classes without an oracle shortlist")
    check("NO-TRUNCATION", not ranking["model"]["truncated_text_indices"], "No encoded requirement or ontology description was truncated")
    check("REAL-MODEL-PROVENANCE", ranking["model"]["dimensions"] == 384 and ranking["model"]["device"] == "cpu" and "model.safetensors" in ranking["model"]["model_files_sha256"], "Report identifies local model weights, runtime and 384-dimensional sentence vectors")
    check("COSINE-NORMALISATION", math.isclose(pm.cosine([3, 4], [6, 8]), 1.0) and math.isclose(pm.cosine([1, 0], [0, 2]), 0.0) and math.isclose(pm.cosine([1, 0], [-1, 0]), -1.0), "Metric handles vector scale, orthogonality and opposite directions")
    template = pm.kg.read_json(fixtures / "review-template.json")
    check("NO-AUTOMATIC-ACCEPTANCE", all(r["decision"] == "needs_review" and not r["classes"] for r in template["decisions"]), "Even the highest ranked candidates remain unaccepted in the generated template")
    rejected("UNNAMED-REVIEW", lambda: pm.make_profile(ranking, needs, template), "reviewer")
    pending = deepcopy(template)
    pending["reviewer"] = "Named demonstration annotation source, pending all decisions"
    pending_profile = pm.make_profile(ranking, needs, pending)
    check("PENDING-PROFILE", not pending_profile["accepted_mappings"] and len(pending_profile["unresolved_requirements"]) == len(needs["requirements"]), "Pending decisions never enter the accepted mapping set")
    check("FOUNDATION-RETAINED", set(pending_profile["foundation_modules_retained"]) == {"core", "person-role", "pilot", "provenance-governance"}, "Core participant, site and governance scope remains available regardless of ranking")
    check("PROFILE-REPRODUCTION", pm.make_profile(ranking, needs, decisions) == profile, "Stored profile reproduces exactly from its bound ranking, needs and review decisions")
    check("REVIEW-BOUNDARIES", {r["requirement_id"]: r["decision"] for r in profile["unresolved_requirements"]} == {"DEMO-KR16": "needs_review"}, "A pending mapping decision remains separate from the ontology update that resolved its earlier representation gap")
    score_lookup = {r["requirement_id"]: {c["iri"]: c for c in r["candidates"]} for r in ranking["requirements"]}
    check("DECISION-SCORES", all(row["rank"] == score_lookup[row["requirement_id"]][row["class_iri"]]["rank"] and row["cosine_similarity"] == score_lookup[row["requirement_id"]][row["class_iri"]]["cosine_similarity"] for row in profile["accepted_mappings"]), "Accepted decisions preserve actual ranks and scores, including lower-ranked reference concepts")
    manual = deepcopy(pending)
    manual["decisions"][0].update(decision="accepted", classes=[ranking["requirements"][0]["candidates"][-1]["iri"]], rationale="Artificial control: explicit override of the last ranked candidate, not a supplied example decision")
    control_profile = pm.make_profile(ranking, needs, manual)
    check("EXPLICIT-OVERRIDE", len(control_profile["accepted_mappings"]) == 1 and control_profile["accepted_mappings"][0]["rank"] == 283, "Review decisions are separate from score rank; the control does not alter shipped mappings")
    bad = deepcopy(needs)
    bad["requirements"][0]["text"] += " Updated requirement."
    rejected("STALE-NEEDS", lambda: pm.make_profile(ranking, bad, decisions), "Needs input changed")
    bad = deepcopy(ranking)
    bad["ontology_sha256"] = "stale"
    rejected("STALE-ONTOLOGY", lambda: pm.make_profile(bad, needs, decisions), "Ontology changed")
    bad = deepcopy(ranking)
    bad["requirements"][0]["candidates"][0]["cosine_similarity"] = float("nan")
    rejected("NONFINITE-SCORE", lambda: pm.make_profile(bad, needs, decisions), "Invalid ranking scores")
    bad = deepcopy(needs)
    bad["requirements"][1]["id"] = bad["requirements"][0]["id"]
    rejected("DUPLICATE-NEED", lambda: pm.validate_needs(bad), "duplicate")
    bad = deepcopy(needs)
    bad["language"] = "es"
    rejected("UNTESTED-LANGUAGE", lambda: pm.validate_needs(bad), "English")
    bad = deepcopy(decisions)
    bad["decisions"][0]["classes"] = ["UnknownClinicalConcept"]
    rejected("UNKNOWN-CLASS", lambda: pm.make_profile(ranking, needs, bad), "undeclared")
    bad = deepcopy(decisions)
    bad["decisions"][0]["classes"] = ["personHasPreference"]
    rejected("PROPERTY-AS-CLASS", lambda: pm.make_profile(ranking, needs, bad), "non-class")
    bad = deepcopy(decisions)
    bad["decisions"][1]["requirement_id"] = bad["decisions"][0]["requirement_id"]
    rejected("DUPLICATE-REVIEW", lambda: pm.make_profile(ranking, needs, bad), "Exactly one decision")
    bad = deepcopy(decisions)
    bad["decisions"][0]["decision"] = "needs_review"
    rejected("PENDING-SELECTION", lambda: pm.make_profile(ranking, needs, bad), "Only accepted")
    check("SUPPORTING-RELATIONSHIPS", bool(profile["supporting_relationships"]) and all(set(row["domains"]) == set(map(str, schema.objects(URIRef(row["property_iri"]), pm.RDFS.domain))) and set(row["ranges"]) == set(map(str, schema.objects(URIRef(row["property_iri"]), pm.RDFS.range))) for row in profile["supporting_relationships"]), "Adjacent relationships retain the ontology's existing domain/range definitions rather than creating new axioms")
    before = ranking_path.read_bytes()
    evaluation = evaluate(ranking, reference, needs, decisions)
    check("REFERENCE-EVALUATION", evaluation["semantic_cosine"]["positive_cases"] == 14 and evaluation["nonmapping_cases"]["count"] == 1 and ranking_path.read_bytes() == before, "Evaluation covers all references without changing saved rankings or imposing a 100-percent retrieval expectation")
    with TemporaryDirectory(prefix="icareonto-profile-") as temp:
        # Exercise generation and rejection paths without modifying shipped examples.
        output = Path(temp) / "generated"
        altered = deepcopy(profile)
        altered["accepted_mappings"].pop()
        rejected("EDITED-PROFILE", lambda: pm.generate_from_profile(altered, ranking, needs, decisions, pilot, participants, output), "stale or edited")
        check("NO-OUTPUT-ON-EDITED-PROFILE", not output.exists(), "Rejected profile does not start a generation run")
        wrong = deepcopy(pilot)
        wrong["site"]["id"] = "different-site"
        rejected("WRONG-SITE", lambda: pm.generate_from_profile(profile, ranking, needs, decisions, wrong, participants, output), "does not match")
        wrong_person = deepcopy(participants[0])
        wrong_person["study_id"] = "other-study"
        rejected("WRONG-PARTICIPANT", lambda: pm.generate_from_profile(profile, ranking, needs, decisions, pilot, [wrong_person], output), "does not belong")
        result = pm.generate_from_profile(profile, ranking, needs, decisions, pilot, participants, output)
        check("PROFILE-BOUND-GENERATION", result["profile_sha256"] == pm.kg.digest(pm.kg.canonical(profile)) and all(r["shacl_conforms"] for r in result["generation_runs"]), "Existing generator validates one pilot and two participants against the bound concept profile")
        check("HONEST-COVERAGE", sum(r["status"] == "REPRESENTED_IN_GENERATED_SEEDS" for r in result["coverage"]) == 5 and sum(r["status"] == "ADDITIONAL_INPUT_PROFILE_OR_DATA_REQUIRED" for r in result["coverage"]) == 9, "Five selected concepts have instances; nine are reported as requiring more data/profiles")
        classes = {str(type_) for p in (output / "participants").glob("*.ttl") for type_ in Graph().parse(p).objects(None, RDF.type)}
        check("NO-INVENTED-CLINICAL-FACTS", str(pm.IC.CancerTreatmentHistory) not in classes and str(pm.IC.ExercisePrescription) not in classes, "Selecting clinical concepts does not fabricate treatment history or an exercise prescription")
        check("TRACEABILITY-FILES", (output / "validation/pilot-concept-profile.json").is_file() and (output / "validation/profile-coverage.json").is_file(), "Generated package contains the exact concept profile and its coverage record")
    report = {"status": "PASS", "checks": len(cases), "cases": cases, "scope": "Technical controls and separately specified demonstration references; no claim of expert mapping approval or real-pilot validity"}
    pm.save(pm.ROOT / "reports/workflow-checks.json", report)
    lines = ["# Pilot mapping workflow checks", "", f"All **{len(cases)} checks passed**.", "", report["scope"], "", "| Check | Result | Purpose |", "|---|---|---|"]
    lines.extend(f"| {r['id']} | PASS | {r['detail']} |" for r in cases)
    (pm.ROOT / "reports/WORKFLOW_CHECKS.md").write_text("\n".join(lines) + "\n")
    print(json.dumps({"status": "PASS", "checks": len(cases)}, indent=2))


if __name__ == "__main__":
    main()
