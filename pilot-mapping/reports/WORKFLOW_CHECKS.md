# Pilot mapping workflow checks

All **31 checks passed**.

Technical controls and separately specified demonstration references; no claim of expert mapping approval or real-pilot validity

| Check | Result | Purpose |
|---|---|---|
| FULL-CANDIDATES | PASS | Every requirement ranks all 283 local classes without an oracle shortlist |
| NO-TRUNCATION | PASS | No encoded requirement or ontology description was truncated |
| REAL-MODEL-PROVENANCE | PASS | Report identifies local model weights, runtime and 384-dimensional sentence vectors |
| COSINE-NORMALISATION | PASS | Metric handles vector scale, orthogonality and opposite directions |
| NO-AUTOMATIC-ACCEPTANCE | PASS | Even the highest ranked candidates remain unaccepted in the generated template |
| UNNAMED-REVIEW | PASS | Rejected: reviewer |
| PENDING-PROFILE | PASS | Pending decisions never enter the accepted mapping set |
| FOUNDATION-RETAINED | PASS | Core participant, site and governance scope remains available regardless of ranking |
| PROFILE-REPRODUCTION | PASS | Stored profile reproduces exactly from its bound ranking, needs and review decisions |
| REVIEW-BOUNDARIES | PASS | A pending mapping decision remains separate from the ontology update that resolved its earlier representation gap |
| DECISION-SCORES | PASS | Accepted decisions preserve actual ranks and scores, including lower-ranked reference concepts |
| EXPLICIT-OVERRIDE | PASS | Review decisions are separate from score rank; the control does not alter shipped mappings |
| STALE-NEEDS | PASS | Rejected: Needs input changed |
| STALE-ONTOLOGY | PASS | Rejected: Ontology changed |
| NONFINITE-SCORE | PASS | Rejected: Invalid ranking scores |
| DUPLICATE-NEED | PASS | Rejected: duplicate |
| UNTESTED-LANGUAGE | PASS | Rejected: English |
| UNKNOWN-CLASS | PASS | Rejected: undeclared |
| PROPERTY-AS-CLASS | PASS | Rejected: non-class |
| DUPLICATE-REVIEW | PASS | Rejected: Exactly one decision |
| PENDING-SELECTION | PASS | Rejected: Only accepted |
| SUPPORTING-RELATIONSHIPS | PASS | Adjacent relationships retain the ontology's existing domain/range definitions rather than creating new axioms |
| REFERENCE-EVALUATION | PASS | Evaluation covers all references without changing saved rankings or imposing a 100-percent retrieval expectation |
| EDITED-PROFILE | PASS | Rejected: stale or edited |
| NO-OUTPUT-ON-EDITED-PROFILE | PASS | Rejected profile does not start a generation run |
| WRONG-SITE | PASS | Rejected: does not match |
| WRONG-PARTICIPANT | PASS | Rejected: does not belong |
| PROFILE-BOUND-GENERATION | PASS | Existing generator validates one pilot and two participants against the bound concept profile |
| HONEST-COVERAGE | PASS | Five selected concepts have instances; nine are reported as requiring more data/profiles |
| NO-INVENTED-CLINICAL-FACTS | PASS | Selecting clinical concepts does not fabricate treatment history or an exercise prescription |
| TRACEABILITY-FILES | PASS | Generated package contains the exact concept profile and its coverage record |
