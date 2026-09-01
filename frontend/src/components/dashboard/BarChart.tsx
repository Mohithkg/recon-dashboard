/**
 * Simple SVG bar chart for discrepancy breakdown.
 *
 * Bars are clickable to filter the parent table.  The active bar is
 * highlighted.  No external charting dependency needed.
 */

interface BarChartProps {
  data: { type: string; count: number; amount_at_risk: number }[];
  activeType: string | null;
  onBarClick: (type: string | null) => void;
}

const COLORS = [
  "#1a73e8",
  "#e8710a",
  "#d93025",
  "#1e8e3e",
  "#9334e6",
  "#e8710a",
];

const CHART_HEIGHT = 220;
const BAR_GAP = 8;
const LABEL_HEIGHT = 40;

function formatType(type: string): string {
  return type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function BarChart({ data, activeType, onBarClick }: BarChartProps) {
  if (!data || data.length === 0) {
    return (
      <div
        style={{
          height: CHART_HEIGHT + LABEL_HEIGHT,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "#999",
          fontSize: "0.9rem",
        }}
      >
        No discrepancies to chart.
      </div>
    );
  }

  const maxCount = Math.max(...data.map((d) => d.count), 1);
  const chartWidth = 600;
  const barWidth = Math.min(
    60,
    (chartWidth - BAR_GAP * (data.length - 1)) / data.length,
  );

  return (
    <div style={{ overflowX: "auto" }}>
      <svg
        viewBox={`0 0 ${chartWidth} ${CHART_HEIGHT + LABEL_HEIGHT}`}
        width="100%"
        style={{ minWidth: 400 }}
        role="img"
        aria-label="Discrepancies by type"
      >
        {/* Grid lines */}
        {[0, 0.25, 0.5, 0.75, 1].map((frac) => {
          const y = CHART_HEIGHT - frac * CHART_HEIGHT;
          return (
            <line
              key={frac}
              x1={0}
              y1={y}
              x2={chartWidth}
              y2={y}
              stroke="#eee"
              strokeWidth={1}
            />
          );
        })}

        {/* Bars */}
        {data.map((d, i) => {
          const barHeight = (d.count / maxCount) * (CHART_HEIGHT - 20);
          const x = i * (barWidth + BAR_GAP);
          const y = CHART_HEIGHT - barHeight;
          const color = COLORS[i % COLORS.length];
          const isActive = activeType === d.type;

          return (
            <g
              key={d.type}
              onClick={() => onBarClick(activeType === d.type ? null : d.type)}
              style={{ cursor: "pointer" }}
              role="button"
              tabIndex={0}
              aria-label={`${formatType(d.type)}: ${d.count} discrepancies`}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  onBarClick(activeType === d.type ? null : d.type);
                }
              }}
            >
              {/* Bar */}
              <rect
                x={x}
                y={y}
                width={barWidth}
                height={barHeight}
                fill={isActive ? color : `${color}99`}
                rx={3}
                stroke={isActive ? color : "none"}
                strokeWidth={isActive ? 2 : 0}
              />
              {/* Count label above bar */}
              <text
                x={x + barWidth / 2}
                y={y - 5}
                textAnchor="middle"
                fontSize={11}
                fontWeight={600}
                fill="#444"
              >
                {d.count}
              </text>
              {/* Type label below x-axis */}
              <text
                x={x + barWidth / 2}
                y={CHART_HEIGHT + 15}
                textAnchor="middle"
                fontSize={10}
                fill="#666"
              >
                {formatType(d.type).length > 12
                  ? formatType(d.type).slice(0, 11) + "…"
                  : formatType(d.type)}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
