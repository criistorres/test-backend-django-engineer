from django.db import models


class FuelStation(models.Model):
    opis_id = models.IntegerField(db_index=True)
    name = models.CharField(max_length=200)
    address = models.CharField(max_length=300)
    city = models.CharField(max_length=120)
    state = models.CharField(max_length=2, db_index=True)
    lat = models.FloatField()
    lng = models.FloatField()
    price = models.DecimalField(max_digits=8, decimal_places=4)

    class Meta:
        indexes = [
            models.Index(fields=["lat", "lng"]),
            models.Index(fields=["state", "city"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.city}, {self.state}) ${self.price}"
