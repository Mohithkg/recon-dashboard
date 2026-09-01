"""Shared fixtures for reconciliation tests."""

import pytest

from app.reconcile import OrderData, PaymentData


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_order(order_id: str, net_amount: float, currency: str = "USD", status: str = "completed") -> OrderData:
    return OrderData(
        order_id=order_id,
        net_amount=net_amount,
        currency=currency,
        status=status,
    )


def make_payment(
    transaction_ref: str,
    order_reference,
    amount: float,
    fee: float = 0.0,
    net_settled: float | None = None,
    type: str = "charge",
    status: str = "completed",
) -> PaymentData:
    if net_settled is None:
        net_settled = round(amount - fee, 2)
    return PaymentData(
        transaction_ref=transaction_ref,
        order_reference=order_reference,
        amount=amount,
        fee=fee,
        net_settled=net_settled,
        type=type,
        status=status,
    )
