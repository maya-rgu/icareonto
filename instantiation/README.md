# KG Instantiator

The **KG Instantiator** turns readable pilot-site and participant JSON records into ontology-conformant RDF. Optional grouped sections cover clinical profiles, cancer history, measurements, risk, care plans, prescribed/performed exercise and the other ontology areas. It exports both Turtle and JSON-LD. All supplied examples are fictional and separate from the shared survivor/CQ fixtures. [Tool roles](../TOOLS.md) describe the components and entry points.

Register a pilot site first, then enrol participants against its identifier. A shared pilot graph holds the study, site, locale, available phases and study arms. Each participant graph contains their person record, enrolment, logical participant-KG entity and any supplied preferences, attributes and consent metadata. It references the existing pilot entities rather than duplicating them.

## Quick start

Run from the project folder, with Python 3.10+ and dependencies from `requirements.txt`:

```bash
python instantiation/kg-instantiator.py pilot --input instantiation/examples/pilot-es-demo.json
python instantiation/kg-instantiator.py participant --input instantiation/examples/participant-es-001.json
python instantiation/kg-instantiator.py participant --input instantiation/examples/participant-es-002.json
python instantiation/kg-instantiator.py participant --input instantiation/examples/participant-es-full.json
```

Environment creation and activation are described in the [installation guide](../README.md). For a tool-only installation:

```bash
python -m pip install -r instantiation/requirements.txt
```

Commands use the activated environment's Python. Operation is offline once dependencies are installed. An IANA time-zone database is required; the Python `tzdata` package provides one on systems without it.

## Preparing inputs

1. Copy a file from `templates/` into your working input folder.
2. Replace the required angle-bracket placeholders. Leave unknown optional fields as `null`, omit them, or leave optional angle-bracket placeholders. The KG Instantiator omits these optional values rather than publishing placeholders. The templates include the optional fields supported by this input profile; fictional examples show completed values and array/object structures.
3. Read [FIELD_GUIDE.md](FIELD_GUIDE.md) for required/optional fields, allowed values and examples. The JSON Schemas in `schemas/` provide machine-readable descriptions and validation rules.
4. Generate the pilot before generating its participants. Each participant must reference an existing site/study pair and any phase or arm declared for that setup.

Use `--output /path/to/new-folder` for a separate deployment and `--base-iri https://your-project.example/instances/` to set its instance namespace. Keep the base IRI the same on every command for that output folder. The example namespace uses `example.org`; it does not identify real participants or sites. Ontology IRIs remain unchanged.

Input fields use readable names rather than ontology IRIs. [MAPPINGS.md](MAPPINGS.md) documents the mapping and controlled values. The generator checks input structure, dates, time-zone names, references, declared ontology terms, explicit domain/range compatibility, datatypes and SHACL constraints before publishing outputs. Required fields are requirements of this initialisation profile, not newly imposed OWL restrictions.

Complete the pilot's study/site identifiers and names, locale, recording time and source. Complete the participant's identifier, matching study/site identifiers, enrolment identifier/date/status, recording time and source. Preferences, age, survivor role, attributes, consent metadata, phases and arms can be supplied later. An optional structured record such as consent must contain its required fields once supplied. Supplied invalid values and unknown field names are rejected even when other fields remain unknown.

The participant template also includes optional `sections` for the ontology's other knowledge areas. Leave a section `null` until information is available, then add typed records and their relationships. See [SECTIONS_GUIDE.md](SECTIONS_GUIDE.md) for the structure, cross-section references, updates, JSON-LD exports and use by the conversational agent. [The full fictional example](examples/participant-es-full.json) demonstrates connected clinical, treatment, measurement, risk and exercise records. The [ontology input reference](reference/ontology-input-reference.json) lists every available local class/property and existing named values.

## Generated outputs

| Location under `generated/`                                         | Purpose                                                                        |
| --------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| `pilots/<site-id>.ttl`                                              | Shared pilot setup                                                             |
| `participants/<participant-id>.ttl`                                 | Individual participant seed, importing the relevant pilot graph and ontology   |
| `pilots/<site-id>.jsonld`, `participants/<participant-id>.jsonld` | The same owner graphs in JSON-LD with inline contexts                          |
| `dataset.ttl`                                                       | Entry ontology importing all registered pilot and participant graphs           |
| `dataset.trig`                                                      | Same instance graphs as separate named graphs, ready for later dataset loading |
| `dataset.jsonld`                                                    | The same instance dataset in JSON-LD, preserving named graphs                  |
| `catalog-v001.xml`                                                  | Offline import mappings; adjacent copies are also provided in the seed folders |
| `validation/registry.json`                                          | Managed outputs, stable graph identities and content/input hashes              |
| `validation/generation-report.json`                                 | Latest successful generation and validation summary                            |
| `validation/shacl-report.ttl`                                       | Latest graph-validation result                                                 |
| `validation/import-map.tsv`                                         | Local import mappings for the existing OWLAPI validator                        |
| `history/`                                                          | Archived seeds when an explicit correction is made                             |

`queries/enrolment-context.rq` demonstrates retrieving participant enrolment, shared site locale and independently supplied participant language preference from the combined instance graphs.

Open **`generated/dataset.ttl` in Protégé** to inspect the combined example, or open a seed directly. Keep this workflow and `serialisation/` in their relative project locations. `--schema-dir` can point to another compatible serialisation package; catalogues are generated using relative paths to that package. Moving only `generated/` will break those references.

The Turtle entry uses OWL imports for convenient local inspection. The TriG file contains instance named graphs only: a graph store must load the ontology separately and query the intended graph combination. Graph-store loading and access control are not performed by this script. Named-graph identifiers describe physical RDF contexts; `ParticipantKnowledgeGraph` remains the ontology's logical collection about the person.

## Progressive completion and refresh

Keep one current JSON file for each pilot and participant. Add further supported information as it becomes available, update `recorded_at` and `source` as appropriate, and rerun exactly the same command:

```bash
python instantiation/kg-instantiator.py pilot --input /path/to/pilot.json --output /path/to/generated
python instantiation/kg-instantiator.py participant --input /path/to/participant.json --output /path/to/generated
```

The first run creates the graph; changed input refreshes that graph and archives its previous version; identical input with the same ontology and mapping returns `UNCHANGED`. An updated ontology or mapping also triggers regeneration, preventing old Turtle from being paired with newly mapped JSON-LD. Entity identifiers remain stable. Updating shared pilot information does not rewrite participant graphs: they see it through the existing links. The pilot must already be registered in the same output deployment before a participant can reference it.

**The JSON is a complete snapshot of the supported current record, not a merge patch.** Retain known values when editing it. Omitting an optional field, setting it to `null`, or leaving an optional placeholder removes any previous assertion for that field when refreshing. Unknown values are never inferred from pilot defaults. Later clinical observations in separately managed graphs are not changed.

The entire managed graph set is validated again before publication, so removing a referenced arm or phase from a pilot setup is rejected. Participant refresh cannot change the enrolment identity, study or site. Additional enrolments require a separate history profile.

The lower-level `scripts/generate_kg.py` command remains compatible: it accepts strictly completed JSON and requires `--replace-seed` for changed inputs. Its new `--refresh` option exposes the same fillable-template behaviour as the named KG Instantiator. Existing callers of `generate()` retain the strict contract.

This snapshot generator expects one writer. Repeated observations and clinical events can be retained as distinct records in the JSON sections. It does not automatically merge partial JSON patches, maintain multiple enrolments or synchronise a graph store. Externally managed observations/interactions remain in their separate graphs. Editing managed Turtle or JSON-LD graph files manually is detected by content hashes and rejected. Individual file writes are atomic; a multi-file publication is not a database transaction. A future service needs write locking and transactional storage.

## Tests and OWL validation

```bash
python instantiation/scripts/check_workflow.py
python instantiation/scripts/check_instantiator.py
python instantiation/scripts/check_sections.py
python serialisation/scripts/validate_with_protege.py --protege-app /path/to/Protege.app --output instantiation/generated --ontology-file instantiation/generated/dataset.ttl --report instantiation/generated/validation/owlapi-report.json
```

The workflow check uses temporary outputs and includes independent checks for shared-site linking, distinct participant preferences, optional-field omission, repeated processing, seed correction, rejected inputs and broken graph constraints. Reports are written to `reports/`. The separate OWL validator requires the installed Protégé Java runtime described in `serialisation/README.md`.

The original suite covers 49 workflow checks. The 18 [KG Instantiator checks](reports/INSTANTIATOR_CHECKS.md) test fillable templates, refresh, snapshot omission and pilot dependencies. The [grouped-record checks](reports/SECTION_CHECKS.md) test connected clinical records, prescriptions versus performance, longitudinal additions, invalid ontology content and exact JSON-LD equivalence. All use temporary fictional outputs. Example logical-validation results are in `generated/validation/owlapi-report.json`.

## Scope and future integration

Enrolment fields provide a required minimum, while optional grouped records expose all declared local classes and object/data properties through an ontology-driven interface. This supports the clinical, cancer-history, risk, exercise and other areas without flattening them into textual `attributes`. The fuller example and query tests demonstrate the principal requested paths. Additional class-specific clinical completeness rules can be added as reviewed SHACL profiles; the current checks establish structure and semantic compatibility rather than clinical correctness.

Participant preferences are never inferred from site defaults. Survivor status is asserted only if supplied; age does not establish AYA eligibility. Consent metadata is optional and never defaults to granted. The current consent representation records status/dates and links to the logical graph; it does not implement consent purposes, verification or access enforcement. The supplied consent example is fictional.

The public Python function `instantiate(kind, data, output, schema_dir, base)` accepts a decoded fillable JSON object and creates or refreshes its graph. A later form/API can call this same function. `generate(kind, data, output, schema_dir, base, replace_seed)` remains the stricter lower-level interface. No UI, API server or live Fuseki connection is included.
