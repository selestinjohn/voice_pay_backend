from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse

def home(request):
    return HttpResponse("Voice Pay Backend is running successfully")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("transactions.urls")),
    path("", home),
]