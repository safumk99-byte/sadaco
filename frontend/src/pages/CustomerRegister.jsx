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
    <div className="grid min-h-screen place-items-center bg-slate-100 p-4">
      <form
        onSubmit={submit}
        className="w-full max-w-md rounded-2xl bg-white p-7 shadow"
      >
        <h1 className="text-2xl font-bold">Create Customer Account</h1>
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
