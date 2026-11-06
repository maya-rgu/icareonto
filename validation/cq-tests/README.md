# Full competency-question test suite

This suite exercises all 78 canonical questions in `icareonto_final_consolidated_competency_questions_v5.xlsx` against iCARE Onto `0.1.0-draft`. It adds a separate, wholly fictional coverage supplement to the existing Spanish survivor graph. It changes neither the ontology nor the original graph.

Read [the validation report](../reports/CQ_VALIDATION_REPORT.md) for per-CQ outcomes and items requiring review. The JSON and TSV versions include complete expected/actual bindings and source CQ identifiers.

## What to open

Open `coverage.ttl` in Protégé and keep the surrounding project folders together. Its local import catalogue loads the Spanish survivor graph and the ontology modules. This test entry includes the contrasting data used to expose broader-than-intended answers; opening it is distinct from opening the simpler Spanish demonstration alone.

## Test design

Each canonical CQ has an individual `.rq` query, source wording and IDs, a specific input context, and an authored, nonempty expected answer. Constants in `../scripts/build_cq_suite.py` define expected answers independently of query execution. Schema enumerations have explicit expected lists. For example, CQ-035 includes DietaryPattern because the ontology defines it as a subclass of NutritionBehaviour, which is a LifestyleBehaviour subclass.

Queries execute over an explicit RDF union in RDFLib. They use SPARQL property paths for subclass traversal; no OWL inference is materialised during query execution. Numeric values are compared with datatype-aware value equality. CQ-043 checks chronological order; the other comparisons check exact unordered multisets, so extra unwanted answers fail the comparison.

The positive fixtures cover risk contributions, treatment history, clinical records, educational metadata, social context, measurements, nutrition, exercise, care plans and trigger associations. Contrasting data include another person, a check-up in another care plan, unrelated topics, prescribed/performed activities, and observations before or exactly at the excluded end of a time window.

Four controls additionally check another participant, an unknown participant, a deliberately removed bridge in the resource-to-goal integration path, and performed versus prescribed duration. Triple removal occurs in a disposable graph only.

The two earlier question/model review items have been addressed in the updated sources and fixtures:

- **CQ-019:** The revised question asks which resources address nutrition as a topic. Both the nutrition-focused resource and the mixed-topic resource are expected matches.
- **CQ-051:** The new `measurementInstrumentHasValidationEvidence` relation identifies validation evidence. The expected answer excludes a separately cited background source, including when both are linked through `dcterms:source`.

The explicit expected answers follow the revised specifications and are not derived from query output. Unexpected extra or missing bindings still fail the comparison.

The fixture also makes explicit interpretation choices. Anthropometric and physiological types are asserted where needed; body-composition membership follows protocol links; trigger queries retrieve authored associations and do not demonstrate actual initiation or execution. All conditions, thresholds, references, evidence and scores are technical fiction, not clinical guidance or real validation evidence.

## Outputs

| Location | Content |
|---|---|
| `coverage.ttl` | Additional test data, importing the original demonstration graph |
| `catalog-v001.xml` | Portable local import resolution |
| `queries/` | 78 canonical queries plus four controls |
| `cases.json` | Authored expected answers, source traceability and interpretation notes |
| `validation/import-map.tsv` | Local map for the existing OWLAPI validator |
| `../reports/CQ_VALIDATION_REPORT.md` | Validation methods, per-question results and limitations |
| `../reports/cq-results.json` | Complete results, comparisons, source hashes and validation summary |
| `../reports/cq-results.tsv` | Flat per-CQ results for filtering or later import into a workbook |
| `../reports/cq-owlapi-report.json` | OWLAPI/HermiT results for the complete fixture imports closure |

## Reproduction

Use a Python environment with `rdflib` installed, as described in `../../serialisation/README.md`. From the project root:

```bash
python validation/scripts/build_cq_suite.py
python serialisation/scripts/validate_with_protege.py \
  --protege-app /path/to/Protege.app \
  --output validation/cq-tests \
  --ontology-file validation/cq-tests/coverage.ttl \
  --report validation/reports/cq-owlapi-report.json
python validation/scripts/run_cq_suite.py
```

The OWLAPI validator uses the installed Protégé Java runtime; the query runner itself only needs Python and RDFLib. Reports identify whether the separate reasoner report was available. The runner exits unsuccessfully on undeclared terms, type mismatches, query errors or unexpected mismatches. Known review items are reported as `COMPLETE_WITH_REVIEW_ITEMS`, never as an overall pass.

If the source CQ register changes, rebuild the suite and review its explicit query and expected-answer definitions. An identifier-set assertion prevents silent omission of canonical CQs. The JSON report records hashes of the source register, RDF inputs, query files and case specification.

Full question coverage means one test context per canonical question. It does not establish exhaustive scenario coverage, clinical validity, production interoperability, or real participant safety.
