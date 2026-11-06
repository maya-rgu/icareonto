# Grouped knowledge records and JSON-LD checks

30 checks; 0 failures; 0 errors. Result: **PASS**.

Fictional clinical inputs and temporary outputs. Expected query answers are independently specified. No clinical efficacy or predictive validity is established.

Repeat: `python instantiation/scripts/check_sections.py`

| Check | Result |
|---|---|
| all deployed datatypes are supported without loss of type | PASS |
| cancer diagnosis and exposure remain connected | PASS |
| changed ontology rebuilds unchanged json in both formats | PASS |
| clinical comparison text is not mistaken for a placeholder | PASS |
| clinical profile is queryable from the participant | PASS |
| duplicate record ids across groups are rejected | PASS |
| forward and cross section references are resolved | PASS |
| invalid date and numeric value are rejected | PASS |
| jsonld preserves exact named graphs | PASS |
| jsonld preserves the exact participant graph | PASS |
| manually altered jsonld is rejected | PASS |
| new observation is added without losing history | PASS |
| new sections can be added later without changing existing record ids | PASS |
| performed update does not rewrite prescription | PASS |
| pilot can instantiate additional typed records | PASS |
| prescribed and performed exercise have separate expected values | PASS |
| property on wrong subject type is rejected | PASS |
| published query files return the specified answers | PASS |
| query files exclude another participants similar records | PASS |
| reference covers every deployed local class and property | PASS |
| removing a still referenced record is rejected | PASS |
| repeated processing is stable in turtle and jsonld | PASS |
| risk input connects to exposure and measurement | PASS |
| unknown class is rejected | PASS |
| unknown controlled value is rejected | PASS |
| unknown property is rejected even when null | PASS |
| unknown valid property value remains unasserted | PASS |
| unresolved reference does not replace existing graph | PASS |
| wrong controlled value category is rejected | PASS |
| wrong reference type is rejected | PASS |
