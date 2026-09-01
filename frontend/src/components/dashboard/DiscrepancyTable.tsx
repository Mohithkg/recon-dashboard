/**
 * Paginated, filterable, searchable discrepancy table.
 */

import { useEffect, useState, useCallback } from "react";
import { api, ApiError } from "../../api/client";

interface DiscrepancyRow {
  id: number;
  order_id: string;
  payment_ref: string | null;
  type: string;
  expected_amount: number | null;
  actual_amount: number | null;
  difference: number | null;
  status: string;
  notes: string | null;
  created_at: string | null;
}

interface DiscrepancyResponse {
  total: number;
  page: number;
  page_size: number;
  items: DiscrepancyRow[];
}

interface DiscrepancyTableProps {
  typeFilter: string | null;
  page: number;
  onPageChange: (page: number) => void;
  onTypeChange: (type: string | null) => void;
  filterVersion: number;
}

const PAGE_SIZE = 10;
const SEARCH_DEBOUNCE_MS = 300;

function formatType(type: string): string {
  return type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatMoney(amount: number | null): string {
  if (amount === null) return "—";
  return amount.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
  });
}

const TYPE_COLORS: Record<string, string> = {
  missing_payment: "#d93025",
  missing_order: "#e8710a",
  amount_mismatch: "#1a73e8",
  duplicate_payment: "#9334e6",
  refund_unmatched: "#1e8e3e",
};

const styles = {
  container: {
    background: "#fff",
    borderRadius: 8,
    boxShadow: "0 1px 4px rgba(0,0,0,0.06)",
    border: "1px solid #e0e0e0",
    overflow: "hidden",
  } as React.CSSProperties,
  toolbar: {
    display: "flex",
    gap: "0.75rem",
    alignItems: "center",
    padding: "0.75rem 1rem",
    borderBottom: "1px solid #eee",
    flexWrap: "wrap" as const,
  } as React.CSSProperties,
  select: {
    padding: "0.4rem 0.6rem",
    border: "1px solid #ccc",
    borderRadius: 4,
    fontSize: "0.85rem",
    fontFamily: "inherit",
    background: "#fff",
  } as React.CSSProperties,
  search: {
    padding: "0.4rem 0.6rem",
    border: "1px solid #ccc",
    borderRadius: 4,
    fontSize: "0.85rem",
    fontFamily: "inherit",
    flex: 1,
    minWidth: 160,
  } as React.CSSProperties,
  table: {
    width: "100%",
    borderCollapse: "collapse" as const,
    fontSize: "0.85rem",
  } as React.CSSProperties,
  th: {
    textAlign: "left" as const,
    padding: "0.6rem 0.75rem",
    borderBottom: "2px solid #eee",
    color: "#555",
    fontWeight: 600,
    whiteSpace: "nowrap" as const,
  } as React.CSSProperties,
  td: {
    padding: "0.55rem 0.75rem",
    borderBottom: "1px solid #f0f0f0",
    color: "#333",
  } as React.CSSProperties,
  typeBadge: (color: string): React.CSSProperties => ({
    display: "inline-block",
    padding: "0.15rem 0.5rem",
    borderRadius: 10,
    background: `${color}1a`,
    color: color,
    fontWeight: 600,
    fontSize: "0.75rem",
    whiteSpace: "nowrap" as const,
  }),
  pagination: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "0.6rem 1rem",
    borderTop: "1px solid #eee",
    fontSize: "0.82rem",
    color: "#666",
  } as React.CSSProperties,
  pageBtn: (disabled: boolean): React.CSSProperties => ({
    padding: "0.3rem 0.6rem",
    border: "1px solid #ccc",
    borderRadius: 4,
    background: disabled ? "#f5f5f5" : "#fff",
    cursor: disabled ? "not-allowed" : "pointer",
    color: disabled ? "#aaa" : "#444",
    fontFamily: "inherit",
    fontSize: "0.82rem",
  }),
  empty: {
    padding: "2rem",
    textAlign: "center" as const,
    color: "#999",
    fontSize: "0.9rem",
  } as React.CSSProperties,
  loading: {
    padding: "2rem",
    textAlign: "center" as const,
    color: "#888",
    fontSize: "0.9rem",
  } as React.CSSProperties,
};

export function DiscrepancyTable({
  typeFilter,
  page,
  onPageChange,
  onTypeChange,
  filterVersion,
}: DiscrepancyTableProps) {
  const [data, setData] = useState<DiscrepancyResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [availableTypes, setAvailableTypes] = useState<string[]>([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");

  // Debounce the search input so we don't fire a request per keystroke.
  useEffect(() => {
    const handle = setTimeout(() => {
      setDebouncedSearch(searchTerm);
      onPageChange(1);
    }, SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(handle);
  }, [searchTerm, onPageChange]);

  // Fetch available types for the dropdown (once).
  useEffect(() => {
    api
      .get<{ breakdown: { type: string }[] }>("/dashboard/breakdown")
      .then((res) => setAvailableTypes(res.breakdown.map((b) => b.type)))
      .catch(() => {});
  }, []);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      params.set("page", String(page));
      params.set("page_size", String(PAGE_SIZE));
      if (typeFilter) params.set("type", typeFilter);
      if (debouncedSearch) params.set("search", debouncedSearch);

      const res = await api.get<DiscrepancyResponse>(
        `/dashboard/discrepancies?${params.toString()}`,
      );
      setData(res);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Failed to load discrepancies",
      );
    } finally {
      setLoading(false);
    }
  }, [typeFilter, debouncedSearch, page]);

  useEffect(() => {
    fetchData();
  }, [fetchData, filterVersion]);

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;

  return (
    <div style={styles.container}>
      {/* Toolbar */}
      <div style={styles.toolbar}>
        <select
          style={styles.select}
          value={typeFilter ?? ""}
          onChange={(e) => {
            onTypeChange(e.target.value || null);
            onPageChange(1);
          }}
        >
          <option value="">All types</option>
          {availableTypes.map((t) => (
            <option key={t} value={t}>
              {formatType(t)}
            </option>
          ))}
        </select>
        <input
          style={styles.search}
          type="text"
          placeholder="Search by order or payment ID…"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />
      </div>

      {/* States */}
      {loading && <div style={styles.loading}>Loading discrepancies…</div>}

      {error && !loading && (
        <div style={{ ...styles.empty, color: "#c0392b" }}>{error}</div>
      )}

      {!loading && !error && data && data.items.length === 0 && (
        <div style={styles.empty}>
          No discrepancies found
          {typeFilter ? ` for "${formatType(typeFilter)}"` : ""}.
        </div>
      )}

      {!loading && !error && data && data.items.length > 0 && (
        <TableBody
          data={data}
          totalPages={totalPages}
          page={page}
          onPageChange={onPageChange}
        />
      )}
    </div>
  );
}

function TableBody({
  data,
  totalPages,
  page,
  onPageChange,
}: {
  data: DiscrepancyResponse;
  totalPages: number;
  page: number;
  onPageChange: (page: number) => void;
}) {
  return (
    <>
      <div style={{ overflowX: "auto" }}>
        <table style={styles.table}>
          <thead>
            <tr>
              <th style={styles.th}>Order ID</th>
              <th style={styles.th}>Payment Ref</th>
              <th style={styles.th}>Type</th>
              <th style={styles.th}>Expected</th>
              <th style={styles.th}>Actual</th>
              <th style={styles.th}>Difference</th>
              <th style={styles.th}>Status</th>
            </tr>
          </thead>
          <tbody>
            {data.items.map((row) => (
              <tr key={row.id}>
                <td style={styles.td}>{row.order_id}</td>
                <td style={styles.td}>{row.payment_ref ?? "—"}</td>
                <td style={styles.td}>
                  <span style={styles.typeBadge(TYPE_COLORS[row.type] ?? "#777")}>
                    {formatType(row.type)}
                  </span>
                </td>
                <td style={styles.td}>{formatMoney(row.expected_amount)}</td>
                <td style={styles.td}>{formatMoney(row.actual_amount)}</td>
                <td
                  style={{
                    ...styles.td,
                    color:
                      row.difference && row.difference < 0
                        ? "#c0392b"
                        : row.difference && row.difference > 0
                          ? "#1e8e3e"
                          : "#333",
                    fontWeight: 600,
                  }}
                >
                  {formatMoney(row.difference)}
                </td>
                <td style={styles.td}>{row.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div style={styles.pagination}>
        <span>
          Showing {(page - 1) * PAGE_SIZE + 1}–
          {Math.min(page * PAGE_SIZE, data.total)} of {data.total}
        </span>
        <div style={{ display: "flex", gap: "0.5rem" }}>
          <button
            style={styles.pageBtn(page <= 1)}
            disabled={page <= 1}
            onClick={() => onPageChange(page - 1)}
          >
            Prev
          </button>
          <span style={{ alignSelf: "center" }}>
            Page {page} of {totalPages || 1}
          </span>
          <button
            style={styles.pageBtn(page >= totalPages)}
            disabled={page >= totalPages}
            onClick={() => onPageChange(page + 1)}
          >
            Next
          </button>
        </div>
      </div>
    </>
  );
}
