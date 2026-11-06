# Shared validation assets

This folder contains the wholly fictional AYA survivor fixture and the additional test data, SPARQL queries and independently authored answers for all 78 consolidated competency questions. Four controls test participant selection, unknown participants, a removed linking relationship and prescribed versus performed activity.

From the repository root, with the core Python dependencies installed:

```bash
python validation/scripts/check_demo.py
python validation/scripts/run_cq_suite.py
```

To regenerate the fixtures and local import catalogues:

```bash
python validation/scripts/build_demo.py
python validation/scripts/build_cq_suite.py
```

The CQ register is the versioned snapshot under `sources/`. The ontology is under `serialisation/`. Neither a private development folder nor an external participant database is needed. Read [the CQ guide](cq-tests/README.md) for the expected-answer methodology and limitations.

`python scripts/run_checks.py` runs the shared checks and the four tools' core tests. The summary is saved under `reports/check-summary.json`. Model-dependent encoder integration requires separate dependencies and a local pinned model; it is enabled explicitly with `--with-encoder`.

OWLAPI/HermiT checks require a compatible Protégé application bundle containing Java 11 `jjs`. The bundle location is supplied with `--protege-app` or the `ICARE_PROTEGE_APP` environment variable. No installation path is assumed:

```bash
python serialisation/scripts/validate_with_protege.py --protege-app /path/to/Protege.app
python serialisation/scripts/validate_with_protege.py --protege-app /path/to/Protege.app --output validation/cq-tests --ontology-file validation/cq-tests/coverage.ttl --report validation/reports/cq-owlapi-report.json
```

Other Protégé distributions can use the application's own profile/reasoner checks or a compatible external OWLAPI tool; the bundled launcher supports only the documented application-bundle layout.

Saved results and workflow checks must be read with their scope. The fuller grouped-record example has a documented `diagnosisDate`/`xsd:date` OWL 2 DL profile finding even though HermiT reports consistency. See [datatype compatibility](../instantiation/reports/DATATYPE_COMPATIBILITY.md). These technical tests do not establish clinical validity.
