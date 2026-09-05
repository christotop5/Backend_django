from django.contrib.gis.db import models

from accounts.models import User


class Zone(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=255, blank=True, null=True)
    boundary = models.PolygonField(srid=4326, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'zones'

    def __str__(self):
        return self.name


class Carrefour(models.Model):
    id = models.AutoField(primary_key=True)
    zone = models.ForeignKey(
        Zone,
        on_delete=models.SET_NULL,
        related_name='carrefours',
        db_column='zone_id',
        blank=True,
        null=True,
    )
    name = models.CharField(max_length=150)
    location = models.PointField(srid=4326)
    is_pickup_point = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'carrefours'

    def __str__(self):
        return self.name


class DriverTrajectory(models.Model):
    driver = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='trajectories',
        db_column='driver_id',
    )
    name = models.CharField(max_length=150, blank=True, null=True)
    geometry = models.LineStringField(srid=4326)
    tolerance_meters = models.PositiveIntegerField(default=500)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'driver_trajectories'


class DriverLocation(models.Model):
    driver = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='locations',
        db_column='driver_id',
    )
    location = models.PointField(srid=4326)
    speed = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    heading = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    recorded_at = models.DateTimeField()

    class Meta:
        db_table = 'driver_locations'
        indexes = [
            models.Index(fields=['driver', '-recorded_at']),
        ]


class CongestionSnapshot(models.Model):
    class CongestionLevel(models.TextChoices):
        LOW = 'low', 'Low'
        MEDIUM = 'medium', 'Medium'
        HIGH = 'high', 'High'

    zone = models.ForeignKey(
        Zone,
        on_delete=models.CASCADE,
        related_name='congestion_snapshots',
        db_column='zone_id',
    )
    congestion_level = models.CharField(max_length=10, choices=CongestionLevel.choices)
    source = models.CharField(max_length=50, blank=True, null=True)
    recorded_at = models.DateTimeField()

    class Meta:
        db_table = 'congestion_snapshots'
        indexes = [
            models.Index(fields=['zone', '-recorded_at']),
        ]
