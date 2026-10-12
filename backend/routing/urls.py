from django.urls import path

from . import apis

urlpatterns = [path("health", apis.health)]
