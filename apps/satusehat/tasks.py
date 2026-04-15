"""SATUSEHAT Celery tasks: sync encounter, retry failed, monitor failure rate."""
import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=5, default_retry_delay=60, queue='satusehat')
def sync_encounter_to_satusehat(self, visit_id: str):
    """Sync a finalized Visit to SATUSEHAT as Encounter + related resources.

    Retry with exponential backoff (max 5 attempts): 1, 2, 4, 8, 16 minutes.
    """
    from apps.emr.models import Visit
    from apps.satusehat.models import SyncLog
    from apps.satusehat.client import SatusehatClient, SatusehatAPIError
    from apps.satusehat.fhir_mapper import (
        build_patient_resource, build_encounter_resource,
        build_condition_resource, build_medication_request_resource,
    )

    try:
        visit = Visit.objects.select_related(
            'patient', 'clinic', 'doctor'
        ).prefetch_related('diagnoses', 'prescriptions').get(id=visit_id)
    except Visit.DoesNotExist:
        logger.error('Visit %s not found for SATUSEHAT sync', visit_id)
        return

    log, _ = SyncLog.objects.get_or_create(
        clinic=visit.clinic,
        resource_type='Encounter',
        local_id=str(visit_id),
        defaults={'status': 'pending'},
    )
    log.attempt_count += 1
    log.last_attempt_at = timezone.now()
    log.save(update_fields=['attempt_count', 'last_attempt_at'])

    client = SatusehatClient(visit.clinic)
    org_id = visit.clinic.satusehat_org_id

    try:
        # 1. Sync Patient
        if not visit.patient.satusehat_patient_id:
            patient_payload = build_patient_resource(visit.patient)
            log.request_payload = {'Patient': patient_payload}
            patient_resp = client.post_resource('Patient', patient_payload)
            visit.patient.satusehat_patient_id = patient_resp.get('id', '')
            visit.patient.save(update_fields=['satusehat_patient_id'])

        # 2. Sync Encounter
        enc_payload = build_encounter_resource(visit, org_id)
        enc_resp = client.post_resource('Encounter', enc_payload)
        visit.satusehat_encounter_id = enc_resp.get('id', '')
        visit.save(update_fields=['satusehat_encounter_id'])

        # 3. Sync Conditions (one per Diagnosis)
        for diagnosis in visit.diagnoses.all():
            if diagnosis.satusehat_condition_id:
                continue
            cond_payload = build_condition_resource(diagnosis, visit)
            cond_resp = client.post_resource('Condition', cond_payload)
            diagnosis.satusehat_condition_id = cond_resp.get('id', '')
            diagnosis.save(update_fields=['satusehat_condition_id'])

        # 4. Sync MedicationRequests
        for prescription in visit.prescriptions.filter(status='dispensed'):
            rx_payload = build_medication_request_resource(prescription, visit)
            client.post_resource('MedicationRequest', rx_payload)

        log.status = 'success'
        log.satusehat_id = visit.satusehat_encounter_id
        log.error_message = ''
        log.save(update_fields=['status', 'satusehat_id', 'error_message', 'updated_at'])
        logger.info('SATUSEHAT sync success for visit %s', visit_id)

    except Exception as exc:
        log.status = 'failed'
        log.error_message = str(exc)[:2000]
        log.save(update_fields=['status', 'error_message', 'updated_at'])
        logger.error('SATUSEHAT sync failed for visit %s: %s', visit_id, exc)

        countdown = 60 * (2 ** self.request.retries)
        raise self.retry(exc=exc, countdown=countdown)


@shared_task(queue='satusehat')
def retry_failed_syncs():
    """Beat task: retry all SATUSEHAT syncs that failed and haven't exceeded max retries."""
    from apps.satusehat.models import SyncLog
    from django.utils import timezone
    import datetime

    cutoff = timezone.now() - datetime.timedelta(hours=24)
    failed = SyncLog.objects.filter(
        status='failed',
        attempt_count__lt=5,
        last_attempt_at__lt=timezone.now() - datetime.timedelta(minutes=30),
    ).select_related('clinic')

    count = 0
    for log in failed:
        if log.resource_type == 'Encounter':
            sync_encounter_to_satusehat.delay(log.local_id)
            count += 1
    logger.info('Queued %d failed SATUSEHAT syncs for retry', count)


@shared_task(queue='satusehat')
def notify_high_failure_rate():
    """Beat task: alert admin if failure rate > 10% in the last hour."""
    from apps.satusehat.models import SyncLog
    import datetime

    one_hour_ago = timezone.now() - datetime.timedelta(hours=1)
    total = SyncLog.objects.filter(last_attempt_at__gte=one_hour_ago).count()
    failed = SyncLog.objects.filter(
        last_attempt_at__gte=one_hour_ago, status='failed'
    ).count()

    if total > 0 and (failed / total) > 0.10:
        logger.critical(
            'SATUSEHAT failure rate is high: %d/%d failed in the last hour',
            failed, total
        )
