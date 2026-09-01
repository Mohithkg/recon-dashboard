"""Unit tests for the deterministic reconciliation engine.

Covers the core matching cases:
  - exact match
  - missing payment
  - missing order
  - amount mismatch within tolerance
  - amount mismatch outside tolerance
  - duplicate payment
  - refund unmatched
  - multiple partial payments summing correctly
  - multiple partial payments summing incorrectly
  - empty inputs
"""

import pytest

from app.reconcile import (
    reconcile,
    DiscrepancyType,
    tolerance_for,
)

from tests.conftest import make_order, make_payment


# ---------------------------------------------------------------------------
# Tolerance tests
# ---------------------------------------------------------------------------


class TestTolerance:
    def test_tolerance_100(self):
        assert tolerance_for(100.0) == 1.0

    def test_tolerance_10(self):
        assert tolerance_for(10.0) == 0.50

    def test_tolerance_50(self):
        assert tolerance_for(50.0) == 0.50

    def test_tolerance_0(self):
        assert tolerance_for(0.0) == 0.50

    def test_tolerance_negative(self):
        assert tolerance_for(-100.0) == 1.0


# ---------------------------------------------------------------------------
# Exact match
# ---------------------------------------------------------------------------


class TestExactMatch:
    def test_single_payment_matches_order(self):
        orders = [make_order("ORD-001", 100.0)]
        payments = [make_payment("TXN-001", "ORD-001", 100.0)]
        assert reconcile(orders, payments) == []

    def test_multiple_exact_matches(self):
        orders = [
            make_order("ORD-001", 100.0),
            make_order("ORD-002", 250.0),
        ]
        payments = [
            make_payment("TXN-001", "ORD-001", 100.0),
            make_payment("TXN-002", "ORD-002", 250.0),
        ]
        assert reconcile(orders, payments) == []


# ---------------------------------------------------------------------------
# Missing payment
# ---------------------------------------------------------------------------


class TestMissingPayment:
    def test_order_with_no_payment(self):
        orders = [make_order("ORD-001", 100.0)]
        result = reconcile(orders, [])
        assert len(result) == 1
        d = result[0]
        assert d.discrepancy_type == DiscrepancyType.MISSING_PAYMENT
        assert d.order_id == "ORD-001"
        assert d.expected_amount == 100.0
        assert d.actual_amount is None
        assert d.difference == 100.0

    def test_one_of_two_orders_missing_payment(self):
        orders = [
            make_order("ORD-001", 100.0),
            make_order("ORD-002", 200.0),
        ]
        payments = [make_payment("TXN-001", "ORD-001", 100.0)]
        result = reconcile(orders, payments)
        assert len(result) == 1
        assert result[0].discrepancy_type == DiscrepancyType.MISSING_PAYMENT
        assert result[0].order_id == "ORD-002"


# ---------------------------------------------------------------------------
# Missing order
# ---------------------------------------------------------------------------


class TestMissingOrder:
    def test_payment_references_nonexistent_order(self):
        orders = [make_order("ORD-001", 100.0)]
        payments = [make_payment("TXN-001", "ORD-999", 100.0)]
        result = reconcile(orders, payments)
        # The payment references a non-existent order AND the real order has
        # no payment, so both discrepancies are legitimately detected.
        types = {d.discrepancy_type for d in result}
        assert DiscrepancyType.MISSING_ORDER in types
        assert DiscrepancyType.MISSING_PAYMENT in types
        missing_order = [d for d in result if d.discrepancy_type == DiscrepancyType.MISSING_ORDER]
        assert len(missing_order) == 1
        assert missing_order[0].order_id == "ORD-999"
        assert missing_order[0].payment_ref == "TXN-001"

    def test_missing_order_and_missing_payment_both_detected(self):
        orders = [make_order("ORD-001", 100.0)]
        payments = [make_payment("TXN-001", "ORD-999", 50.0)]
        result = reconcile(orders, payments)
        types = {d.discrepancy_type for d in result}
        assert DiscrepancyType.MISSING_ORDER in types
        assert DiscrepancyType.MISSING_PAYMENT in types


# ---------------------------------------------------------------------------
# Amount mismatch within tolerance
# ---------------------------------------------------------------------------


class TestAmountMismatchWithinTolerance:
    def test_small_difference_accepted(self):
        # $0.30 diff on $100 order (tolerance is $1.00)
        orders = [make_order("ORD-001", 100.0)]
        payments = [make_payment("TXN-001", "ORD-001", 100.30)]
        assert reconcile(orders, payments) == []

    def test_difference_at_tolerance_boundary(self):
        # Exactly at tolerance ($1.00 on $100 order) — should pass
        orders = [make_order("ORD-001", 100.0)]
        payments = [make_payment("TXN-001", "ORD-001", 101.00)]
        assert reconcile(orders, payments) == []

    def test_negative_difference_within_tolerance(self):
        # Payment $0.50 short on $100 order (tolerance $1.00)
        orders = [make_order("ORD-001", 100.0)]
        payments = [make_payment("TXN-001", "ORD-001", 99.50)]
        assert reconcile(orders, payments) == []


# ---------------------------------------------------------------------------
# Amount mismatch outside tolerance
# ---------------------------------------------------------------------------


class TestAmountMismatchOutsideTolerance:
    def test_payment_too_high(self):
        orders = [make_order("ORD-001", 100.0)]
        payments = [make_payment("TXN-001", "ORD-001", 102.00)]
        result = reconcile(orders, payments)
        assert len(result) == 1
        d = result[0]
        assert d.discrepancy_type == DiscrepancyType.AMOUNT_MISMATCH
        assert d.order_id == "ORD-001"
        assert d.expected_amount == 100.0
        assert d.actual_amount == 102.0
        assert d.difference == 2.0

    def test_payment_too_low(self):
        orders = [make_order("ORD-001", 100.0)]
        payments = [make_payment("TXN-001", "ORD-001", 95.00)]
        result = reconcile(orders, payments)
        assert len(result) == 1
        d = result[0]
        assert d.discrepancy_type == DiscrepancyType.AMOUNT_MISMATCH
        assert d.difference == -5.0

    def test_just_outside_tolerance(self):
        # $1.01 over on $100 order (tolerance is $1.00)
        orders = [make_order("ORD-001", 100.0)]
        payments = [make_payment("TXN-001", "ORD-001", 101.01)]
        result = reconcile(orders, payments)
        assert len(result) == 1
        assert result[0].discrepancy_type == DiscrepancyType.AMOUNT_MISMATCH


# ---------------------------------------------------------------------------
# Duplicate payment
# ---------------------------------------------------------------------------


class TestDuplicatePayment:
    def test_same_transaction_ref_twice(self):
        orders = [make_order("ORD-001", 100.0)]
        payments = [
            make_payment("TXN-001", "ORD-001", 50.0),
            make_payment("TXN-001", "ORD-001", 50.0),
        ]
        result = reconcile(orders, payments)
        dupes = [d for d in result if d.discrepancy_type == DiscrepancyType.DUPLICATE_PAYMENT]
        assert len(dupes) == 1
        assert dupes[0].payment_ref == "TXN-001"

    def test_duplicate_also_triggers_amount_mismatch(self):
        # Same TXN ref twice, each $30 → sum $60 vs $100 order
        orders = [make_order("ORD-001", 100.0)]
        payments = [
            make_payment("TXN-001", "ORD-001", 30.0),
            make_payment("TXN-001", "ORD-001", 30.0),
        ]
        result = reconcile(orders, payments)
        types = {d.discrepancy_type for d in result}
        assert DiscrepancyType.DUPLICATE_PAYMENT in types
        assert DiscrepancyType.AMOUNT_MISMATCH in types


# ---------------------------------------------------------------------------
# Refund unmatched
# ---------------------------------------------------------------------------


class TestRefundUnmatched:
    def test_negative_payment_no_order_reference(self):
        orders = [make_order("ORD-001", 100.0)]
        payments = [make_payment("TXN-REF", None, -50.0)]
        result = reconcile(orders, payments)
        refunds = [d for d in result if d.discrepancy_type == DiscrepancyType.REFUND_UNMATCHED]
        assert len(refunds) == 1
        assert refunds[0].payment_ref == "TXN-REF"
        assert refunds[0].actual_amount == -50.0

    def test_positive_payment_no_reference_not_flagged_as_refund(self):
        orders = [make_order("ORD-001", 100.0)]
        payments = [make_payment("TXN-001", None, 50.0)]
        result = reconcile(orders, payments)
        refunds = [d for d in result if d.discrepancy_type == DiscrepancyType.REFUND_UNMATCHED]
        assert len(refunds) == 0


# ---------------------------------------------------------------------------
# Multiple partial payments
# ---------------------------------------------------------------------------


class TestMultiplePartialPayments:
    def test_two_payments_sum_correctly(self):
        orders = [make_order("ORD-001", 100.0)]
        payments = [
            make_payment("TXN-001", "ORD-001", 60.0),
            make_payment("TXN-002", "ORD-001", 40.0),
        ]
        assert reconcile(orders, payments) == []

    def test_two_payments_sum_incorrectly(self):
        orders = [make_order("ORD-001", 100.0)]
        payments = [
            make_payment("TXN-001", "ORD-001", 60.0),
            make_payment("TXN-002", "ORD-001", 30.0),
        ]
        result = reconcile(orders, payments)
        assert len(result) == 1
        assert result[0].discrepancy_type == DiscrepancyType.AMOUNT_MISMATCH
        assert result[0].expected_amount == 100.0
        assert result[0].actual_amount == 90.0
        assert result[0].difference == -10.0


# ---------------------------------------------------------------------------
# Empty inputs
# ---------------------------------------------------------------------------


class TestEmptyInputs:
    def test_no_orders_no_payments(self):
        assert reconcile([], []) == []

    def test_orders_no_payments(self):
        orders = [make_order("ORD-001", 100.0), make_order("ORD-002", 200.0)]
        result = reconcile(orders, [])
        assert len(result) == 2
        assert all(d.discrepancy_type == DiscrepancyType.MISSING_PAYMENT for d in result)

    def test_no_orders_with_payments(self):
        payments = [make_payment("TXN-001", "ORD-001", 100.0)]
        result = reconcile([], payments)
        assert len(result) == 1
        assert result[0].discrepancy_type == DiscrepancyType.MISSING_ORDER
