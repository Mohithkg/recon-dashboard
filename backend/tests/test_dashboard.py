"""Unit tests for the dashboard endpoints.

Tests the summary, breakdown, and paginated discrepancy list endpoints
using mocked async database sessions.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

from app.routers import dashboard


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_mock_discrepancy(
    id=1,
    order_id="ORD-001",
    payment_ref="TXN-001",
    discrepancy_type="missing_payment",
    expected_amount=100.0,
    actual_amount=None,
    difference=100.0,
    status="open",
    notes="Test",
    created_at=None,
):
    """Create a mock Discrepancy ORM object."""
    d = MagicMock()
    d.id = id
    d.order_id = order_id
    d.payment_ref = payment_ref
    d.discrepancy_type = discrepancy_type
    d.expected_amount = expected_amount
    d.actual_amount = actual_amount
    d.difference = difference
    d.status = status
    d.notes = notes
    d.created_at = created_at or datetime(2026, 1, 15, tzinfo=timezone.utc)
    return d


def make_mock_user(id=1, email="test@example.com"):
    """Create a mock User ORM object."""
    u = MagicMock()
    u.id = id
    u.email = email
    return u


def make_mock_db(scalar_results=None, execute_results=None):
    """Create a mock async database session.

    scalar_results: list of values to return from db.scalar() calls
    execute_results: list of values to return from db.execute() calls
    """
    db = AsyncMock()

    scalar_queue = list(scalar_results or [])
    execute_queue = list(execute_results or [])

    async def mock_scalar(*args, **kwargs):
        if scalar_queue:
            return scalar_queue.pop(0)
        return None

    async def mock_execute(*args, **kwargs):
        if execute_queue:
            result = execute_queue.pop(0)
            return result
        # Return a default mock result
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_result.__iter__ = MagicMock(return_value=iter([]))
        return mock_result

    db.scalar = mock_scalar
    db.execute = mock_execute
    return db


# ---------------------------------------------------------------------------
# Summary tests
# ---------------------------------------------------------------------------


class TestDashboardSummary:
    @pytest.mark.asyncio
    async def test_summary_with_no_data(self):
        """All zeros when user has no orders, payments, or discrepancies."""
        from app.dependencies import get_current_user

        current_user = make_mock_user()
        db = make_mock_db(
            scalar_results=[0, 0, 0, 0.0, 0.0]  # orders, payments, total_value, value_in_dispute, money_at_risk
        )

        result = await dashboard.dashboard_summary(current_user=current_user, db=db)

        assert result["total_orders"] == 0
        assert result["total_payments"] == 0
        assert result["total_value_reconciled"] == 0.0
        assert result["total_value_in_dispute"] == 0.0
        assert result["total_money_at_risk"] == 0.0

    @pytest.mark.asyncio
    async def test_summary_with_reconciled_orders(self):
        """Fully reconciled orders show up in total_value_reconciled."""
        current_user = make_mock_user()
        db = make_mock_db(
            scalar_results=[
                10,     # total_orders
                10,     # total_payments
                1000.0, # total_order_value
                0.0,    # value_in_dispute (no discrepancies)
                0.0,    # money_at_risk
            ]
        )

        result = await dashboard.dashboard_summary(current_user=current_user, db=db)

        assert result["total_orders"] == 10
        assert result["total_payments"] == 10
        assert result["total_value_reconciled"] == 1000.0
        assert result["total_value_in_dispute"] == 0.0
        assert result["total_money_at_risk"] == 0.0

    @pytest.mark.asyncio
    async def test_summary_with_discrepancies(self):
        """Discrepancies reduce reconciled value and increase at-risk."""
        current_user = make_mock_user()
        db = make_mock_db(
            scalar_results=[
                10,     # total_orders
                8,      # total_payments
                1000.0, # total_order_value
                300.0,  # value_in_dispute
                150.0,  # money_at_risk
            ]
        )

        result = await dashboard.dashboard_summary(current_user=current_user, db=db)

        assert result["total_orders"] == 10
        assert result["total_payments"] == 8
        assert result["total_value_reconciled"] == 700.0  # 1000 - 300
        assert result["total_value_in_dispute"] == 300.0
        assert result["total_money_at_risk"] == 150.0


# ---------------------------------------------------------------------------
# Breakdown tests
# ---------------------------------------------------------------------------


class TestDashboardBreakdown:
    @pytest.mark.asyncio
    async def test_breakdown_with_no_discrepancies(self):
        """Empty breakdown when no discrepancies exist."""
        current_user = make_mock_user()

        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(return_value=iter([]))

        db = make_mock_db(execute_results=[mock_result])

        result = await dashboard.dashboard_breakdown(current_user=current_user, db=db)

        assert result["breakdown"] == []

    @pytest.mark.asyncio
    async def test_breakdown_grouped_by_type(self):
        """Breakdown groups discrepancies by type with counts and amounts."""
        current_user = make_mock_user()

        row1 = MagicMock()
        row1.discrepancy_type = "missing_payment"
        row1.count = 5
        row1.amount_at_risk = 500.0

        row2 = MagicMock()
        row2.discrepancy_type = "amount_mismatch"
        row2.count = 3
        row2.amount_at_risk = 75.5

        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(return_value=iter([row1, row2]))

        db = make_mock_db(execute_results=[mock_result])

        result = await dashboard.dashboard_breakdown(current_user=current_user, db=db)

        assert len(result["breakdown"]) == 2
        assert result["breakdown"][0]["type"] == "missing_payment"
        assert result["breakdown"][0]["count"] == 5
        assert result["breakdown"][0]["amount_at_risk"] == 500.0
        assert result["breakdown"][1]["type"] == "amount_mismatch"
        assert result["breakdown"][1]["count"] == 3
        assert result["breakdown"][1]["amount_at_risk"] == 75.5


# ---------------------------------------------------------------------------
# Discrepancy list tests
# ---------------------------------------------------------------------------


class TestDashboardDiscrepancies:
    @pytest.mark.asyncio
    async def test_discrepancies_empty(self):
        """Empty result when no discrepancies match."""
        current_user = make_mock_user()

        count_result = 0
        items_result = MagicMock()
        items_result.scalars.return_value.all.return_value = []

        db = make_mock_db(
            scalar_results=[count_result],
            execute_results=[items_result],
        )

        result = await dashboard.dashboard_discrepancies(
            current_user=current_user, db=db,
            page=1, page_size=25,
        )

        assert result["total"] == 0
        assert result["page"] == 1
        assert result["page_size"] == 25
        assert result["items"] == []

    @pytest.mark.asyncio
    async def test_discrepancies_paginated(self):
        """Returns paginated items with correct metadata."""
        current_user = make_mock_user()

        disc1 = make_mock_discrepancy(id=1, order_id="ORD-001", difference=100.0)
        disc2 = make_mock_discrepancy(id=2, order_id="ORD-002", difference=50.0)

        count_result = 50
        items_result = MagicMock()
        items_result.scalars.return_value.all.return_value = [disc1, disc2]

        db = make_mock_db(
            scalar_results=[count_result],
            execute_results=[items_result],
        )

        result = await dashboard.dashboard_discrepancies(
            current_user=current_user, db=db,
            page=2, page_size=25,
        )

        assert result["total"] == 50
        assert result["page"] == 2
        assert result["page_size"] == 25
        assert len(result["items"]) == 2
        assert result["items"][0]["order_id"] == "ORD-001"
        assert result["items"][0]["difference"] == 100.0
        assert result["items"][1]["order_id"] == "ORD-002"

    @pytest.mark.asyncio
    async def test_discrepancies_item_format(self):
        """Each item has the expected fields and types."""
        current_user = make_mock_user()

        disc = make_mock_discrepancy(
            id=42,
            order_id="ORD-999",
            payment_ref="TXN-123",
            discrepancy_type="amount_mismatch",
            expected_amount=200.0,
            actual_amount=195.0,
            difference=-5.0,
            status="open",
            notes="Test note",
            created_at=datetime(2026, 3, 15, 12, 0, 0, tzinfo=timezone.utc),
        )

        count_result = 1
        items_result = MagicMock()
        items_result.scalars.return_value.all.return_value = [disc]

        db = make_mock_db(
            scalar_results=[count_result],
            execute_results=[items_result],
        )

        result = await dashboard.dashboard_discrepancies(
            current_user=current_user, db=db,
            page=1, page_size=25,
        )

        assert len(result["items"]) == 1
        item = result["items"][0]
        assert item["id"] == 42
        assert item["order_id"] == "ORD-999"
        assert item["payment_ref"] == "TXN-123"
        assert item["type"] == "amount_mismatch"
        assert item["expected_amount"] == 200.0
        assert item["actual_amount"] == 195.0
        assert item["difference"] == -5.0
        assert item["status"] == "open"
        assert item["notes"] == "Test note"
        assert item["created_at"] == "2026-03-15T12:00:00+00:00"

    @pytest.mark.asyncio
    async def test_discrepancies_null_amounts(self):
        """Handles NULL expected/actual/difference gracefully."""
        current_user = make_mock_user()

        disc = make_mock_discrepancy(
            id=1,
            expected_amount=None,
            actual_amount=None,
            difference=None,
        )

        count_result = 1
        items_result = MagicMock()
        items_result.scalars.return_value.all.return_value = [disc]

        db = make_mock_db(
            scalar_results=[count_result],
            execute_results=[items_result],
        )

        result = await dashboard.dashboard_discrepancies(
            current_user=current_user, db=db,
            page=1, page_size=25,
        )

        item = result["items"][0]
        assert item["expected_amount"] is None
        assert item["actual_amount"] is None
        assert item["difference"] is None
