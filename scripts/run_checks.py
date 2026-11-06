#!/usr/bin/env python3
"""Run the public package's reproducible checks from any current directory."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--with-encoder", action="store_true", help="Also test live ranking; configure ICARE_ENCODER_PYTHON and optionally ICARE_MODEL_DIR")
    args = parser.parse_args()
    checks = [
        "serialisation/scripts/check_outputs.py",
        "instantiation/scripts/check_workflow.py",
        "instantiation/scripts/check_instantiator.py",
        "instantiation/scripts/check_sections.py",
        "pilot-mapping/scripts/check_mapping.py",
        "education/scripts/check_workflow.py",
        "validation/scripts/check_demo.py",
        "validation/scripts/run_cq_suite.py",
        "scripts/check_publication.py",
    ]
    if args.with_encoder:
        checks.append("pilot-mapping/scripts/check_operational_interface.py")
    results = []
    for script in checks:
        print(f"Checking {script}", flush=True)
        result = subprocess.run([sys.executable, str(ROOT / script)], cwd=ROOT)
        results.append({"script": script, "exit_code": result.returncode, "status": "PASS" if result.returncode == 0 else "FAIL"})
    report = {"run_date": datetime.now(timezone.utc).date().isoformat(), "status": "PASS" if all(r["status"] == "PASS" for r in results) else "FAIL",
              "live_encoder_requested": args.with_encoder, "checks": results,
              "scope": "Reproducible software and query checks; formal OWL conformance and clinical validity are separate."}
    folder = ROOT / "validation/reports"; folder.mkdir(exist_ok=True)
    (folder / "check-summary.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["status"] == "PASS" else 1)
