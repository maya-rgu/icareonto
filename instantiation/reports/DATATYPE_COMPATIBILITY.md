# Datatype compatibility surfaced by the fuller participant example

The grouped-record interface validates all ten datatypes currently declared by iCARE Onto. Populating the cancer diagnosis exposes a distinction between correct RDF data and the standard OWL 2 DL datatype map.

| Check                                                | Full participant example result                                   |
| ---------------------------------------------------- | ----------------------------------------------------------------- |
| JSON structure and field validation                  | Pass                                                              |
| Calendar-date validation for `diagnosisDate`       | Pass                                                              |
| Ontology declarations, domain/range and SHACL checks | Pass                                                              |
| SPARQL retrieval of connected records                | Pass                                                              |
| Turtle/JSON-LD and named-dataset equivalence         | Pass                                                              |
| HermiT consistency                                   | Consistent; no unsatisfiable named classes                        |
| OWLAPI OWL 2 DL profile                              | One violation: a literal typed `xsd:date` for `diagnosisDate` |

The serialised ontology already declares `diagnosisDate` with range `xsd:date`; it also uses `xsd:duration` in schedule-related properties. These datatypes are valid in RDF but are not in the standard OWL 2 datatype map. The previous enrolment-only examples did not instantiate a diagnosis-date literal. This is not a JSON-LD conversion error: both the Turtle and JSON-LD exports preserve the ontology's declared datatype.

The unmodified OWLAPI/HermiT validator reports the profile finding and returns a failing exit status for its combined strict check, while its consistency/classification results remain available in `generated/validation/owlapi-report.json`. No profile check is suppressed and no conflicting report is substituted.

The input interface, RDF queries, graph exports and independent date validation remain usable. Full OWL 2 DL conformance for populated records requires a source-model decision. A possible date-only representation is an ISO calendar-date string with explicit calendar validation/SHACL constraints; another is a timepoint model when a genuine instant is known. A date must not be converted to an invented midnight timestamp. Duration representation similarly needs an agreed policy if full OWL 2 DL conformance is required. Any such choice should be reflected in the authoritative ontology specification and then reserialised, rather than patched only in the exporter.

Source: [W3C OWL 2 Structural Specification, datatype maps](https://www.w3.org/TR/owl2-syntax/#Datatype_Maps).
