/**
 * Dashboard page.
 *
 * Headline metric cards + breakdown bar chart + drill-down discrepancy
 * table.  Clicking a metric card or chart bar filters the table to the
 * matching discrepancy type.  The table also has its own type dropdown and
 * search input.
 */

import { useEffect, useState, useCallback } from "react";
import { api, ApiError } from "../api/client";
import { MetricCard } from "../components/dashboard/MetricCard";
import { BarChart } from "../components/dashboard/BarChart";
import { DiscrepancyTable } from "../components/dashboard/DiscrepancyTable";

interface Summary {
  total_orders: number;
  total_payments: number;
  total_value_reconciled: number;
  total_value_in_dispute: number;
  total_money_at_risk: number;
}

interface BreakdownItem {
  type: string;
  count: number;
  amount_at_risk: number;
}

function formatMoney(amount: number): string {
  return amount.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
  });
}

const styles = {
  page: { maxWidth: 1000, margin: "0 auto" } as React.CSSProperties,
  loading: {
    textAlign: "center" as const,
    padding: "3rem",
    color: "#888",
    fontSize: "0.95rem",
  } as React.CSSProperties,
  error: {
    textAlign: "center" as const,
    padding: "2rem",
    color: "#c0392b",
    fontSize: "0.9rem",
    background: "#fdecea",
    borderRadius: 8,
    marginBottom: "1rem",
  } as React.CSSProperties,
  cardGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
    gap: "1rem",
    marginBottom: "1.5rem",
  } as React.CSSProperties,
  chartCard: {
    background: "#fff",
    borderRadius: 8,
    padding: "1.25rem",
    boxShadow: "0 1px 4px rgba(0,0,0,0.06)",
    border: "1px solid #e0e0e0",
    marginBottom: "1.5rem",
  } as React.CSSProperties,
  chartTitle: {
    fontSize: "1rem",
    fontWeight: 600,
    marginBottom: "0.75rem",
    color: "#333",
  } as React.CSSProperties,
  tableTitle: {
    fontSize: "1rem",
    fontWeight: 600,
    marginBottom: "0.75rem",
    color: "#333",
  } as React.CSSProperties,
  empty: {
    textAlign: "center" as const,
    padding: "3rem",
    color: "#999",
    fontSize: "0.9rem",
    background: "#fff",
    borderRadius: 8,
    border: "1px solid #e0e0e0",
  } as React.CSSProperties,
};

export function Dashboard() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [breakdown, setBreakdown] = useState<BreakdownItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Cross-filtering state
  const [typeFilter, setTypeFilter] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [filterVersion, setFilterVersion] = useState(0);

  // Fetch summary + breakdown on mount
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    Promise.all([
      api.get<Summary>("/dashboard/summary"),
      api.get<{ breakdown: BreakdownItem[] }>("/dashboard/breakdown"),
    ])
      .then(([summaryRes, breakdownRes]) => {
        if (cancelled) return;
        setSummary(summaryRes);
        setBreakdown(breakdownRes.breakdown);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(
          err instanceof ApiError ? err.message : "Failed to load dashboard",
        );
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const handleFilterByType = useCallback((type: string | null) => {
    setTypeFilter(type);
    setPage(1);
    setFilterVersion((v) => v + 1);
  }, []);

  return (
    <div style={styles.page}>
      <h1 style={{ marginBottom: "1.5rem" }}>Dashboard</h1>

      {loading && <div style={styles.loading}>Loading dashboard…</div>}

      {error && <div style={styles.error}>{error}</div>}

      {!loading && !error && summary && (
        <>
          <div style={styles.cardGrid}>
            <MetricCard
              label="Total Orders"
              value={summary.total_orders.toLocaleString()}
              accent="#1a73e8"
              onClick={() => handleFilterByType(null)}
            />
            <MetricCard
              label="Total Payments"
              value={summary.total_payments.toLocaleString()}
              accent="#1e8e3e"
              onClick={() => handleFilterByType(null)}
            />
            <MetricCard
              label="Value Reconciled"
              value={formatMoney(summary.total_value_reconciled)}
              accent="#1e8e3e"
              onClick={() => handleFilterByType(null)}
            />
            <MetricCard
              label="Value in Dispute"
              value={formatMoney(summary.total_value_in_dispute)}
              accent="#e8710a"
              onClick={() => handleFilterByType(null)}
            />
            <MetricCard
              label="Money at Risk"
              value={formatMoney(summary.total_money_at_risk)}
              accent="#d93025"
              onClick={() => handleFilterByType(null)}
            />
          </div>

          <div style={styles.chartCard}>
            <div style={styles.chartTitle}>Discrepancies by Type</div>
            {breakdown.length === 0 ? (
              <div style={{ textAlign: "center", color: "#999", padding: "1.5rem 0" }}>
                No discrepancies found — all orders reconciled.
              </div>
            ) : (
              <BarChart
                data={breakdown}
                activeType={typeFilter}
                onBarClick={handleFilterByType}
              />
            )}
          </div>

          <div style={styles.tableTitle}>Discrepancy Details</div>
          {breakdown.length === 0 ? (
            <div style={styles.empty}>
              Nothing to display. Upload orders and payments, then run reconciliation.
            </div>
          ) : (
            <DiscrepancyTable
              typeFilter={typeFilter}
              page={page}
              onPageChange={setPage}
              onTypeChange={handleFilterByType}
              filterVersion={filterVersion}
            />
          )}
        </>
      )}
    </div>
  );
}
