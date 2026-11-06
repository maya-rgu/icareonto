# iCARE Onto tools and ontology

This repository contains the shared ontology and four tools supporting knowledge representation in the MAYA iCARE Health Hub. The ontology is **0.1.0-draft**, under review toward iCARE Onto Version 1. Participant and pilot examples are fictional.

| Tool                        | Purpose                                                                                                              | Documentation                              |
| --------------------------- | -------------------------------------------------------------------------------------------------------------------- | ------------------------------------------ |
| Ontology Serialiser         | Build the modular OWL ontology from the release source snapshots                                                     | [serialisation](serialisation/README.md)    |
| KG Instantiator             | Create and refresh pilot/participant knowledge graphs, including grouped clinical records; export Turtle and JSON-LD | [instantiation](instantiation/README.md)    |
| Pilot Mapper                | Rank ontology concepts against pilot knowledge needs and record reviewed mapping decisions                           | [pilot-mapping](pilot-mapping/INTERFACE.md) |
| Education Resource Selector | Publish reviewed resource metadata and select candidate educational signposts                                        | [education](education/README.md)            |

## Install and inspect

Use Python 3.10+ and run commands from the repository root:

```bash
python -m venv .venv
```

Activate the environment with `source .venv/bin/activate` on macOS/Linux or `.venv\Scripts\Activate.ps1` in Windows PowerShell, then install the dependencies:

```bash
python -m pip install -r requirements.txt
```

Open `serialisation/icareonto.ttl` in Protégé with its supplied modules, imports and catalogue. The ontology can be inspected without rebuilding it or installing Python.

## Run the workflows

```bash
python instantiation/kg-instantiator.py pilot --input instantiation/examples/pilot-es-demo.json
python instantiation/kg-instantiator.py participant --input instantiation/examples/participant-es-full.json
python education/scripts/education_resources.py select --output education/data/catalogue --request education/examples/spanish-cardiovascular.json
```

The pilot must exist before its participants. Instantiation inputs are current-record snapshots; retain earlier records when adding information. See [the section guide](instantiation/SECTIONS_GUIDE.md).

The educational catalogue contains metadata and links to reviewed resources, not copied provider content. Rebuild a local catalogue from the supplied workbook using `python education/scripts/education_resources.py build`; local results go under `education/generated/`. Use `--output education/generated` when selecting from that local build.

The Pilot Mapper's saved-ranking checks run without model weights. Live semantic ranking additionally needs the encoder dependencies in `pilot-mapping/requirements.txt` and the pinned local model described in its guide. Downloaded weights and embedding caches are not distributed here.

## Reproduce validation

```bash
python scripts/run_checks.py
```

This runs ontology/source reconciliation, instantiation, grouped-record, educational and saved-ranking workflow tests, and all 78 CQs with four additional controls. [Validation documentation](validation/README.md) explains the datasets and scope. The optional live encoder integration can be run with `--with-encoder` and a configured encoder environment. The public-file audit uses Git's ignore rules when Git is available; source-integrity and import checks also run without Git.

Formal OWL checking is separate. The ontology and original CQ fixtures have saved results. Populating `diagnosisDate` in the fuller participant example exposes an existing `xsd:date` OWL 2 DL profile compatibility issue; HermiT reports consistency. See [the recorded limitation](instantiation/reports/DATATYPE_COMPATIBILITY.md). Do not interpret passing workflow tests as clinical validation or as zero OWL profile violations for every dataset.

## Repository contents

- `sources/`: exact release input snapshots and integrity hashes.
- `serialisation/`: the ontology release, generator and reconciliation evidence.
- `instantiation/`, `pilot-mapping/`, `education/`: implementation, templates, schemas, examples and tests.
- `education/data/catalogue/`: one complete published catalogue snapshot, including its loader metadata.
- `validation/`: shared synthetic CQ fixtures, queries, runners and reports.
- `local/`: ignored working area for operational inputs and outputs.

A project licence and citation metadata have not yet been included in this snapshot.
