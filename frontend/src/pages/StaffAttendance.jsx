import { useEffect, useState } from "react";
import api from "../services/api";
export default function StaffAttendance() {
  const [rows, setRows] = useState([]);
  const [error, setError] = useState("");
  useEffect(() => {
    api
      .get("/staff/attendance/")
      .then((r) => setRows(r.data.records || []))
      .catch((e) =>
        setError(e.response?.data?.detail || "Unable to load attendance."),
      );
  }, []);
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">My Attendance</h1>
        <p className="text-slate-500">
          Attendance records available to your account.
        </p>
      </div>
      {error && <div className="alert-error">{error}</div>}
      <div className="card overflow-x-auto">
        <table className="table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Staff</th>
              <th>Status</th>
              <th>Remarks</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id}>
                <td>{r.date}</td>
                <td>{r.staff}</td>
                <td>{r.status_label}</td>
                <td>{r.remarks || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
