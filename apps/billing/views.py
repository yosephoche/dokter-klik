"""Billing views: invoice detail, cash/QRIS payment, Midtrans webhook."""
import logging
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsAdminOrOwner
from .models import Invoice
from .midtrans import MidtransClient
from .serializers import InvoiceSerializer

logger = logging.getLogger(__name__)


class InvoiceListView(generics.ListAPIView):
    permission_classes = [IsAdminOrOwner]
    serializer_class = InvoiceSerializer

    def get_queryset(self):
        return Invoice.objects.filter(clinic=self.request.user.clinic).select_related('visit')


class InvoiceDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAdminOrOwner]
    serializer_class = InvoiceSerializer

    def get_queryset(self):
        return Invoice.objects.filter(clinic=self.request.user.clinic)


class PayCashView(APIView):
    """Record a cash payment for an invoice."""
    permission_classes = [IsAdminOrOwner]

    def post(self, request, pk):
        try:
            invoice = Invoice.objects.get(pk=pk, clinic=request.user.clinic)
        except Invoice.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        if invoice.payment_status == 'paid':
            return Response(InvoiceSerializer(invoice).data)

        invoice.payment_method = 'cash'
        invoice.payment_status = 'paid'
        invoice.paid_at = timezone.now()
        invoice.cashier_notes = request.data.get('notes', '')
        invoice.save(update_fields=['payment_method', 'payment_status', 'paid_at', 'cashier_notes', 'updated_at'])
        return Response(InvoiceSerializer(invoice).data)


class PayQRISView(APIView):
    """Create a Midtrans QRIS transaction for an invoice."""
    permission_classes = [IsAdminOrOwner]

    def post(self, request, pk):
        try:
            invoice = Invoice.objects.get(pk=pk, clinic=request.user.clinic)
        except Invoice.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        if invoice.payment_status == 'paid':
            return Response({'detail': 'Invoice already paid.'}, status=status.HTTP_400_BAD_REQUEST)

        client = MidtransClient()
        try:
            result = client.create_qris_transaction(
                order_id=invoice.invoice_number,
                amount=int(invoice.grand_total),
            )
        except Exception as exc:
            logger.exception('Midtrans QRIS creation failed for invoice %s', invoice.invoice_number)
            return Response(
                {'detail': f'Payment gateway error: {str(exc)}'},
                status=status.HTTP_502_BAD_GATEWAY
            )

        invoice.midtrans_order_id = invoice.invoice_number
        invoice.payment_method = 'qris'
        invoice.save(update_fields=['midtrans_order_id', 'payment_method', 'updated_at'])

        # Extract QR code URL from Midtrans response
        actions = result.get('actions', [])
        qr_url = next((a['url'] for a in actions if a.get('name') == 'generate-qr-code'), None)
        return Response({
            'qr_code_url': qr_url,
            'order_id': invoice.invoice_number,
            'amount': invoice.grand_total,
        })


@method_decorator(csrf_exempt, name='dispatch')
class MidtransWebhookView(APIView):
    """Midtrans payment notification webhook. No CSRF, verify signature instead."""
    permission_classes = [AllowAny]

    def post(self, request):
        data = request.data
        order_id = data.get('order_id', '')
        status_code = data.get('status_code', '')
        gross_amount = data.get('gross_amount', '')
        signature_key = data.get('signature_key', '')
        transaction_status = data.get('transaction_status', '')

        client = MidtransClient()
        if not client.verify_webhook_signature(order_id, status_code, gross_amount, signature_key):
            return Response({'detail': 'Invalid signature.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            invoice = Invoice.objects.get(invoice_number=order_id)
        except Invoice.DoesNotExist:
            return Response({'detail': 'Invoice not found.'}, status=status.HTTP_404_NOT_FOUND)

        if invoice.payment_status == 'paid':
            return Response({'detail': 'Already processed.'})

        if transaction_status in ('settlement', 'capture'):
            invoice.payment_status = 'paid'
            invoice.paid_at = timezone.now()
            invoice.midtrans_transaction_id = data.get('transaction_id', '')
            invoice.save(update_fields=['payment_status', 'paid_at', 'midtrans_transaction_id', 'updated_at'])

        return Response({'detail': 'OK'})
