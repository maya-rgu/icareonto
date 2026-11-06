# iCARE Onto v1 — draft ontology

Open **`icareonto.ttl`** in Protégé Desktop using **File → Open**. Keep this folder and its subfolders together. The adjacent `catalog-v001.xml` maps imports to local files, so the package can be loaded offline.

This is **version `0.1.0-draft`**, a pre-release under review toward **iCARE Onto v1**. The ontology provides the semantic foundation for AYA cancer survivorship, cardiovascular health, personalised care, educational support and conversational interaction within the MAYA iCARE Health Hub.

The ontology files can be used independently of the development materials. They contain no workbook filenames, worksheet/cell references or mapping-register identifiers. Build provenance and requirements traceability are retained separately in `validation/`. The pre-release version and Draft review status are recorded consistently in each ontology header.

## Contents

| Location                    | Content                                                                                                                   |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| `icareonto.ttl`           | Main ontology importing the 17 modules and approved alignments                                                            |
| `modules/`                | One Turtle file per module, containing its classes, properties, controlled values and concept schemes                     |
| `alignments/approved.ttl` | The three approved semantic alignments, with semantic rationale and external source links                                 |
| `imports/`                | Source-derived SKOS and PROV-O reference subsets, resource metadata declarations, and unchanged official source downloads |
| `catalog-v001.xml`        | Portable local import resolution                                                                                          |
| `scripts/`                | Workbook reader, generator and validators                                                                                 |
| `validation/`             | Build provenance, source reconciliation, term inventory, import map, CQ term checks and OWLAPI/HermiT results             |

In Protégé, inspect **Classes**, **Object properties**, **Data properties**, and **Individuals**. Controlled values are individuals of their module-defined controlled classes and of `skos:Concept`. The 62 concept schemes are also individuals. Imports introduce additional external entities, so Protégé's complete counts can be larger than the local schema counts below. The selected active ontology and imported-entity display settings affect the views.

If an import appears unresolved, select the **local file** option in Protégé's import resolver and select the matching file shown in `catalog-v001.xml`. Do not substitute an online ontology simply because a local module IRI is an HTTP URL. The HTTP entity and ontology IRIs are preserved identifiers; web hosting is not required for this package.

## Coverage and development inputs

- **Ontology source:** `../sources/icareonto_review_workbook_v021126.xlsx`.
- **Approved alignments:** `../sources/icareonto_alignment_mapping_workbook_v301026_4.xlsx`, `Alignment Register` sheet.
- **Competency questions:** `../sources/icareonto_final_consolidated_competency_questions_v5.xlsx`.
- **Output:** 17 modules, 283 local classes, 284 local object properties, 137 local data properties, 304 controlled values and 62 concept schemes.
- **CQ checks:** All 78 consolidated CQs have recognised path terms. No participant instances or executed CQ answers are included.

In the ontology source workbook, the controlled vocabulary detail sheet is the source of value definitions for controlled vocabulary entries and its Module column is used to determine ontology module ownership.

## Modelling decisions (using the ontology source workbook)

1. Existing entity IRIs are preserved. For example, all modules share the existing entity namespace `http://maya-project.eu/icareonto/`; the module worksheet names do not create new entity namespaces.
2. Stable module ontology and entity IRIs are preserved. Version IRIs identify `0.1.0-draft`, separately from those stable IRIs. The next intended reviewed release is iCARE Onto v1; development-source revision numbers do not define the ontology version.
3. Named parent relationships become `rdfs:subClassOf`. Object and data properties retain their source domains, ranges and XSD datatypes. No cardinalities, inverse relations, closed enumerations or disjointness axioms are inferred from descriptions.
4. Entity definitions use `skos:definition` once. `rdfs:comment` is reserved for distinct explanatory context, such as ontology descriptions and alignment rationale. Labels and alternative labels are preserved. The `metadata#reviewStatus` annotation records Draft ontology status and the existing review statuses of controlled concepts and semantic alignments. Development provenance is kept outside the ontology: entity source cells in `validation/entity-manifest.tsv`, value source cells in `validation/controlled-value-provenance.tsv`, alignment-register IDs in `validation/alignment-trace.tsv`, and source filenames/hashes in `validation/build-report.json`.
5. Vocabulary categories remain OWL classes subclassing `skos:Concept`. Their values are named individuals, with labels, definitions, scheme membership, source status and explicit broader relationships. The schemes are not OWL classes. Lists are not treated as exhaustive or pairwise-distinct unless future modelling explicitly requires that.
6. Only mappings marked **Approved** in the primary Alignment Register are emitted as semantic axioms. The three current mappings connect Agent, ParticipantKnowledgeGraph and ConsentRecord to PROV-O. Proposed mappings, coding recommendations and all FHIR transformations remain in the workbook. The excluded rows are listed in `validation/excluded-alignments.tsv`.
7. External reference subsets preserve selected named axioms and annotations from the official W3C sources. The SKOS subset excludes unused collection/list constructs. The PROV-O subset includes Agent, Entity, Collection and InstantaneousEvent, their relevant hierarchy and disjointness. They have explicit local ontology IRIs and are labelled as subsets. The full sources are retained unchanged in `imports/skos.rdf` and `imports/prov-o.ttl` but are not imported. This avoids OWL 2 DL profile issues in unrelated full-source constructs and ontology metadata.
8. Dublin Core resource metadata predicates are declared as OWL annotation properties in `imports/metadata.ttl`. They accept the appropriate literal or IRI annotation values. In particular, `dcterms:language` supports language metadata and `dcterms:source` can link an instrument/resource to its evidence source. These declarations are a local usage convention, not a complete import of DCMI or new domain relations.

## Validation results

The iCARE Onto package was checked using RDFLib and the OWLAPI 4.5.29/HermiT 1.4.3.456 libraries bundled with Protégé:

- All generated RDF files parse, and their local imports resolve.
- The OWLAPI imports closure contains 22 ontology documents.
- The local OWL signature contains 283 classes, 284 object properties, 137 data properties and 366 named individuals (304 values plus 62 schemes).
- The complete packaged imports closure passes the OWL 2 DL profile check with **zero violations**.
- HermiT reports the ontology **consistent**, with **zero unsatisfiable named classes**, using its default datatype settings.
- Independent source reconciliation checks the saved declarations, labels, definitions, data ranges, vocabulary entries, ownership, catalogue targets and RDF/XML round-trips.

The workbook's `xsd:date` and `xsd:duration` ranges are explicitly declared and preserved. Successful classification of this schema and its controlled values does not test all possible participant literals or guarantee another reasoner's support for those datatype values. Required-field checks and value validation should be added with the subsequent knowledge-graph work. OWL domains and ranges express inference, not form-validation constraints.

## Regeneration

From the repository root, create and activate a Python environment as described in the [installation guide](../README.md). The serialiser dependencies and build commands are:

```bash
python -m pip install -r serialisation/scripts/requirements.txt
python serialisation/scripts/serialise_ontology.py
python serialisation/scripts/check_outputs.py
```

The generator is offline once RDFLib is installed and the bundled import source files are present. It overwrites generated files within `serialisation/`, so regenerate from the workbook rather than maintaining independent edits in Turtle. Update the source workbook or generator conventions first, then rebuild.

The optional OWLAPI/HermiT launcher requires a compatible Protégé application bundle containing Java 11 `jjs`. Its location is supplied explicitly; the results are written to `serialisation/validation/owlapi-report.json`:

```bash
python serialisation/scripts/validate_with_protege.py --protege-app /path/to/Protege.app
```

`ICARE_PROTEGE_APP` can supply the bundle location instead of the command-line option. This launcher supports a bundle with a `Contents/` directory and the required Java runtime; it does not support all operating-system distributions or newer Java runtimes. For other installations, profile and reasoner checks can be run in Protégé or with another compatible OWLAPI validation tool.

The generator also accepts `--ontology`, `--alignments`, `--cqs`, `--output`, `--version` and `--release`. `--version` controls ontology version metadata and version IRIs; `--release` records the build date in the development report. For a separate output location, first copy the two unchanged external source files into that location's `imports/` directory.

## External source provenance

Official W3C source files retrieved on 30 October 2026:

- SKOS: https://www.w3.org/2009/08/skos-reference/skos.rdf
- PROV-O: https://www.w3.org/ns/prov-o.ttl

Reference documentation:

- SKOS: https://www.w3.org/TR/skos-reference/
- PROV-O: https://www.w3.org/TR/prov-o/
- Dublin Core Terms: https://www.dublincore.org/specifications/dublin-core/dcmi-terms/
- Protégé local imports: https://protegewiki.stanford.edu/wiki/Importing_Ontologies_in_P41

The original external downloads retain their copyright and licensing notices. The source-derived subset files retain relevant term documentation and identify their source; they must not be represented as the full W3C ontologies.
