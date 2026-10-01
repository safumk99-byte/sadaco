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
  const presentCount = rows.filter((r) => String(r.status_label || "").toLowerCase().includes("present")).length;
  const absentCount = rows.filter((r) => String(r.status_label || "").toLowerCase().includes("absent")).length;

  return (
    <div className="space-y-6">
      <section className="relative overflow-hidden rounded-[28px] bg-gradient-to-br from-blue-700 via-indigo-700 to-violet-800 p-5 text-white shadow-xl shadow-indigo-900/15 sm:p-6">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-blue-100">People & Workforce</p>
            <h1 className="mt-1 text-2xl font-bold tracking-tight sm:text-3xl">My Attendance</h1>
            <p className="mt-2 max-w-2xl text-sm text-indigo-100">Review your attendance history, daily status and remarks in one place.</p>
          </div>
          <div className="rounded-2xl border border-white/20 bg-white/10 px-4 py-3 text-sm backdrop-blur-sm">
            <div className="text-blue-100">Attendance records</div>
            <div className="text-xl font-bold">{rows.length}</div>
          </div>
        </div>
      </section>

      {error && <div className="alert-error">{error}</div>}

      <div className="grid gap-4 sm:grid-cols-3">
        <div className="card border-t-4 border-t-indigo-500 p-5"><p className="text-sm text-slate-500">Total records</p><p className="mt-1 text-2xl font-bold text-slate-900">{rows.length}</p></div>
        <div className="card border-t-4 border-t-emerald-500 p-5"><p className="text-sm text-slate-500">Present</p><p className="mt-1 text-2xl font-bold text-emerald-600">{presentCount}</p></div>
        <div className="card border-t-4 border-t-rose-500 p-5"><p className="text-sm text-slate-500">Absent</p><p className="mt-1 text-2xl font-bold text-rose-600">{absentCount}</p></div>
      </div>

      <section className="card overflow-hidden">
        <div className="flex items-center justify-between gap-3 border-b border-slate-200 bg-gradient-to-r from-slate-50 to-indigo-50 px-5 py-4">
          <div><h2 className="font-bold text-slate-900">Attendance History</h2><p className="text-xs text-slate-500">Your available attendance records</p></div>
          <span className="rounded-full bg-indigo-100 px-3 py-1 text-xs font-semibold text-indigo-700">Live data</span>
        </div>
        <div className="overflow-x-auto">
          <table className="table">
            <thead><tr><th>Date</th><th>Staff</th><th>Status</th><th>Remarks</th></tr></thead>
            <tbody>
              {rows.map((r) => <tr key={r.id}><td>{r.date}</td><td>{r.staff}</td><td>{r.status_label}</td><td>{r.remarks || "—"}</td></tr>)}
              {!rows.length && <tr><td colSpan="4" className="py-12 text-center text-slate-500">No attendance records available.</td></tr>}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
