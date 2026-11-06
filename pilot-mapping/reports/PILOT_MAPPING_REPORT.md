# Pilot concept mapping demonstration report

**Scope:** Fictional Spanish pilot `es-demo-01`, study `maya-demo`. The inputs and mapping decisions are agent-authored demonstration material, not actual workshop findings or pilot/expert approval.

All **15 fictional needs** were scored against **283 local ontology classes**. There are **14 accepted demonstration mappings** and **1 requirements without an accepted mapping**.

## Method

Each class is described by its preferred label, alternative labels, definition and available named-parent labels. A locally cached `sentence-transformers/all-MiniLM-L6-v2` encoder produces sentence vectors. Cosine similarity ranks classes separately for each requirement. Scores are not confidence probabilities. No threshold automatically accepts a mapping.

The model snapshot directory is `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`; file hashes, runtime versions, CPU execution, vector dimensions and truncation checks are recorded in `tests/fixtures/rankings.json`. This report evaluates those saved rankings; it does not itself execute the encoder. All descriptions are English. No text was sent to an external inference service. No descriptions were truncated.

The comparison baseline is unweighted token-set Jaccard overlap using the same texts. It measures lexical overlap, not semantic similarity. The separate reference file specifies expected classes before scoring and is never read by the ranker. It is a small agent-authored demonstration reference, not an expert gold standard or held-out real-pilot evaluation.

## Candidate retrieval results

The 14 positive references each specify one target class. Hit@k is the fraction with that class in the first k candidates. Mean reciprocal rank averages the reciprocal of its rank. Requirements without a specified positive reference (1) are excluded from these retrieval metrics.

| Metric | Semantic cosine | Lexical baseline |
|---|---:|---:|
| Hit@1 | 64.3% | 28.6% |
| Hit@5 | 85.7% | 64.3% |
| Hit@10 | 92.9% | 78.6% |
| Mean reciprocal rank | 0.760 | 0.450 |

| Requirement | Reference class | Semantic rank | Lexical rank |
|---|---|---:|---:|
| DEMO-KR01 | `LanguagePreference` | 2 | 25 |
| DEMO-KR02 | `InformationPreference` | 82 | 3 |
| DEMO-KR03 | `ParticipantEnrolment` | 2 | 1 |
| DEMO-KR04 | `BloodPressureMeasurementProtocol` | 1 | 2 |
| DEMO-KR05 | `Questionnaire` | 1 | 6 |
| DEMO-KR06 | `HealthLiteracyNeedType` | 8 | 11 |
| DEMO-KR07 | `AccessibilityFeature` | 1 | 72 |
| DEMO-KR08 | `PerformedExerciseSession` | 2 | 3 |
| DEMO-KR09 | `ExercisePrescription` | 1 | 1 |
| DEMO-KR10 | `CancerTreatmentHistory` | 1 | 8 |
| DEMO-KR11 | `ConsentRecord` | 1 | 1 |
| DEMO-KR12 | `EvidenceSource` | 1 | 1 |
| DEMO-KR13 | `NutritionInstruction` | 1 | 2 |
| DEMO-KR14 | `Locale` | 1 | 5 |

All candidates and scores remain available even when the reference is ranked poorly. Targets are not changed to manufacture successful retrieval.

For DEMO-KR02, `InformationPreference` ranked **82** with semantic similarity and **3** with lexical overlap. The supplied demonstration decision retains this class through an explicit review selection. This miss shows why the top-ten list alone is insufficient for reviewing all needs; reviewers must be able to search the full catalogue and identify omitted candidates.

## Review decisions and open items

The generated review template starts with no accepted mappings. The separate demonstration decisions select ontology concepts with recorded rationale, including any selections below rank 1. Real use requires review by the responsible pilot/domain team.

- **DEMO-KR16:** The ontology now supplies `measurementInstrumentHasValidationEvidence`, resolving the earlier CQ-051 distinction. The existing pending demonstration mapping is retained for explicit review of its selected classes and source-data mapping. It remains outside the original 14 positive retrieval references; a schema update does not automatically accept a mapping.

These are supplied review outcomes, not an automatically measured out-of-scope detection rate.

## Connection to KG generation

The accepted mappings form a pilot concept profile bound to the needs, ranking, review and ontology hashes. It lists relevant modules and adjacent relationships for input-profile design. Adjacent properties are contextual suggestions rather than independently reviewed mappings. Core participant, pilot and governance structures remain available; the ontology is not pruned.

The profile was bound to the existing generator for one fictional pilot and two participant enrolments. **5 of the 14 accepted class mappings** have matching instances in these initial graphs; **9** require additional input profiles or data. Class relevance alone does not create clinical facts.

| Requirement | Selected class | Initial graph coverage |
|---|---|---|
| DEMO-KR01 | `LanguagePreference` | Represented |
| DEMO-KR02 | `InformationPreference` | Represented |
| DEMO-KR03 | `ParticipantEnrolment` | Represented |
| DEMO-KR04 | `BloodPressureMeasurementProtocol` | Additional input profile or data required |
| DEMO-KR05 | `Questionnaire` | Additional input profile or data required |
| DEMO-KR06 | `HealthLiteracyNeedType` | Additional input profile or data required |
| DEMO-KR07 | `AccessibilityFeature` | Additional input profile or data required |
| DEMO-KR08 | `PerformedExerciseSession` | Additional input profile or data required |
| DEMO-KR09 | `ExercisePrescription` | Additional input profile or data required |
| DEMO-KR10 | `CancerTreatmentHistory` | Additional input profile or data required |
| DEMO-KR11 | `ConsentRecord` | Represented |
| DEMO-KR12 | `EvidenceSource` | Additional input profile or data required |
| DEMO-KR13 | `NutritionInstruction` | Additional input profile or data required |
| DEMO-KR14 | `Locale` | Represented |

The inputs used for this demonstration contain enrolment information. The KG Instantiator also supports grouped clinical and contextual records when supplied. Coverage describes the data used in this run, not a restriction on the ontology or instantiation interface.

## Limits and next steps

The prototype ranks classes, not arbitrary properties, controlled values or external-standard equivalences. It establishes a candidate-retrieval and traceability workflow rather than automatic ontology alignment, exhaustive schema extraction or deployed pilot adaptation. The current encoder is a general English model, not an evaluated multilingual or clinical-specialist model. Actual pilot needs, local terminology and any translations must be assessed with pilot/domain reviewers. No single similarity cutoff or performance guarantee is established by this small demonstration.

Methods: [Sentence Transformers similarity documentation](https://sbert.net/docs/sentence_transformer/usage/semantic_textual_similarity.html); [model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2). These sources describe the underlying technique, not the validity of the project-specific mappings.
