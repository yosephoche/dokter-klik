"""Midtrans payment gateway client for QRIS and Virtual Account payments."""
import hashlib
import hmac
import logging
import requests
from base64 import b64encode
from django.conf import settings

logger = logging.getLogger(__name__)


class MidtransClient:
    """Thin wrapper around Midtrans Core API."""

    @property
    def BASE_URL(self):
        if getattr(settings, 'MIDTRANS_SANDBOX', True):
            return 'https://api.sandbox.midtrans.com/v2'
        return 'https://api.midtrans.com/v2'

    def __init__(self):
        self.server_key = settings.MIDTRANS_SERVER_KEY

    def _auth_header(self) -> str:
        encoded = b64encode(f'{self.server_key}:'.encode()).decode()
        return f'Basic {encoded}'

    def _headers(self) -> dict:
        return {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': self._auth_header(),
        }

    def _post(self, path: str, payload: dict) -> dict:
        url = f'{self.BASE_URL}{path}'
        resp = requests.post(url, json=payload, headers=self._headers(), timeout=30)
        resp.raise_for_status()
        return resp.json()

    def create_qris_transaction(self, order_id: str, amount: int) -> dict:
        """Create a QRIS payment transaction. Returns dict with qr_string / qr_code_url."""
        payload = {
            'payment_type': 'qris',
            'transaction_details': {
                'order_id': order_id,
                'gross_amount': amount,
            },
            'qris': {'acquirer': 'gopay'},
        }
        return self._post('/charge', payload)

    def create_va_transaction(self, order_id: str, amount: int, bank: str = 'bca') -> dict:
        """Create a virtual account payment transaction."""
        payload = {
            'payment_type': 'bank_transfer',
            'transaction_details': {
                'order_id': order_id,
                'gross_amount': amount,
            },
            'bank_transfer': {'bank': bank},
        }
        return self._post('/charge', payload)

    def get_transaction_status(self, order_id: str) -> dict:
        """Get transaction status by order ID."""
        resp = requests.get(
            f'{self.BASE_URL}/{order_id}/status',
            headers=self._headers(),
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()

    def verify_webhook_signature(
        self,
        order_id: str,
        status_code: str,
        gross_amount: str,
        signature_key: str,
    ) -> bool:
        """Verify Midtrans webhook notification signature.

        Signature = SHA-512(order_id + status_code + gross_amount + server_key)
        """
        raw = f'{order_id}{status_code}{gross_amount}{self.server_key}'
        expected = hashlib.sha512(raw.encode()).hexdigest()
        return hmac.compare_digest(expected, signature_key)
