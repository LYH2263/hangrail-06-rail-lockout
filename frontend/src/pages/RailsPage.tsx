import { useEffect, useState } from "react";
import { api } from "../api/client";
type R = { id: number; store_id: number; label: string; length_cm: number; maintenance: boolean };
export default function RailsPage() {
  const [rows, setRows] = useState<R[]>([]);
  const [msg, setMsg] = useState(""); const [err, setErr] = useState("");
  const [busy, setBusy] = useState<number | null>(null);
  const reload = () => api<R[]>("/rails").then(setRows);
  useEffect(() => { reload(); }, []);
  async function toggle(r: R) {
    setMsg(""); setErr(""); setBusy(r.id);
    try {
      const next = !r.maintenance;
      const updated = await api<R>(`/rails/${r.id}/maintenance`, {
        method: "POST",
        body: JSON.stringify({ maintenance: next }),
      });
      setMsg(next ? `${updated.label} 已封锁检修，暂不可上杆` : `${updated.label} 已解除封锁，恢复可挂`);
      await reload();
    } catch (e) { setErr(e instanceof Error ? e.message : String(e)); }
    finally { setBusy(null); }
  }
  return (<>
    <h2>挂杆</h2>
    {msg && <div className="ok">{msg}</div>}
    {err && <div className="err">{err}</div>}
    <table className="table"><thead><tr><th>标签</th><th>门店</th><th>长度 cm</th><th>状态</th><th></th></tr></thead>
    <tbody>{rows.map(r => <tr key={r.id} className={r.maintenance ? "row-locked" : undefined}>
      <td>{r.label}</td><td>{r.store_id}</td><td className="mono">{r.length_cm}</td>
      <td>{r.maintenance
        ? <span className="badge-maint">检修中</span>
        : <span className="badge-ok">可挂</span>}</td>
      <td><button disabled={busy === r.id} onClick={() => toggle(r)}>
        {r.maintenance ? "解除封锁" : "封锁检修"}
      </button></td>
    </tr>)}</tbody></table>
  </>);
}
