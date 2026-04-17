from django.contrib import admin
from .models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "sender_phone",
        "receiver_phone",
        "amount",
        "action",
        "status",
        "provider_name",
        "collection_reference",
        "collection_status",
        "payout_reference",
        "payout_status",
        "created_at",
    )

    list_filter = (
        "status",
        "action",
        "provider_name",
        "collection_status",
        "payout_status",
        "created_at",
    )

    search_fields = (
        "sender_phone",
        "receiver_phone",
        "collection_reference",
        "payout_reference",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )
