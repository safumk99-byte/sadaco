import { useEffect, useState } from "react";
import api from "../services/api";
export default function StaffPerformance() {
  const [rows, setRows] = useState([]);
  useEffect(() => {
    api.get("/staff/performance/").then((r) => setRows(r.data.records || []));
  }, []);
  return (
    <div className="space-y-6">
      <div className="relative overflow-hidden rounded-[28px] bg-gradient-to-br from-blue-700 via-indigo-700 to-violet-800 p-5 text-white shadow-xl shadow-indigo-900/15 sm:p-6">
        <p className="text-xs font-bold uppercase tracking-[0.2em] text-blue-100">People & Workforce</p>
        <h1 className="mt-1 text-2xl font-bold tracking-tight sm:text-3xl">My Performance</h1>
        <p className="mt-2 text-sm text-indigo-100">Performance reviews, scores and development insights.</p>
      </div>
      <div className="card overflow-x-auto">
        <table className="table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Staff</th>
              <th>Score</th>
              <th>Strengths</th>
              <th>Improvements</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id}>
                <td>{r.review_date}</td>
                <td>{r.staff}</td>
                <td>{r.score}/100</td>
                <td>{r.strengths || "—"}</td>
                <td>{r.improvements || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
