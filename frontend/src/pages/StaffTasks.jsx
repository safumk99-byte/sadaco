import { useEffect, useState } from "react";
import api from "../services/api";
export default function StaffTasks() {
  const [data, setData] = useState({ tasks: [], staff: [], can_manage: false });
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const load = () =>
    api
      .get("/staff/tasks/", { params: { status } })
      .then((r) => setData(r.data))
      .catch((e) =>
        setError(e.response?.data?.detail || "Unable to load tasks."),
      );
  useEffect(load, [status]);
  async function update(id, v) {
    try {
      await api.post(
        `/staff/tasks/${id}/status/`,
        new URLSearchParams({ status: v }),
      );
      load();
    } catch (e) {
      setError(e.response?.data?.detail || "Unable to update task.");
    }
  }
  return (
    <div className="space-y-5">
      <div className="relative overflow-hidden rounded-[28px] bg-gradient-to-br from-blue-700 via-indigo-700 to-violet-800 p-5 text-white shadow-xl shadow-indigo-900/15 sm:p-6">
        <p className="text-xs font-bold uppercase tracking-[0.2em] text-blue-100">Operations Workspace</p>
        <h1 className="mt-1 text-2xl font-bold tracking-tight sm:text-3xl">Staff Tasks</h1>
        <p className="mt-2 text-sm text-indigo-100">Track assigned work, priorities and task progress.</p>
      </div>
      <div className="flex gap-2 overflow-x-auto">
        {[
          ["", "All"],
          ["todo", "To Do"],
          ["in_progress", "In Progress"],
          ["completed", "Completed"],
          ["cancelled", "Cancelled"],
        ].map(([v, l]) => (
          <button
            key={v}
            onClick={() => setStatus(v)}
            className={`whitespace-nowrap rounded-full px-4 py-2 text-sm ${status === v ? "bg-slate-900 text-white" : "bg-white border border-slate-200"}`}
          >
            {l}
          </button>
        ))}
      </div>
      {error && (
        <div className="rounded-xl bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}
      <div className="grid gap-4 lg:grid-cols-2">
        {data.tasks.map((t) => (
          <div
            key={t.id}
            className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
          >
            <div className="flex justify-between gap-3">
              <div>
                <h3 className="font-semibold">{t.title}</h3>
                <p className="mt-1 text-sm text-slate-500">
                  {t.description || "No description"}
                </p>
              </div>
              <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs">
                {t.priority_label}
              </span>
            </div>
            <div className="mt-4 text-xs text-slate-500">
              Assigned to {t.assigned_to.name}
              {t.due_date ? ` · Due ${t.due_date}` : ""}
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              {["todo", "in_progress", "completed"]
                .filter((v) => v !== t.status)
                .map((v) => (
                  <button
                    key={v}
                    onClick={() => update(t.id, v)}
                    className="rounded-lg border border-slate-300 px-3 py-2 text-xs"
                  >
                    Mark {v.replace("_", " ")}
                  </button>
                ))}
            </div>
          </div>
        ))}
        {!data.tasks.length && (
          <div className="rounded-2xl bg-white p-8 text-center text-sm text-slate-500 lg:col-span-2">
            No tasks found.
          </div>
        )}
      </div>
    </div>
  );
}
