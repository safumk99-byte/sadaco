import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import api from "../services/api";

const statusLabel = {
  active: "Active",
  inactive: "Inactive",
  on_leave: "On Leave",
};

export default function StaffManagement() {
  const [data, setData] = useState({
    staff: [],
    stats: {},
    designations: [],
    work_areas: [],
    can_manage: false,
  });
  const [filters, setFilters] = useState({
    q: "",
    status: "",
    designation: "",
    work_area: "",
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState(null);

  async function load() {
    setLoading(true);
    setError("");
    try {
      const r = await api.get("/staff/", { params: filters });
      setData(r.data);
    } catch (e) {
      setError(e.response?.data?.detail || "Unable to load staff.");
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    load();
  }, [filters.q, filters.status, filters.designation, filters.work_area]);

  const stats = useMemo(() => data.stats || {}, [data.stats]);
  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">
            Staff Management
          </h1>
          <p className="text-sm text-slate-500">
            Manage staff profiles, roles, status and work assignments.
          </p>
        </div>
        {data.can_manage && (
          <button
            onClick={() => {
              setEditing(null);
              setShowForm(true);
            }}
            className="rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white"
          >
            + Add Staff
          </button>
        )}
      </div>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="Total Staff" value={stats.total ?? 0} />
        <Stat label="Active" value={stats.active ?? 0} />
        <Stat label="Inactive" value={stats.inactive ?? 0} />
        <Stat label="On Leave" value={stats.on_leave ?? 0} />
      </div>
      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="grid gap-3 md:grid-cols-4">
          <input
            value={filters.q}
            onChange={(e) => setFilters({ ...filters, q: e.target.value })}
            placeholder="Search name, username or Staff ID"
            className="rounded-xl border border-slate-300 px-3 py-2.5 text-sm outline-none focus:border-slate-500 md:col-span-2"
          />
          <select
            value={filters.status}
            onChange={(e) => setFilters({ ...filters, status: e.target.value })}
            className="rounded-xl border border-slate-300 px-3 py-2.5 text-sm"
          >
            <option value="">All Status</option>
            {Object.entries(statusLabel).map(([v, l]) => (
              <option key={v} value={v}>
                {l}
              </option>
            ))}
          </select>
          <select
            value={filters.designation}
            onChange={(e) =>
              setFilters({ ...filters, designation: e.target.value })
            }
            className="rounded-xl border border-slate-300 px-3 py-2.5 text-sm"
          >
            <option value="">All Designations</option>
            {data.designations.map((x) => (
              <option key={x.id} value={x.id}>
                {x.name}
              </option>
            ))}
          </select>
        </div>
      </div>
      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}
      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        {loading ? (
          <div className="p-8 text-center text-sm text-slate-500">
            Loading staff...
          </div>
        ) : data.staff.length === 0 ? (
          <div className="p-8 text-center text-sm text-slate-500">
            No staff members found.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase text-slate-500">
                <tr>
                  <th className="px-5 py-3">Staff</th>
                  <th className="px-5 py-3">Designation</th>
                  <th className="px-5 py-3">Work Area</th>
                  <th className="px-5 py-3">Phone</th>
                  <th className="px-5 py-3">Status</th>
                  <th className="px-5 py-3"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data.staff.map((s) => (
                  <tr key={s.id} className="hover:bg-slate-50">
                    <td className="px-5 py-4">
                      <Link
                        to={`/staff/${s.id}`}
                        className="font-semibold text-slate-900 hover:underline"
                      >
                        {s.name}
                      </Link>
                      <div className="text-xs text-slate-500">
                        {s.staff_id} · @{s.username}
                      </div>
                    </td>
                    <td className="px-5 py-4 text-slate-600">
                      {s.designation?.name || "—"}
                    </td>
                    <td className="px-5 py-4 text-slate-600">
                      {s.work_area?.name || "—"}
                    </td>
                    <td className="px-5 py-4 text-slate-600">
                      {s.phone || "—"}
                    </td>
                    <td className="px-5 py-4">
                      <span
                        className={`rounded-full px-2.5 py-1 text-xs font-medium ${s.status === "active" ? "bg-emerald-100 text-emerald-700" : s.status === "on_leave" ? "bg-amber-100 text-amber-700" : "bg-slate-100 text-slate-600"}`}
                      >
                        {s.status_label}
                      </span>
                    </td>
                    <td className="px-5 py-4 text-right">
                      <Link
                        to={`/staff/${s.id}`}
                        className="text-sm font-medium text-slate-700 hover:text-slate-950"
                      >
                        View
                      </Link>
                      {data.can_manage && (
                        <button
                          onClick={() => {
                            setEditing(s);
                            setShowForm(true);
                          }}
                          className="ml-4 text-sm font-medium text-blue-600"
                        >
                          Edit
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      {showForm && (
        <StaffForm
          initial={editing}
          data={data}
          onClose={() => setShowForm(false)}
          onSaved={() => {
            setShowForm(false);
            load();
          }}
        />
      )}
    </div>
  );
}
function Stat({ label, value }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="text-xs font-medium uppercase tracking-wide text-slate-500">
        {label}
      </div>
      <div className="mt-2 text-2xl font-bold text-slate-900">{value}</div>
    </div>
  );
}
function StaffForm({ initial, data, onClose, onSaved }) {
  const [form, setForm] = useState({
    username: initial?.username || "",
    password: "",
    first_name: initial?.first_name || "",
    last_name: initial?.last_name || "",
    email: initial?.email || "",
    staff_id: initial?.staff_id || "",
    designation: initial?.designation?.id || "",
    work_area: initial?.work_area?.id || "",
    phone: initial?.phone || "",
    joining_date: initial?.joining_date || "",
    address: initial?.address || "",
    status: initial?.status || "active",
    notes: initial?.notes || "",
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    const body = new FormData();
    Object.entries(form).forEach(([k, v]) => {
      if (v !== "" && !(k === "password" && !v)) body.append(k, v);
    });
    try {
      await api.post(
        initial ? `/staff/${initial.id}/update/` : "/staff/create/",
        body,
      );
      onSaved();
    } catch (e) {
      setError(e.response?.data?.detail || "Unable to save staff.");
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="max-h-[92vh] w-full max-w-3xl overflow-y-auto rounded-2xl bg-white p-5 shadow-xl">
        <div className="mb-5 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold">
              {initial ? "Edit Staff" : "Add Staff"}
            </h2>
            <p className="text-sm text-slate-500">
              {initial
                ? "Update the staff profile."
                : "Create a new staff account and profile."}
            </p>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg px-3 py-2 text-slate-500 hover:bg-slate-100"
          >
            ✕
          </button>
        </div>
        {error && (
          <div className="mb-4 rounded-xl bg-red-50 p-3 text-sm text-red-700">
            {error}
          </div>
        )}
        <form onSubmit={submit} className="grid gap-4 md:grid-cols-2">
          {[
            ["first_name", "First name"],
            ["last_name", "Last name"],
            ["email", "Email"],
            ["staff_id", "Staff ID"],
            ["phone", "Phone"],
            ["joining_date", "Joining date"],
            ["address", "Address"],
            ["notes", "Notes"],
          ].map(([k, l]) => (
            <label
              key={k}
              className={
                k === "address" || k === "notes" ? "md:col-span-2" : ""
              }
            >
              <span className="mb-1 block text-sm font-medium text-slate-700">
                {l}
              </span>
              <input
                type={k === "joining_date" ? "date" : "text"}
                value={form[k]}
                onChange={(e) => set(k, e.target.value)}
                className="w-full rounded-xl border border-slate-300 px-3 py-2.5"
              />
            </label>
          ))}
          <label>
            <span className="mb-1 block text-sm font-medium">Username</span>
            <input
              disabled={!!initial}
              value={form.username}
              onChange={(e) => set("username", e.target.value)}
              className="w-full rounded-xl border border-slate-300 px-3 py-2.5 disabled:bg-slate-100"
            />
          </label>
          {!initial && (
            <label>
              <span className="mb-1 block text-sm font-medium">Password</span>
              <input
                required={!initial}
                type="password"
                value={form.password}
                onChange={(e) => set("password", e.target.value)}
                className="w-full rounded-xl border border-slate-300 px-3 py-2.5"
              />
            </label>
          )}
          <label>
            <span className="mb-1 block text-sm font-medium">Designation</span>
            <select
              value={form.designation}
              onChange={(e) => set("designation", e.target.value)}
              className="w-full rounded-xl border border-slate-300 px-3 py-2.5"
            >
              <option value="">None</option>
              {data.designations.map((x) => (
                <option key={x.id} value={x.id}>
                  {x.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span className="mb-1 block text-sm font-medium">Work Area</span>
            <select
              value={form.work_area}
              onChange={(e) => set("work_area", e.target.value)}
              className="w-full rounded-xl border border-slate-300 px-3 py-2.5"
            >
              <option value="">None</option>
              {data.work_areas.map((x) => (
                <option key={x.id} value={x.id}>
                  {x.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span className="mb-1 block text-sm font-medium">Status</span>
            <select
              value={form.status}
              onChange={(e) => set("status", e.target.value)}
              className="w-full rounded-xl border border-slate-300 px-3 py-2.5"
            >
              {Object.entries(statusLabel).map(([v, l]) => (
                <option key={v} value={v}>
                  {l}
                </option>
              ))}
            </select>
          </label>
          <div className="flex justify-end gap-3 md:col-span-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-xl border border-slate-300 px-4 py-2.5"
            >
              Cancel
            </button>
            <button
              disabled={busy}
              className="rounded-xl bg-slate-900 px-5 py-2.5 font-semibold text-white disabled:opacity-50"
            >
              {busy ? "Saving..." : "Save Staff"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
