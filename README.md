# iCARE Onto

> ⚠️ **Status: Early-stage / Draft ontology**  
> iCARE Onto is under active development. **Classes, properties, IRIs, and axioms may change without notice** until a stable v1.0 release.  
> Users who require a stable reference are encouraged to rely on **tagged releases** rather than the `main` branch.

**iCARE Onto** is the ontology developed in the [MAYA Project](https://maya-project.eu) to support AYA (Adolescents and Young Adults) cancer survivorship care.  
It is currently in an **initial design phase** and is being iteratively refined through expert input, workshops, and use-case evaluation.

---

## Repository structure

- `ontology/modules/` – thematic modules (user, clinical, lifestyle, devices, etc.).
- `ontology/imports/` – slim extracts of external ontologies reused in iCARE Onto (NCIt, ExMO, FHIR, etc.).
- `ontology/icare-all.owl` – meta-ontology that imports all modules and core components for full browsing.
- `docs/` – background documentation, competency questions, and workshop methods.
- `catalog-v001.xml` – local mapping of ontology IRIs to file paths (so Protégé resolves imports offline).
- `CHANGELOG.md` – tracks ontology changes per version.
- `README.md` – this file.

---

## Stability & versioning

iCARE Onto currently follows a **0.x versioning scheme**, indicating a draft and unstable phase.

- During the 0.x series, **breaking changes may occur at any time**, including:
  - Renaming, modification, or removal of classes and properties
  - Changes to axioms, domain/range restrictions, or module boundaries
  - Refactoring of imports and alignments with external ontologies
- The `main` branch reflects ongoing development and **should not be considered stable**.
- Users who need a fixed and reproducible reference should use **tagged releases** and cite the corresponding version.

A **v1.0.0 release** will mark the first stable version of iCARE Onto, after which backward compatibility and deprecation policies will apply.

---

## Getting started

1. **Clone the repository**:
   ```bash
   git clone https://github.com/maya-rgu/icareonto.git
   cd icare-onto
