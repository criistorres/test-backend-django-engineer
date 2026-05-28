"""Client for the public OSRM server. Makes exactly one HTTP call per request."""

from __future__ import annotations

from dataclasses import dataclass

import polyline as polyline_lib
import requests
from django.conf import settings

METERS_PER_MILE = 1609.344


class RoutingProviderError(RuntimeError):
    """OSRM returned a logical error (e.g., NoRoute) or a non-2xx HTTP status."""


class RoutingProviderTimeout(RuntimeError):
    """OSRM did not respond within the timeout."""


@dataclass(frozen=True)
class Route:
    distance_miles: float
    polyline_encoded: str
    points: list[tuple[float, float]]  # decoded list of (lat, lng)


def fetch_route(start: tuple[float, float], finish: tuple[float, float]) -> Route:
    """Call the public OSRM server once and return the route.

    start, finish: (lat, lng)
    """
    base = settings.OSRM_BASE_URL.rstrip("/")
    coords = f"{start[1]:.6f},{start[0]:.6f};{finish[1]:.6f},{finish[0]:.6f}"
    url = f"{base}/route/v1/driving/{coords}"
    params = {"overview": "simplified", "geometries": "polyline"}

    try:
        resp = requests.get(url, params=params, timeout=settings.OSRM_TIMEOUT_SECONDS)
    except requests.Timeout as exc:
        raise RoutingProviderTimeout("OSRM did not respond within the timeout") from exc
    except requests.RequestException as exc:
        raise RoutingProviderError(f"OSRM network failure: {exc}") from exc

    if resp.status_code != 200:
        raise RoutingProviderError(f"OSRM HTTP {resp.status_code}: {resp.text[:200]}")

    data = resp.json()
    if data.get("code") != "Ok":
        raise RoutingProviderError(f"OSRM code={data.get('code')} message={data.get('message', '')}")

    routes = data.get("routes") or []
    if not routes:
        raise RoutingProviderError("OSRM returned no routes")

    route = routes[0]
    encoded = route["geometry"]
    distance_meters = float(route["distance"])
    points = polyline_lib.decode(encoded)  # [(lat, lng), ...]

    return Route(
        distance_miles=distance_meters / METERS_PER_MILE,
        polyline_encoded=encoded,
        points=points,
    )
