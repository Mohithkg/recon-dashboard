interface MetricCardProps {
  label: string;
  value: string;
  hint?: string;
  accent?: string;
  active?: boolean;
  onClick?: () => void;
}

const styles = {
  card: (accent: string, active: boolean): React.CSSProperties => ({
    background: "#fff",
    borderRadius: 8,
    padding: "1.1rem 1.25rem",
    boxShadow: "0 1px 4px rgba(0,0,0,0.06)",
    border: `1px solid ${active ? accent : "#e0e0e0"}`,
    borderLeft: `4px solid ${accent}`,
    cursor: "pointer",
    transition: "box-shadow 0.15s, border-color 0.15s",
    ...(active ? { boxShadow: `0 0 0 2px ${accent}33` } : {}),
  }),
  label: {
    fontSize: "0.78rem",
    fontWeight: 500,
    color: "#777",
    textTransform: "uppercase" as const,
    letterSpacing: "0.03em",
    marginBottom: "0.35rem",
  },
  value: (accent: string): React.CSSProperties => ({
    fontSize: "1.6rem",
    fontWeight: 700,
    color: accent,
    lineHeight: 1.2,
  }),
  hint: {
    fontSize: "0.75rem",
    color: "#999",
    marginTop: "0.25rem",
  },
};

export function MetricCard({
  label,
  value,
  hint,
  accent = "#1a73e8",
  active = false,
  onClick,
}: MetricCardProps) {
  return (
    <div
      style={styles.card(accent, active)}
      onClick={onClick}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={
        onClick
          ? (e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onClick();
              }
            }
          : undefined
      }
    >
      <div style={styles.label}>{label}</div>
      <div style={styles.value(accent)}>{value}</div>
      {hint && <div style={styles.hint}>{hint}</div>}
    </div>
  );
}
