# Publication package validation

Validated on 5 November 2026 in a standalone copy using the repository's bundled inputs, fixtures and dependency specifications.

| Activity | Result |
|---|---|
| Release source snapshots | Four bundled workbooks verified against the source manifest |
| Source-to-ontology reconciliation | 4,254 checks passed |
| Ontology rebuild using bundled inputs | 22 rebuilt ontology graphs are semantically identical to the distributed graphs |
| KG initialisation workflow | 49 checks passed |
| Fillable-template and refresh interface | 18 checks passed |
| Grouped clinical records and JSON-LD | 30 checks passed |
| Saved pilot-ranking workflow | 31 checks passed against regenerated, current-ontology fixtures |
| Live encoder and operational mapping interface | 22 checks passed with a separately configured local encoder |
| Educational catalogue workflow | 40 checks passed |
| Canonical competency questions | All 78 expected answers matched; four controls passed |
| Shared demonstration smoke checks | 17 checks passed |
| Standalone public check runner | All nine commands passed |
| Reviewed educational catalogue | 16 eligible resources; one complete release package retained |
| Local import portability | Ontology, shared fixtures, educational catalogue and selected demo resolve within this repository |
| Ontology OWLAPI/HermiT | 22 documents; zero profile violations; consistent; no unsatisfiable named classes |
| CQ fixture OWLAPI/HermiT | 24 documents; zero profile violations; consistent; no unsatisfiable named classes |
| Educational example OWLAPI/HermiT | 26 documents; zero profile violations; consistent; no unsatisfiable named classes |

The fuller grouped clinical example retains the existing `diagnosisDate`/`xsd:date` OWL 2 DL compatibility finding described in [the datatype note](../../instantiation/reports/DATATYPE_COMPATIBILITY.md). The successful checks above do not remove that finding or establish clinical/predictive validity.

The fixed pilot-ranking baseline was recomputed against the packaged ontology; stale fingerprints were not bypassed. The test baseline is distributed without embedding caches or model weights. Source model/encoder provenance is retained in `pilot-mapping/tests/fixtures/rankings.json`.

The distributed assets include a current resource catalogue and a compact fictional educational example. Runtime outputs, histories and caches are excluded by the repository's ignore rules.

The core checks can be reproduced from the repository root with `python scripts/run_checks.py`. Live encoder integration is enabled with `--with-encoder` and the documented environment settings.
