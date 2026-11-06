# KG Instantiator checks

18 checks; 0 failures; 0 errors. Result: **PASS**.

Fictional JSON inputs and temporary outputs; existing delivered graphs and the ontology are unchanged.

Repeat: `python instantiation/scripts/check_instantiator.py`

| Check | Result |
|---|---|
| filled invalid optional value is rejected | PASS |
| incomplete supplied consent record is rejected | PASS |
| named command accepts the same file for creation and refresh | PASS |
| optional placeholder is not published | PASS |
| participant cannot be silently reassigned | PASS |
| participant requires a registered pilot | PASS |
| participant template leaves unknown information unasserted | PASS |
| pilot refresh cannot remove a referenced arm | PASS |
| pilot refresh updates shared context without rewriting participants | PASS |
| pilot template can leave phases and arms unknown | PASS |
| progressive enrichment preserves identity and archives previous graph | PASS |
| refresh rejects a controlled value with an incompatible ontology type | PASS |
| refresh rejects a property absent from the loaded ontology | PASS |
| required placeholders prevent publication | PASS |
| snapshot omission removes old optional assertions | PASS |
| unchanged input keeps seed bytes | PASS |
| unknown field is rejected even when null | PASS |
| wrong study site pair is rejected | PASS |
