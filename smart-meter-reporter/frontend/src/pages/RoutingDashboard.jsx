import React, { useState } from "react";
import { api, useApi } from "../api.js";
import { Badge, CATEGORIES, Card, Err, Priority, Table } from "../components.jsx";

function CorrectionForm({ r, onDone }) {
  const [category, setCategory] = useState(r.category || "");
  const [section, setSection] = useState(r.routing_key && "ABCDE".includes(r.routing_key) ? r.routing_key : "A");
  const [err, setErr] = useState("");

  async function apply() {
    const res = await api(`/reports/${r.report_id}/correct`, { method: "POST", body: { category: category || undefined, section } });
    if (res.ok) onDone();
    else setErr(res.data?.error || "Failed");
  }

  return (
    <div className="inline wrap">
      <select value={category} onChange={(e) => setCategory(e.target.value)}>
        <option value="">Category…</option>
        {CATEGORIES.map((c) => <option key={c}>{c}</option>)}
      </select>
      <select value={section} onChange={(e) => setSection(e.target.value)}>
        {"ABCDE".split("").map((s) => <option key={s}>{s}</option>)}
      </select>
      <button className="btn small" onClick={apply} disabled={!category}>Fix &amp; dispatch</button>
      {err && <small className="err">{err}</small>}
    </div>
  );
}

export default function RoutingDashboard() {
  const { data, error, reload } = useApi("/routing", 5000);
  return (
    <>
      <Err msg={error} />
      <Card title="Routing table">
        <Table
          rows={data?.table}
          cols={[
            { label: "Key (meter ID letter)", key: "key" },
            { label: "Zone", key: "zone" },
            { label: "Crew", key: "crew" },
            { label: "Depot", key: "depot" },
          ]}
        />
        <p className="muted small">Unknown key or unclassified report → {data?.fallback}. Overflow goes to the nearest available section crew.</p>
      </Card>

      <Card title="Current handler loads">
        <Table
          rows={data?.loads}
          cols={[
            { label: "Crew", key: "id" },
            { label: "Zone", key: "zone" },
            { label: "Open", render: (c) => `${c.open_cases}/${c.capacity}` },
            { label: "Load", render: (c) => <div className="bar-track slim"><div className="bar-fill" style={{ width: `${Math.min(100, (c.open_cases / c.capacity) * 100)}%`, background: c.open_cases > c.capacity ? "var(--bad)" : "var(--accent)" }} /></div> },
            { label: "Availability", render: (c) => <Badge kind={c.available ? "resolved" : "rejected"}>{c.available ? "Available" : "Unavailable"}</Badge> },
          ]}
        />
      </Card>

      <Card title="Backup assignments, escalations & priority overrides">
        <Table
          rows={data?.backups}
          empty="No escalations yet"
          cols={[
            { label: "ID", key: "report_id" },
            { label: "Home zone", key: "zone" },
            { label: "Assigned crew", key: "assigned_crew" },
            { label: "Priority", render: (r) => <Priority p={r.priority} /> },
            { label: "Decision", render: (r) => <Badge kind={r.routing_decision === "PRIORITY_OVERRIDE" ? "p1" : "info"}>{r.routing_decision}</Badge> },
            { label: "Reason", key: "routing_note" },
          ]}
        />
      </Card>

      <Card title={`Waiting queue (${data?.waiting?.length ?? 0}) — ordered by priority, then time`}>
        <Table
          rows={data?.waiting}
          empty="Queue is empty"
          cols={[
            { label: "#", render: (r) => data.waiting.indexOf(r) + 1 },
            { label: "ID", key: "report_id" },
            { label: "Zone", key: "zone" },
            { label: "Category", key: "category" },
            { label: "Priority", render: (r) => <Priority p={r.priority} /> },
            { label: "Submitted", render: (r) => new Date(r.created_at).toLocaleTimeString() },
          ]}
        />
      </Card>

      <Card title={`Central correction queue (${data?.correction?.length ?? 0})`}>
        <Table
          rows={data?.correction}
          empty="No reports need correction"
          cols={[
            { label: "ID", key: "report_id" },
            { label: "Meter", key: "meter_id" },
            { label: "Why", key: "routing_note" },
            { label: "Fix", render: (r) => <CorrectionForm r={r} onDone={reload} /> },
          ]}
        />
      </Card>

      <Card title="Recent routing decisions">
        <Table
          rows={data?.decisions}
          cols={[
            { label: "Time", render: (d) => new Date(d.ts).toLocaleTimeString() },
            { label: "Report", key: "report_id" },
            { label: "Decision", key: "decision" },
            { label: "Detail", key: "detail" },
          ]}
        />
      </Card>
    </>
  );
}
