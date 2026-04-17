from django.urls import path
from .views import (
    register_user,
    login_user,
    check_balance,
    process_voice,
    transaction_status,
    payment_webhook,
)

urlpatterns = [
    path("register/", register_user, name="register_user"),
    path("login/", login_user, name="login_user"),
    path("check-balance/", check_balance, name="check_balance"),
    path("process-voice/", process_voice, name="process_voice"),
    path("transactions/<int:transaction_id>/", transaction_status, name="transaction_status"),
    path("payments/webhook/", payment_webhook, name="payment_webhook"),
]