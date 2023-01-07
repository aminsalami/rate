from django.contrib import admin
from django.urls import path

from rate.api import RatesAPI

urlpatterns = [
    path('admin/', admin.site.urls),
    path('v1/rates/', RatesAPI.as_view())
]
