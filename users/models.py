from django.db import models


class UserProfile(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15, unique=True)
    passphrase = models.CharField(max_length=100)
    balance = models.IntegerField(default=10000)

    voice_sample = models.FileField(upload_to="voices/", null=True, blank=True)
    voice_profile_id = models.CharField(max_length=100, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.phone})"