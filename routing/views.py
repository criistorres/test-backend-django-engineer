from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from routing.serializers import RouteResponseSerializer
from routing.services.geocoder import GeocodingError, geocode
from routing.services.optimizer import RouteInfeasibleError, optimize
from routing.services.osrm_client import (
    RoutingProviderError,
    RoutingProviderTimeout,
    fetch_route,
)


class RouteView(APIView):
    """GET /api/route/?start=<origin>&finish=<destination>

    Accepts 'City, ST' (e.g., 'Houston, TX'), 'lat,lng' (e.g., '29.76,-95.36'),
    or a full US address (resolved via Photon when not in the local dataset).
    """

    def get(self, request):
        start_raw = request.query_params.get("start", "").strip()
        finish_raw = request.query_params.get("finish", "").strip()

        if not start_raw or not finish_raw:
            return Response(
                {"error": "invalid_input", "detail": "Both 'start' and 'finish' query parameters are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            start_coords = geocode(start_raw)
            finish_coords = geocode(finish_raw)
        except GeocodingError as exc:
            return Response(
                {"error": "invalid_input", "detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            route = fetch_route(start_coords, finish_coords)
        except RoutingProviderTimeout as exc:
            return Response(
                {"error": "routing_provider_timeout", "detail": str(exc)},
                status=status.HTTP_504_GATEWAY_TIMEOUT,
            )
        except RoutingProviderError as exc:
            return Response(
                {"error": "routing_provider_error", "detail": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        try:
            result = optimize(route.points, route.distance_miles)
        except RouteInfeasibleError as exc:
            return Response(
                {"error": "route_infeasible_with_range", "detail": str(exc)},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        # Google Maps URL supports up to 9 waypoints; for longer routes we keep the first 9.
        waypoint_stops = result.stops[:9]
        waypoints_param = ""
        if waypoint_stops:
            wps = "|".join(f"{s.station.lat:.5f},{s.station.lng:.5f}" for s in waypoint_stops)
            waypoints_param = f"&waypoints={wps}"

        view_url_google = (
            f"https://www.google.com/maps/dir/?api=1"
            f"&origin={start_coords[0]:.5f},{start_coords[1]:.5f}"
            f"&destination={finish_coords[0]:.5f},{finish_coords[1]:.5f}"
            f"{waypoints_param}"
            f"&travelmode=driving"
        )

        # OSRM viewer accepts N points via &loc=; the path is re-computed by OSRM itself.
        osrm_locs = [f"&loc={start_coords[0]:.5f},{start_coords[1]:.5f}"]
        for s in result.stops:
            osrm_locs.append(f"&loc={s.station.lat:.5f},{s.station.lng:.5f}")
        osrm_locs.append(f"&loc={finish_coords[0]:.5f},{finish_coords[1]:.5f}")
        view_url_osrm = (
            f"https://map.project-osrm.org/?z=4"
            f"&center={(start_coords[0] + finish_coords[0]) / 2:.5f}"
            f",{(start_coords[1] + finish_coords[1]) / 2:.5f}"
            f"{''.join(osrm_locs)}"
            f"&srv=0"
        )

        payload = {
            "start": {"address": start_raw, "lat": start_coords[0], "lng": start_coords[1]},
            "finish": {"address": finish_raw, "lat": finish_coords[0], "lng": finish_coords[1]},
            "total_distance_miles": round(route.distance_miles, 2),
            "total_gallons": round(result.total_gallons, 2),
            "total_cost_usd": round(result.total_cost, 2),
            "route_polyline": route.polyline_encoded,
            "view_url": view_url_google,
            "view_url_osrm": view_url_osrm,
            "fuel_stops": [
                {
                    "name": s.station.name,
                    "address": s.station.address,
                    "city": s.station.city,
                    "state": s.station.state,
                    "lat": s.station.lat,
                    "lng": s.station.lng,
                    "price_per_gallon": float(s.station.price),
                    "gallons": round(s.gallons, 2),
                    "cost": round(s.cost, 2),
                    "miles_from_start": round(s.miles_from_start, 1),
                }
                for s in result.stops
            ],
        }
        serializer = RouteResponseSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)
