# Grouped pilot and participant knowledge records

The KG Instantiator accepts optional `sections` alongside the existing enrolment fields. The sections can be completed gradually. They use actual ontology classes and properties rather than placing clinical information in free-text person attributes. The same interface validates supplied records against the deployed ontology on every run.

Start with [the participant template](templates/participant.json) and [the complete fictional example](examples/participant-es-full.json). The example connects clinical conditions, symptoms, medications, cancer diagnosis and treatment exposure, measurements, cardiovascular risk, a care plan, prescribed exercise and performed exercise. It is test data, not a clinical recommendation or a validated risk calculation.

## Input organisation

| Section                               | Typical records                                                                          |
| ------------------------------------- | ---------------------------------------------------------------------------------------- |
| `clinical_profile`                  | Clinical profile, conditions, symptoms, medication and assessment records                |
| `cancer_history`                    | Cancer diagnoses, stages, treatment history, treatment records and exposures             |
| `measurements`                      | Measurements, observation results, units, instruments and protocols                      |
| `cv_risk`                           | Supplied risk profiles, estimates, categories, model inputs and model executions         |
| `care_plans`                        | Care plans, goals, interventions, referrals and triggers                                 |
| `exercise`                          | Prescriptions, prescribed activities, planned sessions, performed sessions and adherence |
| `nutrition`                         | Nutrition instructions, dietary components and action types                              |
| `lifestyle`                         | Lifestyle profiles, behaviour records, barriers and facilitators                         |
| `social_context`                    | Literacy, support, social circumstances and access barriers                              |
| `education`                         | Knowledge resources, recommendations and resource classifications                        |
| `dialogue`, `agents`              | Dialogue records and agent context                                                       |
| `digital_services`                  | Health Hub services, devices and service use                                             |
| `governance`                        | Consent, verification and graph context                                                  |
| `person_context`, `pilot_context` | Additional person/role and shared pilot records                                          |
| `common`                            | Timepoints, intervals, schedules, sources and other shared structures                    |

These groups organise input. The class and properties determine RDF meaning; a record's identifier remains the same if it moves to another group. All locally declared classes, object properties and data properties are available through this general record interface. This does not assert that every possible clinical workflow or class-specific completeness rule has been separately implemented or tested.

## Record structure and relationships

Each section contains `records` and/or `links`. A record has a stable `id`, an ontology `type`, optional `label`, `source` and `recorded_at`, and its supplied `properties`.

```json
{
  "clinical_profile": {
    "records": [
      {
        "id": "clinical-profile-1",
        "type": "ClinicalProfile",
        "properties": {
          "clinicalProfileIncludesRecord": {"ref": "condition-record-1"}
        }
      },
      {
        "id": "condition-record-1",
        "type": "ClinicalConditionRecord",
        "properties": {
          "conditionRecordRecordsCondition": {"ref": "condition-1"},
          "conditionRecordHasClinicalStatus": {"term": "ActiveClinicalStatus"}
        }
      },
      {
        "id": "condition-1",
        "type": "CardiovascularCondition",
        "properties": {"conditionName": "Supplied condition name"}
      }
    ],
    "links": [
      {
        "subject": "$person",
        "property": "personHasClinicalProfile",
        "object": {"ref": "clinical-profile-1"}
      }
    ]
  }
}
```

Place this object inside the participant input's `sections`. Record IDs accept letters, digits, underscores and hyphens, up to 80 characters, and must be unique across that participant's sections. New IDs identify new records; reuse an ID to update the same record. Local ontology names such as `ClinicalProfile` or full iCARE Onto IRIs are accepted. `type` can also be an array of explicitly supplied ontology classes.

For an object property, use `{"ref": "record-id"}` to link a supplied record, or `{"term": "ActiveClinicalStatus"}` for an existing ontology value. Forward references and references across sections are supported. A list represents several values. Data properties accept JSON strings, numbers or booleans according to the ontology's declared datatype. Dates use `YYYY-MM-DD`; date-times require a timezone. Numeric-looking strings are accepted only for decimal lexical values; boolean and integer fields require their actual JSON types. Property values set to `null` remain unasserted. A misspelled property is rejected even when its value is null.

The recognised datatype set covers the ten datatypes currently declared in iCARE Onto: string, decimal, non-negative integer, positive integer, boolean, date, date-time, language, URI and duration. For example, duration values use `PT30M`. Numeric ranges such as the meaning of a risk score depend on the supplied model; the software does not compute risk estimates or prescribe treatment.

### References to the generated setup

| Alias                  | Meaning                                        |
| ---------------------- | ---------------------------------------------- |
| `$person`            | This participant                               |
| `$site`              | Existing pilot site                            |
| `$study`             | Existing study                                 |
| `$enrolment`         | This participant's existing enrolment          |
| `$participant_graph` | The logical participant knowledge-graph entity |
| `$source`            | Participant input source entity                |
| `$recorded_at`       | Participant input recording timepoint          |
| `$locale`            | Shared locale; available in pilot inputs       |
| `$graph`             | The physical pilot or participant graph        |

Participant-only aliases are unavailable in pilot inputs. References to arbitrary undeclared record IDs are rejected. Additional records receive owner-scoped IRIs, for example `BASEpeople/<participant-id>/records/<record-id>` or `BASEsites/<site-id>/records/<record-id>`. Core enrolment identifiers are unchanged.

## Updating the record over time

1. Retain the existing JSON record and stable IDs.
2. Add sections or records when information becomes available. Keep separate record IDs for repeated observations, treatment events and performed sessions that need to remain in the history.
3. Change the properties of an existing ID when correcting that record. Include the source and original record time when known; graph-level recording metadata identifies the imported snapshot, not the clinical onset time.
4. Rerun the same KG Instantiator command. The current owner graph is rebuilt, the previous graph is archived, and the combined pilot/participant graph set is validated before publication.

Ontology and mapping fingerprints are recorded with each graph. A changed ontology or mapping regenerates that graph even if the JSON is unchanged, so the Turtle and JSON-LD exports remain aligned with the deployed model. Rerun each affected owner record after a model update.

The JSON is the complete current snapshot, not an incremental merge patch. Keep earlier records and sections in it if they should remain queryable. Removing an unreferenced record removes it from the active graph; removing a still-referenced record fails validation. An earlier graph remains in the archive. A change of participant ID creates a different person; the interface does not silently transfer an existing enrolment to another pilot.

Missing information remains unknown. For example, an absent condition record does not establish that a participant has no such condition; consuming agents should preserve that distinction.

Prescriptions and performance are separate. `ExercisePrescription` links to prescribed activities. `PlannedExerciseSession` follows the prescription. `PerformedExerciseSession` links to the planned session and its own performed activities. In the full example, prescribed duration is 30 minutes and recorded performance is 20 minutes. Updating the performed activity does not change the prescribed activity. The ontology stores supplied facts and relationships; logical reasoning and agent interpretation operate on that evidence rather than creating an unrecorded clinical decision.

## Ontology validation and field discovery

Validation checks the JSON structure, declared classes/properties, datatype values, vocabulary values, cross-record references, explicit domain/range compatibility and the existing SHACL constraints. It rejects invalid content before publishing. The runtime ontology is authoritative; the interface does not silently replace unknown terms with similar labels.

[The input reference](reference/ontology-input-reference.json) lists all 283 local classes and 421 object/data properties, their labels, definitions, domains/ranges, and existing named values. This enables form builders to present valid choices without hard-coding the ontology into the data-entry application. Regenerate it after an ontology update:

```bash
python instantiation/scripts/export_input_reference.py
```

The checks assess data structure and semantic compatibility. They do not verify a diagnosis, authenticate its source, validate a prediction model or judge whether a prescription is clinically appropriate. Class-specific completeness requirements can be added as reviewed SHACL profiles while retaining the same JSON structure.

The fuller example exposes an existing datatype compatibility issue in the ontology: `diagnosisDate` uses `xsd:date`. The input and RDF datatype checks accept the supplied valid date, and HermiT reports consistency, but OWLAPI flags that literal when checking the OWL 2 DL profile. The ontology also declares `xsd:duration`, which is outside the standard OWL 2 datatype map. These source-model datatypes are preserved; the exporter does not silently replace a date with a timestamp or string. The full example therefore does not have zero OWL 2 DL profile violations. See [the datatype review](reports/DATATYPE_COMPATIBILITY.md) and the [W3C OWL 2 datatype map](https://www.w3.org/TR/owl2-syntax/#Datatype_Maps).

## JSON-LD for the conversational agent

The KG Instantiator writes the same knowledge in several formats:

| File                                        | Use                                                                         |
| ------------------------------------------- | --------------------------------------------------------------------------- |
| `participants/<id>.ttl`                   | Participant RDF graph, convenient for Protégé and RDF tools               |
| `participants/<id>.jsonld`                | The same participant assertions as JSON-LD                                  |
| `pilots/<id>.ttl`, `pilots/<id>.jsonld` | Shared pilot graph in the two formats                                       |
| `dataset.trig`                            | Combined instance dataset preserving named graphs                           |
| `dataset.jsonld`                          | The same named-graph dataset in JSON-LD                                     |
| `dataset.ttl`                             | OWL import entry for local inspection; it does not duplicate all assertions |

JSON-LD adds an explicit context connecting JSON names to ontology IRIs. Its `id`, `type` and relation fields retain entity identity, datatype meaning and links across records. Each export has an inline context containing the properties it actually uses; no remote context retrieval is needed. The complete reusable context is in `reference/jsonld-context.json`.

JSON-LD and Turtle contain equivalent RDF, so choosing JSON-LD does not itself add reasoning or establish better LLM answers. For an agent interaction, retrieve the relevant participant facts and their dates, sources and related pilot context, then expose that bounded graph or query result through a tool. The entire dataset is an integration/export asset; it need not be included in every prompt. The current implementation exports the graphs and provides executable query examples; it does not deploy an avatar, SPARQL endpoint or an LLM reasoning service.

JSON-LD format reference: [W3C JSON-LD 1.1](https://www.w3.org/TR/json-ld11/).

## Reproduction

With the Python dependencies installed, run from the project root:

```bash
python instantiation/kg-instantiator.py pilot --input instantiation/examples/pilot-es-demo.json
python instantiation/kg-instantiator.py participant --input instantiation/examples/participant-es-full.json
python instantiation/scripts/check_sections.py
```

[The section test report](reports/SECTION_CHECKS.md) lists the checked behaviours. Query tests independently specify clinical, treatment, risk and exercise answers. Other tests cover adding sections later, record updates, invalid references, vocabulary/type errors, stable identities, JSON-LD/Turtle equivalence and JSON-LD/TriG named-graph equivalence.
