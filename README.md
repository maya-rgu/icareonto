# iCARE Onto

**iCARE Onto** is the ontology developed in the [MAYA Project](https://maya-project.eu) to support AYA (Adolescents and Young Adults) cancer survivorship care.

---

## Repository structure

- `ontology/modules/` – thematic modules (user, clinical, lifestyle, devices, et.c.).
- `ontology/imports/` – slim extracts of external ontologies reused in iCARE Onto (NCIt, ExMO, FHIR, etc.).
- `ontology/icare-all.owl` – meta-ontology that imports all modules + core for full browsing.
- `docs/` – background docs, competency questions, workshop methods.
- `catalog-v001.xml` – local mapping of ontology IRIs to file paths (so Protégé resolves imports offline).
- `CHANGELOG.md` – tracks ontology changes per version.
- `README.md` – this file.

---

## Getting started

1. **Clone the repo**:
   ```bash
   git clone https://github.com/maya-rgu/icareonto.git
   cd icare-onto
