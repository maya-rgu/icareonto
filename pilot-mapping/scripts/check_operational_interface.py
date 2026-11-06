#!/usr/bin/env python3
"""Exercise the operational interface with fictional data and temporary outputs."""
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

from rdflib import Graph, RDF, URIRef

import pilot_mapping as pm


def main():
    checks = []
    def check(name, result, detail):
        if not result:
            raise AssertionError(name + ": " + detail)
        checks.append({"id": name, "status": "PASS", "detail": detail})
    def rejected(name, action, message):
        try:
            action()
        except pm.kg.InputError as error:
            check(name, message in str(error), "Rejected: " + message)
        else:
            raise AssertionError(name + ": accepted invalid input")
    script = pm.ROOT / "scripts/pilot_mapping.py"
    def cli(*args, success=True):
        result = subprocess.run([sys.executable, str(script), *map(str, args)], capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
        if success and result.returncode:
            raise AssertionError(result.stderr)
        return result
    demo = pm.kg.read_json(pm.ROOT / "examples/pilot-needs.json")
    demo_decisions = pm.kg.read_json(pm.ROOT / "examples/demo-review-decisions.json")
    # Fictional records exercise operational-format commands inside a disposable workspace.
    with TemporaryDirectory(prefix="icareonto-operational-interface-") as temp:
        root = Path(temp)
        template_dir, output = root / "inputs", root / "run"
        result = cli("init", "--pilot-id", "interface-test-site", "--study-id", "interface-test-study", "--output", template_dir)
        template = pm.kg.read_json(template_dir / "pilot-needs.json")
        check("INIT", template["status"] == "operational" and template["pilot_id"] == "interface-test-site" and "NEEDS_TEMPLATE_CREATED" in result.stdout, "CLI creates an operational template without requiring real data or an embedding run")
        result = cli("validate", "--needs", template_dir / "pilot-needs.json", success=False)
        check("UNFILLED-TEMPLATE", result.returncode == 2, "Unreplaced placeholders fail validation")
        result = cli("init", "--pilot-id", "interface-test-site", "--study-id", "interface-test-study", "--output", template_dir, success=False)
        check("NO-TEMPLATE-OVERWRITE", result.returncode == 2 and "already exists" in result.stderr, "Initialisation preserves a previously created working template")
        needs = deepcopy(demo)
        needs.update(schema_version="1.1", pilot_id="interface-test-site", study_id="interface-test-study", status="operational", owner="Fictional interface-test team", source="Fictional test of the operational input format; no actual pilot approval or real participant data")
        for row in needs["requirements"]:
            row["source_refs"] = ["INTERFACE-TEST/" + row["id"]]
        needs_path = root / "needs.json"
        pm.save(needs_path, needs)
        check("OPERATIONAL-NEEDS-VALIDATE", cli("validate", "--needs", needs_path).returncode == 0, "Completed source-referenced operational-format input passes validation")
        bad = deepcopy(needs)
        del bad["requirements"][0]["source_refs"]
        rejected("SOURCE-REF-REQUIRED", lambda: pm.validate_needs(bad), "source_refs")
        bad = deepcopy(needs)
        bad.pop("owner")
        rejected("OWNER-REQUIRED", lambda: pm.validate_needs(bad), "owner")
        # Reuse the exact model/text cache where available; the scorer still
        # processes these input files and writes a fresh, hash-bound ranking.
        # Live encoder integration is optional; callers select their own Python
        # environment and local model snapshot rather than a developer's paths.
        model_args = ["--model-dir", os.environ["ICARE_MODEL_DIR"]] if os.environ.get("ICARE_MODEL_DIR") else []
        cli("rank", "--needs", needs_path, "--output", output, "--cache-dir", root / "encoder-cache",
            "--encoder-python", os.environ.get("ICARE_ENCODER_PYTHON", sys.executable), *model_args)
        ranking = pm.kg.read_json(output / "rankings.json")
        draft = pm.kg.read_json(output / "review-template.json")
        check("OPERATIONAL-RANKING", ranking["source_status"] == "operational" and ranking["requirements_owner"] == needs["owner"] and all(r["source_refs"] for r in ranking["requirements"]), "Rankings retain operational provenance and original requirement references")
        check("DRAFT-REVIEW-TEMPLATE", draft["review_status"] == "draft" and all(r["decision"] == "needs_review" for r in draft["decisions"]), "Operational input creates a draft review bound to the exact ranking")
        draft["reviewer"] = "Fictional interface-test reviewer, not an actual pilot reviewer"
        draft["decisions"] = demo_decisions["decisions"]
        # Selecting classes in a draft must not imply that operational review is complete.
        decisions_path = root / "review.json"
        pm.save(decisions_path, draft)
        cli("profile", "--needs", needs_path, "--decisions", decisions_path, "--output", output)
        draft_profile = pm.kg.read_json(output / "pilot-profile.json")
        check("DRAFT-PROFILE", draft_profile["status"].startswith("DRAFT_PROFILE") and all(r["decision"] == "provisional_selection" for r in draft_profile["accepted_mappings"]), "Proposed selections may be inspected without claiming completed review")
        pilot = pm.kg.read_json(pm.ROOT.parent / "instantiation/examples/pilot-es-demo.json")
        pilot["site"]["id"], pilot["study"]["id"] = needs["pilot_id"], needs["study_id"]
        participants = [pm.kg.read_json(pm.ROOT.parent / "instantiation/examples" / name) for name in ("participant-es-001.json", "participant-es-002.json")]
        for row in participants:
            row.update(site_id=needs["pilot_id"], study_id=needs["study_id"])
        rejected("DRAFT-NOT-APPLIED", lambda: pm.generate_from_profile(draft_profile, ranking, needs, draft, pilot, participants, output / "generated"), "reviewed profile")
        check("NO-PREMATURE-GENERATION", not (output / "generated").exists(), "Draft profile rejection leaves no generated graph output")
        reviewed = deepcopy(draft)
        reviewed["review_status"] = "reviewed"
        rejected("REVIEW-TIME-REQUIRED", lambda: pm.make_profile(ranking, needs, reviewed), "reviewed_at")
        reviewed["reviewed_at"] = "2026-10-31T12:00:00Z"
        pm.save(decisions_path, reviewed)
        cli("validate", "--needs", needs_path, "--rankings", output / "rankings.json", "--decisions", decisions_path)
        cli("profile", "--needs", needs_path, "--rankings", output / "rankings.json", "--decisions", decisions_path, "--output", output)
        profile = pm.kg.read_json(output / "pilot-profile.json")
        check("REVIEWED-PROFILE", profile["status"].startswith("REVIEWED_PROFILE") and all(r["source_refs"] and r["decision"] == "accepted" for r in profile["accepted_mappings"]), "Reviewed-format profile retains source references, actual scores and recorded reviewer details")
        rejected("NAMESPACE-REQUIRED", lambda: pm.generate_from_profile(profile, ranking, needs, reviewed, pilot, participants, output / "generated"), "--base-iri")
        stale = deepcopy(reviewed)
        stale["ranking_sha256"] = "0" * 64
        rejected("STALE-REVIEW", lambda: pm.make_profile(ranking, needs, stale), "Review is stale")
        demo_review = deepcopy(demo_decisions)
        demo_review.update(pilot_id=needs["pilot_id"], study_id=needs["study_id"])
        rejected("NO-DEMO-APPROVAL", lambda: pm.make_profile(ranking, needs, demo_review), "Operational needs")
        base = "https://example.org/interface-test/instances/"
        pilot_path, participant_paths = root / "pilot.json", []
        pm.save(pilot_path, pilot)
        for i, row in enumerate(participants):
            path = root / f"participant-{i}.json"
            pm.save(path, row)
            participant_paths.append(path)
        generate_args = ["generate", "--needs", needs_path, "--rankings", output / "rankings.json", "--profile", output / "pilot-profile.json", "--decisions", decisions_path, "--pilot", pilot_path, "--output", output, "--base-iri", base]
        for path in participant_paths:
            generate_args.extend(["--participant", path])
        cli(*generate_args)
        registry = pm.kg.read_json(output / "generated/validation/registry.json")
        check("CUSTOM-NAMESPACE", registry["base_iri"] == base and len(registry["entries"]) == 3, "CLI generates the pilot and both participants using the supplied instance namespace")
        first_path = output / "generated/participants/es-demo-aya-001.ttl"
        graph = Graph().parse(first_path)
        check("REAL-IRI-OUTPUT", (URIRef(base + "people/es-demo-aya-001"), RDF.type, pm.IC.Person) in graph and not any(str(s).startswith(pm.kg.DEFAULT_BASE) for s in graph.subjects()), "RDF entities use the configured namespace rather than the demonstration default")
        coverage = pm.kg.read_json(output / "generated/validation/profile-coverage.json")
        check("REVIEW-TRACEABILITY", coverage["source_status"] == "operational" and coverage["review_status"] == "reviewed" and coverage["reviewer"] == reviewed["reviewer"] and coverage["base_iri"] == base, "Generation records operational-format provenance, reviewer, namespace and scope limits")
        before = first_path.read_bytes()
        # Repeated inputs preserve identity; changed inputs require explicit correction.
        cli(*generate_args)
        check("REPEAT-OPERATIONAL-INPUT", first_path.read_bytes() == before, "Repeated processing preserves the existing participant seed")
        participants[0]["preferences"]["detail_level"] = "detailed"
        pm.save(participant_paths[0], participants[0])
        result = cli(*generate_args, success=False)
        check("NO-SILENT-CORRECTION", result.returncode == 2 and first_path.read_bytes() == before, "Changed seed requires an explicit correction flag")
        cli(*generate_args, "--replace-seed")
        check("EXPLICIT-OPERATIONAL-CORRECTION", first_path.read_bytes() != before and bool(list((output / "generated/history/participant/es-demo-aya-001").glob("*.ttl"))), "Explicit correction archives the previous participant seed")
    report = {"status": "PASS", "checks": len(checks), "scope": "All data and reviewer identities are fictional. This tests the operational input/code paths; it does not assert that a real pilot review or deployment has occurred.", "cases": checks}
    pm.save(pm.ROOT / "reports/operational-interface-checks.json", report)
    lines = ["# Operational interface checks", "", f"All **{len(checks)} checks passed**.", "", report["scope"], "", "| Check | Result | Purpose |", "|---|---|---|"]
    lines.extend(f"| {row['id']} | PASS | {row['detail']} |" for row in checks)
    (pm.ROOT / "reports/OPERATIONAL_INTERFACE_CHECKS.md").write_text("\n".join(lines) + "\n")
    print(json.dumps({"status": "PASS", "checks": len(checks)}, indent=2))


if __name__ == "__main__":
    main()
