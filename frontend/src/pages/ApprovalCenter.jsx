import { useEffect, useState } from "react";
import api from "../services/api";
export default function ApprovalCenter() {
  const [rows, setRows] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(null);

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const r = await api.get("/approvals/");
      setRows(r.data.items || []);
    } catch (e) {
      setError(e.response?.data?.detail || "Unable to load approvals.");
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    load();
  }, []);

  const review = async (id, status) => {
    setBusy(id);
    setError("");
    try {
      await api.post(`/approvals/${id}/review/`, { status });
      await load();
    } catch (e) {
      setError(e.response?.data?.detail || "Review failed.");
    } finally {
      setBusy(null);
    }
  };

  const pending = rows.filter((x) => x.status === "pending").length;
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Approval Center</h1>
          <p className="text-slate-500">Review pending management approvals.</p>
        </div>
        <button className="btn-secondary" onClick={load} disabled={loading}>
          Refresh
        </button>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="card border-l-4 border-l-slate-900">
          <p className="text-sm text-slate-500">Total Requests</p>
          <p className="text-2xl font-bold mt-1">{rows.length}</p>
        </div>
        <div className="card">
          <p className="text-sm text-slate-500">Pending</p>
          <p className="text-2xl font-bold mt-1">{pending}</p>
        </div>
        <div className="card">
          <p className="text-sm text-slate-500">Completed</p>
          <p className="text-2xl font-bold mt-1">{rows.length - pending}</p>
        </div>
      </div>
      {error && <div className="alert-error">{error}</div>}
      <div className="card overflow-x-auto">
        <table className="table">
          <thead>
            <tr>
              <th>Module</th>
              <th>Action</th>
              <th>Reference</th>
              <th>Amount</th>
              <th>Status</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan="6" className="text-center py-10">
                  Loading approvals...
                </td>
              </tr>
            ) : rows.length === 0 ? (
              <tr>
                <td colSpan="6" className="text-center py-12 text-slate-500">
                  No approval requests available.
                </td>
              </tr>
            ) : (
              rows.map((x) => (
                <tr key={x.id}>
                  <td>{x.module}</td>
                  <td>{x.action}</td>
                  <td>{x.reference || "—"}</td>
                  <td>{x.amount ?? "—"}</td>
                  <td>{x.status_label || x.status}</td>
                  <td>
                    {x.status === "pending" ? (
                      <span className="flex gap-2">
                        <button
                          className="btn-primary"
                          disabled={busy === x.id}
                          onClick={() => review(x.id, "approved")}
                        >
                          {busy === x.id ? "Saving..." : "Approve"}
                        </button>
                        <button
                          className="btn-danger"
                          disabled={busy === x.id}
                          onClick={() => review(x.id, "rejected")}
                        >
                          Reject
                        </button>
                      </span>
                    ) : (
                      <span className="text-slate-500">—</span>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
