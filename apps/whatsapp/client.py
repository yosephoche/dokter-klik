"""Meta Cloud API client for WhatsApp Business messaging."""
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

GRAPH_API_VERSION = 'v19.0'
GRAPH_API_BASE = f'https://graph.facebook.com/{GRAPH_API_VERSION}'


class WhatsAppAPIError(Exception):
    pass


class WhatsAppClient:
    """Send WhatsApp template messages via Meta Cloud API."""

    def __init__(self, clinic):
        self.phone_number_id = clinic.whatsapp_phone_number_id
        self.access_token = clinic.whatsapp_access_token  # auto-decrypted

    def send_template_message(
        self,
        to: str,
        template_name: str,
        language_code: str = 'id',
        components: list = None,
    ) -> dict:
        """Send a pre-approved WhatsApp template message.

        Args:
            to: recipient phone number in E.164 format (e.g. '628123456789')
            template_name: approved template name in Meta Business Manager
            language_code: BCP-47 language code (default 'id' for Indonesian)
            components: list of template component objects (header/body/button params)
        """
        if not getattr(settings, 'WHATSAPP_ENABLED', False):
            logger.debug('WhatsApp disabled (WHATSAPP_ENABLED=False). Skipping send to %s', to)
            return {'skipped': True}

        if not self.phone_number_id or not self.access_token:
            raise WhatsAppAPIError('WhatsApp credentials not configured for this clinic.')

        # Normalize phone number: strip leading + and non-digits
        to_normalized = ''.join(c for c in to if c.isdigit())
        if to_normalized.startswith('0'):
            to_normalized = '62' + to_normalized[1:]

        payload = {
            'messaging_product': 'whatsapp',
            'to': to_normalized,
            'type': 'template',
            'template': {
                'name': template_name,
                'language': {'code': language_code},
                'components': components or [],
            },
        }

        url = f'{GRAPH_API_BASE}/{self.phone_number_id}/messages'
        try:
            resp = requests.post(
                url,
                json=payload,
                headers={'Authorization': f'Bearer {self.access_token}'},
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.HTTPError as exc:
            raise WhatsAppAPIError(
                f'WhatsApp API error: {exc.response.text}'
            ) from exc
        except requests.RequestException as exc:
            raise WhatsAppAPIError(f'WhatsApp request failed: {exc}') from exc

    def send_text_message(self, to: str, body: str) -> dict:
        """Send a free-text reply message (valid within 24h of user-initiated conversation).

        Args:
            to: recipient phone number (will be normalized to E.164)
            body: plain text message body
        """
        if not getattr(settings, 'WHATSAPP_ENABLED', False):
            logger.debug('WhatsApp disabled. Skipping text send to %s', to)
            return {'skipped': True}

        if not self.phone_number_id or not self.access_token:
            raise WhatsAppAPIError('WhatsApp credentials not configured for this clinic.')

        to_normalized = ''.join(c for c in to if c.isdigit())
        if to_normalized.startswith('0'):
            to_normalized = '62' + to_normalized[1:]

        payload = {
            'messaging_product': 'whatsapp',
            'to': to_normalized,
            'type': 'text',
            'text': {'body': body},
        }

        url = f'{GRAPH_API_BASE}/{self.phone_number_id}/messages'
        try:
            resp = requests.post(
                url,
                json=payload,
                headers={'Authorization': f'Bearer {self.access_token}'},
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.HTTPError as exc:
            raise WhatsAppAPIError(
                f'WhatsApp API error: {exc.response.text}'
            ) from exc
        except requests.RequestException as exc:
            raise WhatsAppAPIError(f'WhatsApp request failed: {exc}') from exc
