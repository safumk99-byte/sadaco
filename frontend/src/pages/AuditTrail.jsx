import { useEffect, useState } from "react";
import api from "../services/api";
export default function AuditTrail() {
  const [rows, setRows] = useState([]);
  useEffect(() => {
    api.get("/audit-log/").then((r) => setRows(r.data.items || []));
  }, []);
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Audit Trail</h1>
        <p className="text-slate-500">System activity and approval history.</p>
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
