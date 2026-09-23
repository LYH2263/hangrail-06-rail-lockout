import { useEffect, useState } from "react";
import { api } from "../api/client";
type Rail = { id: number; label: string; length_cm: number; blocked: boolean };
type Occ = { rail_id: number; label: string; length_cm: number; segments: { ticket_code: string; garment_name: string; start_cm: number; end_cm: number }[] };
export default function OccupancyPage() {
  const [rails, setRails] = useState<Rail[]>([]);
  const [maps, setMaps] = useState<Occ[]>([]);
  useEffect(() => {
    api<Rail[]>("/rails").then(async rs => {
      setRails(rs);
      const all = await Promise.all(rs.map(r => api<Occ>(`/occupancy/${r.id}`)));
      setMaps(all);
    });
  }, []);
  const blockedMap = new Map(rails.map(r => [r.id, r.blocked]));
  return (<>
    <h2>占位图（横向尺线）</h2>
    {maps.map(m => (
      <div className="ruler-wrap" key={m.rail_id}>
        <div className="ruler-label">
          <span>{m.label}{blockedMap.get(m.rail_id) && <span className="badge badge-blocked badge-inline">检修封锁中 · 禁止上新</span>}</span>
          <span className="mono">0 — {m.length_cm} cm</span>
        </div>
        <div className={`ruler${blockedMap.get(m.rail_id) ? " ruler-blocked" : ""}`}>
          {m.segments.map((s, i) => (
            <div key={i} className="seg" style={{ left: `${(s.start_cm / m.length_cm) * 100}%`, width: `${((s.end_cm - s.start_cm) / m.length_cm) * 100}%` }}
              title={`${s.ticket_code} ${s.start_cm}-${s.end_cm}cm`}>
              {s.garment_name}
            </div>
          ))}
        </div>
      </div>
    ))}
    {!rails.length && <p>暂无挂杆</p>}
  </>);
}
