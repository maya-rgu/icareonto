#!/usr/bin/env python3
"""Rank pilot needs against ontology classes, record decisions and bind a KG run.

Flow: requirement input -> candidate scores -> separate review -> pilot profile
-> enrolment graphs and coverage report. Ranking never reads review decisions
or evaluation reference mappings.
"""
import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from rdflib import Graph, RDF, RDFS, OWL, URIRef
from rdflib.namespace import SKOS

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent
sys.path.insert(0, str(ROOT.parent / "instantiation/scripts"))
import generate_kg as kg

IC = kg.IC
MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
DEFAULT_MODEL = Path.home() / ".cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2/snapshots" / MODEL_REVISION
FOUNDATION_MODULES = {"core", "person-role", "pilot", "provenance-governance"}
METHOD_VERSION = "1.1"
ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$")


def save(path, data):
    kg.atomic_write(Path(path), kg.canonical(data))


def require(condition, message):
    if not condition:
        raise kg.InputError(message)


def nonempty(value):
    return isinstance(value, str) and bool(value.strip()) and "<" not in value and ">" not in value


def validate_document(data, name):
    spec = kg.read_json(ROOT / "schemas" / (name + ".schema.json"))
    kg.Draft202012Validator.check_schema(spec)
    errors = sorted(kg.Draft202012Validator(spec, format_checker=kg.FORMATS).iter_errors(data), key=lambda error: str(list(error.absolute_path)))
    require(not errors, "Invalid " + name + " input: " + "; ".join(f"{'.'.join(map(str, error.absolute_path)) or '$'}: {error.message}" for error in errors[:8]))


def validate_needs(data):
    """Check input fields, source references and unique requirement identifiers."""
    require(isinstance(data, dict), "Needs input must be an object")
    require(data.get("language") == "en", "Supply English descriptions for the current encoder; participant language preferences are separate")
    validate_document(data, "needs")
    require(nonempty(data["source"]), "Needs require a source description")
    if "owner" in data:
        require(nonempty(data["owner"]), "Supply the requirement-set owner")
    require(all(isinstance(data[k], str) and ID.fullmatch(data[k]) for k in ("pilot_id", "study_id")), "Invalid pilot/study identifier")
    require(isinstance(data["requirements"], list) and 0 < len(data["requirements"]) <= 200, "Supply 1–200 requirements")
    seen = set()
    for row in data["requirements"]:
        require(isinstance(row, dict) and {"id", "text"} <= set(row), "Each requirement needs id and text")
        require(isinstance(row["id"], str) and ID.fullmatch(row["id"]) and row["id"] not in seen, "Invalid or duplicate requirement ID")
        require(nonempty(row["text"]) and len(row["text"]) <= 2000, "Requirement text must be nonempty, without placeholders, and at most 2000 characters")
        require(all(nonempty(ref) for ref in row.get("source_refs", [])), "Replace source-reference placeholders")
        seen.add(row["id"])


def ontology_data(schema_dir=kg.DEFAULT_SCHEMA):
    """Build a class search catalogue and fingerprint the loaded ontology files."""
    schema_dir = Path(schema_dir).resolve()
    schema, paths = kg.schema_package(schema_dir)
    manifest = {Path(path).relative_to(schema_dir).as_posix(): kg.digest(path.read_bytes()) for path in set(paths.values())}
    catalogue = []
    # Rank locally owned classes; imported vocabularies stay available as context.
    for cls in sorted(schema.subjects(RDF.type, OWL.Class), key=str):
        owners = [str(owner).removeprefix(str(IC)) for owner in schema.objects(cls, RDFS.isDefinedBy) if str(owner).startswith(str(IC))]
        if not str(cls).startswith(str(IC)) or not owners:
            continue
        label = str(next(schema.objects(cls, RDFS.label), str(cls).removeprefix(str(IC))))
        definitions = sorted(str(v) for v in schema.objects(cls, SKOS.definition))
        alternatives = sorted(str(v) for v in schema.objects(cls, SKOS.altLabel))
        parents = sorted(str(next(schema.objects(parent, RDFS.label), str(parent).removeprefix(str(IC)))) for parent in schema.objects(cls, RDFS.subClassOf) if str(parent).startswith(str(IC)))
        text = ". ".join([label] + alternatives + definitions + (["Broader concepts: " + ", ".join(parents)] if parents else []))
        catalogue.append({"iri": str(cls), "label": label, "module": owners[0], "definition": " ".join(definitions), "alternative_labels": alternatives, "parents": parents, "text": text})
    require(len(catalogue) > 0 and len({r["iri"] for r in catalogue}) == len(catalogue), "Empty or ambiguous local class catalogue")
    return schema, catalogue, kg.digest(kg.canonical(manifest)), manifest


STOP = set("a an the and or of to in for with from on at is are be by as that this its it which each their into when whether than more".split())


def tokens(text):
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    return set(re.findall(r"[a-z]+", text.lower())) - STOP


def jaccard(left, right):
    a, b = tokens(left), tokens(right)
    return len(a & b) / len(a | b) if a | b else 0.0


def cosine(left, right):
    require(len(left) == len(right) and len(left) > 0, "Embedding dimensions differ")
    require(all(math.isfinite(x) for x in left + right), "Non-finite embedding")
    denominator = math.sqrt(math.fsum(v * v for v in left) * math.fsum(v * v for v in right))
    require(denominator > 0, "Zero-length embedding")
    return max(-1.0, min(1.0, math.fsum(x * y for x, y in zip(left, right)) / denominator))


def rank(needs_path, output, encoder_python, model_dir=DEFAULT_MODEL, schema_dir=kg.DEFAULT_SCHEMA, cache_dir=None):
    """Score all classes for each need and write candidates plus a pending review."""
    needs = kg.read_json(needs_path)
    validate_needs(needs)
    _, catalogue, ontology_hash, ontology_files = ontology_data(schema_dir)
    model_dir = Path(model_dir).resolve()
    require(model_dir.is_dir() and (model_dir / "model.safetensors").is_file(), "A local all-MiniLM-L6-v2 snapshot with safetensors weights is required; no model is downloaded automatically")
    # Keep classes first and requirements second so vector positions remain traceable.
    texts = [r["text"] for r in catalogue] + [r["text"] for r in needs["requirements"]]
    request = {"texts": texts}
    model_hashes = {p.relative_to(model_dir).as_posix(): kg.digest(p.read_bytes()) for p in sorted(model_dir.rglob("*")) if p.is_file() and p.suffix in {".json", ".txt", ".safetensors"}}
    # Reuse vectors only for the same texts, model files and encoder worker.
    key = kg.digest(kg.canonical({"request": request, "model_files": model_hashes, "worker_sha256": kg.digest((ROOT / "scripts/encode_texts.py").read_bytes())}))
    cache = Path(cache_dir) if cache_dir else Path(output) / ".cache" if needs["status"] == "operational" else ROOT / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    cache_file = cache / (key + ".json")
    if cache_file.exists():
        encoded = kg.read_json(cache_file)
    else:
        with tempfile.TemporaryDirectory(prefix="encode-", dir=cache) as temp:
            request_path, result_path = Path(temp) / "request.json", Path(temp) / "vectors.json"
            save(request_path, request)
            env = dict(os.environ, HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", TOKENIZERS_PARALLELISM="false", PYTHONDONTWRITEBYTECODE="1", MPLCONFIGDIR=str(cache / "matplotlib"))
            subprocess.run([str(encoder_python), str(ROOT / "scripts/encode_texts.py"), "--request", str(request_path), "--output", str(result_path), "--model-dir", str(model_dir)], check=True, env=env)
            encoded = kg.read_json(result_path)
            save(cache_file, encoded)
    vectors = encoded["vectors"]
    require(len(vectors) == len(texts), "Wrong embedding count")
    require(not encoded["truncated_text_indices"], "Input text exceeded the encoder limit; shorten descriptions explicitly before ranking")
    require(all(len(v) == encoded["dimensions"] and all(isinstance(x, (int, float)) and math.isfinite(x) for x in v) for v in vectors), "Invalid embedding vector")
    output = Path(output)
    results = []
    # Preserve every candidate; a reviewer may need a class outside the top ten.
    for index, need in enumerate(needs["requirements"]):
        query_vector = vectors[len(catalogue) + index]
        candidates = [{"iri": row["iri"], "cosine_similarity": cosine(query_vector, vectors[i]), "lexical_jaccard": jaccard(need["text"], row["text"])} for i, row in enumerate(catalogue)]
        candidates.sort(key=lambda row: (-row["cosine_similarity"], row["iri"]))
        for position, row in enumerate(candidates, 1):
            row["rank"] = position
        result = {"requirement_id": need["id"], "text": need["text"], "candidates": candidates}
        if "source_refs" in need:
            result["source_refs"] = need["source_refs"]
        results.append(result)
    report = {
        "schema_version": "1.1", "method_version": METHOD_VERSION, "status": "CANDIDATES_ONLY_NO_AUTOMATIC_ACCEPTANCE",
        "pilot_id": needs["pilot_id"], "study_id": needs["study_id"], "source_status": needs["status"], "source": needs["source"],
        "needs_sha256": kg.digest(kg.canonical(needs)), "requirements_owner": needs.get("owner"), "ontology_sha256": ontology_hash, "ontology_files_sha256": ontology_files,
        "candidate_scope": "All locally owned OWL classes; properties and controlled individuals are not independently ranked",
        "candidate_count": len(catalogue), "catalogue_sha256": kg.digest(kg.canonical(catalogue)), "catalogue": catalogue,
        "metric": "Cosine similarity of sentence embeddings; labels, alternative labels, definitions and named parent labels",
        "baseline": "Unweighted token-set Jaccard overlap on the same texts; a lexical comparator, not a semantic metric",
        "model": {"id": MODEL_ID, "snapshot_directory_name": model_dir.name, "embedding_cache_key": key, **{k: v for k, v in encoded.items() if k != "vectors"}},
        "selection": "Ranked candidates only. No acceptance threshold; cosine similarity is not a probability or validation result.",
        "requirements": results
    }
    save(output / "rankings.json", report)
    lookup = {row["iri"]: row for row in catalogue}
    output.mkdir(parents=True, exist_ok=True)
    with (output / "top-candidates.tsv").open("w", newline="") as file:
        writer = csv.writer(file, delimiter="\t")
        writer.writerow(["requirement_id", "rank", "cosine_similarity", "lexical_jaccard", "class_iri", "label", "module"])
        for need in results:
            for row in need["candidates"][:10]:
                term = lookup[row["iri"]]
                writer.writerow([need["requirement_id"], row["rank"], f"{row['cosine_similarity']:.8f}", f"{row['lexical_jaccard']:.8f}", row["iri"], term["label"], term["module"]])
    template = {"schema_version": "1.1", "pilot_id": needs["pilot_id"], "study_id": needs["study_id"], "review_status": "draft" if needs["status"] == "operational" else "demonstration_annotation_not_site_approval", "reviewer": "REPLACE WITH REVIEWER DESCRIPTION", "needs_sha256": report["needs_sha256"], "ranking_sha256": kg.digest(kg.canonical(report)), "decisions": [{"requirement_id": row["requirement_id"], "decision": "needs_review", "classes": [], "rationale": "Review the ranked candidates; no mapping accepted automatically."} for row in results]}
    save(output / "review-template.json", template)
    return report


def verify_rankings(ranking, needs, schema_dir):
    """Reject stale inputs, changed ontology files or malformed candidate rankings."""
    validate_needs(needs)
    schema, catalogue, ontology_hash, _ = ontology_data(schema_dir)
    require(ranking["needs_sha256"] == kg.digest(kg.canonical(needs)), "Needs input changed; rerank before using these mappings")
    require(ranking["ontology_sha256"] == ontology_hash and ranking["catalogue_sha256"] == kg.digest(kg.canonical(catalogue)), "Ontology changed; rerank before using these mappings")
    require((ranking["pilot_id"], ranking["study_id"]) == (needs["pilot_id"], needs["study_id"]), "Pilot/study mismatch in ranking")
    require(len(ranking["requirements"]) == len(needs["requirements"]) and {row["requirement_id"] for row in ranking["requirements"]} == {row["id"] for row in needs["requirements"]}, "Ranking requirement IDs differ")
    known = {row["iri"] for row in catalogue}
    for row in ranking["requirements"]:
        require(len(row["candidates"]) == len(known) and {r["iri"] for r in row["candidates"]} == known, "Candidate list is incomplete or duplicated")
        require(all(r["rank"] == i and math.isfinite(r["cosine_similarity"]) and -1 <= r["cosine_similarity"] <= 1 for i, r in enumerate(row["candidates"], 1)), "Invalid ranking scores or positions")
        require(row["candidates"] == sorted(row["candidates"], key=lambda r: (-r["cosine_similarity"], r["iri"])), "Candidate order is invalid")
    return schema, catalogue


def make_profile(ranking, needs, decisions, schema_dir=kg.DEFAULT_SCHEMA):
    """Apply separately recorded decisions while retaining scores and open needs."""
    schema, catalogue = verify_rankings(ranking, needs, schema_dir)
    validate_document(decisions, "review")
    require(nonempty(decisions.get("reviewer")) and "REPLACE" not in decisions["reviewer"], "A named reviewer or demonstration annotation source is required")
    if needs["status"] == "operational":
        require(decisions["review_status"] in {"draft", "reviewed"}, "Operational needs require draft or reviewed operational decisions, not demonstration annotations")
    else:
        require(decisions["review_status"] == "demonstration_annotation_not_site_approval", "Synthetic needs retain demonstration review status")
    for field, expected in (("needs_sha256", ranking["needs_sha256"]), ("ranking_sha256", kg.digest(kg.canonical(ranking)))):
        if field in decisions:
            require(decisions[field] == expected, "Review is stale: " + field + " differs from the current input/ranking")
    require((decisions.get("pilot_id"), decisions.get("study_id")) == (needs["pilot_id"], needs["study_id"]), "Review pilot/study mismatch")
    rows = decisions.get("decisions")
    require(isinstance(rows, list), "Review decisions must be a list")
    require(all(isinstance(row, dict) and set(row) == {"requirement_id", "decision", "classes", "rationale"} for row in rows), "Each review row requires requirement_id, decision, classes and rationale")
    require(len(rows) == len(needs["requirements"]) and {row["requirement_id"] for row in rows} == {row["id"] for row in needs["requirements"]}, "Exactly one decision is required per requirement")
    lookup = {row["iri"]: row for row in catalogue}
    ranked = {row["requirement_id"]: {r["iri"]: r for r in row["candidates"]} for row in ranking["requirements"]}
    sources = {row["id"]: row.get("source_refs", []) for row in needs["requirements"]}
    accepted, unresolved = [], []
    for row in rows:
        require(row["decision"] in {"accepted", "rejected", "needs_review", "no_match"} and nonempty(row["rationale"]), "Invalid review decision or missing rationale")
        require(isinstance(row["classes"], list) and all(isinstance(c, str) for c in row["classes"]) and len(row["classes"]) == len(set(row["classes"])), "Review classes must be a list without duplicates")
        require(bool(row["classes"]) if row["decision"] == "accepted" else not row["classes"], "Only accepted decisions may select classes; accepted decisions need at least one class")
        if row["decision"] != "accepted":
            unresolved.append(row)
        for name in row["classes"]:
            iri = name if name.startswith(str(IC)) else str(IC) + name
            require(iri in lookup, "Review selects an undeclared or non-class ontology term: " + name)
            rank_ = ranked[row["requirement_id"]][iri]
            state = "accepted_for_demonstration" if needs["status"] == "synthetic_demonstration" else "accepted" if decisions["review_status"] == "reviewed" else "provisional_selection"
            accepted.append({"requirement_id": row["requirement_id"], "class_iri": iri, "label": lookup[iri]["label"], "module": lookup[iri]["module"], "rank": rank_["rank"], "cosine_similarity": rank_["cosine_similarity"], "decision": state, "rationale": row["rationale"], "source_refs": sources[row["requirement_id"]]})
    seeds = {URIRef(row["class_iri"]) for row in accepted}
    supporting = []
    # Adjacent properties help design input profiles; they are not approved mappings.
    for prop in sorted(schema.subjects(RDF.type, OWL.ObjectProperty), key=str):
        if not str(prop).startswith(str(IC)):
            continue
        domains, ranges = set(schema.objects(prop, RDFS.domain)), set(schema.objects(prop, RDFS.range))
        if domains & seeds or ranges & seeds:
            supporting.append({"property_iri": str(prop), "domains": sorted(map(str, domains)), "ranges": sorted(map(str, ranges)), "status": "adjacent_relation_for_profile_design_not_independently_reviewed"})
    state = "DEMONSTRATION_PROFILE" if needs["status"] == "synthetic_demonstration" else "REVIEWED_PROFILE" if decisions["review_status"] == "reviewed" else "DRAFT_PROFILE"
    return {
        "schema_version": "1.1", "status": state + ("_WITH_OPEN_ITEMS" if unresolved else ""), "source_status": needs["status"], "pilot_id": needs["pilot_id"], "study_id": needs["study_id"],
        "needs_sha256": ranking["needs_sha256"], "ontology_sha256": ranking["ontology_sha256"],
        "ranking_sha256": kg.digest(kg.canonical(ranking)), "review_sha256": kg.digest(kg.canonical(decisions)),
        "review_status": decisions["review_status"], "reviewer": decisions["reviewer"], "reviewed_at": decisions.get("reviewed_at"), "requirements_owner": needs.get("owner"),
        "accepted_mappings": accepted, "unresolved_requirements": unresolved,
        "foundation_modules_retained": sorted(FOUNDATION_MODULES),
        "relevant_modules": sorted(FOUNDATION_MODULES | {row["module"] for row in accepted}),
        "supporting_relationships": supporting,
        "requirement_sources": sources,
        "scope": "A concept-relevance manifest with explicit input and review status. The shared ontology is not pruned; relevance does not supply clinical values or create factual instances."
    }


def generate_from_profile(profile, ranking, needs, decisions, pilot, participants, output, schema_dir=kg.DEFAULT_SCHEMA, base_iri=None, replace_seed=False):
    """Bind a verified concept profile to seed generation and report actual coverage."""
    expected = make_profile(ranking, needs, decisions, schema_dir)
    require(profile == expected, "Profile is stale or edited; rebuild it from rankings and decisions")
    if needs["status"] == "operational":
        require(decisions["review_status"] == "reviewed", "Operational generation requires a reviewed profile; draft selections remain available for inspection")
        require(base_iri is not None, "Supply --base-iri explicitly for operational generation")
    base_iri = base_iri or kg.DEFAULT_BASE
    kg.validate_input("pilot", pilot)
    require((pilot["site"]["id"], pilot["study"]["id"]) == (profile["pilot_id"], profile["study_id"]), "Pilot setup does not match mapping profile")
    for participant in participants:
        kg.validate_input("participant", participant)
        require((participant["site_id"], participant["study_id"]) == (profile["pilot_id"], profile["study_id"]), "Participant does not belong to the profiled pilot/study")
    require(len({row["participant_id"] for row in participants}) == len(participants), "Duplicate participant input")
    registry_path = Path(output) / "validation/registry.json"
    if registry_path.exists():
        previous = kg.read_json(registry_path)
        require(all((r["kind"] == "pilot" and r["id"] == profile["pilot_id"]) or (r["kind"] == "participant" and (r["site_id"], r["study_id"]) == (profile["pilot_id"], profile["study_id"])) for r in previous["entries"].values()), "Use a separate output folder for each pilot concept profile")
    # The existing generator retains its explicit mappings and all validation.
    # Binding the profile records its scope without inventing missing values.
    runs = [kg.generate("pilot", pilot, output=output, schema_dir=schema_dir, base=base_iri, replace_seed=replace_seed)]
    runs += [kg.generate("participant", row, output=output, schema_dir=schema_dir, base=base_iri, replace_seed=replace_seed) for row in participants]
    registry = kg.read_json(Path(output) / "validation/registry.json")
    instance_data = Graph()
    for row in registry["entries"].values():
        instance_data += Graph().parse(Path(output) / row["file"], format="turtle")
    schema, _, _, _ = ontology_data(schema_dir)
    coverage = []
    # Count seed instances only, rather than treating imported vocabulary as pilot data.
    for row in profile["accepted_mappings"]:
        cls = URIRef(row["class_iri"])
        instances = sorted({str(subject) for subject, type_ in instance_data.subject_objects(RDF.type) if type_ == cls or cls in schema.transitive_objects(type_, RDFS.subClassOf)})
        coverage.append({"requirement_id": row["requirement_id"], "class_iri": row["class_iri"], "instances": instances, "status": "REPRESENTED_IN_GENERATED_SEEDS" if instances else "ADDITIONAL_INPUT_PROFILE_OR_DATA_REQUIRED"})
    report = {"status": "GENERATED_WITH_EXPLICIT_COVERAGE_LIMITS", "profile_sha256": kg.digest(kg.canonical(profile)), "pilot_id": profile["pilot_id"], "study_id": profile["study_id"], "source_status": needs["status"], "base_iri": base_iri, "registry_sha256": kg.digest(kg.canonical(registry)), "review_status": profile["review_status"], "reviewer": decisions["reviewer"], "coverage": coverage, "generation_runs": [{k: r[k] for k in ("status", "file", "shacl_conforms")} for r in runs]}
    save(Path(output) / "validation/pilot-concept-profile.json", profile)
    save(Path(output) / "validation/profile-coverage.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    initialise = sub.add_parser("init", help="Create an editable operational needs template without requiring data or the encoder")
    initialise.add_argument("--pilot-id", required=True)
    initialise.add_argument("--study-id", required=True)
    initialise.add_argument("--output", type=Path, required=True)
    validate = sub.add_parser("validate", help="Check a completed needs input and optionally its bound review without generating files")
    validate.add_argument("--needs", type=Path, required=True)
    validate.add_argument("--rankings", type=Path)
    validate.add_argument("--decisions", type=Path)
    validate.add_argument("--schema-dir", type=Path, default=kg.DEFAULT_SCHEMA)
    for name in ("rank", "profile", "generate"):
        command = sub.add_parser(name)
        command.add_argument("--needs", type=Path, default=ROOT / "examples/pilot-needs.json")
        command.add_argument("--output", type=Path, default=ROOT / "outputs")
        command.add_argument("--schema-dir", type=Path, default=kg.DEFAULT_SCHEMA)
        if name == "rank":
            command.add_argument("--encoder-python", default=sys.executable)
            command.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL)
            command.add_argument("--cache-dir", type=Path, help="Embedding cache; operational runs default to <output>/.cache")
        else:
            command.add_argument("--rankings", type=Path, help="Defaults to <output>/rankings.json")
            command.add_argument("--decisions", type=Path, required=True)
        if name == "generate":
            command.add_argument("--profile", type=Path, help="Defaults to <output>/pilot-profile.json")
            command.add_argument("--pilot", type=Path, required=True)
            command.add_argument("--participant", type=Path, action="append", default=[])
            command.add_argument("--base-iri", help="Stable instance namespace ending in /; explicit for operational inputs")
            command.add_argument("--replace-seed", action="store_true", help="Intentionally correct managed seeds and archive their previous versions")
    args = parser.parse_args()
    try:
        if args.command == "init":
            require(all(ID.fullmatch(value) for value in (args.pilot_id, args.study_id)), "Invalid pilot/study identifier")
            destination = args.output / "pilot-needs.json"
            require(not destination.exists(), "Template already exists; choose a new output folder")
            template = kg.read_json(ROOT / "templates/pilot-needs.json")
            template.update(pilot_id=args.pilot_id, study_id=args.study_id)
            save(destination, template)
            summary = {"status": "NEEDS_TEMPLATE_CREATED", "file": str(destination), "next_step": "Complete owner, source, requirement text and source references; then run validate"}
        elif args.command == "validate":
            needs = kg.read_json(args.needs)
            validate_needs(needs)
            require(bool(args.rankings) == bool(args.decisions), "Supply both --rankings and --decisions to validate a review")
            summary = {"status": "VALID", "source_status": needs["status"], "requirements": len(needs["requirements"])}
            if args.decisions:
                profile = make_profile(kg.read_json(args.rankings), needs, kg.read_json(args.decisions), args.schema_dir)
                summary["profile_status"] = profile["status"]
        elif args.command == "rank":
            result = rank(args.needs, args.output, args.encoder_python, args.model_dir, args.schema_dir, args.cache_dir)
            summary = {"status": result["status"], "requirements": len(result["requirements"]), "candidate_classes": result["candidate_count"]}
        else:
            ranking, needs, decisions = kg.read_json(args.rankings or args.output / "rankings.json"), kg.read_json(args.needs), kg.read_json(args.decisions)
            if args.command == "profile":
                result = make_profile(ranking, needs, decisions, args.schema_dir)
                save(args.output / "pilot-profile.json", result)
                summary = {"status": result["status"], "accepted_mappings": len(result["accepted_mappings"]), "open_requirements": len(result["unresolved_requirements"])}
            else:
                result = generate_from_profile(kg.read_json(args.profile or args.output / "pilot-profile.json"), ranking, needs, decisions, kg.read_json(args.pilot), [kg.read_json(p) for p in args.participant], args.output / "generated", args.schema_dir, args.base_iri, args.replace_seed)
                summary = {"status": result["status"], "represented_mappings": sum(row["status"] == "REPRESENTED_IN_GENERATED_SEEDS" for row in result["coverage"]), "additional_input_needed": sum(row["status"] != "REPRESENTED_IN_GENERATED_SEEDS" for row in result["coverage"])}
    except (kg.InputError, OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(2, f"ERROR: {error}\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
