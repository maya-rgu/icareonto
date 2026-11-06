// Nashorn script run by validate_with_protege.py using Protégé's installed Java libraries.
var File = Java.type('java.io.File');
var Files = Java.type('java.nio.file.Files');
var Paths = Java.type('java.nio.file.Paths');
var Charset = Java.type('java.nio.charset.StandardCharsets');
var OWLManager = Java.type('org.semanticweb.owlapi.apibinding.OWLManager');
var IRI = Java.type('org.semanticweb.owlapi.model.IRI');
var SimpleIRIMapper = Java.type('org.semanticweb.owlapi.util.SimpleIRIMapper');
var MissingImport = Java.type('org.semanticweb.owlapi.model.MissingImportHandlingStrategy');
var Imports = Java.type('org.semanticweb.owlapi.model.parameters.Imports');
var Profile = Java.type('org.semanticweb.owlapi.profiles.OWL2DLProfile');
var ReasonerFactory = Java.type('org.semanticweb.HermiT.ReasonerFactory');
var Configuration = Java.type('org.semanticweb.HermiT.Configuration');
var InferenceType = Java.type('org.semanticweb.owlapi.reasoner.InferenceType');
Java.type('org.slf4j.LoggerFactory').getLogger('ROOT').setLevel(Java.type('ch.qos.logback.classic.Level').WARN);
var root = new File(arguments[0]).getCanonicalFile();
var manager = OWLManager.createOWLOntologyManager();
manager.setOntologyLoaderConfiguration(manager.getOntologyLoaderConfiguration().setMissingImportHandlingStrategy(MissingImport.THROW_EXCEPTION));
var lines = Files.readAllLines(Paths.get(root.toString(), 'validation', 'import-map.tsv'), Charset.UTF_8);
for (var i = 1; i < lines.size(); i++) {
    var parts = String(lines.get(i)).split('\t');
    manager.getIRIMappers().add(new SimpleIRIMapper(IRI.create(parts[0]), IRI.create(new File(root, parts[1]))));
}
var entry = arguments.length > 1 ? new File(arguments[1]) : new File(root, 'icareonto.ttl');
var reportFile = arguments.length > 2 ? Paths.get(arguments[2]) : Paths.get(root.toString(), 'validation', 'owlapi-report.json');
var ontology = manager.loadOntologyFromOntologyDocument(entry);
var closure = ontology.getImportsClosure();
var report = {
    engine: 'Installed Protégé OWLAPI and HermiT',
    ontology: String(ontology.getOntologyID()),
    imports_closure_size: closure.size(),
    loaded_documents: [],
    local_signature_counts: {},
    owl2_dl_profile: {},
    reasoner: {}
};
var it = closure.iterator();
while (it.hasNext()) {
    var o = it.next();
    var document = String(manager.getOntologyDocumentIRI(o));
    if (document.indexOf('file:') === 0) {
        document = String(root.toPath().relativize(new File(Java.type('java.net.URI').create(document)).toPath()));
    }
    report.loaded_documents.push({ontology: String(o.getOntologyID()), document: document, axioms: o.getAxiomCount()});
}
function localCount(collection) {
    var i = collection.iterator(), n = 0;
    while (i.hasNext()) {
        var e = i.next();
        if (String(e.getIRI()).indexOf('http://maya-project.eu/icareonto/') === 0) n++;
    }
    return n;
}
report.local_signature_counts.classes = localCount(ontology.getClassesInSignature(Imports.INCLUDED));
report.local_signature_counts.object_properties = localCount(ontology.getObjectPropertiesInSignature(Imports.INCLUDED));
report.local_signature_counts.data_properties = localCount(ontology.getDataPropertiesInSignature(Imports.INCLUDED));
report.local_signature_counts.individuals = localCount(ontology.getIndividualsInSignature(Imports.INCLUDED));
report.total_named_individuals = ontology.getIndividualsInSignature(Imports.INCLUDED).size();
var profile = new Profile().checkOntology(ontology);
report.owl2_dl_profile.in_profile = profile.isInProfile();
report.owl2_dl_profile.violations = [];
it = profile.getViolations().iterator();
while (it.hasNext()) report.owl2_dl_profile.violations.push(String(it.next()));
var reasoner = null;
try {
    reasoner = new ReasonerFactory().createReasoner(ontology);
    report.reasoner.datatype_mode = 'strict';
} catch (err) {
    report.reasoner.strict_initialisation_error = String(err);
    var configuration = new Configuration();
    configuration.ignoreUnsupportedDatatypes = true;
    reasoner = new ReasonerFactory().createReasoner(ontology, configuration);
    report.reasoner.datatype_mode = 'unsupported datatypes ignored; not full datatype validation';
}
try {
    report.reasoner.consistent = reasoner.isConsistent();
    if (report.reasoner.consistent) {
        reasoner.precomputeInferences(Java.to([InferenceType.CLASS_HIERARCHY], 'org.semanticweb.owlapi.reasoner.InferenceType[]'));
        report.reasoner.unsatisfiable_named_classes = [];
        it = reasoner.getUnsatisfiableClasses().getEntitiesMinusBottom().iterator();
        while (it.hasNext()) report.reasoner.unsatisfiable_named_classes.push(String(it.next().getIRI()));
    }
} finally {
    reasoner.dispose();
}
Files.write(reportFile, new java.lang.String(JSON.stringify(report, null, 2) + '\n').getBytes(Charset.UTF_8));
print(JSON.stringify({imports: report.imports_closure_size, local_signature_counts: report.local_signature_counts, profile: report.owl2_dl_profile.in_profile, profile_violations: report.owl2_dl_profile.violations.length, reasoner: report.reasoner}, null, 2));
if (!report.owl2_dl_profile.in_profile || !report.reasoner.consistent || (report.reasoner.unsatisfiable_named_classes || []).length > 0) throw new Error('OWL profile/consistency/classification failed');
