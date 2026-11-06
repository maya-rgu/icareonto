# Input fields

The JSON Schemas are the authoritative field definitions after template preparation. The named **KG Instantiator** accepts `null`, blank text or an angle-bracket placeholder for an unknown optional field and omits that field before validation. Required values must be supplied. Unknown field names and invalid supplied values are rejected. The lower-level `generate()` interface still rejects nulls and placeholders directly. JSON uses `true`/`false`, quoted strings and numeric values without quotes; it does not permit comments.

Each input is the complete current snapshot of this supported pilot or enrolment record. Keep known values when adding new information: optional fields omitted or left unknown will not be represented in the refreshed graph, even if supplied on an earlier run. An input must still include the required minimum identity/context fields. Register the pilot before referencing it in a participant record.

Identifiers accept letters, digits, underscores and hyphens, begin with a letter or digit and have at most 80 characters. Participant and site identifiers are unique across one output deployment; phase and arm identifiers are scoped to their study. Use pseudonymous participant identifiers. These rules are specific to this input profile.

All timestamps use a full ISO-style date-time with seconds and `Z` or an explicit UTC offset, for example `2026-10-15T10:00:00+02:00`. Fractional seconds are accepted; leap seconds are outside this profile. The supplied instant is preserved; a site's time zone does not supply a missing offset. An explicit date-time format checker validates both calendar values and offsets. `enrolled_at` must be no later than `recorded_at`.

## Common fields

| Field | Required | Meaning |
|---|---|---|
| `schema_version` | Yes | `"1.1"` for grouped records; `"1.0"` remains accepted for existing inputs; independent of ontology version |
| `recorded_at` | Yes | When these statements were recorded |
| `source` | Yes | Short source description; recorded as graph metadata and, for participant statements, a source entity |

## Pilot setup

| Field | Required | Meaning and example |
|---|---|---|
| `study.id` | Yes | Shared study identifier, e.g. `maya-demo` |
| `study.name` | Yes | Study display name |
| `study.phases` | No | Array of `{ "id": "feasibility", "name": "Feasibility phase" }` records |
| `study.arms` | No | Array of `{ "id": "intervention", "name": "Intervention arm" }` records |
| `site.id` | Yes | Site identifier, e.g. `es-demo-01` |
| `site.name` | Yes | Site display name |
| `site.locale.language_tag` | Yes | Site locale such as `es-ES`; this profile accepts two/three lowercase language letters and two uppercase country letters |
| `site.locale.country_code` | Yes | Two uppercase country letters matching the locale suffix; syntax checked without an ISO registry lookup |
| `site.locale.time_zone` | Yes | IANA zone, e.g. `Europe/Madrid`, checked against the runtime database |

Each phase/arm requires both `id` and `name`; repeated identifiers in the same array are rejected. Sites sharing a study should use consistent names for shared study entities. Pilot setup does not assign participant preferences, study arms or clinical facts.

## Participant enrolment

| Field | Required | Meaning and example |
|---|---|---|
| `participant_id` | Yes | Pseudonymous deployment-wide person identifier |
| `study_id` | Yes | Existing study identifier for the selected site |
| `site_id` | Yes | Identifier of a previously generated site |
| `enrolment.id` | Yes | Stable enrolment record identifier within this participant |
| `enrolment.enrolled_at` | Yes | Enrolment start instant |
| `enrolment.status` | Yes | `screening`, `enrolled`, `active`, `completed` or `withdrawn` |
| `enrolment.phase_id` | No | Phase declared in the selected pilot setup |
| `enrolment.arm_id` | No | Arm declared in the selected pilot setup |
| `age_years` | No | Number between 0 and 130; a snapshot at `recorded_at`, not an eligibility assessment |
| `survivor_role` | No | Explicitly supplied `cancer_survivor` or `aya_cancer_survivor` |
| `preferences.language_tag` | No | Supplied language preference, e.g. `es-ES` or `en-GB`; no fallback to site locale |
| `preferences.detail_level` | No | `brief` or `detailed` |
| `preferences.communication_channel` | No | `smart_mirror`, `mobile_app`, `email`, `sms`, `telephone` or `in_person` |
| `preferences.contact_time` | No | `morning`, `afternoon`, `evening`, `night` or `any_time` |
| `attributes` | No | Array of textual `{ "id": "access", "name": "Information access context", "value": "Requests explanations of unfamiliar terms" }` records |
| `consent` | No | Metadata object described below; omitted means no consent assertion |

If `preferences` is supplied, at least one preference is needed. Language tags accept a useful syntax subset without a registry lookup. Attribute records require all three fields and unique IDs. Attribute time and source are taken from the enclosing input; records with different provenance need a later dedicated input profile.

## Consent metadata

| Field | Required when consent is supplied | Meaning |
|---|---|---|
| `consent.id` | Yes | Stable record identifier within this participant |
| `consent.status` | Yes | `pending`, `granted`, `refused`, `withdrawn` or `expired` |
| `consent.valid_from` | Yes | Start of record applicability |
| `consent.valid_until` | No | End of applicability, strictly later than `valid_from` |

No automatic status/date reconciliation or legal validity judgement is performed. Consent does not establish enrolment status and enrolment does not establish consent. Records are marked `Unverified`. This limited profile does not capture purpose-specific authorisations or replace the project's consent process.

## Clinical and other ontology sections

Both pilot and participant inputs can include optional `sections`. Participant groups include clinical profile, cancer history, measurements, cardiovascular risk, care plans, exercise, nutrition, lifestyle, social context and educational support. Shared pilot inputs use the same typed-record structure for site-owned context. The section names and record/link structure are documented in [SECTIONS_GUIDE.md](SECTIONS_GUIDE.md); `schemas/sections.schema.json` specifies the contract. The [ontology reference](reference/ontology-input-reference.json) supplies the available class/property names, definitions and vocabulary values.

Unknown whole sections can remain `null` in the fillable template. Once supplied, records need stable IDs and declared ontology types. Unknown values of valid properties can remain `null`; misspelled or undeclared property names are rejected. Different clinical encounters, observations, prescriptions and performed sessions should have different record IDs when they need to be retained separately. Class/property validation and reference resolution run against the current ontology on every refresh.
