# Semantic mapping of pilot knowledge needs

This workflow ranks iCARE Onto classes for pilot-specific knowledge needs, records separate mapping decisions and binds the resulting concept profile to KG initialisation. The scripts accept operational pilot inputs through a documented interface; fictional examples demonstrate the same processing logic.

For a new pilot, start with [the input and command interface](INTERFACE.md). It includes fill-in templates, JSON Schemas and commands to initialise, validate, rank, review and generate graphs without editing Python.

The published regression baseline is in [tests/fixtures/](tests/fixtures/README.md). Run `python pilot-mapping/scripts/check_mapping.py` to reproduce its 31 checks without model weights. Live ranking requires the encoder dependencies and the pinned local model; `check_operational_interface.py` uses `ICARE_ENCODER_PYTHON` and optional `ICARE_MODEL_DIR` rather than a developer-specific environment. Run outputs and caches are deliberately excluded from the repository.

Read [the demonstration report](reports/PILOT_MAPPING_REPORT.md) for retrieval results, open mapping issues, graph coverage and limitations. Supplied requirements and decisions are explicitly agent-authored demonstration material. They are not actual Living Lab findings, expert approval or confirmed needs of a Spanish MAYA site.

## Workflow

```text
Pilot knowledge needs
              +
Ontology class labels, definitions and hierarchy context
              ↓
Local sentence embeddings and cosine similarity
              ↓
Ranked candidates, scores and a pending review template
              ↓
Separate mapping decisions and rationale
              ↓
Pilot concept profile with accepted mappings and open items
              ↓
Existing KG generator with pilot/profile identity checks
              ↓
Pilot and participant seed graphs plus a coverage record
```

The concept profile guides the selection of relevant concepts and the design of data-input mappings. The existing enrolment generator retains its explicit field-to-ontology mappings. It does not acquire new clinical fields solely because a concept scores highly. The coverage record identifies which selected classes have instances and which require additional profiles or data. The shared ontology is retained in full.

## Files

| Location                                       | Contents                                                                                       |
| ---------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| `examples/pilot-needs.json`                  | Fifteen fictional requirements linked to site `es-demo-01` and study `maya-demo`           |
| `examples/demo-review-decisions.json`        | Separate demonstration decisions: 14 accepted mappings and one unresolved requirement          |
| `templates/`, `schemas/`, `INTERFACE.md` | Operational input template, machine-readable contracts and command guide                       |
| `tests/reference-mappings.json`              | Separately specified evaluation references; never read by the scorer                           |
| `scripts/encode_texts.py`                    | Offline sentence-embedding worker                                                              |
| `scripts/pilot_mapping.py`                   | Candidate ranking, profile construction and profile-bound KG generation                        |
| `scripts/evaluate_mapping.py`                | Comparison with reference mappings and lexical baseline; report generation                     |
| `scripts/check_mapping.py`                   | Technical controls for rankings, review boundaries, stale inputs and KG generation             |
| `outputs/rankings.json`                      | All 283 class candidates for each requirement, scores and method/model provenance              |
| `outputs/top-candidates.tsv`                 | Ten highest-ranked candidates per requirement for inspection                                   |
| `outputs/review-template.json`               | Pending decisions; no mappings accepted automatically                                          |
| `outputs/pilot-profile.json`                 | Selected concepts, scores, decisions, relevant modules and supporting relationship suggestions |
| `outputs/generated/`                         | Separate pilot/participant graphs and the bound profile/coverage records                       |
| `reports/`                                   | Retrieval evaluation, technical checks and report-ready explanation                            |
| `cache/`                                     | Rebuildable embedding cache, excluded by `.gitignore`                                        |

The original ontology, Spanish survivor example, CQ tests and initialisation example outputs remain separate.

## Input and decision rules

Operational requirements use input version `"1.1"`, `status: "operational"`, pilot/study identifiers, English descriptions, an owner, source description and original `source_refs` for every requirement. Synthetic version 1.0 inputs remain supported. No expected class or target IRI is supplied to the scorer. IDs use the same letter/digit/underscore/hyphen convention as the initialisation templates. Each description is limited to 2000 characters and must also fit the encoder token limit; the run is rejected rather than silently truncating text. See `schemas/needs.schema.json` for the complete contract.

Operational review records distinguish `draft` and `reviewed` states, identify the reviewer, retain the exact input/ranking hashes and record a review date-time when completed. Synthetic examples retain `demonstration_annotation_not_site_approval`. Each requirement has exactly one decision: `accepted`, `rejected`, `needs_review` or `no_match`. Accepted decisions must name one or more declared local classes and provide rationale. Other decisions select no classes and retain their explanation. A reviewer can select a lower-ranked class; the actual rank and score remain visible. The supplied example decisions are illustrative annotations; operational decisions are supplied by the responsible pilot/domain team. See `schemas/review.schema.json`.

Copy the generated review template to a separate working file before recording decisions. Rerunning the rank command regenerates the pending template. The supplied `demo-review-decisions.json` is used only to reproduce this demonstration.

## Reproducing this example

Run from the project root. The existing ontology environment provides RDFLib, JSON Schema and SHACL validation. The existing `nlp` environment provides the embedding libraries. No installation or model download was required for this run.

```bash
python pilot-mapping/scripts/pilot_mapping.py rank --encoder-python python

python pilot-mapping/scripts/pilot_mapping.py profile --decisions pilot-mapping/examples/demo-review-decisions.json

python pilot-mapping/scripts/pilot_mapping.py generate --decisions pilot-mapping/examples/demo-review-decisions.json --pilot instantiation/examples/pilot-es-demo.json --participant instantiation/examples/participant-es-001.json --participant instantiation/examples/participant-es-002.json

python pilot-mapping/scripts/evaluate_mapping.py

python pilot-mapping/scripts/check_mapping.py
```

These demonstration commands write to `pilot-mapping/outputs/generated/`, preserving the earlier example package under `instantiation/generated/`. Operational commands select a working output folder and explicitly provide `--base-iri`. Repeating unchanged inputs retains seed identities. The wrapper supports intentional corrections through `--replace-seed` and archives old seeds; it does not silently overwrite changed seeds.

The optional OWLAPI/HermiT check uses the installed Protégé runtime:

```bash
python serialisation/scripts/validate_with_protege.py --protege-app /path/to/Protege.app --output pilot-mapping/outputs/generated --ontology-file pilot-mapping/outputs/generated/dataset.ttl --report pilot-mapping/outputs/generated/validation/owlapi-report.json
```

Open `outputs/generated/dataset.ttl` in Protégé to inspect the bound example. Its adjacent import catalogue resolves the unchanged ontology package. The profile is retained in `validation/pilot-concept-profile.json`; `validation/profile-coverage.json` connects the mapping decisions to the generated examples without asserting unsupported clinical facts in RDF.

## Dependencies and model portability

The tested interpreters are Python 3.12 environments. A fresh single environment can install `requirements.txt`, which also includes the initialisation dependencies. If using separate environments, the main scripts need `instantiation/requirements.txt`; the embedding worker needs the four model-runtime packages listed here. `--encoder-python` selects the worker interpreter and defaults to the main interpreter.

The default model is the locally cached `sentence-transformers/all-MiniLM-L6-v2` snapshot `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`. `--model-dir` can point to the same complete snapshot at another location. Prepare a trusted model snapshot separately if it is not available; the scorer never downloads it automatically. Model files are not copied into this project or redistributed. File hashes, installed runtime versions, dimensions, CPU execution and truncation checks are recorded with the ranking results. The model card identifies the model's Apache 2.0 licence.

The worker uses `local_files_only=True`, disables remote model code and runs on CPU. No requirement text or ontology content is sent to an external inference service. An ignored local embedding cache avoids re-encoding identical text/model combinations.

## Interpretation and limits

The semantic score is cosine similarity between sentence vectors computed from class labels, alternative labels, definitions and parent labels. A separate token-set Jaccard baseline quantifies lexical overlap. Candidate scores are not probabilities, automatic approvals, OWL equivalence statements or estimates of clinical suitability.

This initial implementation ranks all local **classes**. Adjacent object properties are subsequently listed as context for designing pilot mappings; they have not been independently scored or approved. Controlled values and external-standard alignments are not automatically mapped by this process. The general English encoder has not been evaluated for Spanish text or clinical-specialist interpretation.

The semantic top-ten list contains 13 of the 14 positive reference concepts. `InformationPreference` is a substantial miss at rank 82 (lexical rank 3) and remains visible in the saved rankings and evaluation results. Reviewers must be able to search the full class catalogue and explicitly select a concept outside the displayed shortlist. The supplied decision demonstrates this correction; it does not turn the retrieval miss into a successful top-ten result.

The small reference set contains 14 positive cases and one case with a pending mapping decision. It is separately specified but authored by the same agent as the synthetic example; it is not an independent expert gold standard, a training/test split or evidence of general performance across pilots. Retrieval misses are retained in the evaluation results. The ontology now resolves the earlier CQ-051 distinction through `measurementInstrumentHasValidationEvidence`. Its associated pilot mapping remains pending explicit review; the ontology update alone does not accept that mapping or add a new retrieval reference.

The same interface can be populated with confirmed pilot needs and reviewed mappings when available. English requirement descriptions are used with the current encoder; additional graph input profiles can be added for information beyond enrolment. The operational interface has been exercised with fictional test records, independently of actual pilot data. See [the interface checks](reports/OPERATIONAL_INTERFACE_CHECKS.md). The demonstration results establish measured technical behaviour rather than real-pilot validation.
