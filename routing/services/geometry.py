"""Geometric helpers: haversine, NumPy-vectorized projection, cumulative distance along a polyline."""

from __future__ import annotations

import math

import numpy as np

EARTH_RADIUS_MILES = 3958.7613


def haversine_miles(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance in miles between two points (haversine formula)."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_MILES * c


def cumulative_distances(points: list[tuple[float, float]]) -> np.ndarray:
    """Cumulative miles from point 0 for each polyline vertex (vectorized)."""
    arr = np.asarray(points, dtype=np.float64)
    lat1 = np.radians(arr[:-1, 0])
    lat2 = np.radians(arr[1:, 0])
    dlat = lat2 - lat1
    dlng = np.radians(arr[1:, 1] - arr[:-1, 1])
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlng / 2) ** 2
    seg = EARTH_RADIUS_MILES * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    cum = np.empty(len(arr), dtype=np.float64)
    cum[0] = 0.0
    cum[1:] = np.cumsum(seg)
    return cum


def bounding_box(points: list[tuple[float, float]], padding_miles: float = 0.0) -> tuple[float, float, float, float]:
    """Return (min_lat, max_lat, min_lng, max_lng) optionally padded in miles."""
    arr = np.asarray(points, dtype=np.float64)
    min_lat = float(arr[:, 0].min())
    max_lat = float(arr[:, 0].max())
    min_lng = float(arr[:, 1].min())
    max_lng = float(arr[:, 1].max())

    if padding_miles > 0:
        lat_pad = padding_miles / 69.0
        mid_lat = (min_lat + max_lat) / 2
        lng_pad = padding_miles / (69.0 * max(math.cos(math.radians(mid_lat)), 0.01))
        min_lat -= lat_pad
        max_lat += lat_pad
        min_lng -= lng_pad
        max_lng += lng_pad

    return min_lat, max_lat, min_lng, max_lng


def project_stations_on_polyline(
    station_lats: np.ndarray,
    station_lngs: np.ndarray,
    points: list[tuple[float, float]],
    cum_dist: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Project an array of stations onto the polyline (vectorized).

    For each station, finds the segment that minimizes the perpendicular distance.
    Returns (perp_miles, pos_miles) with shape = (n_stations,).

    Strategy: for each segment, performs the scalar projection of all stations
    in parallel (broadcast) and keeps the best result per station.
    """
    arr = np.asarray(points, dtype=np.float64)
    n_stations = len(station_lats)

    best_perp = np.full(n_stations, np.inf, dtype=np.float64)
    best_pos = np.zeros(n_stations, dtype=np.float64)

    # Local flat-Earth conversion (lat/lng -> miles); accurate enough for short segments.
    # The longitude factor uses the average latitude of each segment.
    for i in range(len(arr) - 1):
        lat1, lng1 = arr[i]
        lat2, lng2 = arr[i + 1]
        mid_lat = (lat1 + lat2) / 2
        lat_to_miles = 69.0
        lng_to_miles = 69.0 * math.cos(math.radians(mid_lat))

        ax = lng1 * lng_to_miles
        ay = lat1 * lat_to_miles
        bx = lng2 * lng_to_miles
        by = lat2 * lat_to_miles
        abx = bx - ax
        aby = by - ay
        ab_len_sq = abx * abx + aby * aby

        # Station positions in the same flat-miles reference frame
        sx = station_lngs * lng_to_miles
        sy = station_lats * lat_to_miles

        if ab_len_sq == 0:
            t = np.zeros(n_stations)
        else:
            t = ((sx - ax) * abx + (sy - ay) * aby) / ab_len_sq
            np.clip(t, 0.0, 1.0, out=t)

        closest_x = ax + t * abx
        closest_y = ay + t * aby
        dx = sx - closest_x
        dy = sy - closest_y
        perp = np.sqrt(dx * dx + dy * dy)

        improved = perp < best_perp
        if np.any(improved):
            best_perp = np.where(improved, perp, best_perp)
            segment_length = math.sqrt(ab_len_sq)
            pos_here = cum_dist[i] + t * segment_length
            best_pos = np.where(improved, pos_here, best_pos)

    return best_perp, best_pos
