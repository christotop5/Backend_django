"""Simulated payments — no real Mobile Money or card charges."""

from __future__ import annotations

import secrets

from django.utils import timezone

from accounts.exceptions import InsufficientFunds, NotFound
from accounts.models import User, UserProfile
from payments.models import PaymentTransaction

SIMULATION_NOTE = 'Simulation VORA — aucun argent réel débité.'


def _confirm(tx: PaymentTransaction) -> PaymentTransaction:
    tx.status = PaymentTransaction.Status.CONFIRMED
    tx.provider_ref = tx.provider_ref or f'SIM-{secrets.token_hex(4).upper()}'
    tx.confirmed_at = timezone.now()
    tx.metadata['simulation'] = True
    tx.metadata['note'] = SIMULATION_NOTE
    tx.save()
    return tx


def _credit_driver_wallet(ride_id: str, amount: int) -> None:
    if not ride_id:
        return
    from rides.models import Ride

    ride = Ride.objects.filter(ride_id=ride_id).select_related('driver').first()
    if ride and ride.driver_id:
        profile, _ = UserProfile.objects.get_or_create(user=ride.driver)
        profile.wallet_balance_fcfa += amount
        profile.save(update_fields=['wallet_balance_fcfa', 'updated_at'])


def initiate_mobile_payment(
    user: User,
    provider: str,
    amount_fcfa: int,
    phone_number: str,
    ride_id: str = '',
    description: str = '',
) -> PaymentTransaction:
    prefix = 'tx_momo' if provider == PaymentTransaction.Provider.MTN_MOMO else 'tx_om'
    tx = PaymentTransaction.objects.create(
        transaction_id=PaymentTransaction.generate_id(prefix),
        user=user,
        ride_id=ride_id or '',
        amount_fcfa=amount_fcfa,
        provider=provider,
        phone_number=phone_number,
        description=description or SIMULATION_NOTE,
        provider_ref=f'SIM-{secrets.token_hex(4).upper()}',
    )
    _confirm(tx)
    _credit_driver_wallet(ride_id, amount_fcfa)
    return tx


def pay_with_wallet(user: User, amount_fcfa: int, ride_id: str = '', description: str = '') -> PaymentTransaction:
    profile, _ = UserProfile.objects.get_or_create(user=user)
    if profile.wallet_balance_fcfa < amount_fcfa:
        raise InsufficientFunds('Solde portefeuille insuffisant.')
    profile.wallet_balance_fcfa -= amount_fcfa
    profile.save(update_fields=['wallet_balance_fcfa', 'updated_at'])
    tx = PaymentTransaction.objects.create(
        transaction_id=PaymentTransaction.generate_id('pay_wallet'),
        user=user,
        ride_id=ride_id or '',
        amount_fcfa=amount_fcfa,
        provider=PaymentTransaction.Provider.WALLET,
        description=description or 'Paiement portefeuille VORA (simulation)',
    )
    _confirm(tx)
    _credit_driver_wallet(ride_id, amount_fcfa)
    return tx


def confirm_cash_payment(
    user: User,
    amount_fcfa: int,
    ride_id: str = '',
    confirmed_by_driver: bool = True,
) -> PaymentTransaction:
    tx = PaymentTransaction.objects.create(
        transaction_id=PaymentTransaction.generate_id('pay_cash'),
        user=user,
        ride_id=ride_id or '',
        amount_fcfa=amount_fcfa,
        provider=PaymentTransaction.Provider.CASH,
        description='Paiement espèces confirmé (simulation)',
        metadata={'confirmed_by_driver': confirmed_by_driver},
    )
    _confirm(tx)
    _credit_driver_wallet(ride_id, amount_fcfa)
    return tx


def get_payment_status(transaction_id: str, user: User | None = None) -> PaymentTransaction:
    qs = PaymentTransaction.objects.filter(transaction_id=transaction_id)
    if user:
        qs = qs.filter(user=user)
    tx = qs.first()
    if tx is None:
        raise NotFound('Transaction introuvable.')
    return tx


def simulate_webhook_confirm(provider_ref: str) -> PaymentTransaction | None:
    tx = PaymentTransaction.objects.filter(provider_ref=provider_ref).first()
    if tx is None:
        return None
    return _confirm(tx)


def payment_to_dict(tx: PaymentTransaction) -> dict:
    return {
        'transaction_id': tx.transaction_id,
        'amount_fcfa': tx.amount_fcfa,
        'provider': tx.provider,
        'phone_number': tx.phone_number,
        'ride_id': tx.ride_id or None,
        'status': tx.status,
        'provider_ref': tx.provider_ref,
        'simulation': True,
        'message': SIMULATION_NOTE,
        'confirmed_at': tx.confirmed_at.isoformat() if tx.confirmed_at else None,
    }
