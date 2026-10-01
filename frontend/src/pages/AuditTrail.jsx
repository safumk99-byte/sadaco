import { useEffect, useState } from "react";
import api from "../services/api";
export default function AuditTrail() {
  const [rows, setRows] = useState([]);
  useEffect(() => {
    api.get("/audit-log/").then((r) => setRows(r.data.items || []));
  }, []);
  return (
    <div className="space-y-6">
      <div className="relative overflow-hidden rounded-[28px] bg-gradient-to-br from-blue-700 via-indigo-700 to-violet-800 p-5 text-white shadow-xl shadow-indigo-900/15 sm:p-6">
        <p className="text-xs font-bold uppercase tracking-[0.2em] text-blue-100">Governance & Security</p>
        <h1 className="mt-1 text-2xl font-bold tracking-tight sm:text-3xl">Audit Trail</h1>
        <p className="mt-2 text-sm text-indigo-100">System activity, approvals and accountability history.</p>
      </div>
      <div className="card overflow-x-auto">
        <table className="table">
          <thead>
            <tr>
              <th>Time</th>
              <th>User</th>
              <th>Module</th>
              <th>Action</th>
              <th>Reference</th>
              <th>Description</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((x) => (
              <tr key={x.id}>
                <td>{new Date(x.created_at).toLocaleString()}</td>
                <td>{x.user || "System"}</td>
                <td>{x.module}</td>
                <td>{x.action_label}</td>
                <td>{x.reference || "—"}</td>
                <td>{x.description || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
