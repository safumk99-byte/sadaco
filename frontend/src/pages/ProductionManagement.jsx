import { useEffect, useMemo, useState } from "react";
import api from "../services/api";

const card = "rounded-2xl border border-slate-200 bg-white shadow-sm transition-shadow hover:shadow-md";
const input =
  "w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100";

export default function ProductionManagement() {
  const [jobs, setJobs] = useState([]),
    [stats, setStats] = useState({}),
    [options, setOptions] = useState({ staff: [], orders: [], products: [] }),
    [filters, setFilters] = useState({ q: "", status: "", station: "" }),
    [detail, setDetail] = useState(null),
    [showForm, setShowForm] = useState(false),
    [loading, setLoading] = useState(true),
    [error, setError] = useState("");
  const [form, setForm] = useState({
    order: "",
    station: "laser",
    stage: "planning",
    status: "pending",
    assigned_staff: "",
    priority: "normal",
    deadline: "",
    safety_checked: false,
    design_checked: false,
    material_ready: false,
    notes: "",
  });
  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const [s, j, o] = await Promise.all([
        api.get("/production/summary/"),
        api.get("/production/jobs/", { params: filters }),
        api.get("/production/options/"),
      ]);
      setStats(s.data.stats);
      setJobs(j.data.jobs);
      setOptions(o.data);
    } catch (e) {
      setError(e.response?.data?.detail || "Unable to load production data.");
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    load();
  }, []);
  useEffect(() => {
    const t = setTimeout(load, 250);
    return () => clearTimeout(t);
  }, [filters.q, filters.status, filters.station]);
  const canCreate = options.orders.length > 0;
  const save = async (e) => {
    e.preventDefault();
    setError("");
    try {
      await api.post("/production/jobs/create/", form);
      setShowForm(false);
      setForm({
        order: "",
        station: "laser",
        stage: "planning",
        status: "pending",
        assigned_staff: "",
        priority: "normal",
        deadline: "",
        safety_checked: false,
        design_checked: false,
        material_ready: false,
        notes: "",
      });
      load();
    } catch (e) {
      setError(e.response?.data?.detail || "Unable to create production job.");
    }
  };
  return (
    <div className="space-y-6">
      <div className="relative overflow-hidden rounded-[28px] bg-gradient-to-br from-blue-700 via-indigo-700 to-violet-800 p-5 text-white shadow-xl shadow-indigo-900/15 sm:p-6">
        <div className="relative flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-blue-100">Operations</p>
            <h1 className="mt-1 text-2xl font-bold tracking-tight sm:text-3xl">Production Management</h1>
            <p className="mt-1 max-w-2xl text-sm text-indigo-100">
              Plan jobs, assign staff, track stages and manage production issues.
            </p>
          </div>
          <button
            onClick={() => setShowForm(true)}
            className="rounded-xl border border-white/40 bg-white/15 px-4 py-2.5 font-semibold text-white backdrop-blur-sm transition hover:bg-white/25"
          >
            + New Production Job
          </button>
        </div>
      </div>
      {error && (
        <div className="rounded-xl bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-6">
        {[
          ["Total", stats.total],
          ["Pending", stats.pending],
          ["Active", stats.active],
          ["On Hold", stats.on_hold],
          ["Completed", stats.completed],
          ["Delayed", stats.delayed],
        ].map(([k, v]) => (
          <div className={`${card} group relative overflow-hidden p-4`} key={k}>
            <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-blue-500 via-indigo-500 to-violet-500" />
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              {k}
            </div>
            <div className="mt-2 text-2xl font-bold text-slate-900">
              {v ?? 0}
            </div>
          </div>
        ))}
      </div>
      <div className={`${card} p-4`}>
        <div className="grid gap-3 md:grid-cols-[1fr_180px_200px_auto]">
          <input
            className={input}
            placeholder="Search job, order, customer..."
            value={filters.q}
            onChange={(e) => setFilters((x) => ({ ...x, q: e.target.value }))}
          />
          <select
            className={input}
            value={filters.status}
            onChange={(e) =>
              setFilters((x) => ({ ...x, status: e.target.value }))
            }
          >
            <option value="">All statuses</option>
            {[
              "pending",
              "assigned",
              "in_progress",
              "on_hold",
              "completed",
              "cancelled",
            ].map((x) => (
              <option key={x} value={x}>
                {x.replaceAll("_", " ")}
              </option>
            ))}
          </select>
          <select
            className={input}
            value={filters.station}
            onChange={(e) =>
              setFilters((x) => ({ ...x, station: e.target.value }))
            }
          >
            <option value="">All stations</option>
            {[
              "laser",
              "cnc",
              "memento",
              "wall_decor",
              "wood_craft",
              "resin",
              "custom",
            ].map((x) => (
              <option key={x} value={x}>
                {x.replaceAll("_", " ")}
              </option>
            ))}
          </select>
          <button
            onClick={load}
            className="rounded-xl border border-indigo-200 bg-indigo-50 px-4 py-2.5 font-semibold text-indigo-700 transition hover:bg-indigo-100"
          >
            Refresh
          </button>
        </div>
      </div>
      <div className={card}>
        {loading ? (
          <div className="p-10 text-center text-sm text-slate-500">
            Loading production jobs...
          </div>
        ) : (
          <JobTable
            jobs={jobs}
            onOpen={async (id) => {
              try {
                const r = await api.get(`/production/jobs/${id}/`);
                setDetail(r.data);
              } catch (e) {
                setError(e.response?.data?.detail || "Unable to load job.");
              }
            }}
          />
        )}
      </div>
      {showForm && (
        <Modal title="Create Production Job" close={() => setShowForm(false)}>
          <form onSubmit={save} className="grid gap-4 md:grid-cols-2">
            <Select
              label="Sales Order"
              value={form.order}
              set={(v) => setForm((x) => ({ ...x, order: v }))}
              options={options.orders.map((o) => [
                o.id,
                `${o.order_no} · ${o.customer} · ${o.item_description}`,
              ])}
            />
            <Select
              label="Station"
              value={form.station}
              set={(v) => setForm((x) => ({ ...x, station: v }))}
              options={[
                "laser",
                "cnc",
                "memento",
                "wall_decor",
                "wood_craft",
                "resin",
                "custom",
              ].map((x) => [x, x.replaceAll("_", " ")])}
            />
            <Select
              label="Stage"
              value={form.stage}
              set={(v) => setForm((x) => ({ ...x, stage: v }))}
              options={[
                "planning",
                "material",
                "design_check",
                "production",
                "finishing",
                "qc_pending",
                "completed",
              ].map((x) => [x, x.replaceAll("_", " ")])}
            />
            <Select
              label="Status"
              value={form.status}
              set={(v) => setForm((x) => ({ ...x, status: v }))}
              options={[
                "pending",
                "assigned",
                "in_progress",
                "on_hold",
                "completed",
                "cancelled",
              ].map((x) => [x, x.replaceAll("_", " ")])}
            />
            <Select
              label="Assigned Staff"
              value={form.assigned_staff}
              set={(v) => setForm((x) => ({ ...x, assigned_staff: v }))}
              options={options.staff.map((s) => [s.id, s.name])}
              optional
            />
            <Select
              label="Priority"
              value={form.priority}
              set={(v) => setForm((x) => ({ ...x, priority: v }))}
              options={["normal", "high", "urgent"].map((x) => [x, x])}
            />
            <label>
              <span className="mb-1 block text-sm font-medium">Deadline</span>
              <input
                className={input}
                type="date"
                value={form.deadline}
                onChange={(e) =>
                  setForm((x) => ({ ...x, deadline: e.target.value }))
                }
              />
            </label>
            <div className="grid grid-cols-3 gap-2 rounded-xl bg-slate-50 p-3 text-sm">
              <Check
                label="Safety"
                value={form.safety_checked}
                set={(v) => setForm((x) => ({ ...x, safety_checked: v }))}
              />
              <Check
                label="Design"
                value={form.design_checked}
                set={(v) => setForm((x) => ({ ...x, design_checked: v }))}
              />
              <Check
                label="Material"
                value={form.material_ready}
                set={(v) => setForm((x) => ({ ...x, material_ready: v }))}
              />
            </div>
            <label className="md:col-span-2">
              <span className="mb-1 block text-sm font-medium">Notes</span>
              <textarea
                className={input}
                rows="3"
                value={form.notes}
                onChange={(e) =>
                  setForm((x) => ({ ...x, notes: e.target.value }))
                }
              />
            </label>
            <div className="md:col-span-2 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="rounded-xl border border-slate-300 px-4 py-2.5"
              >
                Cancel
              </button>
              <button
                disabled={!canCreate}
                className="rounded-xl bg-slate-900 px-5 py-2.5 font-semibold text-white"
              >
                Create Job
              </button>
            </div>
            {!canCreate && (
              <p className="md:col-span-2 text-sm text-amber-700">
                No confirmed/production-pending sales orders are available for
                production planning.
              </p>
            )}
          </form>
        </Modal>
      )}
      {detail && (
        <JobDetail data={detail} close={() => setDetail(null)} refresh={load} />
      )}
    </div>
  );
}
function JobTable({ jobs, onOpen }) {
  if (!jobs.length)
    return (
      <div className="p-10 text-center text-sm text-slate-500">
        No production jobs found.
      </div>
    );
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[980px] text-left text-sm">
        <thead className="bg-slate-50 text-xs uppercase text-slate-500">
          <tr>
            <th className="px-5 py-3">Job</th>
            <th>Order / Customer</th>
            <th>Station</th>
            <th>Stage</th>
            <th>Status</th>
            <th>Progress</th>
            <th>Deadline</th>
            <th></th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {jobs.map((j) => (
            <tr key={j.id} className="hover:bg-slate-50">
              <td className="px-5 py-4 font-bold">
                {j.job_no}
                <div className="text-xs font-normal text-slate-500">
                  {j.priority_label}
                </div>
              </td>
              <td>
                {j.order.order_no}
                <div className="text-xs text-slate-500">{j.order.customer}</div>
              </td>
              <td>{j.station_label}</td>
              <td>{j.stage_label}</td>
              <td>
                <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium">
                  {j.status_label}
                </span>
              </td>
              <td className="w-40">
                <div className="flex items-center gap-2">
                  <div className="h-2 flex-1 rounded-full bg-slate-200">
                    <div
                      className="h-2 rounded-full bg-slate-900"
                      style={{ width: `${j.progress_percent}%` }}
                    />
                  </div>
                  <span className="text-xs font-semibold">
                    {j.progress_percent}%
                  </span>
                </div>
              </td>
              <td>{j.deadline || "—"}</td>
              <td className="px-5 text-right">
                <button
                  onClick={() => onOpen(j.id)}
                  className="font-semibold text-blue-600"
                >
                  Open
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
function JobDetail({ data, close, refresh }) {
  const j = data.job;
  const [progress, setProgress] = useState({
    stage: j.stage,
    progress_percent: j.progress_percent,
    note: "",
  });
  const [issue, setIssue] = useState({
    issue_type: "delay",
    stage: j.stage,
    reason: "",
    corrective_action: "",
    staff: "",
  });
  const [material, setMaterial] = useState({
    product: "",
    material_name: "",
    quantity_required: "1",
    unit: "Piece",
    issued_quantity: "0",
    notes: "",
  });
  const [busy, setBusy] = useState(false);
  const saveProgress = async () => {
    setBusy(true);
    try {
      await api.post(`/production/jobs/${j.id}/progress/`, progress);
      refresh();
      close();
    } finally {
      setBusy(false);
    }
  };
  const saveIssue = async () => {
    if (!issue.reason) return;
    await api.post(`/production/jobs/${j.id}/issues/`, issue);
    refresh();
    close();
  };
  const saveMaterial = async () => {
    if (!material.material_name) return;
    await api.post(`/production/jobs/${j.id}/materials/`, material);
    refresh();
    close();
  };
  return (
    <Modal title={`${j.job_no} · ${j.order.customer}`} close={close}>
      <div className="space-y-5">
        <div className="grid gap-3 sm:grid-cols-4">
          {[
            ["Status", j.status_label],
            ["Stage", j.stage_label],
            ["Progress", `${j.progress_percent}%`],
            ["Deadline", j.deadline || "—"],
          ].map((x) => (
            <div key={x[0]} className="rounded-xl bg-slate-50 p-3">
              <div className="text-xs uppercase text-slate-500">{x[0]}</div>
              <div className="mt-1 font-bold">{x[1]}</div>
            </div>
          ))}
        </div>
        <div>
          <h3 className="mb-2 font-bold">Update Progress</h3>
          <div className="grid gap-3 md:grid-cols-3">
            <select
              className={input}
              value={progress.stage}
              onChange={(e) =>
                setProgress((x) => ({ ...x, stage: e.target.value }))
              }
            >
              {[
                "planning",
                "material",
                "design_check",
                "production",
                "finishing",
                "qc_pending",
                "completed",
              ].map((x) => (
                <option key={x} value={x}>
                  {x.replaceAll("_", " ")}
                </option>
              ))}
            </select>
            <input
              className={input}
              type="number"
              min="0"
              max="100"
              value={progress.progress_percent}
              onChange={(e) =>
                setProgress((x) => ({
                  ...x,
                  progress_percent: Number(e.target.value),
                }))
              }
            />
            <input
              className={input}
              placeholder="Progress note"
              value={progress.note}
              onChange={(e) =>
                setProgress((x) => ({ ...x, note: e.target.value }))
              }
            />
          </div>
          <button
            disabled={busy}
            onClick={saveProgress}
            className="mt-3 rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white"
          >
            Save Progress
          </button>
        </div>
        <div>
          <h3 className="mb-2 font-bold">Materials</h3>
          <div className="grid gap-2 md:grid-cols-5">
            <input
              className={input}
              placeholder="Material name"
              value={material.material_name}
              onChange={(e) =>
                setMaterial((x) => ({ ...x, material_name: e.target.value }))
              }
            />
            <input
              className={input}
              type="number"
              placeholder="Required"
              value={material.quantity_required}
              onChange={(e) =>
                setMaterial((x) => ({
                  ...x,
                  quantity_required: e.target.value,
                }))
              }
            />
            <input
              className={input}
              placeholder="Unit"
              value={material.unit}
              onChange={(e) =>
                setMaterial((x) => ({ ...x, unit: e.target.value }))
              }
            />
            <input
              className={input}
              type="number"
              placeholder="Issued"
              value={material.issued_quantity}
              onChange={(e) =>
                setMaterial((x) => ({ ...x, issued_quantity: e.target.value }))
              }
            />
            <button
              onClick={saveMaterial}
              className="rounded-xl bg-slate-100 px-3 py-2 font-semibold"
            >
              Add
            </button>
          </div>
          <div className="mt-3 space-y-2">
            {data.materials.map((m) => (
              <div
                key={m.id}
                className="flex justify-between rounded-xl bg-slate-50 p-3 text-sm"
              >
                <span>
                  {m.material_name} · {m.quantity_required} {m.unit}
                </span>
                <span>
                  Issued {m.issued_quantity} · Pending {m.pending_quantity}
                </span>
              </div>
            ))}
          </div>
        </div>
        <div>
          <h3 className="mb-2 font-bold">Issues / Delays</h3>
          <div className="grid gap-2 md:grid-cols-4">
            <select
              className={input}
              value={issue.issue_type}
              onChange={(e) =>
                setIssue((x) => ({ ...x, issue_type: e.target.value }))
              }
            >
              <option value="delay">Delay</option>
              <option value="rework">Rework</option>
            </select>
            <select
              className={input}
              value={issue.stage}
              onChange={(e) =>
                setIssue((x) => ({ ...x, stage: e.target.value }))
              }
            >
              {[
                "planning",
                "material",
                "design_check",
                "production",
                "finishing",
                "qc_pending",
                "completed",
              ].map((x) => (
                <option key={x} value={x}>
                  {x.replaceAll("_", " ")}
                </option>
              ))}
            </select>
            <input
              className={input}
              placeholder="Reason"
              value={issue.reason}
              onChange={(e) =>
                setIssue((x) => ({ ...x, reason: e.target.value }))
              }
            />
            <button
              onClick={saveIssue}
              className="rounded-xl bg-slate-100 px-3 py-2 font-semibold"
            >
              Record
            </button>
          </div>
          <div className="mt-3 space-y-2">
            {data.issues.map((i) => (
              <div key={i.id} className="rounded-xl bg-amber-50 p-3 text-sm">
                <b>{i.issue_type_label}</b> · {i.stage_label}
                <div>{i.reason}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </Modal>
  );
}
function Modal({ title, close, children }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="max-h-[94vh] w-full max-w-6xl overflow-y-auto rounded-2xl bg-white p-5 shadow-xl">
        <div className="mb-5 flex items-center justify-between">
          <h2 className="text-xl font-bold">{title}</h2>
          <button
            onClick={close}
            className="rounded-lg px-3 py-2 text-slate-500 hover:bg-slate-100"
          >
            ✕
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
function Select({ label, value, set, options, optional = false }) {
  return (
    <label>
      <span className="mb-1 block text-sm font-medium">{label}</span>
      <select
        required={!optional}
        className={input}
        value={value || ""}
        onChange={(e) => set(e.target.value)}
      >
        <option value="">Select {label}</option>
        {options.map(([v, l]) => (
          <option key={v} value={v}>
            {l}
          </option>
        ))}
      </select>
    </label>
  );
}
function Check({ label, value, set }) {
  return (
    <label className="flex items-center gap-2">
      <input
        type="checkbox"
        checked={value}
        onChange={(e) => set(e.target.checked)}
      />
      {label}
    </label>
  );
}
