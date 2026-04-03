from django.db import models

class UserProfile(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15, unique=True)
    balance = models.IntegerField(default=10000)

    # Optional: store voice recording for backup/debugging
    voice_sample = models.FileField(upload_to='voices/', null=True, blank=True)

    # Azure Speaker Recognition Profile ID (text-independent)
    voice_profile_id = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.phone})"