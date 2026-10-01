import { useEffect, useState } from "react";
import api from "../services/api";

export default function UsersManagement() {
  const [data, setData] = useState({ users: [], roles: [] });
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const load = async () => {
    setLoading(true);
    try {
      const r = await api.get("/users/", { params: { q } });
      setData(r.data);
    } catch (e) {
      setError(e.response?.data?.detail || "Unable to load users.");
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    load();
  }, []);
  const toggle = async (u) => {
    try {
      await api.post(`/users/${u.id}/update/`, {
        is_active: !u.is_active,
        role: u.role,
      });
      load();
    } catch (e) {
      setError(e.response?.data?.detail || "Update failed.");
    }
  };
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Users & Roles</h1>
        <p className="text-slate-500">
          Manage internal accounts and access roles.
        </p>
      </div>
      <div className="flex gap-2">
        <input
          className="input flex-1"
          placeholder="Search users"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && load()}
        />
        <button className="btn-primary" onClick={load}>
          Search
        </button>
      </div>
      {error && <div className="alert-error">{error}</div>}
      <div className="card overflow-x-auto">
        <table className="table">
          <thead>
            <tr>
              <th>User</th>
              <th>Role</th>
              <th>Email</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan="5">Loading…</td>
              </tr>
            ) : (
              data.users.map((u) => (
                <tr key={u.id}>
                  <td>
                    <b>{u.name}</b>
                    <div className="text-xs text-slate-500">@{u.username}</div>
                  </td>
                  <td>{u.role_label}</td>
                  <td>{u.email || "—"}</td>
                  <td>{u.is_active ? "Active" : "Inactive"}</td>
                  <td>
                    <button className="btn-secondary" onClick={() => toggle(u)}>
                      {u.is_active ? "Deactivate" : "Activate"}
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
