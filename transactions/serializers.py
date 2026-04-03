from rest_framework import serializers
from .models import UserProfile, Transaction


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['id', 'name', 'phone', 'balance']


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = [
            'id',
            'sender_phone',
            'receiver_phone',
            'amount',
            'action',
            'status',
            'created_at',
        ]