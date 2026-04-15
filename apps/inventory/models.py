"""Inventory models: Drug and StockMovement."""
import uuid
from django.db import models
from apps.core.models import BaseModel
from apps.core.managers import ClinicScopedManager


class Drug(BaseModel):
    """Drug/medication catalogue per clinic."""
    clinic = models.ForeignKey(
        'clinics.Clinic', on_delete=models.CASCADE, related_name='drugs'
    )
    name = models.CharField(max_length=255)
    generic_name = models.CharField(max_length=255, blank=True)
    category = models.CharField(max_length=100, blank=True)
    unit = models.CharField(max_length=50)
    buy_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    sell_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    stock = models.IntegerField(default=0)
    min_stock = models.IntegerField(default=10)
    expiry_date = models.DateField(null=True, blank=True)
    barcode = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)

    objects = ClinicScopedManager()

    class Meta:
        db_table = 'inventory_drug'
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.stock} {self.unit})'

    @property
    def is_low_stock(self) -> bool:
        return self.stock < self.min_stock

    @property
    def is_out_of_stock(self) -> bool:
        return self.stock <= 0


class StockMovement(BaseModel):
    """Audit trail for all stock changes."""
    MOVEMENT_TYPES = [
        ('in', 'Restock'),
        ('out', 'Dispense'),
        ('adjustment', 'Adjustment'),
        ('expired', 'Expired'),
    ]

    drug = models.ForeignKey(Drug, on_delete=models.CASCADE, related_name='movements')
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPES)
    quantity = models.IntegerField()  # positive = in, negative = out
    reference_type = models.CharField(max_length=50, blank=True)  # 'prescription', 'restock', etc.
    reference_id = models.UUIDField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        'accounts.CustomUser', null=True, on_delete=models.SET_NULL
    )

    class Meta:
        db_table = 'inventory_stockmovement'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.movement_type} {abs(self.quantity)} {self.drug.unit} of {self.drug.name}'
