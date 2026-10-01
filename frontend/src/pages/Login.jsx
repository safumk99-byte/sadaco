import { useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const { user, signIn } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (user)
    return (
      <Navigate to={user.role === "customer" ? "/customer" : "/"} replace />
    );

  async function submit(event) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      const data = await signIn(username, password);
      navigate(
        location.state?.from?.pathname ||
          (data.user?.role === "customer" ? "/customer" : "/"),
        { replace: true },
      );
    } catch (err) {
      setError(err.response?.data?.detail || "Invalid username or password.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="relative grid min-h-screen place-items-center overflow-hidden bg-gradient-to-br from-slate-950 via-indigo-950 to-violet-950 p-4">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(99,102,241,0.28),transparent_38%),radial-gradient(circle_at_bottom_left,rgba(59,130,246,0.22),transparent_35%)]" />
      <form
        onSubmit={submit}
        className="relative w-full max-w-md rounded-[28px] border border-white/20 bg-white/95 p-7 shadow-2xl backdrop-blur-xl sm:p-8"
      >
        <div className="mb-7">
          <div className="inline-flex rounded-2xl bg-gradient-to-br from-blue-700 via-indigo-700 to-violet-800 px-4 py-2 text-2xl font-black tracking-tight text-white shadow-lg">SADACO</div>
          <p className="mt-3 text-sm text-slate-500">Management System</p>
        </div>
        {error && (
          <div className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">
            {error}
          </div>
        )}
        <label htmlFor="username" className="mb-1 block text-sm font-medium">
          Username
        </label>
        <input
          id="username"
          name="username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          autoComplete="username"
          className="mb-4 w-full rounded-lg border border-slate-300 px-3 py-2.5 outline-none focus:border-slate-500"
          required
        />
        <label htmlFor="password" className="mb-1 block text-sm font-medium">
          Password
        </label>
        <input
          id="password"
          name="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete="current-password"
          className="mb-6 w-full rounded-lg border border-slate-300 px-3 py-2.5 outline-none focus:border-slate-500"
          required
        />
        <div className="mb-4 text-right">
          <a className="text-sm text-slate-600 underline" href="/register">
            Customer account? Register
          </a>
        </div>
        <button
          disabled={busy}
          className="w-full rounded-lg bg-slate-900 px-4 py-3 font-medium text-white disabled:opacity-60"
        >
          {busy ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </div>
  );
}
