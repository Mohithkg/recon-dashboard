"""Reconciliation endpoint.

Runs the deterministic reconciliation engine against the authenticated
user's orders and payments, persists the results to the discrepancies
table, and returns a summary.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user
from app.database import get_db
from app.models import User, Order, Payment, Discrepancy
from app.reconcile import (
    reconcile,
    OrderData,
    PaymentData,
    DiscrepancyType,
)

router = APIRouter(prefix="/reconcile", tags=["reconcile"])


@router.post("/run")
async def run_reconciliation(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Run reconciliation for the current user and persist discrepancies.

    Returns a summary with counts per discrepancy type and the full list
    of discrepancies found.
    """
    # -- Fetch user's orders and payments from the database ---------------
    orders_result = await db.execute(
        select(Order).where(Order.user_id == current_user.id)
    )
    orders = orders_result.scalars().all()

    payments_result = await db.execute(
        select(Payment).where(Payment.user_id == current_user.id)
    )
    payments = payments_result.scalars().all()

    # -- Map ORM objects to pure data carriers ----------------------------
    order_data = [
        OrderData(
            order_id=o.order_id,
            net_amount=float(o.net_amount),
            currency=o.currency,
            status=o.status,
        )
        for o in orders
    ]

    payment_data = [
        PaymentData(
            transaction_ref=p.transaction_ref,
            order_reference=p.order_reference,
            amount=float(p.amount),
            fee=float(p.fee),
            net_settled=float(p.net_settled),
            type=p.type,
            status=p.status,
        )
        for p in payments
    ]

    # -- Run the pure reconciliation engine -------------------------------
    discrepancies = reconcile(order_data, payment_data)

    # -- Persist: clear previous results, insert new ones -----------------
    await db.execute(
        delete(Discrepancy).where(Discrepancy.user_id == current_user.id)
    )

    for d in discrepancies:
        record = Discrepancy(
            user_id=current_user.id,
            order_id=d.order_id,
            payment_ref=d.payment_ref,
            discrepancy_type=d.discrepancy_type.value,
            expected_amount=d.expected_amount,
            actual_amount=d.actual_amount,
            difference=d.difference,
            notes=d.notes,
        )
        db.add(record)

    await db.commit()

    # -- Build summary -----------------------------------------------------
    by_type: dict[str, int] = {}
    for d in discrepancies:
        key = d.discrepancy_type.value
        by_type[key] = by_type.get(key, 0) + 1

    return {
        "orders_count": len(orders),
        "payments_count": len(payments),
        "discrepancies_found": len(discrepancies),
        "by_type": by_type,
        "discrepancies": [
            {
                "type": d.discrepancy_type.value,
                "order_id": d.order_id,
                "payment_ref": d.payment_ref,
                "expected_amount": d.expected_amount,
                "actual_amount": d.actual_amount,
                "difference": d.difference,
                "notes": d.notes,
            }
            for d in discrepancies
        ],
    }
