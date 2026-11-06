#!/usr/bin/env python3
"""Publish the ontology vocabulary accepted by grouped JSON records."""
import argparse
from pathlib import Path

import generate_kg as w
import section_records

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schema-dir", type=Path, default=w.DEFAULT_SCHEMA)
    parser.add_argument("--output", type=Path, default=w.ROOT / "reference")
    args = parser.parse_args()
    schema, paths = w.schema_package(args.schema_dir)
    reference = section_records.ontology_reference(schema)
    reference["ontology_files_sha256"] = {iri: w.digest(path.read_bytes()) for iri, path in sorted(paths.items())}
    w.atomic_write(args.output / "ontology-input-reference.json", w.canonical(reference))
    w.atomic_write(args.output / "jsonld-context.json", w.canonical({"@context": section_records.jsonld_context(schema)}))
    print(f"Exported {len(reference['classes'])} classes and {len(reference['properties'])} properties to {args.output}")
