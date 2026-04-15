"""Inventory Celery tasks: low-stock alert and expiry check."""
import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(queue='reminders')
def check_low_stock(drug_id: str):
    """Check if a drug is below min_stock after a stock update. Send WA alert if so."""
    from apps.inventory.models import Drug
    try:
        drug = Drug.objects.select_related('clinic').get(id=drug_id)
    except Drug.DoesNotExist:
        return

    if drug.is_low_stock:
        logger.info(
            'Low stock alert: %s (%s/%s %s) at clinic %s',
            drug.name, drug.stock, drug.min_stock, drug.unit, drug.clinic.name
        )
        try:
            from apps.whatsapp.tasks import send_low_stock_alert
            send_low_stock_alert.delay(drug_id)
        except Exception:
            logger.exception('Failed to queue low stock WA alert for drug %s', drug_id)


@shared_task(queue='reminders')
def check_expiry():
    """Daily beat task: alert clinics for drugs expiring within 3 months."""
    import datetime
    from apps.inventory.models import Drug

    threshold = datetime.date.today() + datetime.timedelta(days=90)
    expiring = Drug.objects.filter(
        expiry_date__lte=threshold,
        expiry_date__gte=datetime.date.today(),
        is_active=True,
    ).select_related('clinic').order_by('clinic_id', 'expiry_date')

    for drug in expiring:
        logger.warning(
            'Drug expiring soon: %s at %s — expires %s (stock: %s %s)',
            drug.name, drug.clinic.name, drug.expiry_date, drug.stock, drug.unit
        )
