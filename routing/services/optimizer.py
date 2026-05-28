"""Greedy fuel-stop optimizer: picks stations along the route to minimize total cost."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

import numpy as np
from django.conf import settings

from routing.models import FuelStation
from routing.services.geometry import (
    bounding_box,
    cumulative_distances,
    project_stations_on_polyline,
)


class RouteInfeasibleError(RuntimeError):
    """Some leg of the route has no station within tank range."""


@dataclass(frozen=True)
class Stop:
    station: FuelStation
    gallons: float
    cost: float
    miles_from_start: float


@dataclass(frozen=True)
class OptimizationResult:
    stops: list[Stop]
    total_gallons: float
    total_cost: float


def _build_candidates(
    points: list[tuple[float, float]],
    cum_dist: np.ndarray,
    buffer_miles: float,
) -> tuple[list[FuelStation], np.ndarray, np.ndarray]:
    """Return (stations, pos_miles, prices) sorted by pos_miles, already buffer-filtered."""
    min_lat, max_lat, min_lng, max_lng = bounding_box(points, padding_miles=buffer_miles)
    qs = list(
        FuelStation.objects.filter(
            lat__gte=min_lat,
            lat__lte=max_lat,
            lng__gte=min_lng,
            lng__lte=max_lng,
        ).only("id", "name", "address", "city", "state", "lat", "lng", "price")
    )
    if not qs:
        return [], np.array([], dtype=np.float64), np.array([], dtype=np.float64)

    lats = np.fromiter((s.lat for s in qs), dtype=np.float64, count=len(qs))
    lngs = np.fromiter((s.lng for s in qs), dtype=np.float64, count=len(qs))
    perp, pos = project_stations_on_polyline(lats, lngs, points, cum_dist)

    mask = perp <= buffer_miles
    if not mask.any():
        return [], np.array([], dtype=np.float64), np.array([], dtype=np.float64)

    filtered_stations = [s for s, keep in zip(qs, mask, strict=True) if keep]
    filtered_pos = pos[mask]
    filtered_prices = np.fromiter(
        (float(s.price) for s in filtered_stations), dtype=np.float64, count=len(filtered_stations)
    )

    order = np.argsort(filtered_pos)
    sorted_stations = [filtered_stations[i] for i in order]
    return sorted_stations, filtered_pos[order], filtered_prices[order]


def optimize(route_points: list[tuple[float, float]], total_distance_miles: float) -> OptimizationResult:
    """Greedy H2: prefer stations in the 60-100% tank window to avoid stops too close together.

    Falls back to the full 0-100% remaining range (H1) when the preferred window is empty.
    """
    tank_miles = float(settings.TANK_RANGE_MILES)
    mpg = float(settings.VEHICLE_MPG)
    buffer_miles = float(settings.ROUTE_BUFFER_MILES)
    preferred_min_ratio = 0.6

    cum = cumulative_distances(route_points)
    stations, positions, prices = _build_candidates(route_points, cum, buffer_miles)

    stops: list[Stop] = []
    position = 0.0
    last_price: Decimal | None = None

    while position + tank_miles < total_distance_miles:
        max_pos = position + tank_miles
        min_pos_pref = position + tank_miles * preferred_min_ratio
        lo = np.searchsorted(positions, min_pos_pref, side="left")
        hi = np.searchsorted(positions, max_pos, side="right")
        if lo == hi:
            # H1 fallback: accept any station within the remaining range
            lo = np.searchsorted(positions, position, side="right")
            hi = np.searchsorted(positions, max_pos, side="right")
            if lo == hi:
                raise RouteInfeasibleError(
                    f"no station within {tank_miles:.0f} miles starting at mile {position:.1f}"
                )
        window_prices = prices[lo:hi]
        best_offset = int(np.argmin(window_prices))
        best_idx = lo + best_offset
        best_station = stations[best_idx]
        best_pos = float(positions[best_idx])
        best_price = float(prices[best_idx])

        gallons = (best_pos - position) / mpg
        cost = gallons * best_price
        stops.append(
            Stop(
                station=best_station,
                gallons=gallons,
                cost=cost,
                miles_from_start=best_pos,
            )
        )
        position = best_pos
        last_price = best_station.price

    # Final leg to the destination
    final_gallons = (total_distance_miles - position) / mpg
    if last_price is not None:
        final_cost = final_gallons * float(last_price)
    elif len(stations) > 0:
        cheapest_idx = int(np.argmin(prices))
        final_cost = final_gallons * float(prices[cheapest_idx])
    else:
        final_cost = 0.0

    total_gallons = sum(s.gallons for s in stops) + final_gallons
    total_cost = sum(s.cost for s in stops) + final_cost

    return OptimizationResult(
        stops=stops,
        total_gallons=total_gallons,
        total_cost=total_cost,
    )
