"""
Deterministic reconciliation engine.

Matches a user's orders against their payments and classifies every mismatch.
Pure function of its input — same input always produces the same output,
no LLM involved, no side effects, no database access.

Tolerance policy:
    $0.50 or 1% of the order net_amount, whichever is greater.
    This absorbs typical rounding differences (e.g. currency conversion,
    processor rounding to 2 dp) while scaling sensibly with order size.
    A $10 order tolerates $0.50; a $100 order tolerates $1.00.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class DiscrepancyType(str, Enum):
    """Classification of a reconciliation mismatch."""

    MISSING_PAYMENT = "missing_payment"
    MISSING_ORDER = "missing_order"
    AMOUNT_MISMATCH = "amount_mismatch"
    DUPLICATE_PAYMENT = "duplicate_payment"
    REFUND_UNMATCHED = "refund_unmatched"


@dataclass(frozen=True)
class OrderData:
    """Minimal order representation for reconciliation."""

    order_id: str
    net_amount: float
    currency: str
    status: str


@dataclass(frozen=True)
class PaymentData:
    """Minimal payment representation for reconciliation."""

    transaction_ref: str
    order_reference: Optional[str]
    amount: float
    fee: float
    net_settled: float
    type: str
    status: str


@dataclass(frozen=True)
class DiscrepancyResult:
    """A single discrepancy found during reconciliation."""

    discrepancy_type: DiscrepancyType
    order_id: str
    payment_ref: Optional[str]
    expected_amount: Optional[float]
    actual_amount: Optional[float]
    difference: Optional[float]
    notes: str


def tolerance_for(amount: float) -> float:
    """Return the absolute tolerance for a given order amount.

    $0.50 or 1% of |amount|, whichever is greater — rounded to 2 dp.
    """
    return round(max(0.50, abs(amount) * 0.01), 2)


def reconcile(
    orders: list[OrderData],
    payments: list[PaymentData],
) -> list[DiscrepancyResult]:
    """Reconcile orders against payments.

    This is a **pure function**: no side effects, no database access, fully
    deterministic.  Given the same *orders* and *payments* it always returns
    the same list of discrepancies.

    Parameters
    ----------
    orders:
        All orders for a single user.
    payments:
        All payments for a single user.

    Returns
    -------
    list[DiscrepancyResult]
        All discrepancies found, ordered by detection phase.
    """
    discrepancies: list[DiscrepancyResult] = []

    # -- Index orders by order_id ------------------------------------------
    order_map: dict[str, OrderData] = {}
    for o in orders:
        order_map[o.order_id] = o

    # -- Index payments by order_reference ---------------------------------
    payments_by_order: dict[str, list[PaymentData]] = {}
    unmatched_payments: list[PaymentData] = []
    txn_ref_counts: dict[str, int] = {}

    for p in payments:
        txn_ref_counts[p.transaction_ref] = txn_ref_counts.get(p.transaction_ref, 0) + 1

        ref = p.order_reference
        if ref and ref in order_map:
            payments_by_order.setdefault(ref, []).append(p)
        elif ref and ref not in order_map:
            # References an order that does not exist.
            discrepancies.append(
                DiscrepancyResult(
                    discrepancy_type=DiscrepancyType.MISSING_ORDER,
                    order_id=ref,
                    payment_ref=p.transaction_ref,
                    expected_amount=None,
                    actual_amount=p.amount,
                    difference=None,
                    notes=(
                        f"Payment '{p.transaction_ref}' references "
                        f"non-existent order '{ref}'."
                    ),
                )
            )
        else:
            # No order_reference at all.
            unmatched_payments.append(p)

    # -- Duplicate transaction refs ----------------------------------------
    for txn_ref, count in txn_ref_counts.items():
        if count > 1:
            discrepancies.append(
                DiscrepancyResult(
                    discrepancy_type=DiscrepancyType.DUPLICATE_PAYMENT,
                    order_id="",
                    payment_ref=txn_ref,
                    expected_amount=None,
                    actual_amount=None,
                    difference=None,
                    notes=(
                        f"Transaction ref '{txn_ref}' appears {count} times; "
                        f"expected at most 1."
                    ),
                )
            )

    # -- Per-order checks --------------------------------------------------
    for order in orders:
        order_payments = payments_by_order.get(order.order_id, [])

        if not order_payments:
            discrepancies.append(
                DiscrepancyResult(
                    discrepancy_type=DiscrepancyType.MISSING_PAYMENT,
                    order_id=order.order_id,
                    payment_ref=None,
                    expected_amount=order.net_amount,
                    actual_amount=None,
                    difference=order.net_amount,
                    notes=(
                        f"No payments found for order '{order.order_id}' "
                        f"(expected net_amount {order.net_amount})."
                    ),
                )
            )
            continue

        # Sum all payment amounts that reference this order.
        total_paid = round(sum(p.amount for p in order_payments), 2)
        diff = round(total_paid - order.net_amount, 2)
        tol = tolerance_for(order.net_amount)

        if abs(diff) > tol:
            payment_refs = ", ".join(p.transaction_ref for p in order_payments)
            discrepancies.append(
                DiscrepancyResult(
                    discrepancy_type=DiscrepancyType.AMOUNT_MISMATCH,
                    order_id=order.order_id,
                    payment_ref=payment_refs,
                    expected_amount=order.net_amount,
                    actual_amount=total_paid,
                    difference=diff,
                    notes=(
                        f"Payments sum to {total_paid} but order net_amount is "
                        f"{order.net_amount} (diff {diff:+.2f}, "
                        f"tolerance +/-{tol:.2f})."
                    ),
                )
            )

    # -- Unmatched payments: refunds ---------------------------------------
    for p in unmatched_payments:
        if p.amount < 0:
            discrepancies.append(
                DiscrepancyResult(
                    discrepancy_type=DiscrepancyType.REFUND_UNMATCHED,
                    order_id="",
                    payment_ref=p.transaction_ref,
                    expected_amount=None,
                    actual_amount=p.amount,
                    difference=p.amount,
                    notes=(
                        f"Refund payment '{p.transaction_ref}' (amount {p.amount}) "
                        f"has no matching order."
                    ),
                )
            )

    return discrepancies
