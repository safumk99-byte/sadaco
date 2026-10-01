import { useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";
import api from "../services/api";

const tabs = [
  "overview",
  "products",
  "requests",
  "quotations",
  "orders",
  "notifications",
  "profile",
];
export default function CustomerPortal() {
  const { user, signOut } = useAuth();
  const [tab, setTab] = useState("overview");
  const [data, setData] = useState({});
  const [busy, setBusy] = useState(true);
  const [message, setMessage] = useState("");
  async function load() {
    setBusy(true);
    try {
      const [s, p, r, q, o, n, me] = await Promise.all([
        api.get("/sales/portal/summary/"),
        api.get("/sales/portal/products/"),
        api.get("/sales/portal/requests/"),
        api.get("/sales/portal/quotations/"),
        api.get("/sales/portal/orders/"),
        api.get("/sales/portal/notifications/"),
        api.get("/sales/portal/profile/"),
      ]);
      setData({
        summary: s.data,
        products: p.data.products,
        requests: r.data.requests,
        quotations: q.data.quotations,
        orders: o.data.orders,
        notifications: n.data.notifications,
        customer: me.data.customer,
      });
    } finally {
      setBusy(false);
    }
  }
  useEffect(() => {
    load();
  }, []);
  async function respondQuotation(id, decision) {
    await api.post(`/sales/portal/quotations/${id}/respond/`, { decision });
    setMessage("Quotation response saved.");
    load();
  }
  async function respondDesign(id, decision) {
    await api.post(`/sales/portal/designs/${id}/respond/`, { decision });
    setMessage("Design response saved.");
    load();
  }
  async function feedback(id) {
    const rating = window.prompt("Rating 1-5");
    if (!rating) return;
    const comment = window.prompt("Comment (optional)") || "";
    await api.post(`/sales/portal/orders/${id}/feedback/`, { rating, comment });
    setMessage("Thank you for your feedback.");
    load();
  }
  async function markRead(id) {
    await api.post(`/sales/portal/notifications/${id}/read/`);
    load();
  }
  if (busy)
    return (
      <div className="rounded-2xl bg-white p-8">Loading customer portal…</div>
    );
  return (
    <div className="space-y-5">
      <div className="relative overflow-hidden rounded-[28px] bg-gradient-to-br from-blue-700 via-indigo-700 to-violet-800 p-5 text-white shadow-xl shadow-indigo-900/15 sm:p-6">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-blue-100">SADACO Customer Experience</p>
            <h1 className="mt-1 text-2xl font-bold tracking-tight sm:text-3xl">Customer Portal</h1>
            <p className="mt-2 text-sm text-indigo-100">Welcome back, {user?.name}</p>
          </div>
        <div className="flex gap-2">
          <button
            onClick={load}
            className="rounded-xl border px-4 py-2 text-sm"
          >
            Refresh
          </button>
          <button
            onClick={() => signOut().then(() => (location.href = "/login"))}
            className="rounded-xl bg-slate-900 px-4 py-2 text-sm text-white"
          >
            Sign out
          </button>
        </div>
        </div>
      </div>
      {message && (
        <div className="rounded-xl bg-emerald-50 p-3 text-sm text-emerald-700">
          {message}
        </div>
      )}
      <div className="flex flex-wrap gap-2">
        {tabs.map((x) => (
          <button
            key={x}
            onClick={() => setTab(x)}
            className={`rounded-xl px-4 py-2 text-sm ${tab === x ? "bg-slate-900 text-white" : "bg-white border"}`}
          >
            {x[0].toUpperCase() + x.slice(1)}
          </button>
        ))}
      </div>
      {tab === "overview" && (
        <div className="grid gap-4 sm:grid-cols-4">
          {Object.entries(data.summary.stats || {}).map(([k, v]) => (
            <div key={k} className="rounded-2xl bg-white p-5 shadow-sm">
              <div className="text-2xl font-bold">{v}</div>
              <div className="text-sm text-slate-500">
                {k.replaceAll("_", " ")}
              </div>
            </div>
          ))}
        </div>
      )}
      {tab === "products" && (
        <Cards
          items={data.products}
          fields={["name", "sku", "price", "stock"]}
        />
      )}{" "}
      {tab === "requests" && (
        <Requests items={data.requests} onCreated={load} />
      )}{" "}
      {tab === "quotations" && (
        <div className="grid gap-4">
          {data.quotations.map((q) => (
            <div key={q.id} className="rounded-2xl bg-white p-5">
              <div className="flex justify-between">
                <b>{q.quotation_no}</b>
                <span>{q.status}</span>
              </div>
              <p className="mt-2">
                {q.item_description} · Qty {q.quantity}
              </p>
              <p className="font-semibold">₹ {q.quoted_price}</p>
              {q.designs?.map((d) => (
                <div key={d.id} className="mt-3 rounded-xl bg-slate-50 p-3">
                  <div className="text-sm font-medium">
                    Design v{d.version} · {d.status}
                  </div>
                  {["sent"].includes(d.status) && (
                    <div className="mt-2 flex gap-2">
                      <button
                        onClick={() => respondDesign(d.id, "approved")}
                        className="rounded-lg bg-emerald-600 px-3 py-2 text-sm text-white"
                      >
                        Approve Design
                      </button>
                      <button
                        onClick={() => respondDesign(d.id, "revision")}
                        className="rounded-lg border px-3 py-2 text-sm"
                      >
                        Request Revision
                      </button>
                    </div>
                  )}
                </div>
              ))}
              {["sent", "draft"].includes(q.status) && (
                <div className="mt-3 flex gap-2">
                  <button
                    onClick={() => respondQuotation(q.id, "approved")}
                    className="rounded-lg bg-emerald-600 px-3 py-2 text-sm text-white"
                  >
                    Approve Quotation
                  </button>
                  <button
                    onClick={() => respondQuotation(q.id, "rejected")}
                    className="rounded-lg bg-red-600 px-3 py-2 text-sm text-white"
                  >
                    Reject
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
      {tab === "orders" && (
        <div className="grid gap-4">
          {data.orders.map((o) => (
            <div key={o.id} className="rounded-2xl bg-white p-5">
              <div className="flex justify-between">
                <b>{o.order_no}</b>
                <span>{o.status}</span>
              </div>
              <p>
                {o.item_description} · Qty {o.quantity}
              </p>
              <p>Balance: ₹ {o.balance}</p>
              {o.delivery && (
                <p className="mt-2 text-sm text-slate-600">
                  Delivery: {o.delivery.status}
                  {o.delivery.delivery_date
                    ? ` · ${o.delivery.delivery_date}`
                    : ""}
                </p>
              )}
              {o.status === "delivered" && !o.feedback && (
                <button
                  onClick={() => feedback(o.id)}
                  className="mt-3 rounded-lg bg-slate-900 px-3 py-2 text-sm text-white"
                >
                  Give Feedback
                </button>
              )}
            </div>
          ))}
        </div>
      )}
      {tab === "notifications" && (
        <div className="grid gap-3">
          {data.notifications.map((n) => (
            <button
              onClick={() => !n.is_read && markRead(n.id)}
              key={n.id}
              className={`rounded-2xl p-4 text-left ${n.is_read ? "bg-white" : "bg-blue-50"}`}
            >
              <div className="font-medium">{n.title}</div>
              <div className="text-sm text-slate-600">{n.message}</div>
            </button>
          ))}
        </div>
      )}{" "}
      {tab === "profile" && <Profile customer={data.customer} onSaved={load} />}
    </div>
  );
}
function Cards({ items, fields }) {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      {items?.map((x, i) => (
        <div key={x.id || i} className="rounded-2xl bg-white p-5 shadow-sm">
          {fields.map((f) => (
            <div key={f} className="mb-1">
              <span className="text-xs uppercase text-slate-400">
                {f.replaceAll("_", " ")}
              </span>
              <div className="text-sm">{String(x[f] ?? "—")}</div>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}
function Requests({ items, onCreated }) {
  const [open, setOpen] = useState(false);
  const [f, setF] = useState({
    product_name: "",
    quantity: 1,
    size: "",
    material_preference: "",
    requirement: "",
    budget: "",
    requested_date: "",
    design_requirement: "",
  });
  async function save(e) {
    e.preventDefault();
    await api.post("/sales/portal/requests/create/", f);
    setOpen(false);
    onCreated();
  }
  return (
    <div className="space-y-4">
      <button
        onClick={() => setOpen(!open)}
        className="rounded-xl bg-slate-900 px-4 py-2 text-sm text-white"
      >
        New Request
      </button>
      {open && (
        <form
          onSubmit={save}
          className="grid gap-3 rounded-2xl bg-white p-5 md:grid-cols-2"
        >
          {[
            "product_name",
            "quantity",
            "size",
            "material_preference",
            "budget",
            "requested_date",
          ].map((k) => (
            <input
              key={k}
              type={
                k === "quantity"
                  ? "number"
                  : k === "requested_date"
                    ? "date"
                    : "text"
              }
              placeholder={k.replaceAll("_", " ")}
              value={f[k]}
              onChange={(e) => setF({ ...f, [k]: e.target.value })}
              className="rounded-lg border px-3 py-2"
              required={k === "quantity"}
            />
          ))}
          <textarea
            placeholder="requirement"
            value={f.requirement}
            onChange={(e) => setF({ ...f, requirement: e.target.value })}
            className="rounded-lg border px-3 py-2 md:col-span-2"
            required
          />
          <textarea
            placeholder="design requirement"
            value={f.design_requirement}
            onChange={(e) => setF({ ...f, design_requirement: e.target.value })}
            className="rounded-lg border px-3 py-2 md:col-span-2"
          />
          <button className="rounded-lg bg-emerald-600 px-4 py-2 text-white md:col-span-2">
            Submit Request
          </button>
        </form>
      )}
      <Cards
        items={items}
        fields={[
          "request_no",
          "product_name",
          "quantity",
          "status",
          "requested_date",
        ]}
      />
    </div>
  );
}
function Profile({ customer, onSaved }) {
  const [form, setForm] = useState(customer || {});
  const save = async (e) => {
    e.preventDefault();
    await api.post("/sales/portal/profile/", form);
    onSaved();
  };
  return (
    <form
      onSubmit={save}
      className="max-w-2xl space-y-4 rounded-2xl bg-white p-6"
    >
      {["name", "email", "alternate_phone", "address"].map((k) => (
        <div key={k}>
          <label className="mb-1 block text-sm font-medium">{k}</label>
          <input
            value={form[k] || ""}
            onChange={(e) => setForm({ ...form, [k]: e.target.value })}
            className="w-full rounded-lg border px-3 py-2"
          />
        </div>
      ))}
      <button className="rounded-lg bg-slate-900 px-4 py-2 text-white">
        Save
      </button>
    </form>
  );
}
