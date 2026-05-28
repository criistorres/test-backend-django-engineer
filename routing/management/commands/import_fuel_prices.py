import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from routing.models import FuelStation


class Command(BaseCommand):
    help = "Loads the OPIS fuel-price CSV into the database, geocoding by (city, state) against the local US cities dataset."

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv",
            default=str(settings.BASE_DIR / "data" / "fuel-prices-for-be-assessment.csv"),
            help="Path to the fuel-price CSV (default: data/fuel-prices-for-be-assessment.csv).",
        )
        parser.add_argument(
            "--cities",
            default=str(settings.BASE_DIR / "data" / "us_cities.csv"),
            help="Path to the US cities dataset (default: data/us_cities.csv).",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=1000,
            help="bulk_create batch size.",
        )

    def handle(self, *args, **options):
        cities_path = Path(options["cities"])
        fuel_path = Path(options["csv"])
        batch_size = options["batch_size"]

        cities = self._load_cities(cities_path)
        self.stdout.write(self.style.SUCCESS(f"US cities dataset loaded: {len(cities)} cities."))

        with transaction.atomic():
            FuelStation.objects.all().delete()
            total, matched, missing, invalid = self._import(fuel_path, cities, batch_size)

        self.stdout.write(self.style.SUCCESS(f"CSV rows read: {total}"))
        self.stdout.write(self.style.SUCCESS(f"Geocoded and saved: {matched}"))
        self.stdout.write(self.style.WARNING(f"Skipped (city not found): {missing}"))
        self.stdout.write(self.style.WARNING(f"Skipped (invalid price): {invalid}"))

    @staticmethod
    def _load_cities(path: Path) -> dict[tuple[str, str], tuple[float, float]]:
        cities: dict[tuple[str, str], tuple[float, float]] = {}
        with path.open(encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = (row["CITY"].strip().upper(), row["STATE_CODE"].strip().upper())
                if key not in cities:
                    cities[key] = (float(row["LATITUDE"]), float(row["LONGITUDE"]))
        return cities

    @staticmethod
    def _import(
        fuel_path: Path,
        cities: dict[tuple[str, str], tuple[float, float]],
        batch_size: int,
    ) -> tuple[int, int, int, int]:
        total = matched = missing = invalid = 0
        buffer: list[FuelStation] = []

        with fuel_path.open(encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                total += 1
                key = (row["City"].strip().upper(), row["State"].strip().upper())
                coords = cities.get(key)
                if coords is None:
                    missing += 1
                    continue

                try:
                    price = Decimal(row["Retail Price"]).quantize(Decimal("0.0001"))
                except (InvalidOperation, KeyError):
                    invalid += 1
                    continue

                buffer.append(
                    FuelStation(
                        opis_id=int(row["OPIS Truckstop ID"]),
                        name=row["Truckstop Name"].strip()[:200],
                        address=row["Address"].strip()[:300],
                        city=row["City"].strip(),
                        state=row["State"].strip(),
                        lat=coords[0],
                        lng=coords[1],
                        price=price,
                    )
                )
                matched += 1

                if len(buffer) >= batch_size:
                    FuelStation.objects.bulk_create(buffer)
                    buffer.clear()

            if buffer:
                FuelStation.objects.bulk_create(buffer)

        return total, matched, missing, invalid
