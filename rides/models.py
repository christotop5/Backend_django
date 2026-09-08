import secrets

from django.db import models

from accounts.models import User


class Ride(models.Model):
    class Status(models.TextChoices):
        PENDING_APPROVAL = 'pending_approval', 'Pending driver approval'
        APPROVED = 'approved', 'Driver approved'
        PASSENGER_ARRIVED = 'passenger_arrived', 'Passenger at pickup'
        IN_TRIP = 'in_trip', 'In trip'
        AWAITING_PAYMENT = 'awaiting_payment', 'Awaiting payment'
        COMPLETED = 'completed', 'Completed'
        REJECTED = 'rejected', 'Rejected'
        CANCELLED = 'cancelled', 'Cancelled'
        # Legacy (kept for old rows)
        SEARCHING = 'searching', 'Searching'
        MATCHED = 'matched', 'Matched'
        EN_ROUTE = 'en_route', 'En route'

    ride_id = models.CharField(max_length=32, unique=True)
    passenger = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='rides_as_passenger',
        db_column='passenger_id',
    )
    driver = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rides_as_driver',
        db_column='driver_id',
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING_APPROVAL,
    )
    pickup_carrefour_id = models.IntegerField()
    pickup_name = models.CharField(max_length=150)
    destination_carrefour_id = models.IntegerField()
    destination_name = models.CharField(max_length=150)
    ride_type = models.CharField(max_length=20, default='shared')
    seats_count = models.PositiveSmallIntegerField(default=1)
    payment_method = models.CharField(max_length=20, default='cash')
    passenger_notes = models.TextField(blank=True, default='')
    fare_fcfa = models.PositiveIntegerField(default=500)
    rating = models.PositiveSmallIntegerField(null=True, blank=True)
    rating_comment = models.TextField(blank=True, default='')
    tip_fcfa = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'rides'

    @classmethod
    def generate_id(cls) -> str:
        return f'rd_{secrets.token_hex(4)}'
