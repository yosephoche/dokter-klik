"""WhatsApp notification Celery tasks."""
import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(queue='notifications')
def send_queue_alert(queue_entry_id: str):
    """Send WhatsApp notification when patient is 3rd in queue or fewer."""
    from apps.queue.models import QueueEntry
    from apps.whatsapp.client import WhatsAppClient, WhatsAppAPIError

    try:
        entry = QueueEntry.objects.select_related('patient', 'clinic').get(
            id=queue_entry_id
        )
    except QueueEntry.DoesNotExist:
        logger.warning('QueueEntry %s not found for WA alert', queue_entry_id)
        return

    if not entry.patient or not entry.patient.phone:
        return

    client = WhatsAppClient(entry.clinic)
    try:
        client.send_template_message(
            to=entry.patient.phone,
            template_name='queue_alert',
            components=[{
                'type': 'body',
                'parameters': [
                    {'type': 'text', 'text': entry.patient.name},
                    {'type': 'text', 'text': str(entry.queue_number)},
                    {'type': 'text', 'text': entry.clinic.name},
                ],
            }],
        )
        entry.notified_at = timezone.now()
        entry.save(update_fields=['notified_at'])
        logger.info('WA queue alert sent for entry %s', queue_entry_id)
    except WhatsAppAPIError as exc:
        logger.error('WA queue alert failed for entry %s: %s', queue_entry_id, exc)


@shared_task(queue='notifications')
def process_whatsapp_message(phone_number_id: str, sender_phone: str, message_text: str):
    """Process an incoming WhatsApp text message through the booking chatbot."""
    from apps.clinics.models import Clinic
    from apps.whatsapp.chatbot import BookingChatbot
    from apps.whatsapp.client import WhatsAppClient, WhatsAppAPIError

    clinic = Clinic.objects.filter(
        whatsapp_phone_number_id=phone_number_id, is_active=True
    ).first()
    if not clinic:
        logger.warning('No active clinic found for phone_number_id=%s', phone_number_id)
        return

    try:
        bot = BookingChatbot(clinic=clinic, sender_phone=sender_phone)
        reply_text = bot.handle(message_text)
    except Exception:
        logger.exception('Chatbot error for clinic %s, phone %s', clinic.id, sender_phone)
        return

    client = WhatsAppClient(clinic)
    try:
        client.send_text_message(to=sender_phone, body=reply_text)
    except WhatsAppAPIError:
        logger.exception('Failed to send chatbot reply to %s', sender_phone)


@shared_task(queue='notifications')
def send_low_stock_alert(drug_id: str):
    """Send WhatsApp notification to clinic owner/admin about low drug stock."""
    from apps.inventory.models import Drug
    from apps.whatsapp.client import WhatsAppClient, WhatsAppAPIError
    from apps.accounts.models import CustomUser

    try:
        drug = Drug.objects.select_related('clinic').get(id=drug_id)
    except Drug.DoesNotExist:
        return

    # Find owner/admin with phone number in the clinic
    admin = CustomUser.objects.filter(
        clinic=drug.clinic, role__in=['owner', 'admin'], phone__isnull=False
    ).exclude(phone='').first()

    if not admin:
        logger.warning('No admin phone for low stock alert at clinic %s', drug.clinic.name)
        return

    client = WhatsAppClient(drug.clinic)
    try:
        client.send_template_message(
            to=admin.phone,
            template_name='low_stock_alert',
            components=[{
                'type': 'body',
                'parameters': [
                    {'type': 'text', 'text': drug.name},
                    {'type': 'text', 'text': str(drug.stock)},
                    {'type': 'text', 'text': drug.unit},
                    {'type': 'text', 'text': str(drug.min_stock)},
                ],
            }],
        )
        logger.info('WA low stock alert sent for drug %s', drug_id)
    except WhatsAppAPIError as exc:
        logger.error('WA low stock alert failed for drug %s: %s', drug_id, exc)
