from unittest.mock import patch

import pytest

from routing.services import geocoder
from routing.services.geocoder import GeocodingError, geocode


@pytest.fixture(autouse=True)
def _clear_photon_cache():
    geocoder._geocode_photon.cache_clear()
    yield
    geocoder._geocode_photon.cache_clear()


def test_geocode_latlng():
    lat, lng = geocode("29.76,-95.36")
    assert lat == 29.76
    assert lng == -95.36


def test_geocode_latlng_with_spaces():
    lat, lng = geocode(" 40.7 , -74.0 ")
    assert lat == 40.7
    assert lng == -74.0


def test_geocode_city_state():
    lat, lng = geocode("Houston, TX")
    assert 29 < lat < 31
    assert -96 < lng < -95


def test_geocode_invalid_format_falls_back_to_photon():
    with patch.object(geocoder, "_geocode_photon", return_value=None):
        with pytest.raises(GeocodingError):
            geocode("xyzqxqzpoi nonexistent place")


def test_geocode_unknown_city_falls_back_to_photon():
    with patch.object(geocoder, "_geocode_photon", return_value=None):
        with pytest.raises(GeocodingError):
            geocode("Atlantis, ZZ")


def test_geocode_empty():
    with pytest.raises(GeocodingError):
        geocode("")


def test_geocode_out_of_range():
    with pytest.raises(GeocodingError):
        geocode("999,0")


def test_geocode_photon_resolves_full_address():
    with patch.object(geocoder, "_geocode_photon", return_value=(34.05, -118.25)):
        lat, lng = geocode("1600 Pennsylvania Ave, Washington, DC")
        assert (lat, lng) == (34.05, -118.25)
