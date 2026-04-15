from rest_framework import serializers
from .models import Invoice


class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = [
            'id', 'invoice_number', 'visit', 'clinic',
            'total_consultation', 'total_procedures', 'total_drugs',
            'discount', 'grand_total',
            'payment_method', 'payment_status',
            'midtrans_order_id', 'paid_at', 'pdf_file',
            'cashier_notes', 'created_at',
        ]
        read_only_fields = [
            'id', 'invoice_number', 'visit', 'clinic',
            'total_consultation', 'total_procedures', 'total_drugs',
            'grand_total', 'midtrans_order_id', 'paid_at', 'created_at',
        ]
