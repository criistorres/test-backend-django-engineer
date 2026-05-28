"""Hybrid geocoder: tries 'lat,lng' -> offline US-cities dataset -> Photon (OSM) as fallback.

The offline dataset covers ~97.7% of cities present in the fuel-prices CSV.
Photon (komoot.io) handles full addresses and POIs without a hard rate limit.
"""

from __future__ import annotations

import csv
import re
from functools import lru_cache
from pathlib import Path

import requests
from django.conf import settings


class GeocodingError(ValueError):
    pass


@lru_cache(maxsize=1)
def _cities_index() -> dict[tuple[str, str], tuple[float, float]]:
    path = Path(settings.BASE_DIR) / "data" / "us_cities.csv"
    index: dict[tuple[str, str], tuple[float, float]] = {}
    with path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            key = (row["CITY"].strip().upper(), row["STATE_CODE"].strip().upper())
            if key not in index:
                index[key] = (float(row["LATITUDE"]), float(row["LONGITUDE"]))
    return index


_LATLNG_RE = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$")
_CITY_STATE_RE = re.compile(r"^\s*([A-Za-z .'\-]+?)\s*,\s*([A-Za-z]{2})\s*$")


@lru_cache(maxsize=512)
def _geocode_photon(text: str) -> tuple[float, float] | None:
    """Query Photon (OSM) restricting results to the USA. Returns None if nothing found."""
    if not getattr(settings, "PHOTON_ENABLED", True):
        return None
    base = getattr(settings, "PHOTON_BASE_URL", "https://photon.komoot.io")
    timeout = float(getattr(settings, "PHOTON_TIMEOUT_SECONDS", 4))
    try:
        resp = requests.get(
            f"{base}/api/",
            params={"q": text, "limit": 5, "lang": "en"},
            timeout=timeout,
            headers={"User-Agent": "fuel-route-optimizer/1.0"},
        )
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError):
        return None

    features = data.get("features") or []
    for feat in features:
        props = feat.get("properties") or {}
        if (props.get("countrycode") or "").upper() != "US":
            continue
        geom = feat.get("geometry") or {}
        coords = geom.get("coordinates") or []
        if len(coords) >= 2:
            lng, lat = float(coords[0]), float(coords[1])
            return lat, lng
    return None


def geocode(text: str) -> tuple[float, float]:
    """Resolve input to (lat, lng).

    Order: literal 'lat,lng' -> local 'City, ST' dataset -> Photon (USA-only).
    Raises GeocodingError when nothing resolves.
    """
    if not text or not text.strip():
        raise GeocodingError("empty input")

    m = _LATLNG_RE.match(text)
    if m:
        lat = float(m.group(1))
        lng = float(m.group(2))
        if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
            raise GeocodingError(f"coordinates out of valid range: {text}")
        return lat, lng

    m = _CITY_STATE_RE.match(text)
    if m:
        city = m.group(1).strip().upper()
        state = m.group(2).strip().upper()
        coords = _cities_index().get((city, state))
        if coords is not None:
            return coords

    coords = _geocode_photon(text.strip())
    if coords is not None:
        return coords

    raise GeocodingError(
        f"could not resolve: {text!r}. Use 'City, ST', 'lat,lng' or a full US address."
    )
