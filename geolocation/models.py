from django.contrib.gis.db import models

from accounts.models import User


class Zone(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    city = models.CharField(max_length=50, blank=True, default='')
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
    city = models.CharField(max_length=50, blank=True, default='')
    location = models.PointField(srid=4326)
    is_pickup_point = models.BooleanField(default=True)
    is_major_intersection = models.BooleanField(default=False)
    typical_waiting_passengers = models.PositiveSmallIntegerField(default=0)
    standard_fare_to_centre_fcfa = models.PositiveIntegerField(default=400)
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


class CorridorLine(models.Model):
    external_id = models.CharField(max_length=10, unique=True)
    code = models.CharField(max_length=32, unique=True)
    city = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    start_point = models.CharField(max_length=150)
    end_point = models.CharField(max_length=150)
    stops = models.JSONField(default=list)
    standard_fare_fcfa = models.PositiveIntegerField(default=400)
    distance_km = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    estimated_duration_min = models.PositiveSmallIntegerField(default=15)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'corridor_lines'

    def __str__(self):
        return self.name
