from django.urls import path
from .views import (
    register_user,
    login_user,
    check_balance,
    send_money,
    process_voice,
    query_payout_status,
    clickpesa_webhook,
)

urlpatterns = [
    path('register/', register_user, name='register_user'),
    path('login/', login_user, name='login_user'),
    path('check-balance/', check_balance, name='check_balance'),
    path('send-money/', send_money, name='send_money'),
    path('process-voice/', process_voice, name='process_voice'),
    path('payout-status/<str:order_reference>/', query_payout_status, name='query_payout_status'),
    path('clickpesa/webhook/', clickpesa_webhook, name='clickpesa_webhook'),
]