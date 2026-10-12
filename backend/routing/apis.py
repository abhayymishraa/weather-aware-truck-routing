from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework.views import exception_handler as drf_exception_handler

from .clients import photon
from .serializers import GeocodeInputSerializer, PlanInputSerializer
from .services import plan as plan_service
from .services.types import LatLon


def exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is None:
        return None
    if isinstance(exc, ValidationError):
        response.data = {
            "detail": _first_message(response.data),
            "code": "invalid",
            "errors": response.data,
        }
    else:
        response.data = {"detail": str(exc.detail), "code": exc.get_codes()}
    return response


def _first_message(errors) -> str:
    while isinstance(errors, dict | list):
        errors = next(iter(errors.values())) if isinstance(errors, dict) else errors[0]
    return str(errors)


@api_view(["GET"])
def health(request):
    return Response({"status": "ok"})


class GeocodeApi(APIView):
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "geocode"

    def get(self, request):
        serializer = GeocodeInputSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return Response({"results": photon.search(serializer.validated_data["q"])})


class PlanApi(APIView):
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "plan"

    def post(self, request):
        serializer = PlanInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        result = plan_service.build_plan(
            origin=LatLon(data["origin"]["lat"], data["origin"]["lon"]),
            destination=LatLon(data["destination"]["lat"], data["destination"]["lon"]),
            departure=data["departure"],
            load_lb=data["load_lb"],
            interval_mi=data["interval_mi"],
            now=timezone.now(),
        )
        return Response(result)
