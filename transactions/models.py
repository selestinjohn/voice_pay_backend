from django.db import models


class UserProfile(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15, unique=True)
    passphrase = models.CharField(max_length=100)
    balance = models.IntegerField(default=10000)

    def __str__(self):
        return f"{self.name} ({self.phone})"


class Transaction(models.Model):
    sender_phone = models.CharField(max_length=15, default="UNKNOWN")
    receiver_phone = models.CharField(max_length=15)
    amount = models.IntegerField()
    action = models.CharField(max_length=50, default="send_money")
    status = models.CharField(max_length=20, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    clickpesa_order_reference = models.CharField(max_length=100, null=True, blank=True)
    clickpesa_status = models.CharField(max_length=50, null=True, blank=True)
    clickpesa_response = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"{self.sender_phone} -> {self.receiver_phone} ({self.amount})"
