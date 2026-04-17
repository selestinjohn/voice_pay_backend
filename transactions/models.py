from django.db import models


class Transaction(models.Model):
    STATUS_AWAITING_CONFIRMATION = "awaiting_confirmation"
    STATUS_PAYMENT_PENDING = "payment_pending"
    STATUS_PROCESSING = "processing"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_AWAITING_CONFIRMATION, "Awaiting Confirmation"),
        (STATUS_PAYMENT_PENDING, "Payment Pending"),
        (STATUS_PROCESSING, "Processing"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_FAILED, "Failed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    ACTION_SEND_MONEY = "send_money"
    ACTION_CHECK_BALANCE = "check_balance"

    ACTION_CHOICES = [
        (ACTION_SEND_MONEY, "Send Money"),
        (ACTION_CHECK_BALANCE, "Check Balance"),
    ]

    sender_phone = models.CharField(max_length=15)
    receiver_phone = models.CharField(max_length=15, null=True, blank=True)
    amount = models.IntegerField(null=True, blank=True)

    action = models.CharField(
        max_length=50,
        choices=ACTION_CHOICES,
        default=ACTION_SEND_MONEY,
    )
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default=STATUS_AWAITING_CONFIRMATION,
    )

    provider_name = models.CharField(max_length=50, null=True, blank=True)

    collection_reference = models.CharField(max_length=100, null=True, blank=True)
    collection_status = models.CharField(max_length=50, null=True, blank=True)
    collection_response = models.JSONField(null=True, blank=True)

    payout_reference = models.CharField(max_length=100, null=True, blank=True)
    payout_status = models.CharField(max_length=50, null=True, blank=True)
    payout_response = models.JSONField(null=True, blank=True)

    voice_text = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return (
            f"{self.sender_phone} -> "
            f"{self.receiver_phone or 'N/A'} "
            f"({self.amount or 0})"
        )