# Initial MAYA educational resource workflow

Implemented and checked on 3 November 2026. This package connects the reviewed educational-resource catalogue to ontology-based selection and draft learning activities. It is an offline, reusable workflow for subsequent Health Hub and avatar integration.

## Current collection and ontology

The release contains **16 resources** marked both Approved and Complete in the saved Release resources worksheet. MAYA-EDU-0014 remains excluded because it is On hold and To complete. Approved resources with verified registration requirements remain eligible, with their access conditions exposed to the delivery component.

The ontology was refreshed from `icareonto_review_workbook_v021126.xlsx`, retaining version `0.1.0-draft`. It contains 17 modules, 283 classes, 284 object properties, 137 data properties, **304 controlled values** and 62 schemes. The knowledge-resource module now includes DigitalHealthPrivacyAndTrust and MentalHealthAndEmotionalWellbeing and the revised topic definitions. Comparing module RDF against the previous package found changes only in knowledge-resource.

The importer maps controlled labels to ontology IRIs, preserves Resource IDs, separates semicolon-delimited values, retains review and rights metadata, and publishes metadata and links without retrieving source content. Source workbook names and row provenance are confined to validation sidecars. Application annotations record journey stage, curation state, access conditions and review details; core domain relationships use iCARE Onto.

Controlled annotations are validated directly against ontology values. Journey stages use the three permitted options; no resource-specific substitutions are applied.

## Educational activities and matching

Three newly authored templates cover cardiovascular follow-up, everyday nutrition/activity choices and adjustment after treatment. Each records a learning objective, need/topic criteria, delivery steps and reflection prompts. Their **Draft** status is separate from the approval of the underlying resources. They require editorial/domain review before participant delivery.

Selection requires matching audience, journey stage, language, at least one identified need and at least one requested topic. Required accessibility annotations are enforced. Format and complexity preferences affect ordering and are reported transparently. No matching resource produces an explicit gap. Clinical suitability, age-specific applicability and local service eligibility remain contextual considerations for the delivery component rather than unimplemented automatic guarantees.

The fictional post-treatment cardiovascular example selects **MAYA-EDU-0004** for an identified comprehension need and a Spanish language preference. Its RDF links a fictional participant and needs-identification event to a draft care plan, goal and HealthLiteracyIntervention using the real resource metadata. The English nutrition request selects **MAYA-EDU-0023** and exposes its registration requirement. These examples do not assert delivered interventions, completed learning or improved literacy.

## Validation

| Validation activity | Result |
|---|---|
| Source-to-ontology reconciliation | 4,254 checks passed |
| Ontology OWLAPI/HermiT | 22 imported documents including the entry; OWL 2 DL; consistent; no unsatisfiable named classes |
| Educational workflow tests | 40 checks passed, with no failures or errors; workbook unchanged during testing |
| Resource graph validation | Required-field SHACL and explicit ontology type/domain/range checks passed |
| Educational demonstration OWLAPI/HermiT | 26 documents; zero OWL 2 DL violations; consistent; no unsatisfiable named classes |
| Existing competency-question regression | All 78 CQs and four controls passed against the refreshed ontology |

The workflow checks exercise new resource IDs, status gating, stable identifiers, row/column movement, updates, withdrawal, repeated builds, interrupted publication, integrity failures, matching and a synthetic draft intervention. They use a fixed reviewed-metadata fixture so that later additions to the live collection do not invalidate the regression baseline. Expected selection results are independently specified resource IDs. These are technical checks; they do not establish educational effectiveness or clinical validation.

See [workflow results](WORKFLOW_CHECKS.md), [machine-readable checks](workflow-checks.json), [educational OWL report](owlapi-report.json), [CQ report](../../validation/reports/CQ_VALIDATION_REPORT.md) and [ontology validation](../../serialisation/validation/).

## Adding and maintaining resources

Save the updated worksheet and rerun the build. Every new approved/complete Resource ID is considered automatically, including for applicable activity templates. Changed records retain their IRIs; withdrawn entries disappear from the current release. Validated snapshots and a single current pointer support reproducibility and rollback. Consumers refresh from the current pointer or replace the active named graphs; appending historical snapshots would retain withdrawn data.

The next integration step is for T3.3/T3.4 to call the selection function with identified needs and preferences, present the returned metadata/links, and record use and feedback through the Health Hub. Full-text ingestion requires an independently established permitted use. Ongoing review can prioritise gaps in language, topic, format or support needs and revise activities using participant and professional feedback.
