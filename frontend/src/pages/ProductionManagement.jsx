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
        <JobDetail data={detail} materials={options.materials || []} close={() => setDetail(null)} refresh={load} />
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
function JobDetail({ data, materials, close, refresh }) {
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
    material_variant: "",
    material_name: "",
    quantity_required: "1",
    unit: "Piece",
    notes: "",
  });
  const [busy, setBusy] = useState(false);
  const [stockBalances, setStockBalances] = useState([]);
  const [stockLots, setStockLots] = useState([]);
  const [issueForm, setIssueForm] = useState({ material_line: "", balance: "", lot: "", quantity: "1" });
  const [issueError, setIssueError] = useState("");
  const [usageForm, setUsageForm] = useState({ material_issue: "", action: "return", quantity: "1" });
  const [usageError, setUsageError] = useState("");
  const [usageBusy, setUsageBusy] = useState(false);
  const [offcuts, setOffcuts] = useState([]);
  const [offcutError, setOffcutError] = useState("");
  const [offcutForm, setOffcutForm] = useState({ source_issue: "", location: "", length_mm: "", width_mm: "", usable_area_sqft: "" });
  const [offcutUsageForm, setOffcutUsageForm] = useState({ offcut: "", material_line: "", used_area_sqft: "" });
  const [jobCostSummary, setJobCostSummary] = useState(data.material_costs || null);
  const reloadOffcutData = async () => {
    const [offcutResponse, jobResponse] = await Promise.all([
      api.get("/inventory/materials/offcuts/"),
      api.get(`/production/jobs/${j.id}/`),
    ]);
    setOffcuts(offcutResponse.data.items || []);
    setJobCostSummary(jobResponse.data.material_costs || null);
  };
  useEffect(() => {
    api.get("/inventory/materials/stock/")
      .then((r) => setStockBalances(r.data.items || []))
      .catch((e) => setIssueError(e.response?.data?.detail || "Unable to load material stock."));
  }, []);
  useEffect(() => {
    api.get("/inventory/materials/offcuts/")
      .then((r) => setOffcuts(r.data.items || []))
      .catch((e) => setOffcutError(e.response?.data?.detail || "Unable to load reusable offcuts."));
  }, []);
  useEffect(() => {
    if (!issueForm.balance) { setStockLots([]); return; }
    api.get("/inventory/materials/lots/", { params: { balance: issueForm.balance } })
      .then((r) => setStockLots(r.data.items || []))
      .catch((e) => setIssueError(e.response?.data?.detail || "Unable to load receipt batches."));
  }, [issueForm.balance]);
  const selectedMaterialLine = data.materials.find((m) => String(m.id) === String(issueForm.material_line));
  const eligibleBalances = stockBalances.filter((b) => b.material_id === selectedMaterialLine?.material_variant_id);
  const submitMaterialIssue = async () => {
    setIssueError("");
    try {
      await api.post("/inventory/materials/issues/create/", issueForm);
      refresh();
      close();
    } catch (e) {
      setIssueError(e.response?.data?.detail || "Unable to issue material.");
    }
  };
  const submitUsageAdjustment = async () => {
    const selected = (data.material_issues || []).find((x) => String(x.id) === String(usageForm.material_issue));
    if (!selected || !selected.trackable) {
      setUsageError("Select a receipt-tracked material issue.");
      return;
    }
    setUsageBusy(true);
    setUsageError("");
    try {
      const endpoint = usageForm.action === "return"
        ? "/inventory/materials/returns/create/"
        : "/inventory/materials/wastage/create/";
      await api.post(endpoint, {
        material_issue: selected.id,
        material_line: selected.material_line,
        quantity: usageForm.quantity,
      });
      refresh();
      close();
    } catch (e) {
      setUsageError(e.response?.data?.detail || "Unable to record material usage.");
    } finally {
      setUsageBusy(false);
    }
  };
  const selectedOffcut = offcuts.find((x) => String(x.id) === String(offcutUsageForm.offcut));
  const matchingOffcutLines = data.materials.filter((m) => m.material_variant_id === selectedOffcut?.material_id);
  const createOffcut = async () => {
    setOffcutError("");
    const source = (data.material_issues || []).find((x) => String(x.id) === String(offcutForm.source_issue));
    if (!source?.material_variant_id) {
      setOffcutError("Select a receipt-costed issue linked to a material master.");
      return;
    }
    try {
      await api.post("/inventory/materials/offcuts/create/", {
        material: source.material_variant_id,
        source_issue: source.id,
        location: offcutForm.location,
        length_mm: offcutForm.length_mm,
        width_mm: offcutForm.width_mm,
        usable_area_sqft: offcutForm.usable_area_sqft,
      });
      await reloadOffcutData();
      setOffcutForm({ source_issue: "", location: "", length_mm: "", width_mm: "", usable_area_sqft: "" });
    } catch (e) {
      setOffcutError(e.response?.data?.detail || "Unable to register reusable offcut.");
    }
  };
  const useOffcut = async () => {
    setOffcutError("");
    try {
      await api.post(`/inventory/materials/offcuts/${offcutUsageForm.offcut}/action/`, {
        action: "used",
        job: j.id,
        material_line: offcutUsageForm.material_line,
        used_area_sqft: offcutUsageForm.used_area_sqft,
      });
      await reloadOffcutData();
      setOffcutUsageForm({ offcut: "", material_line: "", used_area_sqft: "" });
    } catch (e) {
      setOffcutError(e.response?.data?.detail || "Unable to allocate offcut to this job.");
    }
  };
  const discardOffcut = async (offcutId) => {
    setOffcutError("");
    try {
      await api.post(`/inventory/materials/offcuts/${offcutId}/action/`, { action: "discarded" });
      await reloadOffcutData();
    } catch (e) {
      setOffcutError(e.response?.data?.detail || "Unable to discard offcut.");
    }
  };
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
        {jobCostSummary && (
          <div className="rounded-xl border border-slate-200 p-4">
            <h3 className="font-bold">Material Cost Summary</h3>
            <p className="mt-1 text-xs text-slate-500">Receipt-backed material costs, reusable offcut value transfers and discard write-offs. Unpriced legacy issues are excluded.</p>
            <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
              {[
                ["Issued material", jobCostSummary.issued_material_cost],
                ["Returned credit", jobCostSummary.returned_material_credit],
                ["Offcut salvage credit", jobCostSummary.offcut_salvage_credit],
                ["Offcut discard write-off", jobCostSummary.offcut_discard_writeoff],
                ["Offcut consumed here", jobCostSummary.offcut_consumed_cost],
                ["Reusable offcut stock value", jobCostSummary.offcut_inventory_value],
                ["Net material cost", jobCostSummary.net_material_cost],
              ].map(([label, value]) => (
                <div key={label} className="rounded-lg bg-slate-50 p-3">
                  <div className="text-xs text-slate-500">{label}</div>
                  <div className="mt-1 font-bold tabular-nums">₹{Number(value || 0).toFixed(2)}</div>
                </div>
              ))}
            </div>
            <div className="mt-2 text-xs text-slate-500">
              Offcuts generated here: {jobCostSummary.offcut_registered_area_sqft} sq ft · {jobCostSummary.generated_offcut_transferred_area_sqft} sq ft transferred out · {jobCostSummary.offcut_discarded_area_sqft} sq ft discarded · {jobCostSummary.offcut_consumed_here_area_sqft} sq ft received from other jobs
              {Number(jobCostSummary.unpriced_issue_count) > 0 && <span className="ml-2 text-amber-700">· {jobCostSummary.unpriced_issue_count} legacy issue(s) have no recorded cost</span>}
            </div>
          </div>
        )}
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
          <div className="grid gap-2 md:grid-cols-4">
            <select
              className={input}
              value={material.material_variant}
              onChange={(e) => {
                const selected = materials.find((item) => String(item.id) === e.target.value);
                setMaterial((x) => ({
                  ...x,
                  material_variant: e.target.value,
                  material_name: selected?.name || x.material_name,
                  unit: selected?.unit || x.unit,
                }));
              }}
            >
              <option value="">Choose Material Master (optional)</option>
              {materials.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name} · {item.brand}{item.thickness_mm ? ` · ${item.thickness_mm} mm` : ""}
                </option>
              ))}
            </select>
            <input
              className={input}
              placeholder="Material name"
              value={material.material_name}
              onChange={(e) =>
                setMaterial((x) => ({ ...x, material_name: e.target.value, material_variant: "" }))
              }
            />
            <input
              className={input}
              type="number"
              min="0.01"
              step="0.01"
              placeholder="Required quantity"
              value={material.quantity_required}
              onChange={(e) =>
                setMaterial((x) => ({ ...x, quantity_required: e.target.value }))
              }
            />
            <button
              onClick={saveMaterial}
              className="rounded-xl bg-slate-100 px-3 py-2 font-semibold"
            >
              Add
            </button>
          </div>
          <p className="mt-1 text-xs text-slate-500">
            Issued quantity is updated only through the stock issue workflow; it cannot be entered manually.
          </p>
          <div className="mt-3 space-y-2">
            {data.materials.map((m) => (
              <div
                key={m.id}
                className="flex justify-between rounded-xl bg-slate-50 p-3 text-sm"
              >
                <span>
                  {m.material_name} · {m.quantity_required} {m.unit}
                </span>
                <span className="text-right">
                  <span className="block">Issued {m.issued_quantity} · Pending {m.pending_quantity}</span>
                  {Number(m.offcut_consumed_area_sqft || 0) > 0 && (
                    <span className="block text-xs text-emerald-700">
                      Offcut {m.offcut_consumed_area_sqft} sq ft · {m.offcut_equivalent_quantity} {m.unit} equivalent
                    </span>
                  )}
                </span>
              </div>
            ))}
          </div>
          <div className="mt-4 rounded-xl border border-indigo-100 bg-indigo-50/60 p-4">
            <h4 className="font-semibold text-slate-900">Issue from receipt batch</h4>
            <p className="mt-1 text-xs text-slate-600">Select a material line, stock location and exact purchase receipt batch. The batch purchase cost is recorded against this issue.</p>
            <div className="mt-3 grid gap-2 md:grid-cols-4">
              <select className={input} value={issueForm.material_line} onChange={(e) => setIssueForm({ material_line: e.target.value, balance: "", lot: "", quantity: "1" })}>
                <option value="">Select material line</option>
                {data.materials.filter((m) => m.material_variant_id).map((m) => <option key={m.id} value={m.id}>{m.material_name} · Pending {m.pending_quantity} {m.unit}</option>)}
              </select>
              <select className={input} value={issueForm.balance} onChange={(e) => setIssueForm((x) => ({ ...x, balance: e.target.value, lot: "" }))} disabled={!issueForm.material_line}>
                <option value="">Select location</option>
                {eligibleBalances.map((b) => <option key={b.id} value={b.id}>{b.department} · {b.location} · Available {b.quantity} {b.unit}</option>)}
              </select>
              <select className={input} value={issueForm.lot} onChange={(e) => setIssueForm((x) => ({ ...x, lot: e.target.value }))} disabled={!issueForm.balance}>
                <option value="">Select receipt batch</option>
                {stockLots.map((lot) => <option key={lot.id} value={lot.id}>{lot.receipt_no} · {lot.received_date} · {lot.remaining_quantity} available · ₹{lot.unit_cost}/{selectedMaterialLine?.unit || "unit"}</option>)}
              </select>
              <input className={input} type="number" min="0.001" step="0.001" value={issueForm.quantity} onChange={(e) => setIssueForm((x) => ({ ...x, quantity: e.target.value }))} placeholder="Issue quantity" />
            </div>
            {issueError && <p className="mt-2 text-sm text-red-700">{issueError}</p>}
            <button onClick={submitMaterialIssue} disabled={!issueForm.material_line || !issueForm.balance || !issueForm.lot || !issueForm.quantity} className="mt-3 rounded-xl bg-indigo-700 px-4 py-2 text-sm font-semibold text-white disabled:opacity-40">Issue Selected Batch</button>
          </div>
          <div className="mt-4 rounded-xl border border-slate-200 p-4">
            <h4 className="font-semibold text-slate-900">Issued Material Returns & Wastage</h4>
            <p className="mt-1 text-xs text-slate-600">Choose the exact issue record. Returns restore stock to its original receipt batch; wastage is attributed to the issue without deducting stock twice.</p>
            <div className="mt-3 grid gap-2 md:grid-cols-3">
              <select className={input} value={usageForm.material_issue} onChange={(e) => setUsageForm((x) => ({ ...x, material_issue: e.target.value }))}>
                <option value="">Select issued material</option>
                {(data.material_issues || []).filter((x) => x.trackable && Number(x.remaining_quantity) > 0).map((x) => (
                  <option key={x.id} value={x.id}>
                    {x.material_name} · Issue #{x.id} · {x.remaining_quantity} {x.unit} remaining · {x.receipt_no || "Receipt batch"}
                  </option>
                ))}
              </select>
              <select className={input} value={usageForm.action} onChange={(e) => setUsageForm((x) => ({ ...x, action: e.target.value }))}>
                <option value="return">Return unused material</option>
                <option value="wastage">Record wastage</option>
              </select>
              <input className={input} type="number" min="0.001" step="0.001" value={usageForm.quantity} onChange={(e) => setUsageForm((x) => ({ ...x, quantity: e.target.value }))} placeholder="Quantity" />
            </div>
            {usageError && <p className="mt-2 text-sm text-red-700">{usageError}</p>}
            <button onClick={submitUsageAdjustment} disabled={usageBusy || !usageForm.material_issue || !usageForm.quantity} className="mt-3 rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-40">
              {usageBusy ? "Saving..." : usageForm.action === "return" ? "Record Return" : "Record Wastage"}
            </button>
            <div className="mt-4 space-y-2">
              {(data.material_issues || []).map((x) => (
                <div key={x.id} className="rounded-lg bg-slate-50 p-3 text-xs text-slate-700">
                  <div className="font-semibold">{x.material_name} · Issue #{x.id}</div>
                  <div className="mt-1">Issued {x.quantity} {x.unit} · Returned {x.returned_quantity} · Wastage {x.wastage_quantity} · Remaining {x.remaining_quantity}</div>
                  <div className="text-slate-500">{x.receipt_no || "Legacy / uncosted issue"}{x.unit_rate !== null ? ` · Unit rate ₹${x.unit_rate}` : ""}</div>
                </div>
              ))}
              {!(data.material_issues || []).length && <p className="text-xs text-slate-500">No material issue records for this job yet.</p>}
            </div>
          </div>
          <div className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50/50 p-4">
            <h4 className="font-semibold text-slate-900">Reusable Offcuts</h4>
            <p className="mt-1 text-xs text-slate-600">Register measured offcuts against the original receipt-costed issue. Reusable pieces are tracked in sq ft separately from sheet stock.</p>
            <div className="mt-3 grid gap-2 md:grid-cols-5">
              <select className={input} value={offcutForm.source_issue} onChange={(e) => setOffcutForm((x) => ({ ...x, source_issue: e.target.value }))}>
                <option value="">Source material issue</option>
                {(data.material_issues || []).filter((x) => x.trackable && x.material_variant_id).map((x) => <option key={x.id} value={x.id}>{x.material_name} · Issue #{x.id} · {x.receipt_no}</option>)}
              </select>
              <input className={input} placeholder="Storage location" value={offcutForm.location} onChange={(e) => setOffcutForm((x) => ({ ...x, location: e.target.value }))} />
              <input className={input} type="number" min="0.01" step="0.01" placeholder="Length (mm)" value={offcutForm.length_mm} onChange={(e) => setOffcutForm((x) => ({ ...x, length_mm: e.target.value }))} />
              <input className={input} type="number" min="0.01" step="0.01" placeholder="Width (mm)" value={offcutForm.width_mm} onChange={(e) => setOffcutForm((x) => ({ ...x, width_mm: e.target.value }))} />
              <input className={input} type="number" min="0.0001" step="0.0001" placeholder="Usable area (sq ft)" value={offcutForm.usable_area_sqft} onChange={(e) => setOffcutForm((x) => ({ ...x, usable_area_sqft: e.target.value }))} />
            </div>
            <button onClick={createOffcut} disabled={!offcutForm.source_issue || !offcutForm.location || !offcutForm.length_mm || !offcutForm.width_mm || !offcutForm.usable_area_sqft} className="mt-3 rounded-xl bg-emerald-700 px-4 py-2 text-sm font-semibold text-white disabled:opacity-40">Register Offcut</button>
            <div className="mt-4 grid gap-2 md:grid-cols-3">
              <select className={input} value={offcutUsageForm.offcut} onChange={(e) => setOffcutUsageForm({ offcut: e.target.value, material_line: "", used_area_sqft: "" })}>
                <option value="">Available offcut</option>
                {offcuts.filter((x) => x.status === "available" && Number(x.remaining_area_sqft) > 0).map((x) => <option key={x.id} value={x.id}>{x.material} · {x.remaining_area_sqft} sq ft · ₹{x.cost_per_sqft}/sq ft</option>)}
              </select>
              <select className={input} value={offcutUsageForm.material_line} onChange={(e) => setOffcutUsageForm((x) => ({ ...x, material_line: e.target.value }))} disabled={!offcutUsageForm.offcut}>
                <option value="">Target material line</option>
                {matchingOffcutLines.map((m) => <option key={m.id} value={m.id}>{m.material_name} · {m.pending_quantity} {m.unit} pending</option>)}
              </select>
              <input className={input} type="number" min="0.0001" step="0.0001" placeholder={selectedOffcut ? `Up to ${selectedOffcut.remaining_area_sqft} sq ft` : "Area used (sq ft)"} value={offcutUsageForm.used_area_sqft} onChange={(e) => setOffcutUsageForm((x) => ({ ...x, used_area_sqft: e.target.value }))} />
            </div>
            <button onClick={useOffcut} disabled={!offcutUsageForm.offcut || !offcutUsageForm.material_line || !offcutUsageForm.used_area_sqft} className="mt-3 rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-40">Allocate Offcut to This Job</button>
            <div className="mt-3 space-y-2">
              {offcuts.slice(0, 8).map((x) => <div key={x.id} className="flex items-start justify-between gap-3 rounded-lg bg-white p-3 text-xs text-slate-700"><div><div className="font-semibold">{x.material} · {x.length_mm} × {x.width_mm} mm · {x.status}</div><div>{x.remaining_area_sqft} sq ft remaining of {x.usable_area_sqft} · ₹{x.cost_per_sqft ?? "—"}/sq ft · {x.source_receipt || "Legacy / uncosted"}</div>{Number(x.discarded_area_sqft) > 0 && <div className="text-amber-700">Discarded {x.discarded_area_sqft} sq ft · write-off ₹{x.discarded_cost}</div>}</div>{x.status === "available" && <button onClick={() => discardOffcut(x.id)} className="shrink-0 rounded-lg border border-amber-300 px-2 py-1 font-semibold text-amber-800">Discard remaining</button>}</div>)}
              {!offcuts.length && <p className="text-xs text-slate-500">No reusable offcuts registered yet.</p>}
            </div>
            {offcutError && <p className="mt-2 text-sm text-red-700">{offcutError}</p>}
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
