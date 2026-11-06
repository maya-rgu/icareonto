# iCARE Onto competency-question validation report

**Ontology:** 0.1.0-draft, under review toward iCARE Onto v1. **Test date:** 2026-11-06.

All **78 consolidated CQs were executed**. **78** matched their authored expected answers; **0** require modelling/scope review. The **4 additional controls** all passed.

CQ-019 follows the corrected question wording and includes mixed-topic resources addressing nutrition. CQ-051 uses the new validation-evidence relation and excludes a general background citation. These changes follow the revised source specifications; expected answers remain separately authored constants.

## Method

The canonical CQ register supplies the question wording, expected answer type, suggested ontology path, modules and original proposal/stakeholder CQ identifiers. Each canonical CQ has one executable SPARQL query and a separately authored, nonempty expected result. Expected answers are constants in the suite definition; they are not calculated from actual query output.

The query dataset is the explicit union of the ontology imports, the existing fictional Spanish survivor graph, and a separate synthetic coverage supplement. SPARQL subclass property paths handle declared class hierarchies; no reasoning engine materialises new facts during query execution. Ordered results are checked for CQ-043. Other answers use exact unordered multisets, including exclusion of extra results. IRIs, numeric datatypes/value equality, language tags and timezone-normalised date-time values are checked.

The Spanish survivor graph and ontology are unchanged by these tests. Added coverage data include two risk-factor contributions, clinical and social records, an interval-based observation, out-of-window observations, nutrition/adherence examples, another fictional person, a mixed-topic resource and separate validation/background evidence sources.

Fixture preflight checks declared terms, import resolution, datatype lexical forms and explicit compatibility with ontology domains/ranges. These checks report mismatches instead of relying on OWL domain/range inference to assign convenient types.

Preflight errors: **0**.

## OWL consistency

Protégé's OWLAPI loads **24 documents** for the complete test entry. OWL 2 DL profile violations: **0**. HermiT consistency: **True**. Unsatisfiable named classes: **0**.

Consistency is checked separately from expected query answers. It does not establish clinical correctness or prove every CQ can be answered.

## Items requiring review

No outstanding query-answer review items in this run.

The suite tests the current source CQ wording and ontology relations. Unexpected missing or additional answers are reported as mismatches.

## Interpretation choices

- CQ-001 enumerates represented risk-factor instances. CQ-015, CQ-029 and CQ-035 enumerate local named subclasses. CQ-060 and CQ-061 enumerate the supplied controlled concepts.
- CQ-039 uses AnthropometricParameter typing. CQ-040 and CQ-046 identify body-composition variables through BodyCompositionProtocol membership. This interpretation is recorded with the cases.
- Systolic/diastolic variables are explicitly typed as PhysiologicalParameter in the supplement because VitalSign is currently a sibling class in the supplied hierarchy. BMI is explicitly typed as both DerivedParameter and AnthropometricParameter. No schema axioms were changed.
- CQ-043 uses a half-open UTC window, includes point observations inside it and intervals overlapping it, and checks chronological ordering. A point exactly at the upper bound is excluded.
- CQ-063 and CQ-064 distinguish prescribed and performed ExerciseActivity instances (20 versus 18 minutes).
- CQ-073–CQ-078 retrieve authored trigger associations. They do not demonstrate execution of a warning rule or causal initiation of an activity.

## Results by theme

| Theme | Executed | Pass | Needs review | Fail/error |
|---|---:|---:|---:|---:|
| Cardiovascular risk | 6 | 6 | 0 | 0 |
| Cancer survivorship and clinical profile | 5 | 5 | 0 | 0 |
| Knowledge resources and health literacy | 17 | 17 | 0 | 0 |
| Social context and dialogue | 6 | 6 | 0 | 0 |
| Lifestyle and behaviour | 4 | 4 | 0 | 0 |
| Measurement and biomarkers | 13 | 13 | 0 | 0 |
| Nutrition | 8 | 8 | 0 | 0 |
| Exercise | 11 | 11 | 0 | 0 |
| Care plans, warnings and check-ups | 8 | 8 | 0 | 0 |

## Per-CQ results

The JSON and TSV reports contain complete expected and actual bindings, source identifiers, query hashes, and test-scope notes.

| CQ | Question | Status | Expected/actual rows | Query |
|---|---|---|---|---|
| CQ-001 | Which modifiable cardiovascular risk factors are represented in iCAREOnto? | PASS | 2/2 | [SPARQL](../cq-tests/queries/CQ-001.rq) |
| CQ-002 | Which interventions target a given modifiable cardiovascular risk factor? | PASS | 1/1 | [SPARQL](../cq-tests/queries/CQ-002.rq) |
| CQ-003 | Which clinical condition does a given cardiovascular risk estimate concern? | PASS | 1/1 | [SPARQL](../cq-tests/queries/CQ-003.rq) |
| CQ-004 | Which adverse cardiac event does a given cardiovascular risk estimate concern? | PASS | 1/1 | [SPARQL](../cq-tests/queries/CQ-004.rq) |
| CQ-005 | Which risk factors contribute to a given risk estimate? | PASS | 2/2 | [SPARQL](../cq-tests/queries/CQ-005.rq) |
| CQ-006 | Which interpretation is assigned to a given cardiovascular risk estimate? | PASS | 1/1 | [SPARQL](../cq-tests/queries/CQ-006.rq) |
| CQ-007 | Which cancer diagnoses are recorded for a person? | PASS | 1/1 | [SPARQL](../cq-tests/queries/CQ-007.rq) |
| CQ-008 | Which treatment-related clinical conditions are recorded for a person? | PASS | 1/1 | [SPARQL](../cq-tests/queries/CQ-008.rq) |
| CQ-009 | Which cancer treatment exposures are recorded for a person? | PASS | 1/1 | [SPARQL](../cq-tests/queries/CQ-009.rq) |
| CQ-010 | Which cancer treatment exposures are represented as risk factors for cardiotoxicity? | PASS | 1/1 | [SPARQL](../cq-tests/queries/CQ-010.rq) |
| CQ-011 | Which clinical records are included in a person's clinical profile? | PASS | 3/3 | [SPARQL](../cq-tests/queries/CQ-011.rq) |
| CQ-012 | Which guidelines are represented in iCAREOnto? | PASS | 1/1 | [SPARQL](../cq-tests/queries/CQ-012.rq) |
| CQ-013 | Which recommendations are contained in a given guideline or other knowledge resource? | PASS | 2/2 | [SPARQL](../cq-tests/queries/CQ-013.rq) |
| CQ-014 | Which knowledge resources support a given recommendation? | PASS | 1/1 | [SPARQL](../cq-tests/queries/CQ-014.rq) |
| CQ-015 | Which intervention types are represented in iCAREOnto? | PASS | 3/3 | [SPARQL](../cq-tests/queries/CQ-015.rq) |
| CQ-016 | Which risk profile was used to derive a given recommendation? | PASS | 1/1 | [SPARQL](../cq-tests/queries/CQ-016.rq) |
| CQ-017 | Which care-plan activity does a given recommendation recommend? | PASS | 1/1 | [SPARQL](../cq-tests/queries/CQ-017.rq) |
| CQ-018 | Which person attributes are included in the model inputs used to generate a risk profile? | PASS | 1/1 | [SPARQL](../cq-tests/queries/CQ-018.rq) |
| CQ-019 | Which knowledge resources address nutrition as a topic? | PASS | 2/2 | [SPARQL](../cq-tests/queries/CQ-019.rq) |
| CQ-020 | Which health-literacy need does a given health-literacy resource address? | PASS | 1/1 | [SPARQL](../cq-tests/queries/CQ-020.rq) |
| CQ-021 | Which health-literacy resources are used by a given health-literacy intervention? | PASS | 1/1 | [SPARQL](../cq-tests/queries/CQ-021.rq) |
| CQ-022 | Which user-facing format does a given knowledge resource have? | PASS | 1/1 | [SPARQL](../cq-tests/queries/CQ-022.rq) |
| CQ-023 | Which content-complexity level does a given knowledge resource have? | PASS | 1/1 | [SPARQL](../cq-tests/queries/CQ-023.rq) |
| CQ-024 | Which accessibility features does a given knowledge resource provide? | PASS | 2/2 | [SPARQL](../cq-tests/queries/CQ-024.rq) |
| CQ-025 | What language is a given knowledge resource available in? | PASS | 1/1 | [SPARQL](../cq-tests/queries/CQ-025.rq) |
| CQ-026 | Which recommendations apply to a given symptom? | PASS | 1/1 | [SPARQL](../cq-tests/queries/CQ-026.rq) |
| CQ-027 | Which applicability criteria apply to a given recommendation? | PASS | 1/1 | [SPARQL](../cq-tests/queries/CQ-027.rq) |
| CQ-028 | Which contraindications apply to a given recommendation? | PASS | 1/1 | [SPARQL](../cq-tests/queries/CQ-028.rq) |
| CQ-029 | Which social-context factor types are represented in iCAREOnto? | PASS | 14/14 | [SPARQL](../cq-tests/queries/CQ-029.rq) |
| CQ-030 | Which socioeconomic factors are recorded for a person? | PASS | 2/2 | [SPARQL](../cq-tests/queries/CQ-030.rq) |
| CQ-031 | Which cultural factors are recorded for a person? | PASS | 1/1 | [SPARQL](../cq-tests/queries/CQ-031.rq) |
| CQ-032 | Which social-context records are included in the dialogue context used to generate a given agent response? | PASS | 3/3 | [SPARQL](../cq-tests/queries/CQ-032.rq) |
| CQ-033 | Which dialogue strategy was used in a given dialogue session? | PASS | 1/1 | [SPARQL](../cq-tests/queries/CQ-033.rq) |
| CQ-034 | Which dialogue strategies are adapted to a given social-context record? | PASS | 1/1 | [SPARQL](../cq-tests/queries/CQ-034.rq) |
| CQ-035 | Which lifestyle behaviour types are represented in iCAREOnto? | PASS | 12/12 | [SPARQL](../cq-tests/queries/CQ-035.rq) |
| CQ-036 | Which modifiable cardiovascular risk factors are influenced by a given lifestyle behaviour? | PASS | 1/1 | [SPARQL](../cq-tests/queries/CQ-036.rq) |
| CQ-037 | Which care-plan activity is related to a given behaviour record? | PASS | 1/1 | [SPARQL](../cq-tests/queries/CQ-037.rq) |
| CQ-038 | Which care-plan goal is related to a given behaviour record? | PASS | 1/1 | [SPARQL](../cq-tests/queries/CQ-038.rq) |
| CQ-039 | Which anthropometric parameters are represented in iCAREOnto? | PASS | 4/4 | [SPARQL](../cq-tests/queries/CQ-039.rq) |
| CQ-040 | Which body-composition parameters are represented in iCAREOnto? | PASS | 4/4 | [SPARQL](../cq-tests/queries/CQ-040.rq) |
| CQ-041 | Which physiological parameters are represented in iCAREOnto? | PASS | 6/6 | [SPARQL](../cq-tests/queries/CQ-041.rq) |
| CQ-042 | When did a given measurement event occur? | PASS | 1/1 | [SPARQL](../cq-tests/queries/CQ-042.rq) |
| CQ-043 | What observation results were recorded for a given measurable parameter over a specified time interval? | PASS | 3/3 | [SPARQL](../cq-tests/queries/CQ-043.rq) |
| CQ-044 | Which threshold category is assigned to a given observation result? | PASS | 1/1 | [SPARQL](../cq-tests/queries/CQ-044.rq) |
| CQ-045 | Which reference range was used to interpret a given observation result? | PASS | 1/1 | [SPARQL](../cq-tests/queries/CQ-045.rq) |
| CQ-046 | Which body-composition observations were used as inputs in a given prediction-model execution? | PASS | 2/2 | [SPARQL](../cq-tests/queries/CQ-046.rq) |
| CQ-047 | Which alert threshold was a given observation result compared against? | PASS | 1/1 | [SPARQL](../cq-tests/queries/CQ-047.rq) |
| CQ-048 | Which measurement instrument was used in a given measurement event? | PASS | 1/1 | [SPARQL](../cq-tests/queries/CQ-048.rq) |
| CQ-049 | Which measurable parameter does a given measurement protocol specify? | PASS | 2/2 | [SPARQL](../cq-tests/queries/CQ-049.rq) |
| CQ-050 | Which measurement method does a given measurement protocol specify? | PASS | 1/1 | [SPARQL](../cq-tests/queries/CQ-050.rq) |
| CQ-051 | Which evidence sources document the validation of a given measurement instrument? | PASS | 1/1 | [SPARQL](../cq-tests/queries/CQ-051.rq) |
| CQ-052 | Which nutrition behaviour records are included in a person's lifestyle profile? | PASS | 1/1 | [SPARQL](../cq-tests/queries/CQ-052.rq) |
| CQ-053 | Which dietary component does a given nutrition instruction target? | PASS | 1/1 | [SPARQL](../cq-tests/queries/CQ-053.rq) |
| CQ-054 | Which action type does a given nutrition instruction specify for its targeted dietary component? | PASS | 1/1 | [SPARQL](../cq-tests/queries/CQ-054.rq) |
| CQ-055 | What target amount and unit are recorded for a given nutrition instruction? | PASS | 1/1 | [SPARQL](../cq-tests/queries/CQ-055.rq) |
| CQ-056 | What schedule applies to a given nutrition instruction? | PASS | 1/1 | [SPARQL](../cq-tests/queries/CQ-056.rq) |
| CQ-057 | Which nutrition instructions are specified by a given nutrition intervention? | PASS | 2/2 | [SPARQL](../cq-tests/queries/CQ-057.rq) |
| CQ-058 | Which care-plan activity is related to a given nutrition behaviour record? | PASS | 1/1 | [SPARQL](../cq-tests/queries/CQ-058.rq) |
| CQ-059 | Which recommendations recommend a given nutrition intervention? | PASS | 1/1 | [SPARQL](../cq-tests/queries/CQ-059.rq) |
| CQ-060 | Which exercise modalities are represented in iCAREOnto? | PASS | 5/5 | [SPARQL](../cq-tests/queries/CQ-060.rq) |
| CQ-061 | Which exercise training patterns are represented in iCAREOnto? | PASS | 4/4 | [SPARQL](../cq-tests/queries/CQ-061.rq) |
| CQ-062 | Which exercise activities are included in a given exercise prescription? | PASS | 1/1 | [SPARQL](../cq-tests/queries/CQ-062.rq) |
| CQ-063 | What duration is prescribed for a given exercise activity? | PASS | 1/1 | [SPARQL](../cq-tests/queries/CQ-063.rq) |
| CQ-064 | What duration was recorded for a given exercise activity in a performed session? | PASS | 1/1 | [SPARQL](../cq-tests/queries/CQ-064.rq) |
| CQ-065 | Which modifiable risk factor does a given exercise intervention target? | PASS | 1/1 | [SPARQL](../cq-tests/queries/CQ-065.rq) |
| CQ-066 | Which care-plan goal does a given exercise intervention contribute to? | PASS | 1/1 | [SPARQL](../cq-tests/queries/CQ-066.rq) |
| CQ-067 | Which recommendations recommend a given exercise intervention? | PASS | 1/1 | [SPARQL](../cq-tests/queries/CQ-067.rq) |
| CQ-068 | Which planned exercise session does a given performed exercise session realise? | PASS | 1/1 | [SPARQL](../cq-tests/queries/CQ-068.rq) |
| CQ-069 | Which adherence result was produced by a given exercise-adherence assessment? | PASS | 1/1 | [SPARQL](../cq-tests/queries/CQ-069.rq) |
| CQ-070 | Which knowledge resource supports the recommendation for a given physical-activity goal? | PASS | 1/1 | [SPARQL](../cq-tests/queries/CQ-070.rq) |
| CQ-071 | Which medical check-up activities are included in a given care plan? | PASS | 1/1 | [SPARQL](../cq-tests/queries/CQ-071.rq) |
| CQ-072 | Which recommendations recommend a given medical check-up activity? | PASS | 1/1 | [SPARQL](../cq-tests/queries/CQ-072.rq) |
| CQ-073 | Which risk profile triggered a given medical check-up activity? | PASS | 1/1 | [SPARQL](../cq-tests/queries/CQ-073.rq) |
| CQ-074 | Which observation result triggered a given medical check-up activity? | PASS | 1/1 | [SPARQL](../cq-tests/queries/CQ-074.rq) |
| CQ-075 | Which symptom record does a given symptom-based trigger use? | PASS | 1/1 | [SPARQL](../cq-tests/queries/CQ-075.rq) |
| CQ-076 | What schedule applies to a given medical check-up activity? | PASS | 1/1 | [SPARQL](../cq-tests/queries/CQ-076.rq) |
| CQ-077 | Which care-plan activity was initiated by a given symptom-based trigger? | PASS | 2/2 | [SPARQL](../cq-tests/queries/CQ-077.rq) |
| CQ-078 | Which referral or escalation activity is associated with a recorded warning trigger? | PASS | 1/1 | [SPARQL](../cq-tests/queries/CQ-078.rq) |

## Additional controls

| Control | Purpose | Result |
|---|---|---|
| CTRL-OTHER-PERSON | Same query path with another participant | PASS |
| CTRL-UNKNOWN-PERSON | No matching record; empty result is not a statement of clinical absence | PASS |
| CTRL-BROKEN-PATH | Remove a bridge in a disposable graph; the integration answer must disappear | PASS |
| CTRL-PERFORMED-NOT-PLANNED | Recorded duration must not be replaced by the prescribed duration | PASS |

## Reproduction and limits

Run the commands in [the suite README](../cq-tests/README.md). Query files, authored cases and fixture are versionable text assets. Input-file and query SHA-256 hashes are included in `cq-results.json`.

Coverage here means all canonical CQs have been exercised with at least one specified scenario. It is not exhaustive testing of all parameter combinations, clinical meanings or data-quality conditions. Empty results under an unknown-participant control indicate no matching assertion in this dataset, not proof that a clinical fact is false.
