# Tool roles

| Tool | Role | Entry point |
|---|---|---|
| Ontology Serialiser | Convert the reviewed ontology, alignment and CQ snapshots into modular OWL | `serialisation/scripts/serialise_ontology.py` |
| KG Instantiator | Validate pilot and participant JSON, resolve ontology relationships and refresh Turtle/JSON-LD graphs | `instantiation/kg-instantiator.py` |
| Pilot Mapper | Rank candidate ontology classes, record reviewed decisions and bind profiles to graph generation | `pilot-mapping/scripts/pilot_mapping.py` |
| Education Resource Selector | Build the reviewed catalogue, select candidate signposts and illustrate draft learning activities | `education/scripts/education_resources.py` |

The tools share the ontology under `serialisation/`. This folder hierarchy is part of the packaged defaults. Templates and schemas are public interfaces; operational records belong outside the versioned examples.
