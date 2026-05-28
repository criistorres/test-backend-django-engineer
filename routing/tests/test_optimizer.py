from decimal import Decimal

import pytest
from django.test import TestCase

from routing.models import FuelStation
from routing.services.optimizer import (
    RouteInfeasibleError,
    optimize,
)


class OptimizerTests(TestCase):
    def _make_station(self, lat, lng, price, name="S"):
        return FuelStation.objects.create(
            opis_id=1,
            name=name,
            address="addr",
            city="C",
            state="TX",
            lat=lat,
            lng=lng,
            price=Decimal(str(price)),
        )

    def test_short_route_no_stops(self):
        # 100-mi route: fits in one tank (500 mi)
        points = [(30.0, -95.0), (30.0, -93.55)]  # ~100 mi
        result = optimize(points, total_distance_miles=100.0)
        assert result.stops == []
        assert result.total_gallons == pytest.approx(10.0, rel=0.01)
        # No stations in DB -> final cost = 0
        assert result.total_cost == 0.0

    def test_long_route_with_one_stop(self):
        # 800-mi route along longitude. Station at ~400 mi from origin.
        # 800 mi ~ 11.59 degrees of longitude at the equator
        points = [(0.0, 0.0), (0.0, 11.59)]
        # station at ~5.8 degrees of lng (~400 mi)
        self._make_station(0.0, 5.79, 3.0, name="A")
        result = optimize(points, total_distance_miles=800.0)
        assert len(result.stops) == 1
        assert result.stops[0].station.name == "A"
        # 800 mi / 10 mpg = 80 gallons total
        assert result.total_gallons == pytest.approx(80.0, rel=0.01)
        # cost: stop (40 gal @ $3) + final (40 gal @ $3) = 240
        assert result.total_cost == pytest.approx(240.0, rel=0.01)

    def test_chooses_cheapest_in_range(self):
        points = [(0.0, 0.0), (0.0, 11.59)]
        self._make_station(0.0, 4.34, 4.0, name="EXPENSIVE")  # ~300 mi
        self._make_station(0.0, 5.79, 3.0, name="CHEAP")  # ~400 mi
        result = optimize(points, total_distance_miles=800.0)
        assert result.stops[0].station.name == "CHEAP"

    def test_infeasible_raises(self):
        # 1000-mi route with no stations at all
        points = [(0.0, 0.0), (0.0, 14.49)]  # ~1000 mi
        with pytest.raises(RouteInfeasibleError):
            optimize(points, total_distance_miles=1000.0)
