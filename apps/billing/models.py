"""Billing models: Invoice and PaymentTransaction."""
from django.db import models
from apps.core.models import BaseModel


class Invoice(BaseModel):
    """Auto-generated invoice from EMR visit data."""
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('qris', 'QRIS'),
        ('virtual_account', 'Virtual Account'),
        ('free', 'Free'),
    ]
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ]

    visit = models.OneToOneField(
        'emr.Visit', on_delete=models.PROTECT, related_name='invoice'
    )
    clinic = models.ForeignKey(
        'clinics.Clinic', on_delete=models.PROTECT, related_name='invoices'
    )
    invoice_number = models.CharField(max_length=50, unique=True)
    total_consultation = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_procedures = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_drugs = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_method = models.CharField(
        max_length=20, blank=True, choices=PAYMENT_METHOD_CHOICES
    )
    payment_status = models.CharField(
        max_length=20, default='pending', choices=PAYMENT_STATUS_CHOICES
    )
    midtrans_order_id = models.CharField(max_length=100, blank=True)
    midtrans_transaction_id = models.CharField(max_length=100, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    pdf_file = models.CharField(max_length=500, blank=True)  # MinIO path
    cashier_notes = models.TextField(blank=True)

    class Meta:
        db_table = 'billing_invoice'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.invoice_number} — {self.payment_status}'
