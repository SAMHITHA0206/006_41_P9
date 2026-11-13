import React, { useEffect, useState } from "react";
import { api } from "../api.js";
import { Badge, Card, Priority } from "../components.jsx";

const empty = { reporter_name: "", reporter_contact: "", meter_id: "", reading: "", code: "", description: "", urgency: "Medium" };

function Field({ label, error, ok, hint, children }) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
      {error ? <small className="err">{error}</small> : ok ? <small className="ok">{ok}</small> : hint ? <small className="muted">{hint}</small> : null}
    </label>
  );
}

export default function SubmitReport() {
  const [form, setForm] = useState(empty);
  const [preview, setPreview] = useState(null);
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  // live (debounced) validation + classification preview
  useEffect(() => {
    const t = setTimeout(async () => {
      const r = await api("/validate", { method: "POST", body: form });
      if (r.ok) setPreview(r.data);
    }, 250);
    return () => clearTimeout(t);
  }, [form]);

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    const r = await api("/reports", { method: "POST", body: form });
    setBusy(false);
    setResult({ status: r.status, ...r.data });
    if (r.status === 201) setForm(empty);
  }

  const meterErr = form.meter_id && preview && !preview.meter.valid ? preview.meter.message : null;
  const meterOk = form.meter_id && preview?.meter.valid ? "Valid meter ID (DFA and regex agree)" : null;
  const readErr = form.reading && preview && !preview.reading.valid ? preview.reading.message : null;
  const readOk = form.reading && preview?.reading.valid ? "Valid reading" : null;
  const cls = preview?.classification;

  return (
    <div className="grid two">
      <Card title="Submit an anomaly report">
        <form onSubmit={submit} noValidate>
          <div className="grid two tight">
            <Field label="Reporter name *"><input value={form.reporter_name} onChange={set("reporter_name")} placeholder="Inspector name" /></Field>
            <Field label="Contact"><input value={form.reporter_contact} onChange={set("reporter_contact")} placeholder="Phone or email" /></Field>
          </div>
          <Field label="Meter ID *" error={meterErr} ok={meterOk} hint="Format: GRID + letter + 3 digits + phase (R/Y/B), e.g. GRIDA123R">
            <input value={form.meter_id} onChange={set("meter_id")} placeholder="GRIDA123R" autoCapitalize="characters" />
          </Field>
          <Field label="Reading *" error={readErr} ok={readOk} hint="Format: 5 digits . 2 digits kWh, e.g. 01234.56kWh">
            <input value={form.reading} onChange={set("reading")} placeholder="01234.56kWh" />
          </Field>
          <div className="grid two tight">
            <Field label="Report code" hint="TMP, OUT, OVR, HWF, COM (optional)">
              <input value={form.code} onChange={set("code")} placeholder="TMP" />
            </Field>
            <Field label="Urgency *">
              <select value={form.urgency} onChange={set("urgency")}>
                {["Low", "Medium", "High", "Critical"].map((u) => <option key={u}>{u}</option>)}
              </select>
            </Field>
          </div>
          <Field label="Description *">
            <textarea rows={4} value={form.description} onChange={set("description")} placeholder="What did the inspector observe?" />
          </Field>
          <button className="btn primary" disabled={busy}>{busy ? "Submitting…" : "Submit report"}</button>
        </form>
      </Card>

      <div>
        <Card title="Live detection">
          <dl className="kv">
            <dt>Category</dt>
            <dd>{cls?.category ? <Badge kind={cls.category.toLowerCase()}>{cls.category}</Badge> : <span className="muted">{form.description || form.code ? "Not classified" : "—"}</span>}</dd>
            <dt>Priority</dt><dd><Priority p={form.urgency && preview?.priority} /></dd>
            <dt>Zone / Crew</dt><dd>{preview?.zone ? `${preview.zone} · ${preview.crew}` : preview?.routing_key ? "Unknown zone → correction queue" : "—"}</dd>
          </dl>
          {cls && <p className="muted small">{cls.message}</p>}
        </Card>

        {result && (
          <Card title={result.status === 201 ? "Report submitted" : "Report rejected"}>
            {result.status === 201 ? (
              <dl className="kv">
                <dt>Report ID</dt><dd><b>{result.report.report_id}</b></dd>
                <dt>Category</dt><dd>{result.report.category || "Unclassified"}</dd>
                <dt>Priority</dt><dd><Priority p={result.report.priority} /></dd>
                <dt>Status</dt><dd><Badge>{result.report.status}</Badge></dd>
                <dt>Assigned to</dt><dd>{result.report.assigned_crew || result.report.queue || "—"}</dd>
                <dt>Decision</dt><dd>{result.report.routing_note}</dd>
              </dl>
            ) : (
              <>
                <p>Saved as <b>{result.report?.report_id}</b> but not dispatched:</p>
                <ul>{Object.entries(result.errors || {}).map(([k, m]) => <li key={k}>{m}</li>)}</ul>
              </>
            )}
          </Card>
        )}
      </div>
    </div>
  );
}
