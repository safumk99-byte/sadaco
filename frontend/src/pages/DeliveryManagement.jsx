import { useEffect, useState } from "react";
import api, {
  getDeliverySummary,
  updateDelivery,
  saveDeliveryFeedback,
} from "../services/api";
const empty = {
  delivery_date: "",
  address: "",
  transport: "",
  responsible_person: "",
  installation_required: false,
  installation_date: "",
  status: "pending",
  acknowledgement: "",
  completion_notes: "",
};
export default function DeliveryManagement() {
  const [data, setData] = useState({ stats: {}, deliveries: [] }),
    [q, setQ] = useState(""),
    [sel, setSel] = useState(null),
    [form, setForm] = useState(empty),
    [fb, setFb] = useState({ rating: "", comment: "" }),
    [loading, setLoading] = useState(true);
  const load = async () => {
    setLoading(true);
    try {
      setData(await getDeliverySummary({ q }));
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    load();
  }, [q]);
  const open = async (id) => {
    const d = (await api.get(`/delivery/orders/${id}/`)).data;
    setSel(id);
    setForm(d);
    setFb(d.feedback || { rating: "", comment: "" });
  };
  const save = async () => {
    await updateDelivery(sel, form);
    await saveDeliveryFeedback(sel, fb);
    setSel(null);
    load();
  };
  return (
    <div className="space-y-6">
      <Header title="Delivery & Installation" />
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        {[
          ["pending", "Pending"],
          ["scheduled", "Scheduled"],
          ["out", "Out"],
          ["delivered", "Delivered"],
          ["installations", "Installation"],
        ].map(([k, l]) => (
          <K key={k} label={l} value={data.stats[k] ?? 0} />
        ))}
      </div>
      <div className="card flex flex-col gap-2 p-4 sm:flex-row sm:items-center">
        <div className="flex-1">
          <p className="text-sm font-semibold text-slate-800">
            Delivery records
          </p>
          <p className="text-xs text-slate-500">
            Search orders and customers to manage delivery status.
          </p>
        </div>
        <input
          className="input sm:max-w-sm"
          placeholder="Search order or customer..."
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
      </div>
      <div className="card overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr>
              <th>Order</th>
              <th>Customer</th>
              <th>Status</th>
              <th>Delivery</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {data.deliveries.map((d) => (
              <tr key={d.id}>
                <td>{d.order_no}</td>
                <td>{d.customer}</td>
                <td>{d.status_label}</td>
                <td>{d.delivery_date || "—"}</td>
                <td>
                  <button className="btn" onClick={() => open(d.order_id)}>
                    Manage
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!loading && !data.deliveries.length && (
          <p className="muted p-4">No delivery records.</p>
        )}
      </div>
      {sel && (
        <Modal
          title={`Delivery · ${form.order_no}`}
          onClose={() => setSel(null)}
        >
          <div className="grid md:grid-cols-2 gap-3">
            {[
              ["delivery_date", "Delivery date"],
              ["transport", "Transport"],
              ["responsible_person", "Responsible person"],
              ["installation_date", "Installation date"],
            ].map(([k, l]) => (
              <label className="field" key={k}>
                {l}
                <input
                  type={k.includes("date") ? "date" : "text"}
                  value={form[k] || ""}
                  onChange={(e) => setForm({ ...form, [k]: e.target.value })}
                />
              </label>
            ))}
            <label className="field">
              Status
              <select
                value={form.status}
                onChange={(e) => setForm({ ...form, status: e.target.value })}
              >
                {[
                  "pending",
                  "scheduled",
                  "ready",
                  "out",
                  "delivered",
                  "installed",
                  "cancelled",
                ].map((x) => (
                  <option key={x}>{x}</option>
                ))}
              </select>
            </label>
            <label className="field flex-row items-center gap-2">
              <input
                type="checkbox"
                checked={!!form.installation_required}
                onChange={(e) =>
                  setForm({ ...form, installation_required: e.target.checked })
                }
              />{" "}
              Installation required
            </label>
          </div>
          <label className="field">
            Address
            <textarea
              value={form.address || ""}
              onChange={(e) => setForm({ ...form, address: e.target.value })}
            />
          </label>
          <label className="field">
            Completion notes
            <textarea
              value={form.completion_notes || ""}
              onChange={(e) =>
                setForm({ ...form, completion_notes: e.target.value })
              }
            />
          </label>
          <div className="border-t pt-4 mt-4">
            <h3 className="font-semibold mb-2">Customer Feedback</h3>
            <div className="grid md:grid-cols-2 gap-3">
              <input
                className="input"
                type="number"
                min="1"
                max="5"
                placeholder="Rating 1–5"
                value={fb.rating || ""}
                onChange={(e) => setFb({ ...fb, rating: e.target.value })}
              />
              <textarea
                className="input"
                placeholder="Comment"
                value={fb.comment || ""}
                onChange={(e) => setFb({ ...fb, comment: e.target.value })}
              />
            </div>
          </div>
          <div className="flex justify-end gap-2 mt-5">
            <button className="btn" onClick={() => setSel(null)}>
              Cancel
            </button>
            <button className="btn-primary" onClick={save}>
              Save
            </button>
          </div>
        </Modal>
      )}
    </div>
  );
}
function Header({ title }) {
  return (
    <div className="relative overflow-hidden rounded-[28px] bg-gradient-to-br from-blue-700 via-indigo-700 to-violet-800 p-5 text-white shadow-xl shadow-indigo-900/15 sm:p-6">
      <div className="relative flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-blue-100">Logistics & Customer Experience</p>
          <h1 className="mt-1 text-2xl font-bold tracking-tight sm:text-3xl">{title}</h1>
          <p className="mt-1 max-w-2xl text-sm text-indigo-100">Schedule deliveries, installation and customer feedback from one operational workspace.</p>
        </div>
        <div className="rounded-2xl border border-white/20 bg-white/10 px-4 py-3 text-sm backdrop-blur-sm">
          <div className="text-blue-100">Live workflow</div>
          <div className="font-semibold">Delivery control</div>
        </div>
      </div>
    </div>
  );
}
function K({ label, value }) {
  return (
    <div className="card relative overflow-hidden p-4 transition-all hover:-translate-y-0.5 hover:shadow-md">
      <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-blue-500 via-indigo-500 to-violet-500" />
      <div className="muted text-xs font-semibold uppercase tracking-wide">{label}</div>
      <div className="mt-2 text-2xl font-bold text-slate-900">{value}</div>
    </div>
  );
}
function Modal({ title, onClose, children }) {
  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl w-full max-w-3xl max-h-[90vh] overflow-auto p-6">
        <div className="flex justify-between mb-4">
          <h2 className="text-xl font-bold">{title}</h2>
          <button onClick={onClose}>✕</button>
        </div>
        {children}
      </div>
    </div>
  );
}
