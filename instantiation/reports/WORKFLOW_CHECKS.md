# KG initialisation workflow checks

All **49 checks passed**.

Temporary fictional outputs; no modification of supplied examples, existing KG fixtures or ontology.

| Check | Result | Purpose |
|---|---|---|
| UNREGISTERED-PILOT | PASS | Rejected without changing published files: pilot must be generated |
| CREATE-PILOT | PASS | Pilot setup generated and validated |
| CREATE-FIRST | PASS | First enrolment generated and validated |
| CREATE-SECOND | PASS | Second enrolment references the same site |
| SHARED-SITE-QUERY | PASS | Combined query returns two distinct participant language preferences at the Spanish site |
| NO-SITE-COPY | PASS | Site is defined once and referenced by both participant graphs |
| CONTROLLED-VALUES | PASS | Readable values map to existing ontology individuals |
| OPTIONAL-OMISSION | PASS | Omitted age, consent and survivor role are not invented |
| SOURCE-TIME | PASS | Preference/attribute provenance and times are represented |
| DOCUMENTED-QUERY | PASS | The supplied enrolment-context query returns the exact independently specified participant/site answers |
| AGE-TYPE | PASS | Age retains decimal datatype and the supplied numeric value |
| REPEAT-IDENTITY | PASS | Repeated input preserves managed seed bytes, graph identities and participant count |
| NAMED-GRAPHS | PASS | TriG preserves exactly three separate instance graphs |
| TRIG-ROUNDTRIP | PASS | Participant named graph survives RDF serialisation |
| CATALOGUE-GENERATED | PASS | All catalogue targets and seed imports resolve locally |
| CATALOGUE-PILOTS | PASS | All catalogue targets and seed imports resolve locally |
| CATALOGUE-PARTICIPANTS | PASS | All catalogue targets and seed imports resolve locally |
| MISSING-ID | PASS | Rejected without changing published files: participant_id |
| UNKNOWN-FIELD | PASS | Rejected without changing published files: Additional properties |
| BAD-STATUS | PASS | Rejected without changing published files: status |
| MISSING-OFFSET | PASS | Rejected without changing published files: date-time |
| BAD-DATE | PASS | Rejected without changing published files: date-time |
| FUTURE-ENROLMENT | PASS | Rejected without changing published files: later than recorded_at |
| PLACEHOLDER | PASS | Rejected without changing published files: participant_id |
| BAD-AGE | PASS | Rejected without changing published files: age_years |
| NULL-OPTIONAL | PASS | Rejected without changing published files: age_years |
| UNKNOWN-SITE | PASS | Rejected without changing published files: pilot must be generated |
| WRONG-STUDY | PASS | Rejected without changing published files: pair does not match |
| UNKNOWN-PHASE | PASS | Rejected without changing published files: phase_id |
| UNKNOWN-ARM | PASS | Rejected without changing published files: arm_id |
| DUPLICATE-ATTRIBUTE | PASS | Rejected without changing published files: Repeated record identifier |
| CONSENT-INTERVAL | PASS | Rejected without changing published files: later than valid_from |
| INVALID-ZONE | PASS | Rejected without changing published files: unknown IANA time zone |
| LOCALE-COUNTRY | PASS | Rejected without changing published files: country suffix |
| DUPLICATE-PHASE | PASS | Rejected without changing published files: Repeated record identifier |
| REMOVE-REFERENCED-ARM | PASS | Rejected without changing published files: Explicit range mismatch |
| CONFLICTING-SHARED-STUDY | PASS | Rejected without changing published files: Conflicting labels |
| PILOT-CORRECTION | PASS | Site correction updates the shared seed without rewriting participant files |
| SHARED-CORRECTION-QUERY | PASS | Both participants see the corrected site information through the existing links |
| UNINTENTIONAL-REPLACEMENT | PASS | Rejected without changing published files: --replace-seed |
| EXPLICIT-CORRECTION | PASS | Intentional preference correction keeps person identity and archives the previous seed |
| NO-SILENT-REENROLMENT | PASS | Rejected without changing published files: cannot replace enrolment identity |
| NO-PREFERENCE-DEFAULT | PASS | Missing participant preferences remain unasserted despite the site's Spanish locale |
| PENDING-CONSENT | PASS | Pending consent does not assert that a grant decision was supplied |
| NAMESPACE-PROTECTION | PASS | An existing deployment cannot silently switch its instance namespace |
| SHACL-MISSING-IDENTIFIER | PASS | Graph-level missing required identifier is rejected independently of input validation |
| EXPLICIT-TYPE-CHECK | PASS | Missing explicit site type is rejected rather than inferred to repair the graph |
| CLI-INVALID-JSON | PASS | CLI returns nonzero without publishing outputs for duplicate JSON keys |
| EXTERNAL-EDIT | PASS | Rejected without changing published files: edited outside the generator |
