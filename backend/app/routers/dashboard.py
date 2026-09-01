"""Dashboard endpoints.

Provides summary metrics, breakdown by discrepancy type, and a paginated
list of individual discrepancy rows.  All data is scoped to the
authenticated user.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user
from app.database import get_db
from app.models import User, Order, Payment, Discrepancy

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------


@router.get("/summary")
async def dashboard_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return high-level reconciliation metrics for the current user.

    - ``total_orders``: number of orders uploaded
    - ``total_payments``: number of payments uploaded
    - ``total_value_reconciled``: sum of net_amount for orders with **no**
      discrepancy (fully matched)
    - ``total_value_in_dispute``: sum of expected amounts for discrepancies
      tied to an order
    - ``total_money_at_risk``: sum of absolute differences / amounts at risk
      across all discrepancies
    """
    user_id = current_user.id

    # --- Counts -----------------------------------------------------------
    orders_count = await db.scalar(
        select(func.count()).where(Order.user_id == user_id)
    )
    payments_count = await db.scalar(
        select(func.count()).where(Payment.user_id == user_id)
    )

    # --- Total order value ------------------------------------------------
    total_order_value = await db.scalar(
        select(func.coalesce(func.sum(Order.net_amount), 0)).where(
            Order.user_id == user_id
        )
    )

    # --- Discrepancy aggregates -------------------------------------------
    # Sum of expected_amount for order-related discrepancies (used to
    # derive reconciled value).
    value_in_dispute = await db.scalar(
        select(func.coalesce(func.sum(Discrepancy.expected_amount), 0)).where(
            and_(
                Discrepancy.user_id == user_id,
                Discrepancy.order_id != "",
            )
        )
    )

    # Money at risk: ABS(difference) when present, else ABS(actual_amount)
    # (covers MISSING_ORDER and REFUND_UNMATCHED where difference is NULL).
    money_at_risk = await db.scalar(
        select(
            func.coalesce(
                func.sum(
                    func.abs(
                        func.coalesce(
                            Discrepancy.difference,
                            Discrepancy.actual_amount,
                            0,
                        )
                    )
                ),
                0,
            )
        ).where(Discrepancy.user_id == user_id)
    )

    total_value_reconciled = round(float(total_order_value) - float(value_in_dispute), 2)

    return {
        "total_orders": orders_count,
        "total_payments": payments_count,
        "total_value_reconciled": total_value_reconciled,
        "total_value_in_dispute": round(float(value_in_dispute), 2),
        "total_money_at_risk": round(float(money_at_risk), 2),
    }


# ---------------------------------------------------------------------------
# Breakdown
# ---------------------------------------------------------------------------


@router.get("/breakdown")
async def dashboard_breakdown(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return discrepancy counts and amounts-at-risk grouped by type.

    Each item contains the discrepancy type, how many occurrences exist,
    and the total money at risk for that type.
    """
    user_id = current_user.id

    rows = await db.execute(
        select(
            Discrepancy.discrepancy_type,
            func.count().label("count"),
            func.coalesce(
                func.sum(
                    func.abs(
                        func.coalesce(
                            Discrepancy.difference,
                            Discrepancy.actual_amount,
                            0,
                        )
                    )
                ),
                0,
            ).label("amount_at_risk"),
        )
        .where(Discrepancy.user_id == user_id)
        .group_by(Discrepancy.discrepancy_type)
    )

    breakdown = []
    for row in rows:
        breakdown.append(
            {
                "type": row.discrepancy_type,
                "count": row.count,
                "amount_at_risk": round(float(row.amount_at_risk), 2),
            }
        )

    return {"breakdown": breakdown}


# ---------------------------------------------------------------------------
# Discrepancy list (paginated, filterable, searchable)
# ---------------------------------------------------------------------------


@router.get("/discrepancies")
async def dashboard_discrepancies(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(25, ge=1, le=100, description="Items per page"),
    type: Optional[str] = Query(None, description="Filter by discrepancy type"),
    date_from: Optional[datetime] = Query(
        None, description="Filter by created_at >= date_from (ISO 8601)"
    ),
    date_to: Optional[datetime] = Query(
        None, description="Filter by created_at <= date_to (ISO 8601)"
    ),
    amount_min: Optional[float] = Query(
        None, description="Filter by |difference| >= amount_min"
    ),
    amount_max: Optional[float] = Query(
        None, description="Filter by |difference| <= amount_max"
    ),
    search: Optional[str] = Query(
        None, description="Search by order_id or payment_ref (case-insensitive)"
    ),
):
    """Return a paginated list of discrepancy rows for the current user.

    Supports filtering by type, date range, amount range, and free-text
    search across order_id / payment_ref.
    """
    user_id = current_user.id

    # --- Build base filter ------------------------------------------------
    filters = [Discrepancy.user_id == user_id]

    if type:
        filters.append(Discrepancy.discrepancy_type == type)
    if date_from:
        filters.append(Discrepancy.created_at >= date_from)
    if date_to:
        filters.append(Discrepancy.created_at <= date_to)
    if search:
        term = f"%{search}%"
        filters.append(
            or_(
                Discrepancy.order_id.ilike(term),
                Discrepancy.payment_ref.ilike(term),
            )
        )

    # Amount range uses ABS(difference) when difference IS NOT NULL,
    # otherwise ABS(actual_amount).
    amount_expr = func.coalesce(
        func.abs(Discrepancy.difference),
        func.abs(Discrepancy.actual_amount),
        0,
    )
    if amount_min is not None:
        filters.append(amount_expr >= amount_min)
    if amount_max is not None:
        filters.append(amount_expr <= amount_max)

    where_clause = and_(*filters)

    # --- Total count ------------------------------------------------------
    total = await db.scalar(select(func.count()).where(where_clause))

    # --- Paginated rows ---------------------------------------------------
    offset = (page - 1) * page_size
    rows = await db.execute(
        select(Discrepancy)
        .where(where_clause)
        .order_by(Discrepancy.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    items = rows.scalars().all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": d.id,
                "order_id": d.order_id,
                "payment_ref": d.payment_ref,
                "type": d.discrepancy_type,
                "expected_amount": float(d.expected_amount) if d.expected_amount is not None else None,
                "actual_amount": float(d.actual_amount) if d.actual_amount is not None else None,
                "difference": float(d.difference) if d.difference is not None else None,
                "status": d.status,
                "notes": d.notes,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d in items
        ],
    }
