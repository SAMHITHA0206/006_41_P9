import React, { useState } from "react";
import { api, useApi } from "../api.js";
import { Badge, Card, Err, NEXT, Priority, Table } from "../components.jsx";

export default function HandlerDashboard() {
  const [crew, setCrew] = useState("CREW-A");
  const crews = useApi("/crews", 5000);
  const reports = useApi(`/reports?crew=${crew}`, 5000);
  const [err, setErr] = useState("");
  const me = crews.data?.find((c) => c.id === crew);

  async function advance(r) {
    const res = await api(`/reports/${r.report_id}/status`, { method: "PATCH", body: { status: NEXT[r.status] } });
    setErr(res.ok ? "" : res.data?.error);
    reports.reload();
    crews.reload();
  }

  async function saveCrew(patch) {
    const res = await api(`/crews/${crew}`, { method: "PATCH", body: patch });
    setErr(res.ok ? "" : res.data?.error);
    crews.reload();
    reports.reload();
  }

  return (
    <>
      <Err msg={err || crews.error} />
      <Card title="Handler dashboard">
        <label className="field">
          <span>Crew</span>
          <select value={crew} onChange={(e) => setCrew(e.target.value)}>
            {(crews.data || []).map((c) => <option key={c.id} value={c.id}>{c.id} — {c.zone}</option>)}
          </select>
        </label>
        {me && (
          <div className="inline wrap">
            <span>Open cases: <b>{me.open_cases}/{me.capacity}</b></span>
            <label className="check">
              <input type="checkbox" checked={me.available} onChange={(e) => saveCrew({ available: e.target.checked })} />
              Available for new work
            </label>
            <label className="check">
              Capacity
              <input type="number" min="1" max="20" defaultValue={me.capacity} key={`${me.id}-${me.capacity}`} style={{ width: 70 }}
                onBlur={(e) => Number(e.target.value) !== me.capacity && saveCrew({ capacity: Number(e.target.value) })} />
            </label>
          </div>
        )}
      </Card>

      <Card title={`Assigned reports — ${crew}`}>
        <Table
          rows={reports.data}
          empty="No reports assigned to this crew"
          cols={[
            { label: "ID", key: "report_id" },
            { label: "Category", render: (r) => <Badge kind={(r.category || "").toLowerCase()}>{r.category}</Badge> },
            { label: "Zone", key: "zone" },
            { label: "Priority", render: (r) => <Priority p={r.priority} /> },
            { label: "Submitted", render: (r) => new Date(r.created_at).toLocaleString() },
            { label: "Status", render: (r) => <Badge>{r.status}</Badge> },
            { label: "Action", render: (r) => NEXT[r.status] ? <button className="btn small" onClick={() => advance(r)}>Mark {NEXT[r.status]}</button> : <span className="muted">Done</span> },
          ]}
        />
      </Card>
    </>
  );
}
