from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from routing.models import FuelStation
from routing.services.osrm_client import Route


class RouteViewTests(TestCase):
    def setUp(self):
        FuelStation.objects.create(
            opis_id=1,
            name="MID STATION",
            address="addr",
            city="MID",
            state="TX",
            lat=0.0,
            lng=5.79,
            price=Decimal("3.0"),
        )

    def test_missing_params_returns_400(self):
        resp = self.client.get(reverse("route"))
        assert resp.status_code == 400
        assert resp.json()["error"] == "invalid_input"

    def test_invalid_city_returns_400(self):
        resp = self.client.get(reverse("route"), {"start": "Nowhere, ZZ", "finish": "29.76,-95.36"})
        assert resp.status_code == 400

    @patch("routing.views.fetch_route")
    def test_happy_path_with_mocked_osrm(self, mock_fetch):
        mock_fetch.return_value = Route(
            distance_miles=800.0,
            polyline_encoded="dummy",
            points=[(0.0, 0.0), (0.0, 11.59)],
        )
        resp = self.client.get(
            reverse("route"),
            {"start": "0,0", "finish": "0,11.59"},
        )
        assert resp.status_code == 200, resp.content
        body = resp.json()
        assert body["total_distance_miles"] == 800.0
        assert body["route_polyline"] == "dummy"
        assert "view_url" in body
        assert "google.com/maps/dir/" in body["view_url"]
        assert "waypoints=" in body["view_url"]
        assert "view_url_osrm" in body
        assert "map.project-osrm.org" in body["view_url_osrm"]
        assert body["view_url_osrm"].count("&loc=") >= 3  # start + 1 parada + finish
        assert len(body["fuel_stops"]) == 1
        assert body["fuel_stops"][0]["name"] == "MID STATION"

    @patch("routing.views.fetch_route")
    def test_route_infeasible_returns_422(self, mock_fetch):
        FuelStation.objects.all().delete()
        mock_fetch.return_value = Route(
            distance_miles=1000.0,
            polyline_encoded="dummy",
            points=[(0.0, 0.0), (0.0, 14.49)],
        )
        resp = self.client.get(
            reverse("route"),
            {"start": "0,0", "finish": "0,14.49"},
        )
        assert resp.status_code == 422
        assert resp.json()["error"] == "route_infeasible_with_range"
