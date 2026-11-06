# Educational resource workflow checks

40 checks; 0 failures; 0 errors. Result: **PASS**.

Tests exercise new approved IDs, status gating, withdrawal, stable IRIs, repeat processing, header and sheet independence, vocabulary validation, dates, permissions, release integrity, participant matching and a synthetic educational activity.

Expected matches are authored resource IDs. The fixed reviewed-metadata fixture and temporary output directories keep these regression checks independent of later additions to the live collection. The source workbook is unchanged. These are technical checks, not evaluation of educational outcomes or clinical suitability.

Repeat from the project root: `python education/scripts/check_workflow.py` (with dependencies from `education/requirements.txt`).

| Test | Result |
|---|---|
| activity does not infer an unidentified need | PASS |
| approved and complete are both required | PASS |
| audience excludes caregiver only resources | PASS |
| columns are located by header | PASS |
| configurable sheet and shifted header row | PASS |
| custom namespace is preserved | PASS |
| demo does not publish real participant data | PASS |
| demo links real resource to synthetic draft intervention | PASS |
| duplicate id fails without replacing current release | PASS |
| email like url is rejected | PASS |
| empty release requires explicit flag | PASS |
| empty required annotation is rejected | PASS |
| exact initial resource set | PASS |
| existing old release is verified before reactivation | PASS |
| failed initial write can be retried | PASS |
| invalid request and unknown term fail | PASS |
| journey stage excludes nonmatching resource | PASS |
| language and topic filters have no automatic fallback | PASS |
| language claims need verified values | PASS |
| missing column fails | PASS |
| multiple values split on semicolons not commas | PASS |
| namespace cannot change in existing deployment | PASS |
| new approved id is automatically published | PASS |
| preferred complexity is not required complexity | PASS |
| registration is visible and can be excluded | PASS |
| reordering keeps resource identities | PASS |
| repeated build is unchanged | PASS |
| required accessibility is not inferred | PASS |
| review dates preserve excel epochs | PASS |
| shacl rejects missing resource url | PASS |
| spanish cardiovascular expected match | PASS |
| sparql returns independent expected answer | PASS |
| stale ontology is rejected | PASS |
| tampered managed file is rejected | PASS |
| unknown need is not fuzzily mapped | PASS |
| unknown stage is rejected | PASS |
| unresolved permission is not released | PASS |
| update preserves iri and removes old url | PASS |
| withdrawal removes current but preserves history | PASS |
| wrong vocabulary category is rejected | PASS |
