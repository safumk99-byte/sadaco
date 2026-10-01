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
    await api.post("/profile/update/", form);
    setMsg("Profile updated successfully.");
    const r = await api.get("/auth/me/");
    setU(r.data.user);
  };
  if (!u) return <div>Loading…</div>;
  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold">My Profile</h1>
        <p className="text-slate-500">Update your account details.</p>
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
