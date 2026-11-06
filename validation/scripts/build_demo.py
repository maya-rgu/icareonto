#!/usr/bin/env python3
"""Build a wholly fictional Spanish AYA survivor knowledge graph for testing."""
import hashlib
import json
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from rdflib import Graph, Literal, Namespace, RDF, RDFS, OWL, URIRef, XSD
from rdflib.namespace import DCTERMS

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT.parent / "serialisation"
IC = Namespace("http://maya-project.eu/icareonto/")
DEMO = Namespace("https://example.org/maya/demo/es/")
ONTOLOGY = URIRef(str(DEMO).rstrip("/"))
TZ = ZoneInfo("Europe/Madrid")
g = Graph()
for prefix, ns in (("demo", DEMO), ("icare", IC), ("rdf", RDF), ("rdfs", RDFS), ("owl", OWL), ("xsd", XSD), ("dcterms", DCTERMS)):
    g.bind(prefix, ns)


def entity(identifier, type_name, label):
    node = DEMO[identifier]
    g.add((node, RDF.type, OWL.NamedIndividual))
    g.add((node, RDF.type, IC[type_name]))
    g.add((node, RDFS.label, Literal(label, lang="en")))
    return node


def rel(subject, prop, object_):
    g.add((subject, IC[prop], object_))


def val(subject, prop, value, datatype="string"):
    g.add((subject, IC[prop], Literal(str(value), datatype=XSD[datatype])))


def note(subject, text):
    g.add((subject, RDFS.comment, Literal(text, lang="en")))


def time(identifier, local_datetime, label):
    node = entity(identifier, "Timepoint", label)
    value = datetime.fromisoformat(local_datetime).replace(tzinfo=TZ).isoformat()
    val(node, "timepointDateTime", value, "dateTime")
    return node


g.add((ONTOLOGY, RDF.type, OWL.Ontology))
g.add((ONTOLOGY, RDFS.label, Literal("Fictional Spanish AYA survivor — technical test graph", lang="en")))
g.add((ONTOLOGY, OWL.imports, URIRef("http://maya-project.eu/icareonto")))
g.add((ONTOLOGY, OWL.versionInfo, Literal("Synthetic fixture 0.1; 2026-10-30")))
g.add((ONTOLOGY, DCTERMS.description, Literal(
    "All people, pilot sites, clinical records, assessments, recommendations, educational resources and dialogue are fictional technical fixtures. "
    "This graph contains no real patient data and asserts no real site participation, clinical validation or medical advice. "
    "Scores and care activities are authored examples, not outputs of a validated prediction model or automated clinical rules.", lang="en")))

# Pilot, participant, roles and preferences.
study = entity("study", "PilotStudy", "Fictional MAYA technical demonstration study")
site = entity("pilot-site", "PilotSite", "ES-DEMO-01 — fictional site in Castilla-La Mancha, Spain")
locale = entity("locale", "Locale", "Spanish demonstration locale")
val(locale, "localeTag", "es-ES", "language")
val(locale, "localeCountryCode", "ES")
val(locale, "localeTimeZoneIdentifier", "Europe/Madrid")
rel(study, "pilotStudyHasPilotSite", site)
rel(site, "pilotSiteHasLocale", locale)
phase = entity("pilot-phase", "PilotPhase", "Fictional feasibility phase")
arm = entity("study-arm", "StudyArm", "Fictional intervention arm")
rel(study, "pilotStudyHasPhase", phase)
rel(study, "pilotStudyHasArm", arm)
person = entity("participant", "Person", "Demo survivor ES-AYA-001")
val(person, "personIdentifier", "DEMO-ES-AYA-001")
val(person, "ageInYears", "27", "decimal")
note(person, "Fictional 27-year-old cancer survivor; age is an enrolment snapshot. No real identity or birth date is represented.")
survivor_role = entity("survivor-role", "AYACancerSurvivorRole", "AYA survivor role")
participant_role = entity("participant-role", "StudyParticipantRole", "Demonstration study participant role")
clinician = entity("clinician", "Person", "Fictional clinician ES-CLINICIAN-001")
clinician_role = entity("clinician-role", "ClinicianRole", "Fictional clinical reviewer role")
rel(person, "personHasRole", survivor_role)
rel(person, "personHasRole", participant_role)
rel(clinician, "personHasRole", clinician_role)
enrolment_time = time("time-enrolment", "2026-10-15T10:00:00", "Enrolment time")
baseline_time = time("time-baseline", "2026-10-20T08:30:00", "First home-monitoring time")
followup_time = time("time-followup", "2026-10-27T08:30:00", "Second home-monitoring time")
interaction_time = time("time-dialogue", "2026-10-27T18:00:00", "Fictional avatar interaction time")
next_review = time("time-review-due", "2026-11-03T10:00:00", "Illustrative review appointment")
enrolment_period = entity("enrolment-period", "TimeInterval", "Enrolment validity interval, open ended")
rel(enrolment_period, "intervalStartsAt", enrolment_time)
enrolment = entity("enrolment", "ParticipantEnrolment", "Fictional enrolment")
for prop, target in (("participantEnrolmentForPerson", person), ("participantEnrolmentInStudy", study),
                     ("participantEnrolmentAtSite", site), ("participantEnrolmentInPhase", phase),
                     ("participantEnrolmentAssignedToArm", arm), ("participantEnrolmentHasStatus", IC.ActiveEnrolmentStatus),
                     ("participantEnrolmentValidDuring", enrolment_period)):
    rel(enrolment, prop, target)
language = entity("language-preference", "LanguagePreference", "Spanish language preference")
val(language, "preferredLanguageTag", "es-ES", "language")
detail = entity("information-preference", "InformationPreference", "Preference for brief explanations")
rel(detail, "informationPreferenceHasDetailLevel", IC.BriefInformation)
channel = entity("communication-preference", "CommunicationPreference", "Smart mirror communication preference")
rel(channel, "preferredCommunicationChannel", IC.SmartMirrorChannel)
contact = entity("contact-preference", "ContactPreference", "Evening contact preference")
rel(contact, "preferredContactTime", IC.EveningTimeOfDay)
for pref in (language, detail, channel, contact):
    rel(person, "personHasPreference", pref)
    rel(pref, "preferenceRecordedAt", enrolment_time)

# Consent and source attribution. These are data records, not enforcement logic.
kg = entity("participant-knowledge-graph", "ParticipantKnowledgeGraph", "Logical collection about demo participant")
rel(kg, "participantKnowledgeGraphAboutPerson", person)
consent = entity("consent", "ConsentRecord", "Fictional consent record for technical demonstration")
rel(consent, "consentRecordGrantedBy", person)
rel(consent, "consentRecordAppliesToKnowledgeGraph", kg)
rel(consent, "consentRecordHasStatus", IC.ConsentGranted)
rel(consent, "consentRecordValidDuring", enrolment_period)
rel(consent, "hasVerificationStatus", IC.Unverified)
note(consent, "A synthetic consent decision; it neither represents real consent nor implements access control.")
clinical_source = entity("source-clinical-record", "ClinicalRecordDataSource", "Fictional imported survivorship summary")
self_source = entity("source-participant", "SelfReportedDataSource", "Fictional participant-reported information")
device_source = entity("source-device", "DeviceDataSource", "Fictional device feed")
questionnaire_source = entity("source-questionnaire", "QuestionnaireDataSource", "Fictional questionnaire response source")
for source, name in ((clinical_source, "Demo clinical summary"), (self_source, "Demo self-report"),
                     (device_source, "Demo home-monitoring feed"), (questionnaire_source, "Demo questionnaire response")):
    val(source, "dataSourceName", name)
    val(source, "dataSourceDescription", "Synthetic fixture source; no real underlying record.")

# Historical cancer treatment. No current therapy or dose recommendation is implied.
diagnosis_time = time("time-diagnosis", "2022-03-14T10:00:00", "Fictional diagnosis record time")
treatment_start = time("time-treatment-start", "2022-04-04T09:00:00", "Fictional treatment start")
treatment_end = time("time-treatment-end", "2022-09-19T09:00:00", "Fictional treatment end")
treatment_period = entity("treatment-period", "TimeInterval", "Historical treatment interval")
rel(treatment_period, "intervalStartsAt", treatment_start)
rel(treatment_period, "intervalEndsAt", treatment_end)
diagnosis = entity("cancer-diagnosis", "CancerDiagnosis", "Fictional historical Hodgkin lymphoma diagnosis")
val(diagnosis, "ageAtCancerDiagnosis", "23", "decimal")
val(diagnosis, "cancerTypeName", "Hodgkin lymphoma — synthetic historical record")
rel(diagnosis, "cancerDiagnosisRecordedAt", diagnosis_time)
rel(diagnosis, "cancerDiagnosisHasSource", clinical_source)
rel(person, "hasCancerDiagnosis", diagnosis)
history = entity("cancer-history", "CancerTreatmentHistory", "Historical cancer treatment summary")
record = entity("treatment-record", "CancerTreatmentRecord", "Fictional systemic treatment record")
regimen = entity("treatment-regimen", "TreatmentRegimen", "Unspecified fictional systemic regimen")
val(regimen, "treatmentRegimenName", "DEMO-HISTORICAL-REGIMEN; illustrative, not a treatment protocol")
agent = entity("historical-treatment-agent", "TreatmentAgent", "Doxorubicin — fictional historical exposure")
val(agent, "treatmentAgentName", "Doxorubicin (synthetic historical record)")
exposure = entity("anthracycline-exposure", "AnthracyclineExposure", "Fictional prior anthracycline exposure")
val(exposure, "cumulativeDrugDose", "200", "decimal")
val(exposure, "cumulativeDrugDoseUnit", "mg/m2")
rel(exposure, "treatmentExposureHasAgent", agent)
rel(exposure, "treatmentExposureHasPeriod", treatment_period)
cardiotoxicity = entity("treatment-related-risk", "CardiotoxicityRisk", "Historical exposure relevance to late-effect follow-up")
val(cardiotoxicity, "cardiotoxicityRiskValue", "Not clinically graded; fictional historical exposure")
rel(exposure, "treatmentExposureIsRiskFactorOf", cardiotoxicity)
rel(person, "personHasCancerTreatmentHistory", history)
rel(history, "cancerTreatmentHistoryHasRecord", record)
for prop, target in (("treatmentRecordIndicatesExposure", exposure), ("treatmentRecordHasTreatmentPeriod", treatment_period),
                     ("treatmentRecordRecordsTreatmentType", IC.ChemotherapyTreatment), ("treatmentRecordHasIntent", IC.CurativeTreatmentIntent),
                     ("treatmentRecordHasSetting", IC.TreatmentAloneSetting), ("treatmentRecordTreatsDiagnosis", diagnosis),
                     ("treatmentRecordHasRegimen", regimen), ("treatmentRecordHasSource", clinical_source),
                     ("treatmentRecordRecordedAt", treatment_end)):
    rel(record, prop, target)

# Clinical profile and a mild participant-reported symptom.
clinical = entity("clinical-profile", "ClinicalProfile", "Fictional survivorship clinical profile")
rel(person, "personHasClinicalProfile", clinical)
rel(clinical, "clinicalProfileHasCurrentStatus", IC.RemissionClinicalStatus)
symptom = entity("fatigue", "Symptom", "Fictional intermittent fatigue")
val(symptom, "symptomName", "Intermittent fatigue after a busy working day")
symptom_record = entity("symptom-record", "SymptomRecord", "Participant-reported fatigue record")
severity = entity("fatigue-severity", "Severity", "Illustrative mild reported symptom severity")
rel(severity, "severityHasSeverityLevel", IC.MildSeverity)
rel(symptom_record, "symptomRecordRecordsSymptom", symptom)
rel(symptom_record, "symptomRecordHasSeverity", severity)
rel(symptom_record, "clinicalRecordRecordedAt", followup_time)
rel(symptom_record, "clinicalRecordHasSource", self_source)
rel(clinical, "clinicalProfileIncludesRecord", symptom_record)

# Monitoring and the Health Hub.
hub = entity("health-hub", "HealthHub", "Fictional Spanish Health Hub deployment")
mirror = entity("smart-mirror", "SmartMirror", "Demo smart mirror")
monitor = entity("blood-pressure-monitor", "MeasurementDevice", "Fictional home blood-pressure monitor")
# MeasurementDevice is not a subclass of core:Device in the workbook; assert both roles explicitly.
g.add((monitor, RDF.type, IC.Device))
scale = entity("scale", "MeasurementDevice", "Fictional home scale")
g.add((scale, RDF.type, IC.Device))
monitoring_service = entity("monitoring-service", "DigitalService", "Demo remote-monitoring service")
dialogue_service = entity("dialogue-service", "DigitalService", "Demo Spanish conversational service")
education_service = entity("education-service", "DigitalService", "Demo educational-content service")
for service, kind in ((monitoring_service, IC.RemoteMonitoringServiceType), (dialogue_service, IC.DialogueServiceType),
                      (education_service, IC.HealthLiteracyServiceType)):
    rel(hub, "healthHubProvidesService", service)
    rel(service, "digitalServiceHasType", kind)
    rel(mirror, "deviceProvidesAccessTo", service)
for device in (mirror, monitor, scale):
    rel(hub, "healthHubIncludesDevice", device)
home_context = entity("home-context", "HomeMonitoringContext", "Fictional home measurement context")
bp_protocol = entity("bp-protocol", "BloodPressureMeasurementProtocol", "Demo blood-pressure recording protocol")
body_protocol = entity("body-protocol", "BodyCompositionProtocol", "Demo anthropometric recording protocol")
bp_method = entity("bp-method", "MeasurementMethod", "Fictional oscillometric measurement method")
rel(bp_protocol, "protocolSpecifiesMethod", bp_method)
baseline_point = entity("baseline-study-timepoint", "StudyTimepoint", "Baseline assessment point")
followup_point = entity("followup-study-timepoint", "StudyTimepoint", "Demonstration follow-up assessment point")
rel(baseline_point, "studyTimepointHasType", IC.BaselineTimepointType)
rel(followup_point, "studyTimepointHasType", IC.FollowUpTimepointType)
for identifier, code, symbol in (("unit-mmhg", "mm[Hg]", "mmHg"), ("unit-kg", "kg", "kg"),
                                 ("unit-m", "m", "m"), ("unit-bmi", "kg/m2", "kg/m²")):
    unit = entity(identifier, "Unit", "Demo unit: " + symbol)
    val(unit, "unitCode", code)
    val(unit, "unitCodeSystem", "http://unitsofmeasure.org", "anyURI")
    val(unit, "unitSymbol", symbol)
parameters = {}
for identifier, cls, label, code in (("systolic-bp", "VitalSign", "Systolic blood pressure", "DEMO-SBP"),
                                    ("diastolic-bp", "VitalSign", "Diastolic blood pressure", "DEMO-DBP"),
                                    ("weight", "AnthropometricParameter", "Body weight", "DEMO-WEIGHT"),
                                    ("height", "AnthropometricParameter", "Height", "DEMO-HEIGHT"),
                                    ("bmi", "DerivedParameter", "Body mass index", "DEMO-BMI")):
    parameter = entity(identifier, cls, label)
    val(parameter, "parameterName", label)
    val(parameter, "parameterCode", code)
    val(parameter, "parameterCodeSystem", "https://example.org/maya/demo/codes/parameters", "anyURI")
    parameters[identifier] = parameter
rel(parameters["bmi"], "derivedParameterDerivedFrom", parameters["weight"])
rel(parameters["bmi"], "derivedParameterDerivedFrom", parameters["height"])
for param in (parameters["systolic-bp"], parameters["diastolic-bp"]):
    rel(bp_protocol, "protocolSpecifiesParameter", param)


def measurement(identifier, parameter, number, unit_id, when, study_point, instrument, protocol):
    event = entity(identifier + "-event", "MeasurementEvent", identifier.replace("-", " ") + " event")
    result = entity(identifier + "-result", "ObservationResult", identifier.replace("-", " ") + " result")
    quantity = entity(identifier + "-quantity", "QuantityValue", identifier.replace("-", " ") + " quantity")
    rel(person, "personParticipatesInMeasurement", event)
    for prop, target in (("measurementEventMeasures", parameter), ("measurementEventUsesInstrument", instrument),
                         ("measurementEventFollowsProtocol", protocol), ("measurementEventHasContext", home_context),
                         ("measurementEventHasOutput", result), ("measurementEventHasQuality", IC.ValidMeasurement),
                         ("activityExecutionOccursAt", when), ("activityExecutionHasSource", device_source),
                         ("activityExecutionUsesDevice", instrument), ("activityExecutionUsesService", monitoring_service)):
        rel(event, prop, target)
    rel(result, "observationHasQuantityValue", quantity)
    rel(quantity, "quantityValueHasUnit", DEMO[unit_id])
    val(quantity, "quantityNumericValue", number, "decimal")
    rel(result, "observationAssociatedWithStudyTimepoint", study_point)
    return result


measurement("baseline-sbp", parameters["systolic-bp"], "128", "unit-mmhg", baseline_time, baseline_point, monitor, bp_protocol)
measurement("baseline-dbp", parameters["diastolic-bp"], "82", "unit-mmhg", baseline_time, baseline_point, monitor, bp_protocol)
recent_bp = measurement("followup-sbp", parameters["systolic-bp"], "122", "unit-mmhg", followup_time, followup_point, monitor, bp_protocol)
measurement("followup-dbp", parameters["diastolic-bp"], "78", "unit-mmhg", followup_time, followup_point, monitor, bp_protocol)
weight_result = measurement("baseline-weight", parameters["weight"], "74", "unit-kg", baseline_time, baseline_point, scale, body_protocol)
height_instrument = entity("height-instrument", "MeasurementInstrument", "Fictional height-measurement instrument")
g.add((height_instrument, RDF.type, IC.Device))
height_result = measurement("baseline-height", parameters["height"], "1.68", "unit-m", baseline_time, baseline_point, height_instrument, body_protocol)
# BMI is derived from the two recorded observations, with no direct physical device assertion.
bmi_event = entity("bmi-derivation-event", "MeasurementEvent", "Derived BMI calculation")
bmi_result = entity("bmi-result", "ObservationResult", "Synthetic derived BMI result")
bmi_quantity = entity("bmi-quantity", "QuantityValue", "Synthetic BMI quantity")
rel(person, "personParticipatesInMeasurement", bmi_event)
rel(bmi_event, "measurementEventMeasures", parameters["bmi"])
rel(bmi_event, "measurementEventHasOutput", bmi_result)
rel(bmi_event, "activityExecutionOccursAt", baseline_time)
rel(bmi_event, "activityExecutionHasSource", device_source)
rel(bmi_result, "observationDerivedFromObservation", weight_result)
rel(bmi_result, "observationDerivedFromObservation", height_result)
rel(bmi_result, "observationHasQuantityValue", bmi_quantity)
val(bmi_quantity, "quantityNumericValue", "26.22", "decimal")
rel(bmi_quantity, "quantityValueHasUnit", DEMO["unit-bmi"])

# Lifestyle, social context and needs identified by a fictional questionnaire.
lifestyle = entity("lifestyle-profile", "LifestyleProfile", "Fictional lifestyle profile")
rel(person, "personHasLifestyleProfile", lifestyle)
activity_behaviour = entity("activity-behaviour", "PhysicalActivityBehaviour", "Irregular physical activity — fictional self-report")
activity_record = entity("activity-behaviour-record", "BehaviourRecord", "Activity self-report record")
activity_metric = entity("activity-metric", "BehaviourMetric", "Fictional weekly activity metric")
rel(activity_metric, "behaviourMetricHasType", IC.PhysicalActivityDuration)
val(activity_metric, "behaviourMetricNumericValue", "60", "decimal")
val(activity_metric, "behaviourMetricUnit", "minutes/week")
rel(activity_record, "behaviourRecordRecordsBehaviour", activity_behaviour)
rel(activity_record, "behaviourRecordHasMetric", activity_metric)
rel(activity_record, "behaviourHasChangeStage", IC.PreparationStage)
rel(activity_record, "behaviourRecordRecordedAt", baseline_time)
rel(activity_record, "behaviourRecordHasSource", self_source)
rel(lifestyle, "lifestyleProfileIncludesBehaviourRecord", activity_record)
smoking = entity("smoking-behaviour", "SmokingBehaviour", "Fictional smoking history")
smoking_record = entity("smoking-record", "BehaviourRecord", "Fictional never-smoker record")
rel(smoking_record, "behaviourRecordRecordsBehaviour", smoking)
rel(smoking_record, "behaviourRecordHasSmokingStatus", IC.NeverSmoker)
rel(smoking_record, "behaviourRecordRecordedAt", baseline_time)
rel(smoking_record, "behaviourRecordHasSource", self_source)
rel(lifestyle, "lifestyleProfileIncludesBehaviourRecord", smoking_record)
social = entity("social-profile", "SocialContextProfile", "Fictional social context")
rel(person, "personHasSocialContextProfile", social)
health_literacy = entity("health-literacy", "HealthLiteracy", "Needs support understanding health information")
rel(health_literacy, "healthLiteracyHasLevel", IC.LimitedLiteracy)
digital_literacy = entity("digital-literacy", "DigitalLiteracy", "Comfortable with everyday digital services")
rel(digital_literacy, "digitalLiteracyHasLevel", IC.AdequateLiteracy)
health_context = None
for identifier, factor in (("health-literacy-record", health_literacy), ("digital-literacy-record", digital_literacy)):
    context_record = entity(identifier, "SocialContextRecord", identifier.replace("-", " "))
    rel(social, "socialProfileIncludesRecord", context_record)
    rel(context_record, "socialContextRecordRecordsFactor", factor)
    rel(context_record, "socialContextRecordRecordedAt", baseline_time)
    rel(context_record, "socialContextRecordHasSource", questionnaire_source)
    if factor == health_literacy:
        health_context = context_record
questionnaire = entity("literacy-questionnaire", "Questionnaire", "Synthetic health-literacy support-needs questionnaire")
val(questionnaire, "instrumentName", "DEMO-HL-NEEDS; not a validated questionnaire")
val(questionnaire, "instrumentVersion", "0.1-fictional")
note(questionnaire, "No licensed instrument or real psychometric validation is claimed.")
q_protocol = entity("literacy-questionnaire-protocol", "QuestionnaireProtocol", "Fictional support-needs questionnaire protocol")
q_parameter = entity("literacy-parameter", "PatientReportedOutcome", "Self-reported health-information support needs")
rel(q_protocol, "protocolSpecifiesParameter", q_parameter)
q_event = entity("literacy-measurement", "MeasurementEvent", "Fictional support-needs assessment event")
q_result = entity("literacy-result", "ObservationResult", "Needs assessment result")
rel(person, "personParticipatesInMeasurement", q_event)
for prop, target in (("measurementEventMeasures", q_parameter), ("measurementEventUsesInstrument", questionnaire),
                     ("measurementEventFollowsProtocol", q_protocol), ("measurementEventHasOutput", q_result),
                     ("activityExecutionOccursAt", baseline_time), ("activityExecutionHasSource", questionnaire_source)):
    rel(q_event, prop, target)
val(q_result, "observationTextValue", "Prefers brief Spanish explanations and help understanding cardiovascular follow-up information.")
rel(q_result, "healthLiteracyResultIdentifiesNeed", IC.InformationComprehensionSupportNeed)
rel(q_result, "healthLiteracyResultIdentifiesNeed", IC.InformationAccessSupportNeed)

# Fictional resource catalogue: Spanish video, nutrition leaflet and an English distractor.
exercise_resource = entity("resource-walking-es", "EducationalResource", "Demo Spanish activity-support leaflet")
literacy_resource = entity("resource-late-effects-es", "HealthLiteracyResource", "Demo Spanish late-effects explainer video")
nutrition_resource = entity("resource-nutrition-es", "EducationalResource", "Demo Spanish nutrition leaflet")
english_resource = entity("resource-late-effects-en", "HealthLiteracyResource", "Demo English late-effects explainer")
for resource, lang, topic, format_, purpose in (
    (exercise_resource, "es-ES", IC.PhysicalActivity, IC.WrittenText, IC.SupportBehaviourChange),
    (literacy_resource, "es-ES", IC.CardiovascularLateEffects, IC.Video, IC.ExplainHealthTopic),
    (nutrition_resource, "es-ES", IC.Nutrition, IC.WrittenText, IC.SupportSelfManagement),
    (english_resource, "en-GB", IC.CardiovascularLateEffects, IC.WrittenText, IC.ExplainHealthTopic)):
    g.add((resource, DCTERMS.language, Literal(lang, datatype=XSD.language)))
    g.add((resource, DCTERMS.identifier, Literal(str(resource).split("/")[-1])))
    g.add((resource, DCTERMS.description, Literal("Fictional catalogue metadata only; no real document or approved health guidance exists.", lang="en")))
    for prop, target in (("knowledgeResourceHasTopic", topic), ("knowledgeResourceHasFormat", format_),
                         ("knowledgeResourceHasPurpose", purpose), ("knowledgeResourceHasAudience", IC.AYASurvivorAudience),
                         ("knowledgeResourceHasComplexityLevel", IC.FoundationalComplexity), ("knowledgeResourceHasAccessibilityFeature", IC.PlainLanguage)):
        rel(resource, prop, target)
rel(literacy_resource, "knowledgeResourceHasAccessibilityFeature", IC.Captions)
rel(literacy_resource, "healthLiteracyResourceAddressesNeed", IC.InformationComprehensionSupportNeed)
rel(english_resource, "healthLiteracyResourceAddressesNeed", IC.InformationComprehensionSupportNeed)

# A dummy risk model demonstrates representation and provenance, not clinical prediction.
risk_factor = entity("low-activity-risk-factor", "ModifiableRiskFactor", "Low physical activity — illustrative modifiable factor")
rel(activity_behaviour, "behaviourInfluencesRiskFactor", risk_factor)
model = entity("demo-model", "PredictionModel", "DEMO ONLY — unvalidated illustrative model")
val(model, "modelIdentifier", "DEMO-NOT-A-CLINICAL-MODEL")
val(model, "modelVersion", "0.1-synthetic")
model_input = entity("model-input", "ModelInput", "Fictional model input record")
rel(model_input, "modelInputIncludesExposure", exposure)
rel(model_input, "modelInputDerivedFromObservation", recent_bp)
execution = entity("model-execution", "ModelExecution", "Authored example of a model execution")
risk = entity("risk-profile", "RiskProfile", "Fictional cardiovascular risk profile")
estimate = entity("risk-estimate", "RiskEstimate", "Unvalidated illustrative score; not a probability")
interpretation = entity("risk-interpretation", "RiskInterpretation", "No validated clinical interpretation")
val(interpretation, "riskInterpretationValue", "Synthetic fixture score only; clinical risk remains unclassified.")
val(estimate, "riskScore", "2", "decimal")
rel(estimate, "riskEstimateHasCategory", IC.UnknownRisk)
rel(estimate, "riskEstimateHasInterpretation", interpretation)
event_risk = entity("adverse-cardiac-event", "AdverseCardiacEvent", "Generic adverse cardiac event — demonstration target")
rel(estimate, "riskEstimateEstimatesEventRisk", event_risk)
rel(risk, "riskProfileIncludesRiskEstimate", estimate)
rel(risk, "riskProfileAssessedAt", followup_time)
rel(person, "personHasRiskProfile", risk)
for prop, target in (("modelExecutionExecutes", model), ("modelExecutionUsesInput", model_input),
                     ("modelExecutionExecutedAt", followup_time), ("modelExecutionGeneratesRiskProfile", risk)):
    rel(execution, prop, target)
note(execution, "This authored test fixture did not run a predictive algorithm. The score has no calibrated scale, horizon or clinical interpretation.")

# Care plan, goals, recommendations and actual/planned activities.
plan = entity("care-plan", "CarePlan", "Fictional participant-agreed support plan")
val(plan, "carePlanName", "DEMO-ES-AYA-001 support plan")
rel(plan, "carePlanIntendedFor", person)
rel(plan, "carePlanHasStatus", IC.ActiveCarePlan)
rel(plan, "carePlanCreatedAt", baseline_time)
rel(plan, "carePlanUpdatedAt", followup_time)
participation = entity("care-plan-participation", "CarePlanParticipation", "Participant involvement in the support plan")
rel(plan, "carePlanHasParticipation", participation)
rel(participation, "participationHasParticipant", person)
rel(participation, "participationHasRole", participant_role)
walking_goal = entity("walking-goal", "Goal", "Illustrative participant goal: establish a walking routine")
nutrition_goal = entity("nutrition-goal", "Goal", "Illustrative participant goal: review dietary habits")
for goal, text in ((walking_goal, "Try a manageable walking routine, with fictional clinician review."),
                   (nutrition_goal, "Discuss dietary habits using a fictional Spanish information resource.")):
    rel(plan, "carePlanHasGoal", goal)
    val(goal, "goalDescriptionText", text)
    rel(goal, "goalHasLifecycleStatus", IC.ActiveGoalLifecycleStatus)
    rel(goal, "goalHasAchievementStatus", IC.InProgressGoalAchievementStatus)
walking = entity("exercise-intervention", "ExerciseIntervention", "Illustrative walking-support intervention")
nutrition = entity("nutrition-intervention", "NutritionIntervention", "Illustrative nutrition-information intervention")
education = entity("literacy-intervention", "HealthLiteracyIntervention", "Illustrative explanation and teach-back activity")
review = entity("clinical-review", "MedicalCheckUpActivity", "Fictional non-urgent survivorship review")
referral = entity("referral", "ReferralActivity", "Fictional professional signposting after a reported concern")
for activity, status in ((walking, IC.InProgressActivity), (nutrition, IC.PlannedActivity),
                         (education, IC.InProgressActivity), (review, IC.ScheduledActivity), (referral, IC.PlannedActivity)):
    rel(plan, "carePlanIncludesActivity", activity)
    rel(activity, "activityHasStatus", status)
    rel(activity, "activityHasPriority", IC.RoutinePriority)
    rel(activity, "activityRequiresReviewBy", clinician_role)
    rel(activity, "carePlanActivityAdaptedToSocialContext", health_context)
rel(walking, "activityContributesToGoal", walking_goal)
rel(walking, "interventionTargetsRiskFactor", risk_factor)
rel(nutrition, "activityContributesToGoal", nutrition_goal)
rel(education, "healthLiteracyInterventionAddressesNeed", IC.InformationComprehensionSupportNeed)
rel(education, "healthLiteracyInterventionUsesResource", literacy_resource)
rel(education, "activityDeliveredThroughService", education_service)
review_schedule = entity("review-schedule", "Schedule", "Illustrative review schedule")
rel(review_schedule, "scheduleNextDueAt", next_review)
rel(review, "activityHasSchedule", review_schedule)
trigger = entity("symptom-trigger", "SymptomBasedTrigger", "Authored demonstration trigger linked to reported fatigue")
rel(trigger, "symptomBasedTriggerUsesSymptomRecord", symptom_record)
rel(review, "activityHasTrigger", trigger)
rel(referral, "activityHasTrigger", trigger)
note(trigger, "An authored example association, not a clinical warning rule or inference that this symptom requires referral.")
symptom_recommendation = entity("symptom-recommendation", "Recommendation", "Fictional recommendation to discuss a reported concern")
rel(symptom_recommendation, "recommendationAppliesToSymptom", symptom)
rel(symptom_recommendation, "recommendationRecommendsActivity", review)
for identifier, resource, activity in (("recommendation-walking", exercise_resource, walking),
                                      ("recommendation-nutrition", nutrition_resource, nutrition),
                                      ("recommendation-literacy", literacy_resource, education)):
    recommendation = entity(identifier, "Recommendation", "Fictional " + identifier)
    rel(resource, "knowledgeResourceContainsRecommendation", recommendation)
    rel(resource, "knowledgeResourceSupportsRecommendation", recommendation)
    rel(recommendation, "recommendationRecommendsActivity", activity)
    val(recommendation, "recommendationText", "Technical fixture linking a resource to a fictional care activity; not medical guidance.")
criterion = entity("recommendation-criterion", "ApplicabilityCriterion", "Illustrative applicability condition")
val(criterion, "criterionText", "Use only in the fictional scenario after review by the fictional clinician.")
rel(DEMO["recommendation-walking"], "recommendationHasApplicabilityCriterion", criterion)
instruction = entity("nutrition-instruction", "NutritionInstruction", "Illustrative instruction to discuss dietary choices")
rel(nutrition, "nutritionInterventionSpecifiesInstruction", instruction)
rel(instruction, "nutritionInstructionTargetsComponent", IC.FruitAndVegetables)
rel(instruction, "nutritionInstructionHasActionType", IC.Increase)
val(instruction, "nutritionInstructionText", "Fictional discussion example about including fruit and vegetables; no clinical dietary target is prescribed.")

# Planned versus performed exercise are separate entities.
prescription = entity("exercise-prescription", "ExercisePrescription", "Fictional activity specification, not a clinical prescription")
activity = entity("walking-activity", "ExerciseActivity", "Illustrative 20-minute walking activity")
performed_activity = entity("performed-walking-activity", "ExerciseActivity", "Fictional 18-minute completed walk")
for item, minutes in ((activity, "20"), (performed_activity, "18")):
    rel(item, "exerciseActivityHasActivityType", IC.Walking)
    val(item, "durationMinutes", minutes, "decimal")
rel(walking, "exerciseInterventionHasPrescription", prescription)
rel(prescription, "exercisePrescriptionIncludesActivity", activity)
val(prescription, "prescriptionIdentifier", "DEMO-WALK-001")
planned = entity("planned-walking-session", "PlannedExerciseSession", "Illustrative planned walk")
performed = entity("performed-walking-session", "PerformedExerciseSession", "Fictional completed walk")
rel(planned, "plannedSessionFollowsPrescription", prescription)
rel(planned, "plannedSessionScheduledAt", followup_time)
rel(planned, "plannedSessionHasStatus", IC.CompletedActivity)
rel(performed, "performedSessionRealises", planned)
rel(performed, "performedSessionIncludesActivity", performed_activity)
rel(performed, "activityExecutionOccursAt", followup_time)
rel(performed, "activityExecutionHasSource", self_source)
rel(walking, "activityRealisedBy", performed)
rel(activity_record, "behaviourRecordRelatesToActivity", walking)
rel(activity_record, "behaviourRecordRelatesToGoal", walking_goal)

# Conversational context, grounded response and human oversight.
digital_agent = entity("avatar", "ConversationAgent", "Fictional Spanish conversational avatar")
val(digital_agent, "agentVersion", "DEMO-0.1")
rel(digital_agent, "agentHasCapability", IC.HealthLiteracySupportCapability)
rel(digital_agent, "agentHasCapability", IC.ResourceRecommendationCapability)
rel(digital_agent, "conversationAgentOverseenBy", clinician)
rel(digital_agent, "conversationAgentEscalatesTo", clinician)
safety = entity("safety-policy", "SafetyPolicy", "Fictional demonstration safety policy")
val(safety, "safetyPolicyVersion", "DEMO-0.1")
rel(digital_agent, "agentGovernedBySafetyPolicy", safety)
rule = entity("evidence-rule", "SafetyRule", "Fictional evidence-grounding rule")
rel(rule, "safetyRuleHasType", IC.EvidenceGroundingRule)
val(rule, "safetyRuleText", "Demonstration responses refer to a labelled fictional resource and do not diagnose or recommend treatment.")
rel(safety, "safetyPolicyHasRule", rule)
session = entity("dialogue-session", "DialogueSession", "Fictional Spanish health-literacy conversation")
context = entity("dialogue-context", "DialogueContext", "Context for the fictional explanation")
utterance = entity("utterance", "UserUtterance", "Fictional participant question")
response = entity("response", "AgentResponse", "Fictional grounded response")
for prop, target in (("dialogueSessionHasParticipant", person), ("dialogueSessionHasAgentParticipant", digital_agent),
                     ("dialogueSessionHasTurn", utterance), ("dialogueSessionHasTurn", response),
                     ("dialogueSessionUsesStrategy", IC.PlainLanguageStrategy), ("dialogueSessionStartedAt", interaction_time),
                     ("dialogueSessionDeliveredThroughService", dialogue_service), ("activityExecutionHasSource", self_source)):
    rel(session, prop, target)
val(utterance, "turnText", "¿Puedes explicarme con palabras sencillas para qué sirve el seguimiento del corazón?")
val(utterance, "turnSequenceNumber", "1", "nonNegativeInteger")
rel(utterance, "userUtteranceExpressesIntent", IC.RequestExplanation)
rel(utterance, "dialogueTurnOccursAt", interaction_time)
val(response, "turnText", "En esta demostración puedo mostrarte un recurso ficticio en español. Las dudas sobre tu situación las revisa tu equipo sanitario.")
val(response, "turnSequenceNumber", "2", "nonNegativeInteger")
rel(response, "agentResponseGeneratedBy", digital_agent)
rel(response, "agentResponseRespondsTo", utterance)
rel(response, "agentResponseUsesContext", context)
rel(response, "agentResponseGroundedInResource", literacy_resource)
rel(response, "dialogueTurnOccursAt", interaction_time)
rel(context, "dialogueContextAddressesIntent", IC.RequestExplanation)
for item in (risk, health_context, detail, language, symptom_record, education):
    rel(context, "dialogueContextIncludesEntity", item)
service_event = entity("education-service-use", "ServiceUseEvent", "Fictional educational service use")
rel(service_event, "serviceUseEventUsesService", education_service)
rel(service_event, "serviceUseEventHasUser", person)
rel(service_event, "serviceUseEventSupportsActivity", education)
rel(service_event, "activityExecutionOccursAt", interaction_time)
rel(service_event, "activityExecutionHasSource", self_source)

# Preserve the source ontology and construct a separate, portable KG import catalogue.
ROOT.mkdir(parents=True, exist_ok=True)
g.serialize(ROOT / "demo_spain_aya.ttl", format="turtle")
catalogue = ET.parse(SCHEMA / "catalog-v001.xml").getroot()
for entry in catalogue:
    entry.set("uri", "../serialisation/" + entry.attrib["uri"])
ET.SubElement(catalogue, "{urn:oasis:names:tc:entity:xmlns:xml:catalog}uri", {"name": str(ONTOLOGY), "uri": "demo_spain_aya.ttl"})
ET.register_namespace("", "urn:oasis:names:tc:entity:xmlns:xml:catalog")
ET.indent(catalogue)
ET.ElementTree(catalogue).write(ROOT / "catalog-v001.xml", encoding="utf-8", xml_declaration=True)
manifest = {
    "dataset": str(ONTOLOGY), "fictional": True, "participant_count": 1,
    "participant_age_at_enrolment": 27, "country": "ES", "language": "es-ES", "time_zone": "Europe/Madrid",
    "site": "ES-DEMO-01, Castilla-La Mancha (fictional; not an assertion of an actual MAYA pilot site)",
    "ontology_entry": "../serialisation/icareonto.ttl", "triples": len(g),
    "named_individuals": len(set(g.subjects(RDF.type, OWL.NamedIndividual))),
    "source_ontology_sha256": hashlib.sha256((SCHEMA / "icareonto.ttl").read_bytes()).hexdigest(),
    "limitations": ["All clinical history, scores, activities and resources are fictional technical examples.",
                    "No official diagnosis or measurement terminology mappings are claimed; parameter codes use a demonstration namespace.",
                    "Risk score is authored, uncalibrated and not a probability; the risk category remains UnknownRisk.",
                    "Consent and verification records are illustrative and do not implement access control.",
                    "Selected CQ smoke tests exercise a subset of the consolidated CQ set, not all 78 CQs."]
}
(ROOT / "validation").mkdir(exist_ok=True)
(ROOT / "validation/demo-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
print(json.dumps({k: manifest[k] for k in ("triples", "named_individuals", "fictional", "participant_count")}, indent=2))
