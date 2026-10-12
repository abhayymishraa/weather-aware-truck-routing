from django.urls import path

from . import apis

urlpatterns = [
    path("health", apis.health),
    path("geocode", apis.GeocodeApi.as_view()),
    path("plan", apis.PlanApi.as_view()),
]
