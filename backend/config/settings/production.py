import os

from .base import *

SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": os.environ["REDIS_URL"],
    }
}
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
REST_FRAMEWORK = {**REST_FRAMEWORK, "NUM_PROXIES": 1}
