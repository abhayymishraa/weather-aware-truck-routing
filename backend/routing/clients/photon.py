from django.core.cache import cache

from . import http

URL = "https://photon.komoot.io/api/"
US_BBOX = "-125,24,-66,50"
CACHE_S = 86_400


def search(query: str, limit: int = 5) -> list[dict]:
    params = {"q": query, "limit": 10, "bbox": US_BBOX, "lang": "en"}

    def load() -> list[dict]:
        data = http.request_json("GET", URL, params=params)
        results: list[dict] = []
        for item in data["features"]:
            props = item["properties"]
            if props.get("countrycode") != "US":
                continue
            label = _label(props)
            if any(r["label"] == label for r in results):
                continue
            lon, lat = item["geometry"]["coordinates"]
            results.append({"label": label, "lat": lat, "lon": lon})
        return results[:limit]

    return cache.get_or_set(http.cache_key("photon", query.strip().lower()), load, CACHE_S)


def _label(props: dict) -> str:
    name = props.get("name") or " ".join(
        p for p in (props.get("housenumber"), props.get("street")) if p
    )
    city = props.get("city")
    parts = [name, city if city != name else None, props.get("state")]
    return ", ".join(p for p in parts if p)
