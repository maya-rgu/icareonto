#!/usr/bin/env python3
"""Evaluate saved rankings against separately specified demonstration references."""
import csv
from pathlib import Path
import json

import pilot_mapping as pm


def evaluate(ranking, reference, needs, decisions):
    """Compare saved ranks with separate references without changing either."""
    pm.verify_rankings(ranking, needs, pm.kg.DEFAULT_SCHEMA)
    rows = reference["cases"]
    pm.require(len(rows) == len(needs["requirements"]) and {r["requirement_id"] for r in rows} == {r["id"] for r in needs["requirements"]}, "Reference must cover each requirement exactly once")
    actual = {r["requirement_id"]: r for r in ranking["requirements"]}
    reviews = {r["requirement_id"]: r for r in decisions["decisions"]}
    results, positive = [], []
    for row in rows:
        expected = {str(pm.IC) + c for c in row["relevant_classes"]}
        need = actual[row["requirement_id"]]
        ranks = {r["iri"]: r["rank"] for r in need["candidates"]}
        baseline = sorted(need["candidates"], key=lambda r: (-r["lexical_jaccard"], r["iri"]))
        lexical_ranks = {r["iri"]: i for i, r in enumerate(baseline, 1)}
        pm.require(expected <= ranks.keys(), "Reference class is outside the catalogue")
        result = {"requirement_id": row["requirement_id"], "text": need["text"], "reference_classes": sorted(expected), "rationale": row["rationale"], "top_class": need["candidates"][0]["iri"], "top_score": need["candidates"][0]["cosine_similarity"], "reference_ranks": {c: ranks[c] for c in sorted(expected)}, "baseline_reference_ranks": {c: lexical_ranks[c] for c in sorted(expected)}}
        if expected:
            result.update(best_reference_rank=min(ranks[c] for c in expected), baseline_best_reference_rank=min(lexical_ranks[c] for c in expected))
            positive.append(result)
        else:
            # A recorded nonmapping decision is not automatic out-of-scope detection.
            result.update(expected_review=row["expected_review"], actual_review=reviews[row["requirement_id"]]["decision"], review_matches_reference=reviews[row["requirement_id"]]["decision"] == row["expected_review"])
        results.append(result)
    pm.require(bool(positive), "No positive evaluation cases")
    # Retrieval metrics apply only where the reference specifies a suitable class.
    def metrics(key):
        return {"positive_cases": len(positive), "hit_at_1": sum(r[key] <= 1 for r in positive) / len(positive), "hit_at_5": sum(r[key] <= 5 for r in positive) / len(positive), "hit_at_10": sum(r[key] <= 10 for r in positive) / len(positive), "mean_reciprocal_rank": sum(1 / r[key] for r in positive) / len(positive)}
    return {"status": "EVALUATED_DEMONSTRATION_NOT_PILOT_VALIDATION", "reference_status": reference["status"], "ranking_sha256": pm.kg.digest(pm.kg.canonical(ranking)), "reference_sha256": pm.kg.digest(pm.kg.canonical(reference)), "semantic_cosine": metrics("best_reference_rank"), "lexical_baseline": metrics("baseline_best_reference_rank"), "nonmapping_cases": {"count": len(results) - len(positive), "decision_matches": sum(r.get("review_matches_reference", False) for r in results), "interpretation": "Checks of supplied demonstration decisions, not automatic no-match detection by the scorer"}, "cases": results}


def main():
    output, reports = pm.ROOT / "outputs", pm.ROOT / "reports"
    fixtures = pm.ROOT / "tests/fixtures"
    if not (output / "rankings.json").is_file():
        output = fixtures
    ranking = pm.kg.read_json(output / "rankings.json")
    reference = pm.kg.read_json(pm.ROOT / "tests/reference-mappings.json")
    needs = pm.kg.read_json(pm.ROOT / "examples/pilot-needs.json")
    decisions = pm.kg.read_json(pm.ROOT / "examples/demo-review-decisions.json")
    profile = pm.kg.read_json(output / "pilot-profile.json")
    coverage_path = output / "generated/validation/profile-coverage.json" if output != fixtures else fixtures / "profile-coverage.json"
    coverage = pm.kg.read_json(coverage_path)
    evaluation = evaluate(ranking, reference, needs, decisions)
    pm.save(reports / "evaluation.json", evaluation)
    with (reports / "reference-ranks.tsv").open("w", newline="") as file:
        writer = csv.writer(file, delimiter="\t")
        writer.writerow(["requirement_id", "reference_class", "semantic_rank", "lexical_rank", "top_candidate", "top_cosine", "expected_review", "actual_review"])
        for row in evaluation["cases"]:
            for cls in row["reference_classes"] or [""]:
                writer.writerow([row["requirement_id"], cls, row["reference_ranks"].get(cls, ""), row["baseline_reference_ranks"].get(cls, ""), row["top_class"], f"{row['top_score']:.8f}", row.get("expected_review", ""), row.get("actual_review", "")])
    def short(iri):
        return iri.removeprefix(str(pm.IC))
    semantic, baseline = evaluation["semantic_cosine"], evaluation["lexical_baseline"]
    represented = [r for r in coverage["coverage"] if r["status"] == "REPRESENTED_IN_GENERATED_SEEDS"]
    lines = [
        "# Pilot concept mapping demonstration report", "",
        "**Scope:** Fictional Spanish pilot `es-demo-01`, study `maya-demo`. The inputs and mapping decisions are agent-authored demonstration material, not actual workshop findings or pilot/expert approval.", "",
        f"All **{len(needs['requirements'])} fictional needs** were scored against **{ranking['candidate_count']} local ontology classes**. There are **{len(profile['accepted_mappings'])} accepted demonstration mappings** and **{len(profile['unresolved_requirements'])} requirements without an accepted mapping**.", "",
        "## Method", "",
        "Each class is described by its preferred label, alternative labels, definition and available named-parent labels. A locally cached `sentence-transformers/all-MiniLM-L6-v2` encoder produces sentence vectors. Cosine similarity ranks classes separately for each requirement. Scores are not confidence probabilities. No threshold automatically accepts a mapping.", "",
        f"The model snapshot directory is `{ranking['model']['snapshot_directory_name']}`; file hashes, runtime versions, CPU execution, vector dimensions and truncation checks are recorded in `{(output / 'rankings.json').relative_to(pm.ROOT)}`. This report evaluates those saved rankings; it does not itself execute the encoder. All descriptions are English. No text was sent to an external inference service. No descriptions were truncated.", "",
        "The comparison baseline is unweighted token-set Jaccard overlap using the same texts. It measures lexical overlap, not semantic similarity. The separate reference file specifies expected classes before scoring and is never read by the ranker. It is a small agent-authored demonstration reference, not an expert gold standard or held-out real-pilot evaluation.", "",
        "## Candidate retrieval results", "",
        f"The {semantic['positive_cases']} positive references each specify one target class. Hit@k is the fraction with that class in the first k candidates. Mean reciprocal rank averages the reciprocal of its rank. Requirements without a specified positive reference ({evaluation['nonmapping_cases']['count']}) are excluded from these retrieval metrics.", "",
        "| Metric | Semantic cosine | Lexical baseline |", "|---|---:|---:|",
        f"| Hit@1 | {semantic['hit_at_1']:.1%} | {baseline['hit_at_1']:.1%} |",
        f"| Hit@5 | {semantic['hit_at_5']:.1%} | {baseline['hit_at_5']:.1%} |",
        f"| Hit@10 | {semantic['hit_at_10']:.1%} | {baseline['hit_at_10']:.1%} |",
        f"| Mean reciprocal rank | {semantic['mean_reciprocal_rank']:.3f} | {baseline['mean_reciprocal_rank']:.3f} |", "",
        "| Requirement | Reference class | Semantic rank | Lexical rank |", "|---|---|---:|---:|"
    ]
    for row in evaluation["cases"]:
        for cls in row["reference_classes"]:
            lines.append(f"| {row['requirement_id']} | `{short(cls)}` | {row['reference_ranks'][cls]} | {row['baseline_reference_ranks'][cls]} |")
    detail_case = next(r for r in evaluation["cases"] if r["requirement_id"] == "DEMO-KR02")
    lines += ["", "All candidates and scores remain available even when the reference is ranked poorly. Targets are not changed to manufacture successful retrieval.", "",
        f"For DEMO-KR02, `InformationPreference` ranked **{detail_case['best_reference_rank']}** with semantic similarity and **{detail_case['baseline_best_reference_rank']}** with lexical overlap. The supplied demonstration decision retains this class through an explicit review selection. This miss shows why the top-ten list alone is insufficient for reviewing all needs; reviewers must be able to search the full catalogue and identify omitted candidates.", "", "## Review decisions and open items", "",
        "The generated review template starts with no accepted mappings. The separate demonstration decisions select ontology concepts with recorded rationale, including any selections below rank 1. Real use requires review by the responsible pilot/domain team.", "",
        "- **DEMO-KR16:** The ontology now supplies `measurementInstrumentHasValidationEvidence`, resolving the earlier CQ-051 distinction. The existing pending demonstration mapping is retained for explicit review of its selected classes and source-data mapping. It remains outside the original 14 positive retrieval references; a schema update does not automatically accept a mapping.", "",
        "These are supplied review outcomes, not an automatically measured out-of-scope detection rate.", "", "## Connection to KG generation", "",
        "The accepted mappings form a pilot concept profile bound to the needs, ranking, review and ontology hashes. It lists relevant modules and adjacent relationships for input-profile design. Adjacent properties are contextual suggestions rather than independently reviewed mappings. Core participant, pilot and governance structures remain available; the ontology is not pruned.", "",
        f"The profile was bound to the existing generator for one fictional pilot and two participant enrolments. **{len(represented)} of the {len(coverage['coverage'])} accepted class mappings** have matching instances in these initial graphs; **{len(coverage['coverage']) - len(represented)}** require additional input profiles or data. Class relevance alone does not create clinical facts.", "",
        "| Requirement | Selected class | Initial graph coverage |", "|---|---|---|"
    ]
    for row in coverage["coverage"]:
        lines.append(f"| {row['requirement_id']} | `{short(row['class_iri'])}` | {'Represented' if row['instances'] else 'Additional input profile or data required'} |")
    lines += ["", "The inputs used for this demonstration contain enrolment information. The KG Instantiator also supports grouped clinical and contextual records when supplied. Coverage describes the data used in this run, not a restriction on the ontology or instantiation interface.", "",
        "## Limits and next steps", "",
        "The prototype ranks classes, not arbitrary properties, controlled values or external-standard equivalences. It establishes a candidate-retrieval and traceability workflow rather than automatic ontology alignment, exhaustive schema extraction or deployed pilot adaptation. The current encoder is a general English model, not an evaluated multilingual or clinical-specialist model. Actual pilot needs, local terminology and any translations must be assessed with pilot/domain reviewers. No single similarity cutoff or performance guarantee is established by this small demonstration.", "",
        "Methods: [Sentence Transformers similarity documentation](https://sbert.net/docs/sentence_transformer/usage/semantic_textual_similarity.html); [model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2). These sources describe the underlying technique, not the validity of the project-specific mappings."
    ]
    (reports / "PILOT_MAPPING_REPORT.md").write_text("\n".join(lines) + "\n")
    print(json.dumps({"semantic": semantic, "lexical_baseline": baseline, "represented_mappings": len(represented), "mapping_decisions": len(profile['accepted_mappings'])}, indent=2))


if __name__ == "__main__":
    main()
