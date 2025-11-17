# iCARE Onto

**iCARE Onto** is the ontology developed in the [MAYA Project](https://maya-project.eu) to support 
AYA (Adolescents and Young Adults) cancer survivorship care.  
It provides a semantic backbone for integrating clinical, lifestyle, psychosocial, 
device, impact, and policy data into one coherent knowledge framework.

---

## Repository structure

- `ontology/core/` – core ontology file (`icare-core.owl`), defining shared primitives.
- `ontology/modules/` – thematic modules (clinical, lifestyle, psychosocial, devices, impact, policy).
- `ontology/imports/` – slim extracts of external ontologies reused in iCARE Onto (HPO, NCIt, ExO, ONS, FHIR).
- `ontology/icare-all.owl` – meta-ontology that imports all modules + core for full browsing.
- `shapes/` – SHACL validation rules for pilot knowledge graphs.
- `docs/` – background docs, competency questions, workshop methods.
- `examples/` – small RDF/Turtle example graphs showing how to instantiate ontology concepts.
- `catalog-v001.xml` – local mapping of ontology IRIs to file paths (so Protégé resolves imports offline).
- `CHANGELOG.md` – tracks ontology changes per version.
- `README.md` – this file.

---

## Getting started

1. **Clone the repo**:
   ```bash
   git clone https://github.com/<org>/icare-onto.git
   cd icare-onto
