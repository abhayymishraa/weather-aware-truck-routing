import hashlib
import json
from typing import Any

import httpx
from rest_framework.exceptions import APIException

USER_AGENT = "weather-aware-truck-routing/1.0"
TIMEOUT_S = 10.0


class UpstreamError(APIException):
    status_code = 502
    default_detail = "An outside service did not respond. Try again."
    default_code = "upstream_error"


class NoRouteError(APIException):
    status_code = 400
    default_detail = "No road route connects these places."
    default_code = "no_route"


def request_json(
    method: str, url: str, *, bad_request_error: type[APIException] = UpstreamError, **kwargs
) -> Any:
    transport = httpx.HTTPTransport(retries=1)
    try:
        with httpx.Client(
            transport=transport, timeout=TIMEOUT_S, headers={"User-Agent": USER_AGENT}
        ) as client:
            response = client.request(method, url, **kwargs)
    except httpx.HTTPError as exc:
        raise UpstreamError() from exc
    if response.status_code == 400:
        raise bad_request_error()
    if response.is_error:
        raise UpstreamError()
    return response.json()


def cache_key(prefix: str, *parts: Any) -> str:
    digest = hashlib.sha256(json.dumps(parts, sort_keys=True).encode()).hexdigest()
    return f"{prefix}:{digest}"
