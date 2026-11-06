#!/usr/bin/env python3
"""Build a separate synthetic coverage fixture and authored tests for all 78 CQs.

Expected answers below are authored constants, not query-derived results.
The baseline Spanish survivor fixture and the ontology are not modified.
"""
import csv
import hashlib
import json
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from rdflib import Graph, Literal, Namespace, OWL, RDF, RDFS, URIRef, XSD
from rdflib.namespace import DCTERMS

KG = Path(__file__).resolve().parents[1]
REPO = KG.parent
OUT = KG / "cq-tests"
sys.path.insert(0, str(REPO / "serialisation/scripts"))
from serialise_ontology import read_xlsx

IC = Namespace("http://maya-project.eu/icareonto/")
D = Namespace("https://example.org/maya/demo/es/")
T = Namespace("https://example.org/maya/demo/cq-tests/")
ENTRY = URIRef(str(T).rstrip("/"))
g = Graph()
g.bind("icare", IC)
g.bind("demo", D)
g.bind("test", T)
g.bind("owl", OWL)
g.bind("rdfs", RDFS)
g.bind("xsd", XSD)
g.bind("dcterms", DCTERMS)


def node(key, cls, label):
    n = T[key]
    g.add((n, RDF.type, OWL.NamedIndividual))
    g.add((n, RDF.type, IC[cls]))
    g.add((n, RDFS.label, Literal(label, lang="en")))
    return n


def rel(s, p, o):
    g.add((s, IC[p], o))


def value(s, p, v, dtype="string"):
    g.add((s, IC[p], Literal(str(v), datatype=XSD[dtype])))


def note(s, text):
    g.add((s, RDFS.comment, Literal(text, lang="en")))


def time(key, timestamp):
    n = node(key, "Timepoint", "Fictional test time " + key)
    value(n, "timepointDateTime", timestamp, "dateTime")
    return n


g.add((ENTRY, RDF.type, OWL.Ontology))
g.add((ENTRY, OWL.imports, URIRef(str(D).rstrip("/"))))
g.add((ENTRY, RDFS.label, Literal("Synthetic CQ coverage supplement", lang="en")))
note(ENTRY, "Wholly fictional technical test data supplementing the Spanish survivor graph. Clinical conditions, evidence, scores, ranges, thresholds and care associations are invented; none constitute validated clinical knowledge or real participant information.")

# Risk estimates and two distinct factor contributions.
cv_condition = node("cv-condition", "CardiovascularCondition", "Fictional late-effect condition for query testing")
g.add((cv_condition, RDF.type, IC.TreatmentRelatedCondition))
rel(D["risk-estimate"], "riskEstimateEstimatesConditionRisk", cv_condition)
prior_factor = node("prior-treatment-factor", "NonModifiableRiskFactor", "Fictional historical-treatment factor")
sodium_factor = node("dietary-factor", "ModifiableRiskFactor", "Fictional dietary factor, contrasting with low activity")
for key, factor, number in (("activity-contribution", D["low-activity-risk-factor"], "0.4"), ("prior-contribution", prior_factor, "0.6")):
    contribution = node(key, "RiskFactorContribution", "Authored example factor contribution")
    rel(D["risk-estimate"], "riskEstimateHasContribution", contribution)
    rel(contribution, "riskFactorContributionForRiskFactor", factor)
    value(contribution, "contributionValue", number, "decimal")
    note(contribution, "Arbitrary fixture coefficient; not an output from a validated risk model.")
age = node("age-attribute", "DemographicAttribute", "Fictional age attribute at enrolment")
value(age, "personAttributeName", "Age at enrolment")
value(age, "personAttributeValue", "27")
rel(D.participant, "personHasAttribute", age)
rel(D["model-input"], "modelInputIncludesPersonAttribute", age)
derivation = node("recommendation-derivation", "RecommendationDerivation", "Fictional derivation linking a risk profile to a recommendation")
rel(derivation, "recommendationDerivationUsesRiskProfile", D["risk-profile"])
rel(derivation, "recommendationDerivationProduces", D["recommendation-walking"])

# Conditions and unrelated records test participant and class filters.
late_record = node("late-effect-record", "ClinicalConditionRecord", "Fictional treatment-related condition record")
rel(late_record, "conditionRecordRecordsCondition", cv_condition)
rel(late_record, "clinicalRecordHasSource", D["source-clinical-record"])
rel(late_record, "clinicalRecordRecordedAt", D["time-baseline"])
rel(D["clinical-profile"], "clinicalProfileIncludesRecord", late_record)
unrelated_condition = node("unrelated-condition", "MetabolicCondition", "Fictional condition not asserted to be treatment-related")
unrelated_record = node("unrelated-condition-record", "ClinicalConditionRecord", "Contrasting non-treatment-related condition record")
rel(unrelated_record, "conditionRecordRecordsCondition", unrelated_condition)
rel(D["clinical-profile"], "clinicalProfileIncludesRecord", unrelated_record)
other_person = node("control-person", "Person", "Separate fictional control person")
other_diagnosis = node("control-diagnosis", "CancerDiagnosis", "Control person's fictional diagnosis")
rel(other_person, "hasCancerDiagnosis", other_diagnosis)
other_profile = node("control-clinical-profile", "ClinicalProfile", "Control person's clinical profile")
rel(other_person, "personHasClinicalProfile", other_profile)
other_record = node("control-record", "ClinicalConditionRecord", "Control person's condition record")
rel(other_profile, "clinicalProfileIncludesRecord", other_record)
rel(other_record, "conditionRecordRecordsCondition", cv_condition)

# General educational and recommendation metadata.
guideline = node("guideline", "Guideline", "Fictional guideline for technical retrieval tests")
note(guideline, "Invented catalogue entry; no genuine guideline or clinical recommendation is asserted.")
rel(guideline, "knowledgeResourceContainsRecommendation", D["recommendation-walking"])
rel(guideline, "knowledgeResourceContainsRecommendation", D["recommendation-nutrition"])
contra = node("contraindication", "Contraindication", "Fictional restriction used only for a query test")
value(contra, "contraindicationText", "Demonstration-only condition requiring fictional reviewer approval.")
rel(D["recommendation-walking"], "recommendationHasContraindication", contra)

# A resource addressing several topics must also match the revised nutrition CQ.
mixed = node("mixed-topic-resource", "EducationalResource", "Fictional activity resource with a secondary nutrition discussion")
rel(mixed, "knowledgeResourceHasTopic", IC.PhysicalActivity)
rel(mixed, "knowledgeResourceHasTopic", IC.Nutrition)
note(mixed, "Addresses physical activity and nutrition. CQ-019 retrieves any resource addressing nutrition, without ranking its topics.")

# Socioeconomic/cultural information and dialogue context filters.
employment = node("employment", "EmploymentStatus", "Fictional part-time employment context")
rel(employment, "hasEmploymentStatus", IC.Employed)
finance = node("financial-context", "FinancialConstraint", "Fictional financial constraint")
rel(finance, "hasFinancialConstraintStatus", IC.SomeFinancialConstraint)
culture = node("communication-context", "CulturalFactor", "Fictional preference for family-inclusive discussions")
for key, factor in (("employment-record", employment), ("financial-record", finance), ("cultural-record", culture)):
    record = node(key, "SocialContextRecord", "Fictional " + key)
    rel(D["social-profile"], "socialProfileIncludesRecord", record)
    rel(record, "socialContextRecordRecordsFactor", factor)
    rel(record, "socialContextRecordHasSource", D["source-participant"])
    rel(record, "socialContextRecordRecordedAt", D["time-baseline"])
    if key != "financial-record":
        rel(D["dialogue-context"], "dialogueContextIncludesEntity", record)
rel(IC.PlainLanguageStrategy, "dialogueStrategyAdaptedToContext", D["health-literacy-record"])
alternate_strategy = node("alternate-strategy", "DialogueStrategy", "Fictional strategy adapted to a different context")
rel(alternate_strategy, "dialogueStrategyAdaptedToContext", T["cultural-record"])

# Anthropometric classification and protocol membership are explicit test data.
g.add((D.bmi, RDF.type, IC.AnthropometricParameter))
g.add((D["systolic-bp"], RDF.type, IC.PhysiologicalParameter))
g.add((D["diastolic-bp"], RDF.type, IC.PhysiologicalParameter))
body_fat = node("body-fat-parameter", "AnthropometricParameter", "Fictional body-fat percentage parameter")
for parameter in (D.weight, D.height, D.bmi, body_fat):
    rel(D["body-protocol"], "protocolSpecifiesParameter", parameter)
body_event = node("body-fat-event", "MeasurementEvent", "Fictional body-composition measurement")
body_result = node("body-fat-result", "ObservationResult", "Fictional body-composition observation")
rel(body_event, "measurementEventMeasures", body_fat)
rel(body_event, "measurementEventFollowsProtocol", D["body-protocol"])
rel(body_event, "measurementEventHasOutput", body_result)
rel(body_event, "activityExecutionOccursAt", D["time-baseline"])
rel(D.participant, "personParticipatesInMeasurement", body_event)
rel(D["model-input"], "modelInputDerivedFromObservation", body_result)
rel(D["model-input"], "modelInputDerivedFromObservation", D["baseline-weight-result"])
range_ = node("reference-range", "ReferenceRange", "Arbitrary technical-test range, not clinical guidance")
value(range_, "referenceRangeLowerBound", "100", "decimal")
value(range_, "referenceRangeUpperBound", "130", "decimal")
threshold = node("alert-threshold", "AlertThreshold", "Arbitrary technical-test threshold, not a clinical alert rule")
value(threshold, "thresholdNumericValue", "150", "decimal")
rel(D["followup-sbp-result"], "observationHasReferenceRange", range_)
rel(D["followup-sbp-result"], "observationComparedAgainst", threshold)
rel(D["followup-sbp-result"], "observationHasThresholdCategory", IC.WithinReferenceRange)

# Instant and interval observations, including exact upper-bound exclusions.
interval = node("measurement-interval", "TimeInterval", "Fictional interval measurement")
rel(interval, "intervalStartsAt", time("interval-start", "2026-10-24T07:00:00+02:00"))
rel(interval, "intervalEndsAt", time("interval-end", "2026-10-24T08:00:00+02:00"))
averaged = node("averaged-sbp-event", "MeasurementEvent", "Fictional interval-based systolic observation")
averaged_result = node("averaged-sbp-result", "ObservationResult", "Fictional interval result")
rel(averaged, "measurementEventMeasures", D["systolic-bp"])
rel(averaged, "measurementEventHasOutput", averaged_result)
rel(averaged, "activityExecutionOccursDuring", interval)
rel(D.participant, "personParticipatesInMeasurement", averaged)
for key, timestamp in (("before-window", "2026-10-18T23:59:59Z"), ("at-upper-bound", "2026-10-28T00:00:00Z")):
    event = node(key + "-event", "MeasurementEvent", "Contrasting " + key + " event")
    result = node(key + "-result", "ObservationResult", "Contrasting out-of-window result")
    rel(event, "measurementEventMeasures", D["systolic-bp"])
    rel(event, "measurementEventHasOutput", result)
    rel(event, "activityExecutionOccursAt", time(key + "-time", timestamp))

# Keep background citations alongside the specific validation-evidence relation.
instrument = node("questionnaire", "Questionnaire", "Fictional instrument for validation-provenance testing")
validation_evidence = node("validation-evidence", "EvidenceSource", "Fictional validation study for this instrument")
background_evidence = node("background-evidence", "EvidenceSource", "Fictional background study, not instrument-validation evidence")
for evidence in (validation_evidence, background_evidence):
    g.add((instrument, DCTERMS.source, evidence))
rel(instrument, "measurementInstrumentHasValidationEvidence", validation_evidence)
note(validation_evidence, "Fixture oracle: specifically supports the fictional instrument's validation. No actual psychometric validation is claimed.")
note(background_evidence, "General background citation only; it is not linked by measurementInstrumentHasValidationEvidence.")

# Nutrition records, a quantitative test instruction and an adherence result.
nutrition_behaviour = node("nutrition-behaviour", "NutritionBehaviour", "Fictional dietary behaviour")
nutrition_record = node("nutrition-record", "BehaviourRecord", "Fictional nutrition self-report")
rel(nutrition_record, "behaviourRecordRecordsBehaviour", nutrition_behaviour)
rel(D["lifestyle-profile"], "lifestyleProfileIncludesBehaviourRecord", nutrition_record)
rel(nutrition_record, "behaviourRecordRelatesToActivity", D["nutrition-intervention"])
rel(nutrition_behaviour, "behaviourInfluencesRiskFactor", sodium_factor)
instruction = node("quantified-nutrition-instruction", "NutritionInstruction", "Fictional quantity/unit test instruction")
value(instruction, "nutritionTargetAmount", "1", "decimal")
value(instruction, "nutritionTargetUnitText", "demo-portion/day")
value(instruction, "nutritionInstructionText", "Arbitrary quantity/unit fixture; not a dietary recommendation.")
rel(instruction, "nutritionInstructionTargetsComponent", IC.WholeGrains)
rel(instruction, "nutritionInstructionHasActionType", IC.Maintain)
schedule = node("nutrition-schedule", "Schedule", "Fictional instruction schedule")
rel(schedule, "scheduleHasRecurrencePattern", IC.DailyRecurrence)
rel(instruction, "nutritionInstructionHasSchedule", schedule)
rel(D["nutrition-intervention"], "nutritionInterventionSpecifiesInstruction", instruction)
assessment = node("adherence-assessment", "ExerciseAdherenceAssessment", "Fictional exercise-adherence assessment")
adherence = node("adherence-result", "ExerciseAdherenceResult", "Fictional duration-completion result")
rel(assessment, "adherenceAssessmentHasResult", adherence)
rel(assessment, "adherenceAssessmentEvaluatesPrescription", D["exercise-prescription"])
rel(assessment, "adherenceAssessmentUsesPerformedSession", D["performed-walking-session"])
value(adherence, "adherencePercent", "90", "decimal")
note(adherence, "Illustrative 18/20 duration-completion percentage; not a validated adherence assessment.")
risk_trigger = node("risk-trigger", "RiskBasedTrigger", "Authored risk-profile-to-review association")
observation_trigger = node("observation-trigger", "MeasurementBasedTrigger", "Authored observation-to-review association")
rel(risk_trigger, "riskBasedTriggerUsesRiskProfile", D["risk-profile"])
rel(observation_trigger, "measurementBasedTriggerUsesObservation", D["followup-sbp-result"])
rel(D["clinical-review"], "activityHasTrigger", risk_trigger)
rel(D["clinical-review"], "activityHasTrigger", observation_trigger)
other_plan = node("control-care-plan", "CarePlan", "Contrasting control person's plan")
other_checkup = node("control-checkup", "MedicalCheckUpActivity", "Contrasting check-up in another plan")
rel(other_plan, "carePlanIntendedFor", other_person)
rel(other_plan, "carePlanIncludesActivity", other_checkup)

PREFIX = """PREFIX icare: <http://maya-project.eu/icareonto/>
PREFIX demo: <https://example.org/maya/demo/es/>
PREFIX test: <https://example.org/maya/demo/cq-tests/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
"""
cases = []


def add(number, query, expected, **extra):
    cases.append(dict(id=f"CQ-{number:03d}", query=PREFIX + query + "\n", expected=expected, **extra))


def paths(number, subject, path, variable, expected, **extra):
    add(number, f"SELECT DISTINCT ?{variable} WHERE {{ {subject} {path} ?{variable} . }}", [{variable: x} for x in expected], **extra)


def subclasses(number, cls, expected):
    add(number, f"SELECT DISTINCT ?type WHERE {{ ?type rdfs:subClassOf+ icare:{cls} . FILTER(STRSTARTS(STR(?type), STR(icare:))) }}", [{"type": "icare:" + x} for x in expected], scope="Schema enumeration; local named subclasses, excluding the root class")


add(1, "SELECT DISTINCT ?factor WHERE { ?factor a/rdfs:subClassOf* icare:ModifiableRiskFactor . }", [{"factor": "demo:low-activity-risk-factor"}, {"factor": "test:dietary-factor"}], scope="Instances in the combined synthetic graph")
add(2, "SELECT DISTINCT ?intervention WHERE { ?intervention icare:interventionTargetsRiskFactor demo:low-activity-risk-factor ; a/rdfs:subClassOf* icare:Intervention . }", [{"intervention": "demo:exercise-intervention"}])
paths(3, "demo:risk-estimate", "icare:riskEstimateEstimatesConditionRisk", "condition", ["test:cv-condition"])
paths(4, "demo:risk-estimate", "icare:riskEstimateEstimatesEventRisk", "event", ["demo:adverse-cardiac-event"])
add(5, "SELECT ?factor ?value WHERE { demo:risk-estimate icare:riskEstimateHasContribution ?contribution . ?contribution icare:riskFactorContributionForRiskFactor ?factor . OPTIONAL { ?contribution icare:contributionValue ?value } }", [{"factor": "demo:low-activity-risk-factor", "value": "0.4"}, {"factor": "test:prior-treatment-factor", "value": "0.6"}], numeric=["value"])
paths(6, "demo:risk-estimate", "icare:riskEstimateHasInterpretation", "interpretation", ["demo:risk-interpretation"])
paths(7, "demo:participant", "icare:hasCancerDiagnosis", "diagnosis", ["demo:cancer-diagnosis"])
add(8, "SELECT ?record ?condition WHERE { demo:participant icare:personHasClinicalProfile/icare:clinicalProfileIncludesRecord ?record . ?record icare:conditionRecordRecordsCondition ?condition . ?condition a/rdfs:subClassOf* icare:TreatmentRelatedCondition . }", [{"record": "test:late-effect-record", "condition": "test:cv-condition"}])
paths(9, "demo:participant", "icare:personHasCancerTreatmentHistory/icare:cancerTreatmentHistoryHasRecord/icare:treatmentRecordIndicatesExposure", "exposure", ["demo:anthracycline-exposure"])
add(10, "SELECT ?exposure ?risk WHERE { ?exposure icare:treatmentExposureIsRiskFactorOf ?risk . }", [{"exposure": "demo:anthracycline-exposure", "risk": "demo:treatment-related-risk"}])
add(11, "SELECT ?record ?type WHERE { demo:participant icare:personHasClinicalProfile/icare:clinicalProfileIncludesRecord ?record . ?record a ?type . ?type rdfs:subClassOf* icare:ClinicalRecord . }", [{"record": "demo:symptom-record", "type": "icare:SymptomRecord"}, {"record": "test:late-effect-record", "type": "icare:ClinicalConditionRecord"}, {"record": "test:unrelated-condition-record", "type": "icare:ClinicalConditionRecord"}], scope="Asserted clinical record types; subtype filtering uses explicit schema paths")
add(12, "SELECT DISTINCT ?guideline WHERE { ?guideline a/rdfs:subClassOf* icare:Guideline . }", [{"guideline": "test:guideline"}])
paths(13, "test:guideline", "icare:knowledgeResourceContainsRecommendation", "recommendation", ["demo:recommendation-walking", "demo:recommendation-nutrition"])
add(14, "SELECT DISTINCT ?resource WHERE { ?resource icare:knowledgeResourceSupportsRecommendation demo:recommendation-walking . }", [{"resource": "demo:resource-walking-es"}])
subclasses(15, "Intervention", ["ExerciseIntervention", "NutritionIntervention", "HealthLiteracyIntervention"])
add(16, "SELECT DISTINCT ?risk WHERE { ?derivation icare:recommendationDerivationProduces demo:recommendation-walking ; icare:recommendationDerivationUsesRiskProfile ?risk . }", [{"risk": "demo:risk-profile"}])
paths(17, "demo:recommendation-walking", "icare:recommendationRecommendsActivity", "activity", ["demo:exercise-intervention"])
add(18, "SELECT DISTINCT ?attribute WHERE { ?execution icare:modelExecutionGeneratesRiskProfile demo:risk-profile ; icare:modelExecutionUsesInput/icare:modelInputIncludesPersonAttribute ?attribute . }", [{"attribute": "test:age-attribute"}])
add(19, "SELECT DISTINCT ?resource WHERE { ?resource icare:knowledgeResourceHasTopic icare:Nutrition . }", [{"resource": "demo:resource-nutrition-es"}, {"resource": "test:mixed-topic-resource"}], scope="Includes both nutrition-focused and mixed-topic resources that address nutrition, as required by the revised CQ")
paths(20, "demo:resource-late-effects-es", "icare:healthLiteracyResourceAddressesNeed", "need", ["icare:InformationComprehensionSupportNeed"])
paths(21, "demo:literacy-intervention", "icare:healthLiteracyInterventionUsesResource", "resource", ["demo:resource-late-effects-es"])
paths(22, "demo:resource-late-effects-es", "icare:knowledgeResourceHasFormat", "format", ["icare:Video"])
paths(23, "demo:resource-late-effects-es", "icare:knowledgeResourceHasComplexityLevel", "complexity", ["icare:FoundationalComplexity"])
paths(24, "demo:resource-late-effects-es", "icare:knowledgeResourceHasAccessibilityFeature", "feature", ["icare:PlainLanguage", "icare:Captions"])
paths(25, "demo:resource-late-effects-es", "dcterms:language", "language", ["es-ES"], datatypes={"language": str(XSD.language)})
add(26, "SELECT DISTINCT ?recommendation WHERE { ?recommendation icare:recommendationAppliesToSymptom demo:fatigue . }", [{"recommendation": "demo:symptom-recommendation"}])
paths(27, "demo:recommendation-walking", "icare:recommendationHasApplicabilityCriterion", "criterion", ["demo:recommendation-criterion"])
paths(28, "demo:recommendation-walking", "icare:recommendationHasContraindication", "contraindication", ["test:contraindication"])
subclasses(29, "SocialContextFactor", ["DigitalLiteracy", "HealthLiteracy", "SupportNetwork", "LivingSituation", "SocioEconomicFactor", "EducationalAttainment", "EmploymentStatus", "FinancialConstraint", "CulturalFactor", "AccessOrEngagementBarrier", "TrustConcern", "PrivacyConcern", "LanguageBarrier", "TransportationBarrier"])
add(30, "SELECT ?record ?factor WHERE { demo:participant icare:personHasSocialContextProfile/icare:socialProfileIncludesRecord ?record . ?record icare:socialContextRecordRecordsFactor ?factor . ?factor a/rdfs:subClassOf* icare:SocioEconomicFactor . }", [{"record": "test:employment-record", "factor": "test:employment"}, {"record": "test:financial-record", "factor": "test:financial-context"}])
add(31, "SELECT ?record ?factor WHERE { demo:participant icare:personHasSocialContextProfile/icare:socialProfileIncludesRecord ?record . ?record icare:socialContextRecordRecordsFactor ?factor . ?factor a/rdfs:subClassOf* icare:CulturalFactor . }", [{"record": "test:cultural-record", "factor": "test:communication-context"}])
add(32, "SELECT DISTINCT ?record WHERE { demo:response icare:agentResponseUsesContext/icare:dialogueContextIncludesEntity ?record . ?record a/rdfs:subClassOf* icare:SocialContextRecord . }", [{"record": "demo:health-literacy-record"}, {"record": "test:employment-record"}, {"record": "test:cultural-record"}])
paths(33, "demo:dialogue-session", "icare:dialogueSessionUsesStrategy", "strategy", ["icare:PlainLanguageStrategy"])
add(34, "SELECT DISTINCT ?strategy WHERE { ?strategy icare:dialogueStrategyAdaptedToContext demo:health-literacy-record . }", [{"strategy": "icare:PlainLanguageStrategy"}])
subclasses(35, "LifestyleBehaviour", ["NutritionBehaviour", "DietaryPattern", "PhysicalActivityBehaviour", "SedentaryBehaviour", "SleepBehaviour", "SmokingBehaviour", "AdherenceBehaviour", "AlcoholUseBehaviour", "SubstanceUseBehaviour", "MedicationAdherenceBehaviour", "MonitoringAdherenceBehaviour", "CarePlanAdherenceBehaviour"])
paths(36, "demo:activity-behaviour", "icare:behaviourInfluencesRiskFactor", "factor", ["demo:low-activity-risk-factor"])
paths(37, "demo:activity-behaviour-record", "icare:behaviourRecordRelatesToActivity", "activity", ["demo:exercise-intervention"])
paths(38, "demo:activity-behaviour-record", "icare:behaviourRecordRelatesToGoal", "goal", ["demo:walking-goal"])
anthro = [{"parameter": x} for x in ("demo:weight", "demo:height", "demo:bmi", "test:body-fat-parameter")]
add(39, "SELECT DISTINCT ?parameter WHERE { ?parameter a/rdfs:subClassOf* icare:AnthropometricParameter . }", anthro)
add(40, "SELECT DISTINCT ?parameter WHERE { ?protocol a/rdfs:subClassOf* icare:BodyCompositionProtocol ; icare:protocolSpecifiesParameter ?parameter . ?parameter a/rdfs:subClassOf* icare:MeasurableParameter . }", anthro, scope="Parameters specified by a body-composition protocol, rather than a dedicated body-composition parameter class")
add(41, "SELECT DISTINCT ?parameter WHERE { ?parameter a/rdfs:subClassOf* icare:PhysiologicalParameter . }", anthro + [{"parameter": "demo:systolic-bp"}, {"parameter": "demo:diastolic-bp"}])
add(42, "SELECT ?time ?datetime WHERE { demo:baseline-sbp-event icare:activityExecutionOccursAt ?time . ?time icare:timepointDateTime ?datetime . }", [{"time": "demo:time-baseline", "datetime": "2026-10-20T08:30:00+02:00"}], datatypes={"datetime": str(XSD.dateTime)})
add(43, '''SELECT ?result ?time WHERE {
  ?event icare:measurementEventMeasures demo:systolic-bp ; icare:measurementEventHasOutput ?result .
  { ?event icare:activityExecutionOccursAt/icare:timepointDateTime ?time .
    FILTER(?time >= "2026-10-19T00:00:00Z"^^xsd:dateTime && ?time < "2026-10-28T00:00:00Z"^^xsd:dateTime)
  } UNION {
    ?event icare:activityExecutionOccursDuring ?interval .
    ?interval icare:intervalStartsAt/icare:timepointDateTime ?time ; icare:intervalEndsAt/icare:timepointDateTime ?end .
    FILTER(?end > "2026-10-19T00:00:00Z"^^xsd:dateTime && ?time < "2026-10-28T00:00:00Z"^^xsd:dateTime)
  }
} ORDER BY ?time''', [{"result": "demo:baseline-sbp-result", "time": "2026-10-20T08:30:00+02:00"}, {"result": "test:averaged-sbp-result", "time": "2026-10-24T07:00:00+02:00"}, {"result": "demo:followup-sbp-result", "time": "2026-10-27T08:30:00+01:00"}], ordered=True, datatypes={"time": str(XSD.dateTime)}, scope="Systolic observations in [19 Oct 00:00Z, 28 Oct 00:00Z); intervals overlap the window; point at upper boundary excluded")
paths(44, "demo:followup-sbp-result", "icare:observationHasThresholdCategory", "category", ["icare:WithinReferenceRange"])
paths(45, "demo:followup-sbp-result", "icare:observationHasReferenceRange", "range", ["test:reference-range"])
add(46, "SELECT DISTINCT ?observation WHERE { demo:model-execution icare:modelExecutionUsesInput/icare:modelInputDerivedFromObservation ?observation . ?event icare:measurementEventHasOutput ?observation ; icare:measurementEventFollowsProtocol ?protocol . ?protocol a/rdfs:subClassOf* icare:BodyCompositionProtocol . }", [{"observation": "demo:baseline-weight-result"}, {"observation": "test:body-fat-result"}])
paths(47, "demo:followup-sbp-result", "icare:observationComparedAgainst", "threshold", ["test:alert-threshold"])
paths(48, "demo:baseline-sbp-event", "icare:measurementEventUsesInstrument", "instrument", ["demo:blood-pressure-monitor"])
paths(49, "demo:bp-protocol", "icare:protocolSpecifiesParameter", "parameter", ["demo:systolic-bp", "demo:diastolic-bp"])
paths(50, "demo:bp-protocol", "icare:protocolSpecifiesMethod", "method", ["demo:bp-method"])
add(51, "SELECT DISTINCT ?evidence WHERE { test:questionnaire icare:measurementInstrumentHasValidationEvidence ?evidence . ?evidence a/rdfs:subClassOf* icare:EvidenceSource . }", [{"evidence": "test:validation-evidence"}], forbidden=[{"evidence": "test:background-evidence"}], scope="Uses the explicit validation-evidence relation and excludes an instrument's general background citation")
add(52, "SELECT DISTINCT ?record WHERE { demo:participant icare:personHasLifestyleProfile/icare:lifestyleProfileIncludesBehaviourRecord ?record . ?record icare:behaviourRecordRecordsBehaviour ?behaviour . ?behaviour a/rdfs:subClassOf* icare:NutritionBehaviour . }", [{"record": "test:nutrition-record"}])
paths(53, "demo:nutrition-instruction", "icare:nutritionInstructionTargetsComponent", "component", ["icare:FruitAndVegetables"])
paths(54, "demo:nutrition-instruction", "icare:nutritionInstructionHasActionType", "action", ["icare:Increase"])
add(55, "SELECT ?amount ?unit WHERE { test:quantified-nutrition-instruction icare:nutritionTargetAmount ?amount ; icare:nutritionTargetUnitText ?unit . }", [{"amount": "1", "unit": "demo-portion/day"}], numeric=["amount"])
paths(56, "test:quantified-nutrition-instruction", "icare:nutritionInstructionHasSchedule", "schedule", ["test:nutrition-schedule"])
paths(57, "demo:nutrition-intervention", "icare:nutritionInterventionSpecifiesInstruction", "instruction", ["demo:nutrition-instruction", "test:quantified-nutrition-instruction"])
paths(58, "test:nutrition-record", "icare:behaviourRecordRelatesToActivity", "activity", ["demo:nutrition-intervention"])
add(59, "SELECT DISTINCT ?recommendation WHERE { ?recommendation icare:recommendationRecommendsActivity demo:nutrition-intervention . }", [{"recommendation": "demo:recommendation-nutrition"}])
add(60, "SELECT DISTINCT ?modality WHERE { ?modality a icare:ExerciseModality . }", [{"modality": "icare:" + x} for x in ("AerobicExercise", "BalanceTraining", "CombinedTraining", "FlexibilityExercise", "ResistanceTraining")])
add(61, "SELECT DISTINCT ?pattern WHERE { ?pattern a icare:ExerciseTrainingPattern . }", [{"pattern": "icare:" + x} for x in ("CircuitTraining", "ContinuousTraining", "HighIntensityIntervalTraining", "IntervalTraining")])
paths(62, "demo:exercise-prescription", "icare:exercisePrescriptionIncludesActivity", "activity", ["demo:walking-activity"])
add(63, "SELECT ?minutes WHERE { demo:exercise-prescription icare:exercisePrescriptionIncludesActivity demo:walking-activity . demo:walking-activity icare:durationMinutes ?minutes . }", [{"minutes": "20"}], numeric=["minutes"])
add(64, "SELECT ?minutes WHERE { demo:performed-walking-session icare:performedSessionIncludesActivity ?activity . ?activity icare:durationMinutes ?minutes . }", [{"minutes": "18"}], numeric=["minutes"])
paths(65, "demo:exercise-intervention", "icare:interventionTargetsRiskFactor", "factor", ["demo:low-activity-risk-factor"])
paths(66, "demo:exercise-intervention", "icare:activityContributesToGoal", "goal", ["demo:walking-goal"])
add(67, "SELECT DISTINCT ?recommendation WHERE { ?recommendation icare:recommendationRecommendsActivity demo:exercise-intervention . }", [{"recommendation": "demo:recommendation-walking"}])
paths(68, "demo:performed-walking-session", "icare:performedSessionRealises", "planned", ["demo:planned-walking-session"])
paths(69, "test:adherence-assessment", "icare:adherenceAssessmentHasResult", "result", ["test:adherence-result"])
add(70, "SELECT DISTINCT ?resource WHERE { ?activity icare:activityContributesToGoal demo:walking-goal . ?recommendation icare:recommendationRecommendsActivity ?activity . ?resource icare:knowledgeResourceSupportsRecommendation ?recommendation . }", [{"resource": "demo:resource-walking-es"}])
add(71, "SELECT DISTINCT ?activity WHERE { demo:care-plan icare:carePlanIncludesActivity ?activity . ?activity a/rdfs:subClassOf* icare:MedicalCheckUpActivity . }", [{"activity": "demo:clinical-review"}])
add(72, "SELECT DISTINCT ?recommendation WHERE { ?recommendation icare:recommendationRecommendsActivity demo:clinical-review . }", [{"recommendation": "demo:symptom-recommendation"}])
paths(73, "demo:clinical-review", "icare:activityHasTrigger/icare:riskBasedTriggerUsesRiskProfile", "profile", ["demo:risk-profile"])
paths(74, "demo:clinical-review", "icare:activityHasTrigger/icare:measurementBasedTriggerUsesObservation", "observation", ["demo:followup-sbp-result"])
paths(75, "demo:symptom-trigger", "icare:symptomBasedTriggerUsesSymptomRecord", "record", ["demo:symptom-record"])
paths(76, "demo:clinical-review", "icare:activityHasSchedule", "schedule", ["demo:review-schedule"])
add(77, "SELECT DISTINCT ?activity WHERE { ?activity icare:activityHasTrigger demo:symptom-trigger . }", [{"activity": "demo:clinical-review"}, {"activity": "demo:referral"}], scope="Retrieves authored trigger associations per the register's path; does not demonstrate execution or causal initiation")
add(78, "SELECT DISTINCT ?activity WHERE { ?activity icare:activityHasTrigger demo:symptom-trigger ; a/rdfs:subClassOf* ?type . VALUES ?type { icare:ReferralActivity icare:EscalationActivity } }", [{"activity": "demo:referral"}], scope="Retrieves referral/escalation associations; no clinical alert rule is executed")

# Additional controls are separate from the 78 canonical questions.
by_id = {c["id"]: c for c in cases}
cases.append(dict(id="CTRL-OTHER-PERSON", query=by_id["CQ-007"]["query"].replace("demo:participant", "test:control-person"), expected=[{"diagnosis": "test:control-diagnosis"}], scope="Same query path with another participant"))
cases.append(dict(id="CTRL-UNKNOWN-PERSON", query=by_id["CQ-007"]["query"].replace("demo:participant", "test:unknown-person"), expected=[], scope="No matching record; empty result is not a statement of clinical absence"))
cases.append(dict(id="CTRL-BROKEN-PATH", query=by_id["CQ-070"]["query"], expected=[], remove_triples=[["demo:recommendation-walking", "icare:recommendationRecommendsActivity", "demo:exercise-intervention"]], scope="Remove a bridge in a disposable graph; the integration answer must disappear"))
cases.append(dict(id="CTRL-PERFORMED-NOT-PLANNED", query=by_id["CQ-064"]["query"], expected=[{"minutes": "18"}], numeric=["minutes"], forbidden=[{"minutes": "20"}], scope="Recorded duration must not be replaced by the prescribed duration"))

for folder in (OUT, OUT / "queries", OUT / "validation", KG / "reports"):
    folder.mkdir(parents=True, exist_ok=True)
g.serialize(OUT / "coverage.ttl", format="turtle")
catalogue = ET.parse(KG / "catalog-v001.xml").getroot()
for entry in catalogue:
    target = (KG / entry.attrib["uri"]).resolve()
    entry.set("uri", os.path.relpath(target, OUT))
ET.SubElement(catalogue, "{urn:oasis:names:tc:entity:xmlns:xml:catalog}uri", {"name": str(ENTRY), "uri": "coverage.ttl"})
ET.register_namespace("", "urn:oasis:names:tc:entity:xmlns:xml:catalog")
ET.indent(catalogue)
ET.ElementTree(catalogue).write(OUT / "catalog-v001.xml", encoding="utf-8", xml_declaration=True)
with (OUT / "validation/import-map.tsv").open("w", newline="") as f:
    w = csv.writer(f, delimiter="\t")
    w.writerow(["iri", "file"])
    w.writerows((e.attrib["name"], e.attrib["uri"]) for e in catalogue)
source_path = REPO / "sources/icareonto_final_consolidated_competency_questions_v5.xlsx"
source = {r["A"]: r for r in read_xlsx(source_path)["Final CQs"] if r.get("A", "").startswith("CQ-")}
assert set(by_id) == set(source), "The suite must cover the complete canonical CQ register"
for case in cases:
    query_path = OUT / "queries" / (case["id"] + ".rq")
    query_path.write_text(case.pop("query"), encoding="utf-8")
    case["query_file"] = "queries/" + query_path.name
    if case["id"] in source:
        r = source[case["id"]]
        case.update(question=r["C"], theme=r["B"], expected_answer_type=r["D"], source_path=r["E"], modules=r["F"], primary_basis=r["G"], stakeholder_cq_ids=r.get("H", ""), proposal_cq_ids=r.get("I", ""))
        assert case["expected"], "Canonical tests must have authored nonempty expected answers"
(OUT / "cases.json").write_text(json.dumps({"ontology_version": "0.1.0-draft", "source_register": source_path.name,
    "source_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
    "fixture": "coverage.ttl plus imported Spanish survivor graph and ontology", "cases": cases}, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"canonical_cqs": len(by_id), "controls": len(cases) - len(by_id), "supplement_triples": len(g), "expected_answers": "Authored independently of query results"}, indent=2))
