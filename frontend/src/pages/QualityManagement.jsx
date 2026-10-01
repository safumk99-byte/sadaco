import { useEffect, useState } from "react";
import api from "../services/api";

const card = "rounded-2xl border border-slate-200 bg-white shadow-sm transition-shadow hover:shadow-md";
const input =
  "w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100";
const label = "mb-1 block text-sm font-medium text-slate-700";

export default function QualityManagement() {
  const [stats, setStats] = useState({}),
    [checks, setChecks] = useState([]),
    [options, setOptions] = useState({
      staff: [],
      jobs: [],
      check_types: [],
      results: [],
      rework_statuses: [],
      packing_statuses: [],
    });
  const [filters, setFilters] = useState({ q: "", result: "", check_type: "" }),
    [detail, setDetail] = useState(null),
    [showCheck, setShowCheck] = useState(false),
    [loading, setLoading] = useState(true),
    [error, setError] = useState("");
  const [form, setForm] = useState({
    job: "",
    check_type: "final",
    result: "pending",
    inspector: "",
    stage: "",
    design_match: false,
    measurement_ok: false,
    finishing_ok: false,
    colour_ok: false,
    engraving_ok: false,
    defects: "",
    rework_reason: "",
    corrective_action: "",
    remarks: "",
  });
  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const [s, c, o] = await Promise.all([
        api.get("/quality/summary/"),
        api.get("/quality/checks/", { params: filters }),
        api.get("/quality/options/"),
      ]);
      setStats(s.data.stats);
      setChecks(c.data.checks);
      setOptions(o.data);
    } catch (e) {
      setError(e.response?.data?.detail || "Unable to load quality data.");
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
  }, [filters.q, filters.result, filters.check_type]);
  const saveCheck = async (e) => {
    e.preventDefault();
    setError("");
    try {
      await api.post("/quality/checks/create/", form);
      setShowCheck(false);
      resetForm();
      load();
    } catch (e) {
      setError(e.response?.data?.detail || "Unable to save quality check.");
    }
  };
  const resetForm = () =>
    setForm({
      job: "",
      check_type: "final",
      result: "pending",
      inspector: "",
      stage: "",
      design_match: false,
      measurement_ok: false,
      finishing_ok: false,
      colour_ok: false,
      engraving_ok: false,
      defects: "",
      rework_reason: "",
      corrective_action: "",
      remarks: "",
    });
  return (
    <div className="space-y-6">
      <div className="relative overflow-hidden rounded-[28px] bg-gradient-to-br from-blue-700 via-indigo-700 to-violet-800 p-5 text-white shadow-xl shadow-indigo-900/15 sm:p-6">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-blue-100">Quality Operations</p>
            <h1 className="mt-1 text-2xl font-bold tracking-tight sm:text-3xl">Quality Management</h1>
            <p className="mt-2 max-w-2xl text-sm text-indigo-100">Inspect production output, manage defects and release approved jobs for packing.</p>
          </div>
          <button
            onClick={() => setShowCheck(true)}
            className="rounded-xl bg-white px-4 py-2.5 font-bold text-indigo-700 shadow-sm transition hover:bg-indigo-50"
          >
            + New Quality Check
          </button>
        </div>
      </div>
      {error && (
        <div className="rounded-xl bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        {[
          ["QC Pending", stats.pending],
          ["Passed", stats.passed],
          ["Rework", stats.rework],
          ["Packed", stats.packed],
          ["Failed", stats.failed],
        ].map(([k, v]) => (
          <div className={`${card} relative overflow-hidden p-4`} key={k}>
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
        <div className="grid gap-3 md:grid-cols-[1fr_180px_180px_auto]">
          <input
            className={input}
            placeholder="Search job, order or customer..."
            value={filters.q}
            onChange={(e) => setFilters((x) => ({ ...x, q: e.target.value }))}
          />
          <select
            className={input}
            value={filters.result}
            onChange={(e) =>
              setFilters((x) => ({ ...x, result: e.target.value }))
            }
          >
            <option value="">All results</option>
            {options.results.map((x) => (
              <option key={x.value} value={x.value}>
                {x.label}
              </option>
            ))}
          </select>
          <select
            className={input}
            value={filters.check_type}
            onChange={(e) =>
              setFilters((x) => ({ ...x, check_type: e.target.value }))
            }
          >
            <option value="">All checks</option>
            {options.check_types.map((x) => (
              <option key={x.value} value={x.value}>
                {x.label}
              </option>
            ))}
          </select>
          <button
            onClick={load}
            className="rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 px-4 py-2.5 font-semibold text-white shadow-sm transition hover:from-blue-700 hover:to-indigo-700"
          >
            Refresh
          </button>
        </div>
      </div>
      <div className={card}>
        {loading ? (
          <div className="p-10 text-center text-sm text-slate-500">
            Loading quality checks...
          </div>
        ) : (
          <CheckTable
            checks={checks}
            onOpen={async (id) => {
              const c = checks.find((x) => x.id === id);
              if (c) {
                try {
                  const r = await api.get(`/quality/jobs/${c.job_id}/`);
                  setDetail(r.data);
                } catch (e) {
                  setError(e.response?.data?.detail || "Unable to load job.");
                }
              }
            }}
          />
        )}
      </div>
      {showCheck && (
        <CheckModal
          options={options}
          form={form}
          setForm={setForm}
          close={() => {
            setShowCheck(false);
            resetForm();
          }}
          save={saveCheck}
        />
      )}
      {detail && (
        <QualityDetail
          data={detail}
          options={options}
          close={() => setDetail(null)}
          refresh={load}
        />
      )}
    </div>
  );
}

function CheckTable({ checks, onOpen }) {
  if (!checks.length)
    return (
      <div className="p-10 text-center text-sm text-slate-500">
        No quality checks found.
      </div>
    );
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[920px] text-left text-sm">
        <thead className="bg-gradient-to-r from-slate-50 via-indigo-50 to-violet-50 text-xs uppercase text-slate-500">
          <tr>
            <th className="px-5 py-3">Job</th>
            <th>Order / Customer</th>
            <th>Check</th>
            <th>Inspector</th>
            <th>Result</th>
            <th>Date</th>
            <th></th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {checks.map((c) => (
            <tr key={c.id} className="hover:bg-slate-50">
              <td className="px-5 py-4 font-bold">
                {c.job_no}
                <div className="text-xs font-normal text-slate-500">
                  {c.stage || "—"}
                </div>
              </td>
              <td>
                {c.order_no}
                <div className="text-xs text-slate-500">{c.customer}</div>
              </td>
              <td>{c.check_type_label}</td>
              <td>{c.inspector?.name || "—"}</td>
              <td>
                <span
                  className={`rounded-full px-2.5 py-1 text-xs font-semibold ${badge(c.result)}`}
                >
                  {c.result_label}
                </span>
              </td>
              <td>
                {c.checked_at
                  ? new Date(c.checked_at).toLocaleString()
                  : "Pending"}
              </td>
              <td className="px-5 text-right">
                <button
                  onClick={() => onOpen(c.id)}
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
function badge(v) {
  return v === "pass"
    ? "bg-emerald-100 text-emerald-700"
    : v === "fail"
      ? "bg-red-100 text-red-700"
      : v === "rework"
        ? "bg-amber-100 text-amber-700"
        : "bg-slate-100 text-slate-700";
}

function CheckModal({ options, form, setForm, close, save }) {
  return (
    <Modal title="New Quality Check" close={close}>
      <form onSubmit={save} className="grid gap-4 md:grid-cols-2">
        <Select
          label="Production Job"
          value={form.job}
          set={(v) => setForm((x) => ({ ...x, job: v }))}
          options={options.jobs.map((j) => [
            j.id,
            `${j.job_no} · ${j.order_no} · ${j.customer}`,
          ])}
        />
        <Select
          label="Check Type"
          value={form.check_type}
          set={(v) => setForm((x) => ({ ...x, check_type: v }))}
          options={options.check_types.map((x) => [x.value, x.label])}
        />
        <Select
          label="Result"
          value={form.result}
          set={(v) => setForm((x) => ({ ...x, result: v }))}
          options={options.results.map((x) => [x.value, x.label])}
        />
        <Select
          label="Inspector"
          value={form.inspector}
          set={(v) => setForm((x) => ({ ...x, inspector: v }))}
          options={options.staff.map((s) => [s.id, s.name])}
          optional
        />
        <label>
          <span className={label}>Stage</span>
          <input
            className={input}
            value={form.stage}
            onChange={(e) => setForm((x) => ({ ...x, stage: e.target.value }))}
            placeholder="e.g. finishing"
          />
        </label>
        <div className="grid grid-cols-2 gap-2 rounded-xl bg-slate-50 p-3 md:col-span-1">
          <Check
            label="Design"
            value={form.design_match}
            set={(v) => setForm((x) => ({ ...x, design_match: v }))}
          />
          <Check
            label="Measurement"
            value={form.measurement_ok}
            set={(v) => setForm((x) => ({ ...x, measurement_ok: v }))}
          />
          <Check
            label="Finishing"
            value={form.finishing_ok}
            set={(v) => setForm((x) => ({ ...x, finishing_ok: v }))}
          />
          <Check
            label="Colour"
            value={form.colour_ok}
            set={(v) => setForm((x) => ({ ...x, colour_ok: v }))}
          />
          <Check
            label="Engraving"
            value={form.engraving_ok}
            set={(v) => setForm((x) => ({ ...x, engraving_ok: v }))}
          />
        </div>
        <Text
          label="Defects"
          value={form.defects}
          set={(v) => setForm((x) => ({ ...x, defects: v }))}
        />
        <Text
          label="Rework Reason"
          value={form.rework_reason}
          set={(v) => setForm((x) => ({ ...x, rework_reason: v }))}
        />
        <Text
          label="Corrective Action"
          value={form.corrective_action}
          set={(v) => setForm((x) => ({ ...x, corrective_action: v }))}
        />
        <Text
          label="Remarks"
          value={form.remarks}
          set={(v) => setForm((x) => ({ ...x, remarks: v }))}
        />
        <div className="md:col-span-2 flex justify-end gap-2">
          <button
            type="button"
            onClick={close}
            className="rounded-xl border border-slate-300 px-4 py-2.5"
          >
            Cancel
          </button>
          <button className="rounded-xl bg-slate-900 px-5 py-2.5 font-semibold text-white">
            Save Check
          </button>
        </div>
      </form>
    </Modal>
  );
}

function QualityDetail({ data, options, close, refresh }) {
  const j = data.job;
  const [rework, setRework] = useState({
    reason: "",
    corrective_action: "",
    assigned_staff: "",
    due_date: "",
    status: "open",
  });
  const [packing, setPacking] = useState(
    data.packing || {
      packing_material: "",
      fragile_protection: false,
      customer_label: false,
      status: "pending",
      packed_by: "",
      notes: "",
    },
  );
  const [busy, setBusy] = useState(false);
  const addRework = async () => {
    if (!data.checks[0]) return;
    if (!rework.reason) return;
    setBusy(true);
    try {
      await api.post(`/quality/checks/${data.checks[0].id}/rework/`, rework);
      refresh();
      const r = await api.get(`/quality/jobs/${j.id}/`);
      Object.assign(data, r.data);
    } catch (e) {
      alert(e.response?.data?.detail || "Unable to create rework.");
    } finally {
      setBusy(false);
    }
  };
  const savePacking = async () => {
    setBusy(true);
    try {
      await api.post(`/quality/jobs/${j.id}/packing/`, packing);
      refresh();
      const r = await api.get(`/quality/jobs/${j.id}/`);
      Object.assign(data, r.data);
    } catch (e) {
      alert(e.response?.data?.detail || "Unable to save packing.");
    } finally {
      setBusy(false);
    }
  };
  return (
    <Modal title={`${j.job_no} · ${j.order.customer}`} close={close}>
      <div className="space-y-6">
        <div className="grid gap-3 sm:grid-cols-5">
          {[
            ["Status", j.status_label],
            ["Stage", j.stage_label],
            ["Progress", `${j.progress_percent}%`],
            ["Order", j.order.order_no],
            ["Deadline", j.deadline || "—"],
          ].map((x) => (
            <div key={x[0]} className="rounded-xl bg-slate-50 p-3">
              <div className="text-xs uppercase text-slate-500">{x[0]}</div>
              <div className="mt-1 font-bold">{x[1]}</div>
            </div>
          ))}
        </div>
        <section>
          <div className="mb-3 flex items-center justify-between">
            <div>
              <h3 className="font-bold">Quality Checks</h3>
              <p className="text-xs text-slate-500">
                Inspection history and checklist results.
              </p>
            </div>
          </div>
          <div className="space-y-2">
            {data.checks.map((c) => (
              <div
                key={c.id}
                className="rounded-xl border border-slate-200 p-4"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <b>{c.check_type_label}</b>
                    <div className="text-xs text-slate-500">
                      {c.inspector?.name || "No inspector"} ·{" "}
                      {c.checked_at
                        ? new Date(c.checked_at).toLocaleString()
                        : "Not completed"}
                    </div>
                  </div>
                  <span
                    className={`rounded-full px-2.5 py-1 text-xs font-semibold ${badge(c.result)}`}
                  >
                    {c.result_label}
                  </span>
                </div>
                <div className="mt-3 grid grid-cols-5 gap-2 text-xs">
                  {[
                    ["Design", c.design_match],
                    ["Measurement", c.measurement_ok],
                    ["Finishing", c.finishing_ok],
                    ["Colour", c.colour_ok],
                    ["Engraving", c.engraving_ok],
                  ].map((x) => (
                    <div key={x[0]} className="rounded-lg bg-slate-50 p-2">
                      {x[0]} <b>{x[1] ? "✓" : "—"}</b>
                    </div>
                  ))}
                </div>
                {c.defects && (
                  <p className="mt-3 text-sm">
                    <b>Defects:</b> {c.defects}
                  </p>
                )}
                {c.corrective_action && (
                  <p className="mt-1 text-sm">
                    <b>Corrective:</b> {c.corrective_action}
                  </p>
                )}
              </div>
            ))}
          </div>
        </section>
        <section>
          <h3 className="mb-3 font-bold">Rework</h3>
          <div className="grid gap-2 md:grid-cols-5">
            <input
              className={input}
              placeholder="Reason"
              value={rework.reason}
              onChange={(e) =>
                setRework((x) => ({ ...x, reason: e.target.value }))
              }
            />
            <input
              className={input}
              placeholder="Corrective action"
              value={rework.corrective_action}
              onChange={(e) =>
                setRework((x) => ({ ...x, corrective_action: e.target.value }))
              }
            />
            <Select
              value={rework.assigned_staff}
              set={(v) => setRework((x) => ({ ...x, assigned_staff: v }))}
              options={options.staff.map((s) => [s.id, s.name])}
              optional
              label="Staff"
            />
            <input
              className={input}
              type="date"
              value={rework.due_date}
              onChange={(e) =>
                setRework((x) => ({ ...x, due_date: e.target.value }))
              }
            />
            <button
              disabled={busy}
              onClick={addRework}
              className="rounded-xl bg-slate-900 px-3 py-2.5 font-semibold text-white"
            >
              Create Rework
            </button>
          </div>
          <div className="mt-3 space-y-2">
            {data.reworks.map((r) => (
              <div key={r.id} className="rounded-xl bg-amber-50 p-3 text-sm">
                <b>{r.status_label}</b> ·{" "}
                {r.assigned_staff?.name || "Unassigned"} ·{" "}
                {r.due_date || "No due date"}
                <div>{r.reason}</div>
              </div>
            ))}
          </div>
        </section>
        <section>
          <h3 className="mb-3 font-bold">Packing</h3>
          <div className="grid gap-3 md:grid-cols-4">
            <input
              className={input}
              placeholder="Packing material"
              value={packing.packing_material || ""}
              onChange={(e) =>
                setPacking((x) => ({ ...x, packing_material: e.target.value }))
              }
            />
            <Select
              label="Status"
              value={packing.status || "pending"}
              set={(v) => setPacking((x) => ({ ...x, status: v }))}
              options={options.packing_statuses.map((x) => [x.value, x.label])}
            />
            <Check
              label="Fragile protection"
              value={packing.fragile_protection}
              set={(v) => setPacking((x) => ({ ...x, fragile_protection: v }))}
            />
            <Check
              label="Customer label"
              value={packing.customer_label}
              set={(v) => setPacking((x) => ({ ...x, customer_label: v }))}
            />
          </div>
          <textarea
            className={`${input} mt-3`}
            rows="2"
            placeholder="Packing notes"
            value={packing.notes || ""}
            onChange={(e) =>
              setPacking((x) => ({ ...x, notes: e.target.value }))
            }
          />
          <button
            disabled={busy || j.status !== "completed"}
            onClick={savePacking}
            className="mt-3 rounded-xl bg-slate-900 px-4 py-2.5 font-semibold text-white disabled:opacity-50"
          >
            Save Packing
          </button>
          {j.status !== "completed" && (
            <p className="mt-2 text-xs text-amber-700">
              Packing becomes available after final QC passes.
            </p>
          )}
        </section>
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
      <span
        className={label ? "mb-1 block text-sm font-medium text-slate-700" : ""}
      >
        {label}
      </span>
      <select
        required={!optional}
        className={input}
        value={value || ""}
        onChange={(e) => set(e.target.value)}
      >
        <option value="">Select {label || "option"}</option>
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
    <label className="flex items-center gap-2 rounded-lg bg-slate-50 p-2 text-sm">
      <input
        type="checkbox"
        checked={!!value}
        onChange={(e) => set(e.target.checked)}
      />
      {label}
    </label>
  );
}
function Text({ label, value, set }) {
  return (
    <label>
      <span className={label}>{label}</span>
      <textarea
        className={input}
        rows="3"
        value={value || ""}
        onChange={(e) => set(e.target.value)}
      />
    </label>
  );
}
