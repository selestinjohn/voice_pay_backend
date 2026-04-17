from django.urls import path
from . import views

urlpatterns = [
    path("register/", views.register_voice, name="register_voice"),
    path("login/", views.login_voice, name="login_voice"),
]