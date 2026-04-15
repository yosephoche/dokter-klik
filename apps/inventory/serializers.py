from rest_framework import serializers
from .models import Drug, StockMovement


class DrugSerializer(serializers.ModelSerializer):
    is_low_stock = serializers.BooleanField(read_only=True)
    is_out_of_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = Drug
        fields = [
            'id', 'name', 'generic_name', 'category', 'unit',
            'buy_price', 'sell_price', 'stock', 'min_stock',
            'expiry_date', 'barcode', 'is_active',
            'is_low_stock', 'is_out_of_stock',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class StockMovementSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockMovement
        fields = [
            'id', 'drug', 'movement_type', 'quantity',
            'reference_type', 'notes', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']
