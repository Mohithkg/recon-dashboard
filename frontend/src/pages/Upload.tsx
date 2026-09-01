/**
 * CSV upload page.
 *
 * Uploads orders and payments CSVs separately to the backend ingestion
 * endpoint, then displays the ingestion summary including counts and any
 * rejected-row warnings.
 */

import { FormEvent, useState } from "react";
import { api, ApiError } from "../api/client";

interface IngestionSummary {
  filename: string;
  total_rows_read: number;
  ingested: number;
  duplicates_removed: number;
  rejected: { row_index: number; reasons: string[] }[];
  rejected_count: number;
}

const styles = {
  card: {
    background: "#fff",
    borderRadius: 8,
    padding: "1.5rem",
    boxShadow: "0 1px 4px rgba(0,0,0,0.08)",
    border: "1px solid #e0e0e0",
    marginBottom: "1.5rem",
  } as React.CSSProperties,
  title: { marginBottom: "1rem", fontSize: "1.1rem" } as React.CSSProperties,
  dropzone: {
    border: "2px dashed #c0c4cc",
    borderRadius: 8,
    padding: "1.5rem",
    textAlign: "center" as const,
    cursor: "pointer",
    background: "#fafbfc",
  } as React.CSSProperties,
  dropzoneActive: {
    borderColor: "#1a73e8",
    background: "#e8f0fe",
  } as React.CSSProperties,
  btn: {
    marginTop: "1rem",
    padding: "0.5rem 1.25rem",
    border: "none",
    borderRadius: 4,
    background: "#1a73e8",
    color: "#fff",
    fontSize: "0.9rem",
    fontWeight: 600,
    cursor: "pointer",
  } as React.CSSProperties,
  btnDisabled: {
    background: "#a0b4d4",
    cursor: "not-allowed",
  } as React.CSSProperties,
  error: {
    color: "#c0392b",
    background: "#fdecea",
    padding: "0.5rem 0.75rem",
    borderRadius: 4,
    fontSize: "0.85rem",
    marginTop: "1rem",
  } as React.CSSProperties,
  summaryBox: {
    background: "#f0f9f0",
    border: "1px solid #b7dfb9",
    borderRadius: 6,
    padding: "1rem",
    marginTop: "1rem",
  } as React.CSSProperties,
  summaryRow: {
    display: "flex",
    justifyContent: "space-between",
    padding: "0.2rem 0",
    fontSize: "0.9rem",
  } as React.CSSProperties,
  warningBox: {
    background: "#fff8e1",
    border: "1px solid #ffe082",
    borderRadius: 6,
    padding: "1rem",
    marginTop: "1rem",
  } as React.CSSProperties,
  rejectedItem: {
    fontSize: "0.82rem",
    padding: "0.3rem 0",
    borderBottom: "1px solid #f0e0c0",
    color: "#555",
  } as React.CSSProperties,
};

export function Upload() {
  return (
    <div>
      <h1 style={{ marginBottom: "1.5rem" }}>Upload CSV Files</h1>
      <UploadCard kind="orders" />
      <UploadCard kind="payments" />
    </div>
  );
}

function UploadCard({ kind }: { kind: "orders" | "payments" }) {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [summary, setSummary] = useState<IngestionSummary | null>(null);
  const [dragActive, setDragActive] = useState(false);

  const endpoint = kind === "orders" ? "/uploads/orders" : "/uploads/payments";
  const label = kind === "orders" ? "Orders CSV" : "Payments CSV";

  const handleUpload = async (e: FormEvent) => {
    e.preventDefault();
    if (!file) return;

    setUploading(true);
    setError(null);
    setSummary(null);

    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await api.upload<IngestionSummary>(endpoint, formData);
      setSummary(res);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Upload failed. Please try again.");
      }
    } finally {
      setUploading(false);
    }
  };

  return (
    <div style={styles.card}>
      <h2 style={styles.title}>{label}</h2>

      <form onSubmit={handleUpload}>
        <div
          style={{
            ...styles.dropzone,
            ...(dragActive ? styles.dropzoneActive : {}),
          }}
          onDragOver={(e) => {
            e.preventDefault();
            setDragActive(true);
          }}
          onDragLeave={() => setDragActive(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragActive(false);
            const dropped = e.dataTransfer.files?.[0];
            if (dropped) setFile(dropped);
          }}
          onClick={() => document.getElementById(`file-${kind}`)?.click()}
        >
          <input
            id={`file-${kind}`}
            type="file"
            accept=".csv"
            style={{ display: "none" }}
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
          <div style={{ fontSize: "0.9rem", color: "#666" }}>
            {file ? (
              <span style={{ fontWeight: 500, color: "#222" }}>{file.name}</span>
            ) : (
              <>Drag & drop a .csv here, or click to browse</>
            )}
          </div>
        </div>

        <button
          type="submit"
          disabled={!file || uploading}
          style={{ ...styles.btn, ...(!file || uploading ? styles.btnDisabled : {}) }}
        >
          {uploading ? "Uploading…" : `Upload ${label}`}
        </button>
      </form>

      {error && <div style={styles.error}>{error}</div>}

      {summary && <SummaryDisplay summary={summary} />}
    </div>
  );
}

function SummaryDisplay({ summary }: { summary: IngestionSummary }) {
  return (
    <>
      <div style={styles.summaryBox}>
        <SummaryRow label="File" value={summary.filename} />
        <SummaryRow label="Rows read" value={summary.total_rows_read} />
        <SummaryRow label="Ingested" value={summary.ingested} />
        <SummaryRow label="Duplicates removed" value={summary.duplicates_removed} />
        <SummaryRow label="Rejected" value={summary.rejected_count} />
      </div>

      {summary.rejected.length > 0 && (
        <div style={styles.warningBox}>
          <strong style={{ fontSize: "0.9rem", display: "block", marginBottom: "0.5rem" }}>
            Rejected rows:
          </strong>
          {summary.rejected.map((r) => (
            <div key={r.row_index} style={styles.rejectedItem}>
              Row {r.row_index}: {r.reasons.join("; ")}
            </div>
          ))}
        </div>
      )}
    </>
  );
}

function SummaryRow({ label, value }: { label: string; value: string | number }) {
  return (
    <div style={styles.summaryRow}>
      <span style={{ color: "#555" }}>{label}</span>
      <span style={{ fontWeight: 600 }}>{value}</span>
    </div>
  );
}
