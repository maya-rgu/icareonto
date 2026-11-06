#!/usr/bin/env python3
"""Validate using a configured Protégé bundle with OWLAPI, HermiT and Java 11 jjs.

The bundle location is supplied through --protege-app or ICARE_PROTEGE_APP.
This launcher supports the application-bundle layout containing a Contents
directory. No GUI is launched; nested jars are extracted to a temporary folder.
"""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile
import zipfile

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--protege-app", type=Path, default=os.environ.get("ICARE_PROTEGE_APP"), help="Protégé application-bundle location; alternatively set ICARE_PROTEGE_APP")
parser.add_argument("--output", type=Path, default=root)
parser.add_argument("--ontology-file", type=Path, help="Optional alternate entry file, e.g. a knowledge graph importing the ontology")
parser.add_argument("--report", type=Path, help="Optional alternate JSON report location")
args = parser.parse_args()
if args.protege_app is None:
    parser.error("Supply --protege-app or set ICARE_PROTEGE_APP to a compatible Protégé bundle")
contents = args.protege_app.expanduser().resolve() / "Contents"
bundles = sorted((contents / "bundles").glob("*.jar"))
hermit = sorted((contents / "plugins").glob("org.semanticweb.hermit-*.jar"))
jjs = contents / "jre" / "bin" / "jjs"
if not bundles or not hermit or not jjs.exists():
    raise SystemExit("This validator requires a Protégé installation with OWLAPI, HermiT and Java 11 jjs. Supply --protege-app.")
with tempfile.TemporaryDirectory(prefix="icareonto-owlapi-") as tmp:
    jars = bundles + hermit
    nested = []
    for jar in jars:
        with zipfile.ZipFile(jar) as z:
            for name in z.namelist():
                if name.endswith(".jar"):
                    dest = Path(tmp) / (jar.stem + "-" + Path(name).name)
                    dest.write_bytes(z.read(name))
                    nested.append(dest)
    entry = (args.ontology_file or (args.output / "icareonto.ttl")).resolve()
    report = (args.report or (args.output / "validation/owlapi-report.json")).resolve()
    cmd = [str(jjs), "-J-Xmx2g", "-cp", os.pathsep.join(map(str, jars + nested)), str(root / "scripts" / "validate_protege.js"), "--", str(args.output.resolve()), str(entry), str(report)]
    subprocess.run(cmd, check=True)
