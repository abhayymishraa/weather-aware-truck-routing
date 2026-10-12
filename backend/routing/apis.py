from rest_framework.decorators import api_view
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework.views import exception_handler as drf_exception_handler

from .clients import photon
from .serializers import GeocodeInputSerializer


def exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is None:
        return None
    if isinstance(exc, ValidationError):
        response.data = {"detail": "Invalid input.", "code": "invalid", "errors": response.data}
    else:
        response.data = {"detail": str(exc.detail), "code": exc.get_codes()}
    return response


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
