from django.contrib.gis.db import models

from accounts.models import User


class Notification(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications',
        db_column='user_id',
    )
    type = models.CharField(max_length=50)
    title = models.CharField(max_length=150)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notifications'
        indexes = [
            models.Index(fields=['user', '-created_at']),
        ]


class HistoriqueActivite(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name='activity_history',
        db_column='user_id',
        blank=True,
        null=True,
    )
    driver = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name='driver_activity_history',
        db_column='driver_id',
        blank=True,
        null=True,
    )
    event_type = models.CharField(max_length=50)
    reference_id = models.CharField(max_length=64, blank=True, null=True)
    metadata = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'historique_activite'
        indexes = [
            models.Index(fields=['-created_at']),
        ]


class Signalement(models.Model):
    class Type(models.TextChoices):
        SOS = 'sos', 'SOS'
        COMPLAINT = 'complaint', 'Complaint'
        ANOMALY = 'anomaly', 'Anomaly'

    class Status(models.TextChoices):
        OPEN = 'open', 'Open'
        INVESTIGATING = 'investigating', 'Investigating'
        RESOLVED = 'resolved', 'Resolved'
        DISMISSED = 'dismissed', 'Dismissed'

    reporter = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reports_filed',
        db_column='reporter_id',
    )
    reported_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name='reports_received',
        db_column='reported_user_id',
        blank=True,
        null=True,
    )
    reservation_id = models.CharField(max_length=64, blank=True, null=True)
    type = models.CharField(max_length=20, choices=Type.choices)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
    )
    location = models.PointField(srid=4326, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'signalements'


class StatistiqueJournaliere(models.Model):
    date = models.DateField(unique=True)
    total_rides = models.PositiveIntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    active_drivers = models.PositiveIntegerField(default=0)
    active_zones = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'statistiques_journalieres'

    def __str__(self):
        return str(self.date)
