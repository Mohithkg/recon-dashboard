/**
 * Dashboard page — placeholder.
 *
 * Intended to consume the /dashboard/summary, /dashboard/breakdown, and
 * /dashboard/discrepancies endpoints.  Wire up charts / tables here once
 * the backend endpoints are confirmed working.
 */

export function Dashboard() {
  return (
    <div>
      <h1 style={{ marginBottom: "1rem" }}>Dashboard</h1>
      <div
        style={{
          background: "#fff",
          borderRadius: 8,
          padding: "2rem",
          boxShadow: "0 1px 4px rgba(0,0,0,0.08)",
          border: "1px solid #e0e0e0",
          textAlign: "center",
          color: "#888",
        }}
      >
        <p>Summary metrics, breakdown charts, and discrepancy table coming soon.</p>
        <p style={{ fontSize: "0.85rem", marginTop: "0.5rem" }}>
          Backend endpoints ready: <code>/dashboard/summary</code>,{" "}
          <code>/dashboard/breakdown</code>, <code>/dashboard/discrepancies</code>.
        </p>
      </div>
    </div>
  );
}
