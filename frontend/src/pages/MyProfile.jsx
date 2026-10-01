import { useEffect, useState } from "react";
import api from "../services/api";
export default function MyProfile() {
  const [u, setU] = useState(null);
  const [form, setForm] = useState({});
  const [msg, setMsg] = useState("");
  useEffect(() => {
    api.get("/auth/me/").then((r) => {
      setU(r.data.user);
      setForm(r.data.user || {});
    });
  }, []);
  const save = async () => {
    const r = await api.post("/profile/update/", form);
    setMsg("Profile updated successfully.");
    if (r.data?.user) {
      setU(r.data.user);
      setForm(r.data.user);
    }
  };
  if (!u) return <div>Loading…</div>;
  return (
    <div className="max-w-3xl space-y-6">
      <div className="relative overflow-hidden rounded-[28px] bg-gradient-to-br from-blue-700 via-indigo-700 to-violet-800 p-5 text-white shadow-xl shadow-indigo-900/15 sm:p-6">
        <p className="text-xs font-bold uppercase tracking-[0.2em] text-blue-100">Account Settings</p>
        <h1 className="mt-1 text-2xl font-bold tracking-tight sm:text-3xl">My Profile</h1>
        <p className="mt-2 text-sm text-indigo-100">Update your personal account details and contact information.</p>
      </div>
      {msg && <div className="alert-success">{msg}</div>}
      <div className="card grid gap-4 md:grid-cols-2">
        <label>
          Username
          <input className="input mt-1" value={u.username} disabled />
        </label>
        <label>
          Role
          <input className="input mt-1" value={u.role_label} disabled />
        </label>
        <label>
          First name
          <input
            className="input mt-1"
            value={form.first_name || ""}
            onChange={(e) => setForm({ ...form, first_name: e.target.value })}
          />
        </label>
        <label>
          Last name
          <input
            className="input mt-1"
            value={form.last_name || ""}
            onChange={(e) => setForm({ ...form, last_name: e.target.value })}
          />
        </label>
        <label className="md:col-span-2">
          Email
          <input
            className="input mt-1"
            value={form.email || ""}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
          />
        </label>
        <button className="btn-primary" onClick={save}>
          Save Changes
        </button>
      </div>
    </div>
  );
}
