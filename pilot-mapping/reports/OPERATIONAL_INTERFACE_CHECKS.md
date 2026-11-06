# Operational interface checks

All **22 checks passed**.

All data and reviewer identities are fictional. This tests the operational input/code paths; it does not assert that a real pilot review or deployment has occurred.

| Check | Result | Purpose |
|---|---|---|
| INIT | PASS | CLI creates an operational template without requiring real data or an embedding run |
| UNFILLED-TEMPLATE | PASS | Unreplaced placeholders fail validation |
| NO-TEMPLATE-OVERWRITE | PASS | Initialisation preserves a previously created working template |
| OPERATIONAL-NEEDS-VALIDATE | PASS | Completed source-referenced operational-format input passes validation |
| SOURCE-REF-REQUIRED | PASS | Rejected: source_refs |
| OWNER-REQUIRED | PASS | Rejected: owner |
| OPERATIONAL-RANKING | PASS | Rankings retain operational provenance and original requirement references |
| DRAFT-REVIEW-TEMPLATE | PASS | Operational input creates a draft review bound to the exact ranking |
| DRAFT-PROFILE | PASS | Proposed selections may be inspected without claiming completed review |
| DRAFT-NOT-APPLIED | PASS | Rejected: reviewed profile |
| NO-PREMATURE-GENERATION | PASS | Draft profile rejection leaves no generated graph output |
| REVIEW-TIME-REQUIRED | PASS | Rejected: reviewed_at |
| REVIEWED-PROFILE | PASS | Reviewed-format profile retains source references, actual scores and recorded reviewer details |
| NAMESPACE-REQUIRED | PASS | Rejected: --base-iri |
| STALE-REVIEW | PASS | Rejected: Review is stale |
| NO-DEMO-APPROVAL | PASS | Rejected: Operational needs |
| CUSTOM-NAMESPACE | PASS | CLI generates the pilot and both participants using the supplied instance namespace |
| REAL-IRI-OUTPUT | PASS | RDF entities use the configured namespace rather than the demonstration default |
| REVIEW-TRACEABILITY | PASS | Generation records operational-format provenance, reviewer, namespace and scope limits |
| REPEAT-OPERATIONAL-INPUT | PASS | Repeated processing preserves the existing participant seed |
| NO-SILENT-CORRECTION | PASS | Changed seed requires an explicit correction flag |
| EXPLICIT-OPERATIONAL-CORRECTION | PASS | Explicit correction archives the previous participant seed |
