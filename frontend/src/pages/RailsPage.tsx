import { useEffect, useState } from "react";
import { api } from "../api/client";
type R = { id: number; store_id: number; label: string; length_cm: number; blocked: boolean };
export default function RailsPage() {
  const [rows, setRows] = useState<R[]>([]);
  const [busy, setBusy] = useState<number | null>(null);
  const [msg, setMsg] = useState(""); const [err, setErr] = useState("");
  const reload = () => api<R[]>("/rails").then(setRows);
  useEffect(() => { reload(); }, []);
  async function toggle(r: R) {
    setBusy(r.id); setMsg(""); setErr("");
    try {
      const next = !r.blocked;
      const updated = await api<R>(`/rails/${r.id}/block`, { method: "PATCH", body: JSON.stringify({ blocked: next }) });
      setRows(prev => prev.map(x => x.id === updated.id ? updated : x));
      setMsg(`${r.label}已${next ? "设为检修封锁" : "解除封锁，恢复可挂"}`);
    } catch (e) { setErr(e instanceof Error ? e.message : String(e)); }
    finally { setBusy(null); }
  }
  return (<>
    <h2>挂杆</h2>
    <p className="hint">检修封锁期间，任何工单不得新上到该杆；已在该杆上的衣物仍可在取件页取件释放。</p>
    {msg && <div className="ok">{msg}</div>}
    {err && <div className="err">{err}</div>}
    <table className="table"><thead><tr><th>标签</th><th>门店</th><th>长度 cm</th><th>检修状态</th><th></th></tr></thead>
    <tbody>{rows.map(r => <tr key={r.id} className={r.blocked ? "row-blocked" : ""}>
      <td>{r.label}</td><td>{r.store_id}</td><td className="mono">{r.length_cm}</td>
      <td>{r.blocked
        ? <span className="badge badge-blocked">检修封锁中</span>
        : <span className="badge badge-ok">正常可挂</span>}</td>
      <td><button className={r.blocked ? "btn-unblock" : "btn-block"} disabled={busy === r.id} onClick={() => toggle(r)}>
        {r.blocked ? "解除封锁" : "封锁检修"}
      </button></td>
    </tr>)}</tbody></table>
  </>);
}
