import numpy as np

from routing.services.geometry import (
    bounding_box,
    cumulative_distances,
    haversine_miles,
    project_stations_on_polyline,
)


def test_haversine_known_distance():
    # Houston (29.76, -95.36) -> Austin (30.27, -97.74) ~ 147 mi straight line (great-circle).
    d = haversine_miles(29.76, -95.36, 30.27, -97.74)
    assert 140 < d < 155


def test_cumulative_distances_increasing():
    points = [(0.0, 0.0), (0.0, 1.0), (0.0, 2.0)]
    cum = cumulative_distances(points)
    assert cum[0] == 0.0
    assert cum[1] > 0
    assert cum[2] > cum[1]


def test_bounding_box_with_padding():
    points = [(30.0, -95.0), (40.0, -75.0)]
    min_lat, max_lat, min_lng, max_lng = bounding_box(points, padding_miles=10.0)
    assert min_lat < 30.0 and max_lat > 40.0
    assert min_lng < -95.0 and max_lng > -75.0


def test_project_station_on_polyline_on_segment():
    points = [(0.0, 0.0), (0.0, 1.0)]
    cum = cumulative_distances(points)
    # Station right on the segment at (0, 0.5) -> perp ~ 0 and pos ~ half of the segment
    lats = np.array([0.0])
    lngs = np.array([0.5])
    perp, pos = project_stations_on_polyline(lats, lngs, points, cum)
    assert perp[0] < 1.0
    assert 30 < pos[0] < 40  # ~ 34.6 mi (half a degree of longitude at the equator)


def test_project_station_off_route():
    points = [(0.0, 0.0), (0.0, 1.0)]
    cum = cumulative_distances(points)
    # Station 1 degree of latitude away from the segment (~ 69 mi)
    lats = np.array([1.0])
    lngs = np.array([0.5])
    perp, _ = project_stations_on_polyline(lats, lngs, points, cum)
    assert perp[0] > 50
