"""Inventory signals — trigger low-stock check after every StockMovement."""
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender='inventory.StockMovement')
def on_stock_movement(sender, instance, created, **kwargs):
    if created and instance.movement_type == 'out':
        from apps.inventory.tasks import check_low_stock
        check_low_stock.delay(str(instance.drug_id))
