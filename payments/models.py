from django.db import models

from core.models import Client, Order


class PaymentLink(models.Model):
    id = models.AutoField(primary_key=True)

    class CanalEnvoi(models.TextChoices):
        MAIL = 'mail', 'Mail'
        SMS = 'sms', 'SMS'

    class MoyenPaiement(models.TextChoices):
        MTN = 'mtn', 'MTN'
        ORANGE = 'orange', 'Orange'
        CARTE = 'carte', 'Carte'
        AUTRE = 'autre', 'Autre'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PAID = 'paid', 'Paid'
        EXPIRED = 'expired', 'Expired'
        FAILED = 'failed', 'Failed'

    token = models.CharField(max_length=255, unique=True, db_index=True)
    client = models.ForeignKey(
        Client,
        on_delete=models.PROTECT,
        related_name='payment_links',
        db_column='client_id',
    )
    order = models.ForeignKey(
        Order,
        on_delete=models.SET_NULL,
        related_name='payment_links',
        db_column='order_id',
        blank=True,
        null=True,
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    devise = models.CharField(max_length=10, default='XAF')
    langue = models.CharField(max_length=5, default='fr')
    description = models.TextField(blank=True, null=True)
    canal_envoi = models.CharField(
        max_length=10,
        choices=CanalEnvoi.choices,
        blank=True,
        null=True,
    )
    moyen_paiement = models.CharField(
        max_length=15,
        choices=MoyenPaiement.choices,
        blank=True,
        null=True,
    )
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.PENDING,
    )
    soleaspay_ref = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'payment_links'

    def __str__(self):
        return f'{self.token} ({self.amount} {self.devise})'
