import React, { useState } from "react";
import { api, useApi } from "../api.js";
import { Badge, Card, Err, Priority, Stat, Table } from "../components.jsx";

export default function UserDashboard() {
  const { data, error } = useApi("/dashboard/user", 5000);
  const [q, setQ] = useState("");
  const [found, setFound] = useState(null);
  const [msg, setMsg] = useState("");

  async function search(e) {
    e.preventDefault();
    setMsg("");
    const r = await api(`/reports/${encodeURIComponent(q.trim())}`);
    if (r.ok) setFound(r.data);
    else {
      setFound(null);
      setMsg(r.data?.error || "Not found");
    }
  }

  return (
    <>
      <Err msg={error} />
      <div className="stats">
        <Stat label="Total" value={data?.total} />
        <Stat label="Pending" value={data?.pending} tone="warn" />
        <Stat label="Assigned / In progress" value={data?.assigned} tone="info" />
        <Stat label="Resolved" value={data?.resolved} tone="ok" />
        <Stat label="Rejected" value={data?.rejected} tone="bad" />
      </div>

      <Card title="Track a report">
        <form className="inline" onSubmit={search}>
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="RPT-000001" />
          <button className="btn primary">Search</button>
        </form>
        {msg && <div className="alert error">{msg}</div>}
        {found && (
          <>
            <dl className="kv">
              <dt>Report</dt><dd><b>{found.report_id}</b></dd>
              <dt>Status</dt><dd><Badge>{found.status}</Badge></dd>
              <dt>Assigned handler</dt><dd>{found.assigned_crew || found.queue || "Not yet assigned"}</dd>
              <dt>Category</dt><dd>{found.category || "Unclassified"}</dd>
              <dt>Priority</dt><dd><Priority p={found.priority} /></dd>
              <dt>Meter</dt><dd>{found.meter_id} · {found.zone || "unknown zone"}</dd>
              <dt>Last update</dt><dd>{new Date(found.updated_at).toLocaleString()}</dd>
            </dl>
            <h4>History</h4>
            <ul className="timeline">
              {found.log.map((l) => <li key={l.id}><b>{l.decision}</b> — {l.detail} <span className="muted small">{new Date(l.ts).toLocaleTimeString()}</span></li>)}
            </ul>
          </>
        )}
      </Card>

      <Card title="Recent reports">
        <Table
          rows={data?.recent}
          cols={[
            { label: "ID", key: "report_id" },
            { label: "Meter", key: "meter_id" },
            { label: "Category", render: (r) => r.category || "—" },
            { label: "Status", render: (r) => <Badge>{r.status}</Badge> },
            { label: "Handler", render: (r) => r.assigned_crew || r.queue || "—" },
          ]}
        />
      </Card>
    </>
  );
}
