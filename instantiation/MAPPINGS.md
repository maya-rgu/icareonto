# Input to ontology mapping

All domain terms below use `http://maya-project.eu/icareonto/`. Domain classes and properties are reused from the current serialisation without modification. Infrastructure metadata uses existing RDF, RDFS, OWL and Dublin Core terms. The generator records the loaded ontology version and file hashes.

| Input or generated structure | RDF representation |
|---|---|
| `study.id`, `study.name` | Stable `PilotStudy` IRI, `dcterms:identifier`, `rdfs:label` |
| `site.id`, `site.name` | Stable `PilotSite` IRI, `dcterms:identifier`, `rdfs:label`; `pilotStudyHasPilotSite` connects study and site |
| `study.phases[]` | `PilotPhase` individuals linked by `pilotStudyHasPhase` |
| `study.arms[]` | `StudyArm` individuals linked by `pilotStudyHasArm` |
| `site.locale` | `Locale` individual linked by `pilotSiteHasLocale` |
| `locale.language_tag`, `country_code`, `time_zone` | `localeTag` (`xsd:language`), `localeCountryCode`, `localeTimeZoneIdentifier` (`xsd:string`) |
| `participant_id` | Stable `Person` IRI and `personIdentifier` (`xsd:string`) |
| Enrolment role | `StudyParticipantRole` linked by `personHasRole`; a record of study participation does not imply a specific consent decision |
| `survivor_role` | Explicit `CancerSurvivorRole` or `AYACancerSurvivorRole`, linked by `personHasRole` |
| `age_years` | `ageInYears` (`xsd:decimal`); graph metadata records the snapshot time |
| `enrolment.id` | `ParticipantEnrolment` individual |
| `study_id`, `site_id` | `participantEnrolmentInStudy`, `participantEnrolmentAtSite`; shared entities are referenced rather than recreated in the participant graph |
| Participant in enrolment | `participantEnrolmentForPerson` |
| `enrolment.enrolled_at` | `participantEnrolmentValidDuring` → `TimeInterval` → `intervalStartsAt` → `Timepoint` → `timepointDateTime` (`xsd:dateTime`) |
| `enrolment.status` | `participantEnrolmentHasStatus` → controlled value |
| `enrolment.phase_id`, `arm_id` | `participantEnrolmentInPhase`, `participantEnrolmentAssignedToArm` |
| Logical participant KG | `ParticipantKnowledgeGraph` linked to person by `participantKnowledgeGraphAboutPerson` |
| `preferences.language_tag` | `LanguagePreference` → `preferredLanguageTag` (`xsd:language`) |
| `preferences.detail_level` | `InformationPreference` → `informationPreferenceHasDetailLevel` → controlled value |
| `preferences.communication_channel` | `CommunicationPreference` → `preferredCommunicationChannel` → controlled value |
| `preferences.contact_time` | `ContactPreference` → `preferredContactTime` → controlled value |
| All preference records | Linked by `personHasPreference`; `preferenceRecordedAt` and `dcterms:source` record time/source |
| `attributes[]` | `PersonAttribute`, `personHasAttribute`, `personAttributeName`, `personAttributeValue`, `personAttributeRecordedAt`, `personAttributeHasSource` |
| `consent.id`, `status` | `ConsentRecord`, `consentRecordHasStatus` → controlled value; `hasVerificationStatus` → `Unverified` |
| Consent scope/person | `consentRecordAppliesToKnowledgeGraph` → logical KG; `consentRecordGrantedBy` identifies the person supplying a non-pending decision |
| Consent dates | `consentRecordValidDuring` → `TimeInterval`, start and optional end `Timepoint` |
| `source` | `dcterms:description` on the physical graph; participant seed also has a `DataSource` with `dataSourceDescription` and a hash-based `dataSourceIdentifier` |
| `recorded_at` | `dcterms:issued` on the physical graph; `Timepoint` for participant preference/attribute records |
| Input provenance | Canonical input SHA-256 in a graph-level `dcterms:source` IRI and sidecar registry; no local input filenames in RDF |
| `schema_version` | Validates input profile; generator/profile version is recorded using `owl:versionInfo` |

## Controlled value mapping

| Input | Existing controlled individual |
|---|---|
| `screening`, `enrolled`, `active`, `completed`, `withdrawn` | `ScreeningEnrolmentStatus`, `EnrolledStatus`, `ActiveEnrolmentStatus`, `CompletedEnrolmentStatus`, `WithdrawnEnrolmentStatus` |
| `brief`, `detailed` | `BriefInformation`, `DetailedInformation` |
| `smart_mirror`, `mobile_app`, `email`, `sms`, `telephone`, `in_person` | `SmartMirrorChannel`, `MobileAppChannel`, `EmailChannel`, `SMSChannel`, `TelephoneChannel`, `InPersonChannel` |
| `morning`, `afternoon`, `evening`, `night`, `any_time` | `MorningTimeOfDay`, `AfternoonTimeOfDay`, `EveningTimeOfDay`, `NightTimeOfDay`, `AnyTimeOfDay` |
| Consent `pending`, `granted`, `refused`, `withdrawn`, `expired` | `ConsentPending`, `ConsentGranted`, `ConsentRefused`, `ConsentWithdrawn`, `ConsentExpired` |

## Stable instance identifiers

With `BASE` as the configured instance namespace:

- Study: `BASEstudies/<study-id>`; phases/arms append `/phases/<id>` or `/arms/<id>`.
- Site: `BASEsites/<site-id>`; locale appends `/locale`.
- Person: `BASEpeople/<participant-id>`; enrolment appends `/enrolments/<id>`.
- Person-owned records append `/preferences/<field>`, `/attributes/<id>`, `/consents/<id>`, `/roles/<role-class>` or `/knowledge-graph`.
- Physical graphs: `BASEgraphs/pilots/<site-id>` and `BASEgraphs/participants/<participant-id>`.

Person IDs are deployment-wide, not site-scoped. The required enrolment profile represents one enrolment per participant record; adding another enrolment requires a separate history profile. Changing IDs creates different entities, so refresh cannot silently reassign an existing enrolment.

## Grouped ontology records

`sections.<group>.records[]` exposes the complete declared local ontology vocabulary through a general mapping:

| Input | RDF representation |
|---|---|
| `id` | Stable owner-scoped `BASEpeople/<participant-id>/records/<id>` or `BASEsites/<site-id>/records/<id>` |
| `type` | Explicit `rdf:type` for each supplied, declared ontology class, plus `owl:NamedIndividual` |
| `label` | Optional `rdfs:label` |
| `source`, `recorded_at` | Optional record-level `dcterms:source` description and `dcterms:modified` recording time; not an inferred onset time |
| `properties.<object-property>: {"ref": "id"}` | Relationship to another declared section record or a documented generated-entity alias |
| `properties.<object-property>: {"term": "ontology-value"}` | Relationship to a named ontology individual, checked for range compatibility |
| `properties.<data-property>: value` | Literal with the property's declared XSD datatype, checked before conversion |
| A list of values | Multiple assertions for the same property |
| A known property with `null` | No assertion for the unknown value |
| `links[]` | Additional assertions using an owner alias or record ID as subject |

Groups organise the JSON but are not encoded as new ontology classes. Record IDs are unique across an owner's sections and remain stable if moved between groups. No record is created in the ontology namespace. Cross-section links are resolved before graph validation, and references to missing records are rejected. The clinical/cancer/risk/care/exercise paths are illustrated in [the complete example](examples/participant-es-full.json) and [section guide](SECTIONS_GUIDE.md).

The generated `.jsonld` files preserve the same RDF assertions as Turtle. `dataset.jsonld` preserves the same named graphs as `dataset.trig`. JSON-LD is an export format, not a second mapping or a different source of truth.
