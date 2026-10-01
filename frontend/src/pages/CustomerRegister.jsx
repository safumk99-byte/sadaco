import { useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../services/api";
import { initCsrf } from "../services/api";
export default function CustomerRegister() {
  const [f, setF] = useState({ name: "", phone: "", email: "", password: "" });
  const [e, setE] = useState("");
  const nav = useNavigate();
  async function submit(ev) {
    ev.preventDefault();
    setE("");
    try {
      await initCsrf();
      await api.post("/sales/portal/register/", f);
      nav("/");
    } catch (err) {
      setE(err.response?.data?.detail || "Registration failed.");
    }
  }
  return (
    <div className="relative grid min-h-screen place-items-center overflow-hidden bg-gradient-to-br from-slate-50 via-indigo-50 to-blue-100 p-4">
      <div className="pointer-events-none absolute -left-24 -top-24 h-72 w-72 rounded-full bg-blue-300/20 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-24 -right-24 h-72 w-72 rounded-full bg-violet-300/20 blur-3xl" />
      <form
        onSubmit={submit}
        className="relative w-full max-w-md rounded-[28px] border border-white/70 bg-white/90 p-7 shadow-2xl shadow-indigo-900/10 backdrop-blur sm:p-8"
      >
        <div className="mb-6 rounded-2xl bg-gradient-to-br from-blue-700 via-indigo-700 to-violet-800 p-5 text-white">
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-blue-100">SADACO Customer Portal</p>
          <h1 className="mt-1 text-2xl font-bold">Create Customer Account</h1>
          <p className="mt-1 text-sm text-indigo-100">Register securely to manage requests, quotations and orders.</p>
        </div>
        {e && (
          <div className="my-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">
            {e}
          </div>
        )}
        {["name", "phone", "email", "password"].map((k) => (
          <input
            key={k}
            type={k === "password" ? "password" : "text"}
            placeholder={k}
            value={f[k]}
            onChange={(ev) => setF({ ...f, [k]: ev.target.value })}
            className="my-2 w-full rounded-lg border px-3 py-2.5"
            required={k !== "email"}
          />
        ))}
        <button className="mt-3 w-full rounded-lg bg-slate-900 px-4 py-3 text-white">
          Create account
        </button>
      </form>
    </div>
  );
}
