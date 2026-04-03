from django.urls import path
from . import views

urlpatterns = [
    # 🔐 Voice Authentication (Text-Independent)
    path('register/', views.register_voice, name='register_user'),
    path('login/', views.login_voice, name='login_voice'),

    # 💰 Voice + Transaction
    path('voice-transaction/', views.voice_transaction, name='voice_transaction'),
]