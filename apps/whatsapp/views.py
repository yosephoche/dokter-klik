"""WhatsApp webhook handler."""
import logging
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class WhatsAppWebhookView(APIView):
    """Handles Meta webhook verification (GET) and incoming messages (POST)."""
    permission_classes = [AllowAny]

    def get(self, request):
        """Meta webhook verification challenge."""
        mode = request.GET.get('hub.mode')
        token = request.GET.get('hub.verify_token')
        challenge = request.GET.get('hub.challenge')

        if mode == 'subscribe' and token == settings.WHATSAPP_VERIFY_TOKEN:
            return HttpResponse(challenge, content_type='text/plain')

        return HttpResponse('Forbidden', status=403)

    def post(self, request):
        """Handle incoming WhatsApp messages — dispatch to chatbot via Celery."""
        data = request.data
        try:
            entry = data.get('entry', [{}])[0]
            changes = entry.get('changes', [{}])[0]
            value = changes.get('value', {})
            phone_number_id = value.get('metadata', {}).get('phone_number_id', '')
            messages = value.get('messages', [])

            if messages:
                msg = messages[0]
                msg_type = msg.get('type')
                sender_phone = msg.get('from', '')
                logger.info('Incoming WA message type=%s from=%s', msg_type, sender_phone)

                if msg_type == 'text':
                    message_text = msg.get('text', {}).get('body', '').strip()
                    if message_text and sender_phone and phone_number_id:
                        from apps.whatsapp.tasks import process_whatsapp_message
                        process_whatsapp_message.delay(
                            phone_number_id, sender_phone, message_text
                        )
        except Exception:
            logger.exception('Error processing WhatsApp webhook payload')

        return Response({'status': 'ok'})
