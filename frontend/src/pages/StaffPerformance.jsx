import { useEffect, useState } from "react";
import api from "../services/api";
export default function StaffPerformance() {
  const [rows, setRows] = useState([]);
  useEffect(() => {
    api.get("/staff/performance/").then((r) => setRows(r.data.records || []));
  }, []);
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">My Performance</h1>
        <p className="text-slate-500">Performance reviews and scores.</p>
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
