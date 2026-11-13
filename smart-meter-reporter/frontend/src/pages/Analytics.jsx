import React from "react";
import { useApi } from "../api.js";
import { BarChart, Card, Donut, Err, LineChart, Stat } from "../components.jsx";

export default function Analytics() {
  const { data, error } = useApi("/analytics", 5000);

  return (
    <>
      <Err msg={error} />
      <div className="stats">
        <Stat label="Resolved" value={data?.resolved} tone="ok" />
        <Stat label="Unresolved" value={data?.unresolved} tone="warn" />
        <Stat label="Rejected (invalid)" value={data?.rejected} tone="bad" />
      </div>

      <div className="grid two">
        <Card title="Reports by zone"><BarChart data={data?.by_zone} /></Card>
        <Card title="Reports by category"><BarChart data={data?.by_category} colorVar="--accent2" /></Card>
        <Card title="Reports by priority"><BarChart data={data?.by_priority} colorVar="--warn" /></Card>
        <Card title="Resolved vs unresolved"><Donut resolved={data?.resolved || 0} unresolved={data?.unresolved || 0} /></Card>
      </div>

      <div className="grid two">
        <Card title="Status trend"><LineChart data={data?.by_status} colorVar="--info" /></Card>
        <Card title="Zone breakdown"><BarChart data={data?.by_zone} colorVar="--ok" /></Card>
      </div>

      <Card title="Reports by status (all)"><BarChart data={data?.by_status} colorVar="--info" /></Card>
    </>
  );
}
