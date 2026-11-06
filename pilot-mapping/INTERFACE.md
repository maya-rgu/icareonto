# Pilot Mapper input and command interface

The same scripts accept operational pilot requirements and the supplied synthetic examples. Completing documented input files is sufficient; no Python changes are needed to rank requirements, record mapping decisions or generate the supported enrolment graphs.

The **Pilot Mapper** uses the **KG Instantiator** for pilot/participant graph generation. See [the tool overview](../TOOLS.md). The combined interface below retains its strict input contract; fillable JSON templates and direct current-record refresh are documented in the [KG Instantiator guide](../instantiation/README.md).

Use one working/output folder per pilot. The examples below use `python` for the environment containing `instantiation/requirements.txt`. The encoder can run in the same environment or another selected with `--encoder-python`. Use `--encoder-python` to select the environment containing the encoder dependencies. No developer-specific Python path is required.

## 1 Prepare the requirement input

Create a template without needing the encoder or any participant data:

```bash
pilot_work="/path/to/pilot-work"
python pilot-mapping/scripts/pilot_mapping.py init --pilot-id SITE_ID --study-id STUDY_ID --output "$pilot_work/inputs"
```

Replace `SITE_ID` and `STUDY_ID` with stable identifiers. Complete `inputs/pilot-needs.json` with the responsible owner, a source description and each pilot knowledge need. Each operational requirement must retain its original identifier or document reference in `source_refs`. A ready-to-copy blank file is also available at `templates/pilot-needs.json`.

| Field | Required | Meaning |
|---|---|---|
| `schema_version` | Yes | `"1.1"` for operational inputs |
| `pilot_id`, `study_id` | Yes | Must match the pilot setup and participant enrolment files |
| `language` | Yes | `"en"` for the current English encoder; this is independent of participant language preferences |
| `status` | Yes | `"operational"` or `"synthetic_demonstration"`; identifies source context |
| `owner` | Operational inputs | Team, role or person responsible for the requirements |
| `source` | Yes | Description of the original requirements/documents |
| `requirements[].id` | Yes | Unique requirement identifier, stable between revisions |
| `requirements[].text` | Yes | Readable English knowledge need; do not prescribe an expected class just to influence ranking |
| `requirements[].source_refs` | Operational inputs | Original requirement IDs, form sections or source-document references |

Identifiers contain letters, digits, underscores or hyphens, start with a letter or digit, and have at most 80 characters. Supply 1–200 requirements, with at most 2000 characters per description. Descriptions must also fit the encoder's token limit; overlong text is rejected explicitly. Unfilled placeholders and unknown input fields are rejected.

The machine-readable contract is [schemas/needs.schema.json](schemas/needs.schema.json). Legacy version 1.0 synthetic inputs remain supported.

Validate before running the model:

```bash
python pilot-mapping/scripts/pilot_mapping.py validate --needs "$pilot_work/inputs/pilot-needs.json"
```

## 2 Rank candidate ontology classes

```bash
python pilot-mapping/scripts/pilot_mapping.py rank --needs "$pilot_work/inputs/pilot-needs.json" --output "$pilot_work/mapping" --encoder-python /path/to/embedding-env/bin/python --model-dir /path/to/local/model-snapshot
```

`--encoder-python` defaults to the main Python interpreter. `--model-dir` defaults to the existing pinned local all-MiniLM-L6-v2 snapshot described in the README. Provide a complete copy of that model when running elsewhere. Neither requirements nor participant data are sent to an external inference service.

The command writes:

- `rankings.json`: all candidates, scores, requirement source references, source context, owner and model/ontology/input hashes.
- `top-candidates.tsv`: the first ten candidates per requirement for convenient inspection.
- `review-template.json`: a draft operational review record bound to this exact input/ranking, with all decisions pending.

The scorer takes ontology classes from `serialisation/` by default. Use `--schema-dir /path/to/serialisation` to select another compatible release. `--cache-dir` chooses an embedding cache; operational runs default to `<output>/.cache` so different pilot workspaces are separate.

## 3 Record mapping decisions

Copy the generated review template to a working input file:

```bash
cp "$pilot_work/mapping/review-template.json" "$pilot_work/inputs/review.json"
```

Fill in `reviewer` and record one decision for every requirement. Leave the generated input and ranking hashes unchanged. Re-ranking changed requirements or a changed ontology requires a new review of the corresponding ranking.

| Field | Meaning |
|---|---|
| `review_status` | `"draft"` while considering mappings; `"reviewed"` when the stated review has been completed |
| `reviewer` | Actual reviewer identity or responsible role |
| `reviewed_at` | Required for `"reviewed"`; full date-time with `Z` or an explicit UTC offset |
| `decisions[].requirement_id` | An ID from the requirement set; every requirement appears exactly once |
| `decisions[].decision` | `"accepted"`, `"rejected"`, `"needs_review"` or `"no_match"` |
| `decisions[].classes` | For accepted decisions, one or more class names or full IRIs; empty for other decisions |
| `decisions[].rationale` | Reason for the decision, including gaps or reservations |

A selected class may come from anywhere in the complete catalogue, not just the top ten. Its actual score/rank is retained. A class requiring an absent relation or unavailable data should be documented accordingly; a high score alone is not an accepted mapping.

The machine-readable contract is [schemas/review.schema.json](schemas/review.schema.json). `draft` profiles can be built and inspected. The generator uses a `reviewed` profile for operational inputs. Review metadata records the supplied review; the script is not an identity-verification or institutional approval system. Synthetic examples retain their explicit demonstration status and cannot be relabelled as operational review decisions.

Build a profile:

```bash
python pilot-mapping/scripts/pilot_mapping.py profile --needs "$pilot_work/inputs/pilot-needs.json" --decisions "$pilot_work/inputs/review.json" --output "$pilot_work/mapping"
```

By default, `profile` reads `<output>/rankings.json` and writes `<output>/pilot-profile.json`. `--rankings` can select another ranking file. The profile retains source references, review details, scores, selected classes, relevant modules, adjacent relationships and unresolved needs. Draft selections are explicitly labelled provisional.

Optionally validate the completed review without writing output:

```bash
python pilot-mapping/scripts/pilot_mapping.py validate --needs "$pilot_work/inputs/pilot-needs.json" --rankings "$pilot_work/mapping/rankings.json" --decisions "$pilot_work/inputs/review.json"
```

## 4 Generate the supported pilot and participant graphs

Complete the existing [pilot](../instantiation/templates/pilot.json) and [participant](../instantiation/templates/participant.json) initialisation templates. Their fields are described in [the field guide](../instantiation/FIELD_GUIDE.md). Save them in the pilot input folder, using matching site/study identifiers.

Choose a stable namespace for the deployment's individual entities and provide it explicitly:

```bash
python pilot-mapping/scripts/pilot_mapping.py generate --needs "$pilot_work/inputs/pilot-needs.json" --decisions "$pilot_work/inputs/review.json" --pilot "$pilot_work/inputs/pilot.json" --participant "$pilot_work/inputs/participant-001.json" --output "$pilot_work/mapping" --base-iri "https://your-project.example/instances/"
```

Replace the illustrative namespace with the namespace chosen for the deployment. It is an identifier base, so it does not need a running web server. Add another `--participant` for each additional input, or omit participants to initialise only the pilot. `--rankings` and `--profile` override the corresponding files under `<output>`.

Outputs appear under `<output>/generated/`:

| Output | Purpose |
|---|---|
| `pilots/`, `participants/` | Linked Turtle seed graphs |
| `dataset.ttl` | Combined entry for local ontology inspection |
| `dataset.trig` | Separate instance named graphs |
| `catalog-v001.xml` | Local ontology import mappings |
| `validation/pilot-concept-profile.json` | Exact concept profile used for this pilot |
| `validation/profile-coverage.json` | Review provenance, namespace and per-concept instance coverage |
| Other `validation/` files | Input/output hashes, generator registry and graph-validation results |

Repeating unchanged inputs preserves existing seeds. Intentional seed corrections use `--replace-seed`, which archives the previous seed; additional enrolments or a change of enrolment identity require a separate update workflow. Keep the base namespace stable and use a separate output folder for each pilot profile.

The generator supports the documented pilot/enrolment fields and optional grouped ontology records, including clinical history, measurements, cardiovascular risk and care activities. See the [section guide](../instantiation/SECTIONS_GUIDE.md) for the record structure. This combined interface accepts fully completed JSON; the direct KG Instantiator also prepares fillable templates. Selected concepts without supplied instances remain in the coverage report as requiring additional inputs; they are not silently populated. The generator exports Turtle and JSON-LD. Storage in a live graph server and ongoing event ingestion are separate integrations.

## Command results and reproducibility

Successful commands print a short JSON summary and exit with code 0. Input/reference/review errors print `ERROR:` and exit with code 2. A failed dependency process also returns a command failure. The ranking command never automatically accepts a concept, and validation does not create graphs.

The input, ontology, ranking, review and generated registry are linked by hashes. Changing requirements, the ontology or review selections requires the corresponding profile to be rebuilt. This prevents an old review or manually edited profile from being silently reused with different inputs.

Run `scripts/check_operational_interface.py` to reproduce the interface tests. They exercise operational input formats using wholly fictional data in temporary directories, including a custom namespace, source references, review states and controlled corrections. See [the test report](reports/OPERATIONAL_INTERFACE_CHECKS.md). Real pilot data are not needed to verify this interface.
