import React from "react";

export const NEXT = { Assigned: "In Progress", "In Progress": "Resolved" };
export const CATEGORIES = ["Tampering", "Outage", "Overconsumption", "Hardware", "Communication"];

export function Badge({ children, kind }) {
  return <span className={`badge ${kind || String(children).toLowerCase().replace(/\s+/g, "-")}`}>{children}</span>;
}

export function Priority({ p }) {
  if (!p) return <span className="muted">—</span>;
  const labels = { 1: "P1 Emergency", 2: "P2 High", 3: "P3 Medium", 4: "P4 Low" };
  return <Badge kind={`p${p}`}>{labels[p]}</Badge>;
}

export function Err({ msg }) {
  return msg ? <div className="alert error">{msg}</div> : null;
}

export function Card({ title, children, right }) {
  return (
    <section className="card">
      {(title || right) && (
        <div className="card-head">
          <h3>{title}</h3>
          {right}
        </div>
      )}
      {children}
    </section>
  );
}

export function Stat({ label, value, tone }) {
  return (
    <div className={`stat ${tone || ""}`}>
      <div className="stat-value">{value ?? "–"}</div>
      <div className="stat-label">{label}</div>
    </div>
  );
}

/* Responsive table: wraps in a scroll container on small screens */
export function Table({ cols, rows, empty = "Nothing here yet" }) {
  if (!rows || rows.length === 0) return <p className="muted">{empty}</p>;
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>{cols.map((c) => <th key={c.label}>{c.label}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={r.report_id || r.id || i}>
              {cols.map((c) => <td key={c.label}>{c.render ? c.render(r) : r[c.key]}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* Dependency-free horizontal bar chart */
export function BarChart({ data, colorVar = "--accent" }) {
  const max = Math.max(1, ...(data || []).map((d) => d.count));
  if (!data || data.length === 0) return <p className="muted">No data yet</p>;
  return (
    <div className="bars">
      {data.map((d) => (
        <div className="bar-row" key={d.name}>
          <span className="bar-name">{d.name}</span>
          <div className="bar-track">
            <div className="bar-fill" style={{ width: `${(d.count / max) * 100}%`, background: `var(${colorVar})` }} />
          </div>
          <span className="bar-count">{d.count}</span>
        </div>
      ))}
    </div>
  );
}

export function Donut({ resolved, unresolved }) {
  const total = resolved + unresolved;
  const pct = total ? Math.round((resolved / total) * 100) : 0;
  const r = 52, c = 2 * Math.PI * r;
  return (
    <div className="donut">
      <svg viewBox="0 0 140 140" width="140" height="140" role="img" aria-label={`${pct}% resolved`}>
        <circle cx="70" cy="70" r={r} fill="none" stroke="var(--track)" strokeWidth="16" />
        <circle cx="70" cy="70" r={r} fill="none" stroke="var(--ok)" strokeWidth="16"
          strokeDasharray={`${(pct / 100) * c} ${c}`} transform="rotate(-90 70 70)" />
        <text x="70" y="76" textAnchor="middle" fontSize="26" fontWeight="700" fill="currentColor">{pct}%</text>
      </svg>
      <div>
        <div><b>{resolved}</b> resolved</div>
        <div><b>{unresolved}</b> unresolved</div>
      </div>
    </div>
  );
}

export function LineChart({ data, colorVar = "--accent", height = 180 }) {
  if (!data || data.length === 0) return <p className="muted">No data yet</p>;

  const width = 520;
  const pad = 28;
  const values = data.map((d) => Number(d.count || 0));
  const max = Math.max(1, ...values);
  const xStep = data.length === 1 ? 0 : (width - pad * 2) / (data.length - 1);

  const points = data
    .map((d, i) => {
      const x = pad + i * xStep;
      const y = height - pad - (Number(d.count || 0) / max) * (height - pad * 2);
      return `${x},${y}`;
    })
    .join(" ");

  const labels = data.map((d, i) => {
    const x = pad + i * xStep;
    const y = height - 8;
    return (
      <g key={`${d.name}-${i}`}>
        <text x={x} y={y} textAnchor="middle" fontSize="10" fill="var(--muted)">{d.name}</text>
      </g>
    );
  });

  return (
    <div className="chart-wrap">
      <svg viewBox={`0 0 ${width} ${height}`} className="line-chart" aria-label="Analytics trend chart">
        <line x1={pad} y1={height - pad} x2={width - pad} y2={height - pad} className="axis-line" />
        <line x1={pad} y1={pad} x2={pad} y2={height - pad} className="axis-line" />
        <polyline fill="none" stroke={`var(${colorVar})`} strokeWidth="3" points={points} />
        {data.map((d, i) => {
          const x = pad + i * xStep;
          const y = height - pad - (Number(d.count || 0) / max) * (height - pad * 2);
          return <circle key={`${d.name}-dot-${i}`} cx={x} cy={y} r="4" fill={`var(${colorVar})`} />;
        })}
        {labels}
      </svg>
    </div>
  );
}
