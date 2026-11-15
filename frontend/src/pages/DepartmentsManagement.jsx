import { useEffect, useState } from "react";
import api from "../services/api";

const emptyForm = { code: "", name: "", description: "", manager: "", is_active: true };

export default function DepartmentsManagement() {
  const [departments, setDepartments] = useState([]);
  const [managers, setManagers] = useState([]);
  const [form, setForm] = useState(emptyForm);
  const [editing, setEditing] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  async function load() {
    setLoading(true);
    setError("");
    try {
      const response = await api.get("/departments/");
      setDepartments(response.data.departments || []);
      setManagers(response.data.manager_options || []);
    } catch (e) {
      setError(e.response?.data?.detail || "Unable to load departments.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  function startEdit(item) {
    setEditing(item.id);
    setForm({ code: item.code, name: item.name, description: item.description || "", manager: item.manager?.id || "", is_active: item.is_active });
    setNotice("");
  }

  function reset() { setEditing(null); setForm(emptyForm); }

  async function submit(e) {
    e.preventDefault();
    setSaving(true); setError(""); setNotice("");
    try {
      if (editing) {
        await api.post("/departments/" + editing + "/update/", form);
        setNotice("Department updated successfully.");
      } else {
        const created = await api.post("/departments/create/", { code: form.code, name: form.name, description: form.description });
        if (form.manager) await api.post("/departments/" + created.data.department.id + "/update/", { ...form, manager: form.manager });
        setNotice("Department created successfully.");
      }
      reset(); await load();
    } catch (e) {
      setError(e.response?.data?.detail || "Unable to save department.");
    } finally { setSaving(false); }
  }

  return (
    <div className="space-y-6">
      <div className="rounded-[28px] bg-gradient-to-br from-slate-900 via-indigo-900 to-blue-800 p-6 text-white shadow-xl">
        <p className="text-xs font-bold uppercase tracking-[.2em] text-blue-200">Organization setup</p>
        <h1 className="mt-2 text-2xl font-extrabold sm:text-3xl">Department Management</h1>
        <p className="mt-2 max-w-2xl text-sm text-blue-100">Manage SADACO divisions and assign one department manager to each division.</p>
      </div>
      {error && <div className="alert-error">{error}</div>}
      {notice && <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-800">{notice}</div>}
      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_380px]">
        <section className="space-y-3">
          <div className="flex items-center justify-between"><h2 className="text-lg font-bold text-slate-900">Business divisions</h2><span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-slate-600">{departments.length} divisions</span></div>
          {loading ? <div className="card p-6 text-sm text-slate-500">Loading departments…</div> :
            departments.length === 0 ? <div className="card p-6 text-sm text-slate-500">No departments available.</div> :
            departments.map(item => (
              <article key={item.id} className="card flex flex-col gap-4 p-5 sm:flex-row sm:items-center sm:justify-between">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="font-bold text-slate-900">{item.name}</h3>
                    <span className={"rounded-full px-2.5 py-1 text-[11px] font-bold " + (item.is_active ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-500")}>{item.is_active ? "Active" : "Inactive"}</span>
                  </div>
                  <p className="mt-1 text-xs font-semibold uppercase tracking-wider text-slate-400">{item.code}</p>
                  <p className="mt-2 text-sm text-slate-600">{item.description || "No description added."}</p>
                  <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-xs text-slate-500">
                    <span>Manager: <b className="text-slate-700">{item.manager?.name || "Not assigned"}</b></span>
                    <span>Staff: <b className="text-slate-700">{item.staff_count}</b></span>
                    <span>Users: <b className="text-slate-700">{item.user_count}</b></span>
                  </div>
                </div>
                <button className="btn-secondary shrink-0" onClick={() => startEdit(item)}>Edit division</button>
              </article>
            ))}
        </section>
        <section className="card h-fit p-5">
          <div className="mb-4 flex items-center justify-between"><h2 className="font-bold text-slate-900">{editing ? "Edit division" : "Add division"}</h2>{editing && <button className="text-xs font-semibold text-slate-500 hover:text-slate-900" onClick={reset}>Cancel</button>}</div>
          <form className="space-y-3" onSubmit={submit}>
            <label className="block text-xs font-semibold text-slate-600">Division code<input className="input mt-1" required value={form.code} onChange={e => setForm({ ...form, code: e.target.value })} placeholder="e.g. creatives" /></label>
            <label className="block text-xs font-semibold text-slate-600">Division name<input className="input mt-1" required value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="SADACO Creatives" /></label>
            <label className="block text-xs font-semibold text-slate-600">Description<textarea className="input mt-1 min-h-24" value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} /></label>
            {editing && <>
              <label className="block text-xs font-semibold text-slate-600">Department manager<select className="input mt-1" value={form.manager} onChange={e => setForm({ ...form, manager: e.target.value })}><option value="">Not assigned</option>{managers.map(m => <option key={m.id} value={m.id}>{m.name} (@{m.username})</option>)}</select></label>
              <label className="flex items-center gap-2 text-sm font-medium text-slate-700"><input type="checkbox" checked={form.is_active} onChange={e => setForm({ ...form, is_active: e.target.checked })} />Active department</label>
            </>}
            <button className="btn-primary w-full" disabled={saving}>{saving ? "Saving…" : editing ? "Save changes" : "Create department"}</button>
          </form>
          {!editing && <p className="mt-3 text-xs leading-5 text-slate-400">After creating the division, edit it to assign its department manager.</p>}
        </section>
      </div>
    </div>
  );
}
