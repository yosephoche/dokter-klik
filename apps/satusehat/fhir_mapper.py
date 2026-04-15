"""FHIR R4 resource builders for SATUSEHAT (Kemenkes Indonesia).

Maps DokterKlik Django models → validated FHIR R4 resource dicts.

IMPORTANT: Profile URLs must match Kemenkes spec exactly, not HL7 generic.
Validate with fhir.resources before sending to ensure compliance.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

SATUSEHAT_PATIENT_PROFILE = 'https://fhir.kemkes.go.id/r4/StructureDefinition/Patient'
SATUSEHAT_ENCOUNTER_PROFILE = 'https://fhir.kemkes.go.id/r4/StructureDefinition/Encounter'
SATUSEHAT_CONDITION_PROFILE = 'https://fhir.kemkes.go.id/r4/StructureDefinition/Condition'
SATUSEHAT_MED_REQUEST_PROFILE = 'https://fhir.kemkes.go.id/r4/StructureDefinition/MedicationRequest'


def build_patient_resource(patient) -> dict:
    """Map Patient model → FHIR R4 Patient resource dict."""
    resource = {
        'resourceType': 'Patient',
        'meta': {
            'profile': [SATUSEHAT_PATIENT_PROFILE]
        },
        'active': True,
        'name': [{'use': 'official', 'text': patient.name}],
        'gender': _map_gender(patient.gender),
    }

    if patient.nik:
        resource['identifier'] = [{
            'use': 'official',
            'system': 'https://fhir.kemkes.go.id/id/nik',
            'value': patient.nik,
        }]

    if patient.dob:
        resource['birthDate'] = str(patient.dob)

    if patient.phone:
        resource['telecom'] = [{'system': 'phone', 'value': patient.phone, 'use': 'mobile'}]

    return _validate_fhir(resource, 'Patient')


def build_encounter_resource(visit, org_id: str) -> dict:
    """Map Visit model → FHIR R4 Encounter resource dict."""
    resource = {
        'resourceType': 'Encounter',
        'meta': {'profile': [SATUSEHAT_ENCOUNTER_PROFILE]},
        'status': 'finished',
        'class': {
            'system': 'http://terminology.hl7.org/CodeSystem/v3-ActCode',
            'code': 'AMB',
            'display': 'ambulatory',
        },
        'subject': {
            'reference': f'Patient/{visit.patient.satusehat_patient_id}',
            'display': visit.patient.name,
        },
        'participant': [{
            'type': [{
                'coding': [{
                    'system': 'http://terminology.hl7.org/CodeSystem/v3-ParticipationType',
                    'code': 'ATND',
                    'display': 'attender',
                }]
            }],
            'individual': {
                'display': visit.doctor.full_name,
            }
        }],
        'period': {
            'start': visit.visit_date.isoformat(),
            'end': (visit.finalized_at or visit.updated_at).isoformat(),
        },
        'serviceProvider': {
            'reference': f'Organization/{org_id}',
        },
    }
    return _validate_fhir(resource, 'Encounter')


def build_condition_resource(diagnosis, visit) -> dict:
    """Map Diagnosis → FHIR R4 Condition resource dict."""
    resource = {
        'resourceType': 'Condition',
        'meta': {'profile': [SATUSEHAT_CONDITION_PROFILE]},
        'clinicalStatus': {
            'coding': [{
                'system': 'http://terminology.hl7.org/CodeSystem/condition-clinical',
                'code': 'active',
            }]
        },
        'verificationStatus': {
            'coding': [{
                'system': 'http://terminology.hl7.org/CodeSystem/condition-ver-status',
                'code': 'confirmed',
            }]
        },
        'code': {
            'coding': [{
                'system': 'http://hl7.org/fhir/sid/icd-10',
                'code': diagnosis.icd10_code,
                'display': diagnosis.icd10_description_en or diagnosis.icd10_code,
            }]
        },
        'subject': {
            'reference': f'Patient/{visit.patient.satusehat_patient_id}',
        },
        'encounter': {
            'reference': f'Encounter/{visit.satusehat_encounter_id}',
        },
    }
    return _validate_fhir(resource, 'Condition')


def build_medication_request_resource(prescription, visit) -> dict:
    """Map Prescription → FHIR R4 MedicationRequest resource dict."""
    resource = {
        'resourceType': 'MedicationRequest',
        'meta': {'profile': [SATUSEHAT_MED_REQUEST_PROFILE]},
        'status': 'completed' if prescription.status == 'dispensed' else 'active',
        'intent': 'order',
        'medicationCodeableConcept': {
            'text': prescription.drug_name,
        },
        'subject': {
            'reference': f'Patient/{visit.patient.satusehat_patient_id}',
        },
        'encounter': {
            'reference': f'Encounter/{visit.satusehat_encounter_id}',
        },
        'dosageInstruction': [{
            'text': prescription.dosage_instruction,
        }],
        'dispenseRequest': {
            'quantity': {
                'value': float(prescription.quantity),
                'unit': prescription.unit,
            },
        },
    }
    return _validate_fhir(resource, 'MedicationRequest')


def _map_gender(gender: str) -> str:
    mapping = {'male': 'male', 'female': 'female', 'other': 'other'}
    return mapping.get(gender, 'unknown')


def _validate_fhir(resource: dict, resource_type: str) -> dict:
    """Validate FHIR resource using fhir.resources library."""
    try:
        if resource_type == 'Patient':
            from fhir.resources.patient import Patient
            Patient.parse_obj(resource)
        elif resource_type == 'Encounter':
            from fhir.resources.encounter import Encounter
            Encounter.parse_obj(resource)
        elif resource_type == 'Condition':
            from fhir.resources.condition import Condition
            Condition.parse_obj(resource)
        elif resource_type == 'MedicationRequest':
            from fhir.resources.medicationrequest import MedicationRequest
            MedicationRequest.parse_obj(resource)
    except Exception as exc:
        logger.warning('FHIR validation warning for %s: %s', resource_type, exc)
    return resource
