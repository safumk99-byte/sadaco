import { useEffect, useState } from "react";
import api from "../services/api";
export default function CustomerRequests() {
  const [rows, setRows] = useState([]);
  const [error, setError] = useState("");
  const load = () =>
    api
      .get("/customer-requests/")
      .then((r) => setRows(r.data.items || []))
      .catch((e) =>
        setError(
          e.response?.data?.detail || "Unable to load customer requests.",
        ),
      );
  useEffect(load, []);
  const update = async (id, status) => {
    try {
      await api.post(`/customer-requests/${id}/update/`, { status });
      load();
    } catch (e) {
      setError(e.response?.data?.detail || "Update failed.");
    }
  };
  return (
    <div className="space-y-6">
      <div className="relative overflow-hidden rounded-[28px] bg-gradient-to-br from-blue-700 via-indigo-700 to-violet-800 p-5 text-white shadow-xl shadow-indigo-900/15 sm:p-6">
        <p className="text-xs font-bold uppercase tracking-[0.2em] text-blue-100">Sales Pipeline</p>
        <h1 className="mt-1 text-2xl font-bold tracking-tight sm:text-3xl">Customer Requests</h1>
        <p className="mt-2 text-sm text-indigo-100">Track and manage requests received through the customer portal.</p>
      </div>
      {error && <div className="alert-error">{error}</div>}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        <div className="card">
          <p className="text-xs text-slate-500">Total Requests</p>
          <p className="mt-1 text-2xl font-bold">{rows.length}</p>
        </div>
        <div className="card">
          <p className="text-xs text-slate-500">New</p>
          <p className="mt-1 text-2xl font-bold">
            {rows.filter((x) => x.status === "new").length}
          </p>
        </div>
        <div className="card">
          <p className="text-xs text-slate-500">Confirmed</p>
          <p className="mt-1 text-2xl font-bold">
            {rows.filter((x) => x.status === "confirmed").length}
          </p>
        </div>
      </div>
      <div className="card overflow-x-auto">
        <table className="table">
          <thead>
            <tr>
              <th>Request</th>
              <th>Customer</th>
              <th>Product</th>
              <th>Qty</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((x) => (
              <tr key={x.id}>
                <td>{x.request_no}</td>
                <td>{x.customer}</td>
                <td>{x.product}</td>
                <td>{x.quantity}</td>
                <td>{x.status_label}</td>
                <td>
                  <select
                    className="input"
                    value={x.status}
                    onChange={(e) => update(x.id, e.target.value)}
                  >
                    {[
                      ["new", "New"],
                      ["reviewing", "Under Review"],
                      ["contacted", "Contacted"],
                      ["quotation", "Quotation"],
                      ["confirmed", "Confirmed"],
                      ["declined", "Declined"],
                      ["cancelled", "Cancelled"],
                    ].map(([v, l]) => (
                      <option key={v} value={v}>
                        {l}
                      </option>
                    ))}
                  </select>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
