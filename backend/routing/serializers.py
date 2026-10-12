from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from .clients.open_meteo import HOURS
from .services.geo import haversine_mi


class GeocodeInputSerializer(serializers.Serializer):
    q = serializers.CharField(min_length=2, max_length=200, trim_whitespace=True)


class PlaceSerializer(serializers.Serializer):
    lat = serializers.FloatField(min_value=-90, max_value=90)
    lon = serializers.FloatField(min_value=-180, max_value=180)
    label = serializers.CharField(max_length=200, required=False, allow_blank=True)


class PlanInputSerializer(serializers.Serializer):
    origin = PlaceSerializer()
    destination = PlaceSerializer()
    departure = serializers.DateTimeField()
    load_lb = serializers.IntegerField(min_value=1, max_value=80_000)
    interval_mi = serializers.ChoiceField(choices=(10, 25, 50))

    def validate_departure(self, value):
        now = timezone.now()
        if not now - timedelta(minutes=15) <= value <= now + timedelta(hours=HOURS):
            raise serializers.ValidationError("Departure must be within the next 48 hours.")
        return value

    def validate(self, data):
        o, d = data["origin"], data["destination"]
        if haversine_mi((o["lat"], o["lon"]), (d["lat"], d["lon"])) < 1:
            raise serializers.ValidationError("Origin and destination must be different places.")
        return data
