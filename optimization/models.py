from django.contrib.gis.db import models

from accounts.models import User


class DemandCache(models.Model):
    reservation_id = models.CharField(max_length=64, unique=True)
    pickup_location = models.PointField(srid=4326)
    destination_location = models.PointField(srid=4326)
    proposed_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=30)
    fetched_at = models.DateTimeField()

    class Meta:
        db_table = 'demand_cache'


class OptimizationRun(models.Model):
    driver = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='optimization_runs',
        db_column='driver_id',
    )
    input_snapshot = models.JSONField()
    output_turn = models.JSONField()
    expected_revenue = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'optimization_runs'
