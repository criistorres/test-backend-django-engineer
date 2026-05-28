from rest_framework import serializers


class LocationSerializer(serializers.Serializer):
    address = serializers.CharField()
    lat = serializers.FloatField()
    lng = serializers.FloatField()


class FuelStopSerializer(serializers.Serializer):
    name = serializers.CharField()
    address = serializers.CharField()
    city = serializers.CharField()
    state = serializers.CharField()
    lat = serializers.FloatField()
    lng = serializers.FloatField()
    price_per_gallon = serializers.FloatField()
    gallons = serializers.FloatField()
    cost = serializers.FloatField()
    miles_from_start = serializers.FloatField()


class RouteResponseSerializer(serializers.Serializer):
    start = LocationSerializer()
    finish = LocationSerializer()
    total_distance_miles = serializers.FloatField()
    total_gallons = serializers.FloatField()
    total_cost_usd = serializers.FloatField()
    route_polyline = serializers.CharField()
    view_url = serializers.CharField()
    view_url_osrm = serializers.CharField()
    fuel_stops = FuelStopSerializer(many=True)
