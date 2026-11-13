import { useCallback, useEffect, useState } from "react";

const BASE = import.meta.env.VITE_API_URL || "";

export async function api(path, { method = "GET", body } = {}) {
  const res = await fetch(`${BASE}/api${path}`, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  let data = null;
  try {
    data = await res.json();
  } catch {
    /* empty body */
  }
  return { ok: res.ok, status: res.status, data };
}

export function useApi(path, refreshMs = 0) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const load = useCallback(async () => {
    try {
      const r = await api(path);
      if (r.ok) {
        setData(r.data);
        setError(null);
      } else setError(r.data?.error || "Request failed");
    } catch {
      setError("Cannot reach the server");
    }
  }, [path]);
  useEffect(() => {
    load();
    if (!refreshMs) return;
    const t = setInterval(load, refreshMs);
    return () => clearInterval(t);
  }, [load, refreshMs]);
  return { data, error, reload: load };
}
