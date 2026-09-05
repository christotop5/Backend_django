from django.db import models

from accounts.models import User


class Client(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        related_name='client_profile',
        db_column='user_id',
        blank=True,
        null=True,
    )
    company_name = models.CharField(max_length=150, blank=True, null=True)
    contact_name = models.CharField(max_length=150)
    email = models.EmailField(max_length=191)
    phone = models.CharField(max_length=30)
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, default='Douala')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'clients'

    def __str__(self):
        return self.contact_name


class Vehicle(models.Model):
    id = models.AutoField(primary_key=True)

    class Status(models.TextChoices):
        AVAILABLE = 'AVAILABLE', 'Available'
        IN_TRANSIT = 'IN_TRANSIT', 'In transit'
        MAINTENANCE = 'MAINTENANCE', 'Maintenance'

    registration_number = models.CharField(max_length=30, unique=True)
    model = models.CharField(max_length=100)
    capacity_kg = models.DecimalField(max_digits=8, decimal_places=2)
    volume_m3 = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.AVAILABLE,
    )
    assigned_driver = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        related_name='assigned_vehicle',
        db_column='assigned_driver_id',
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'vehicles'

    def __str__(self):
        return self.registration_number


class Route(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        OPTIMIZED = 'OPTIMIZED', 'Optimized'
        IN_PROGRESS = 'IN_PROGRESS', 'In progress'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    driver = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='routes',
        db_column='driver_id',
    )
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.PROTECT,
        related_name='routes',
        db_column='vehicle_id',
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    optimized_geometry = models.JSONField(blank=True, null=True)
    total_distance_km = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    estimated_duration_min = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'routes'


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        ASSIGNED = 'ASSIGNED', 'Assigned'
        IN_TRANSIT = 'IN_TRANSIT', 'In transit'
        DELIVERED = 'DELIVERED', 'Delivered'
        FAILED = 'FAILED', 'Failed'

    tracking_number = models.CharField(max_length=64, unique=True)
    client = models.ForeignKey(
        Client,
        on_delete=models.PROTECT,
        related_name='orders',
        db_column='client_id',
    )
    route = models.ForeignKey(
        Route,
        on_delete=models.SET_NULL,
        related_name='orders',
        db_column='route_id',
        blank=True,
        null=True,
    )
    delivery_address = models.TextField()
    latitude = models.DecimalField(max_digits=10, decimal_places=8, blank=True, null=True)
    longitude = models.DecimalField(max_digits=11, decimal_places=8, blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    amount_to_collect = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'orders'

    def __str__(self):
        return self.tracking_number
