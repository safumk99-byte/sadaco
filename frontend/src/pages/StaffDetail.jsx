import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import api from "../services/api";
export default function StaffDetail() {
  const { id } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => {
    api
      .get(`/staff/${id}/`)
      .then((r) => setData(r.data))
      .catch((e) =>
        setError(e.response?.data?.detail || "Unable to load profile."),
      );
  }, [id]);
  if (error)
    return <div className="rounded-xl bg-red-50 p-4 text-red-700">{error}</div>;
  if (!data)
    return (
      <div className="p-8 text-center text-slate-500">Loading profile...</div>
    );
  const s = data.staff;
  return (
    <div className="space-y-6">
      <Link to="/staff" className="text-sm font-medium text-slate-600">
        ← Back to Staff
      </Link>
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-5 sm:flex-row sm:items-center">
          <div className="flex h-20 w-20 items-center justify-center overflow-hidden rounded-2xl bg-slate-100 text-2xl font-bold text-slate-500">
            {s.photo ? (
              <img src={s.photo} className="h-full w-full object-cover" />
            ) : (
              s.name?.charAt(0)
            )}
          </div>
          <div className="flex-1">
            <h1 className="text-2xl font-bold">{s.name}</h1>
            <p className="text-sm text-slate-500">
              {s.staff_id} · {s.designation?.name || "Staff"} ·{" "}
              {s.work_area?.name || "No work area"}
            </p>
            <p className="mt-2 text-sm text-slate-600">
              {s.email || "No email"} · {s.phone || "No phone"}
            </p>
          </div>
          <span className="rounded-full bg-emerald-100 px-3 py-1 text-sm font-medium text-emerald-700">
            {s.status_label}
          </span>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {[
          ["KPI Score", data.kpi.score],
          ["Task Rate", `${data.kpi.task_rate}%`],
          ["Attendance", `${data.kpi.attendance_rate}%`],
          ["Avg Review", data.kpi.average_review],
        ].map(([l, v]) => (
          <div
            className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
            key={l}
          >
            <div className="text-xs uppercase text-slate-500">{l}</div>
            <div className="mt-2 text-2xl font-bold">{v}</div>
          </div>
        ))}
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <Panel title="Recent Tasks">
          <List
            items={data.tasks}
            empty="No tasks"
            render={(x) => (
              <div>
                <div className="font-medium">{x.title}</div>
                <div className="text-xs text-slate-500">
                  {x.status_label} · {x.priority_label}
                  {x.due_date ? ` · Due ${x.due_date}` : ""}
                </div>
              </div>
            )}
          />
        </Panel>
        <Panel title="Recent Attendance">
          <List
            items={data.attendance}
            empty="No attendance records"
            render={(x) => (
              <div>
                <div className="font-medium">{x.date}</div>
                <div className="text-xs text-slate-500">
                  {x.status_label}
                  {x.remarks ? ` · ${x.remarks}` : ""}
                </div>
              </div>
            )}
          />
        </Panel>
      </div>
      <Panel title="Performance Reviews">
        <List
          items={data.performance}
          empty="No performance reviews"
          render={(x) => (
            <div>
              <div className="font-medium">
                {x.review_date} · Score {x.score}/100
              </div>
              <div className="text-xs text-slate-500">
                {x.remarks || x.strengths || "No remarks"}
              </div>
            </div>
          )}
        />
      </Panel>
    </div>
  );
}
function Panel({ title, children }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-100 px-5 py-4 font-semibold">
        {title}
      </div>
      {children}
    </div>
  );
}
function List({ items, empty, render }) {
  return items.length ? (
    <div className="divide-y divide-slate-100">
      {items.map((x) => (
        <div key={x.id} className="px-5 py-4">
          {render(x)}
        </div>
      ))}
    </div>
  ) : (
    <div className="p-5 text-sm text-slate-500">{empty}</div>
  );
}
