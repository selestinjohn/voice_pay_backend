from rest_framework import serializers
from .models import Transaction


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = [
            "id",
            "sender_phone",
            "receiver_phone",
            "amount",
            "action",
            "status",
            "provider_name",
            "collection_reference",
            "collection_status",
            "collection_response",
            "payout_reference",
            "payout_status",
            "payout_response",
            "voice_text",
            "created_at",
            "updated_at",
        ]