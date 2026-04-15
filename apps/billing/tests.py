"""Tests for Midtrans webhook signature verification."""
from django.test import TestCase
from apps.billing.midtrans import MidtransClient
from unittest.mock import patch
import hashlib


class MidtransClientTests(TestCase):
    def setUp(self):
        with patch.object(MidtransClient, 'server_key', 'test-server-key', create=True):
            pass

    @patch('django.conf.settings.MIDTRANS_SERVER_KEY', 'test-server-key')
    @patch('django.conf.settings.MIDTRANS_SANDBOX', True)
    def test_verify_webhook_signature_valid(self):
        """Valid signature passes verification."""
        order_id = 'INV-202401-0001'
        status_code = '200'
        gross_amount = '150000.00'
        server_key = 'test-server-key'

        raw = f'{order_id}{status_code}{gross_amount}{server_key}'
        signature = hashlib.sha512(raw.encode()).hexdigest()

        client = MidtransClient()
        result = client.verify_webhook_signature(order_id, status_code, gross_amount, signature)
        self.assertTrue(result)

    @patch('django.conf.settings.MIDTRANS_SERVER_KEY', 'test-server-key')
    @patch('django.conf.settings.MIDTRANS_SANDBOX', True)
    def test_verify_webhook_signature_invalid(self):
        """Invalid signature fails verification."""
        client = MidtransClient()
        result = client.verify_webhook_signature('ORDER-1', '200', '100000', 'wrong-signature')
        self.assertFalse(result)

    @patch('django.conf.settings.MIDTRANS_SANDBOX', True)
    def test_sandbox_base_url(self):
        """Sandbox mode uses sandbox URL."""
        client = MidtransClient()
        self.assertIn('sandbox', client.BASE_URL)
