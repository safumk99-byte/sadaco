import { useEffect, useMemo, useState } from "react";
import {
  createPurchaseOrder,
  createPurchaseSupplier,
  getPurchaseOrders,
  getPurchaseSummary,
  receivePurchaseOrder,
} from "../services/api";

const money = (v) =>
  `₹ ${Number(v || 0).toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;
const Field = ({ label, children }) => (
  <label className="block">
    <span className="mb-1 block text-xs font-semibold text-slate-500">
      {label}
    </span>
    {children}
  </label>
);
const input =
  "w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100";

export default function PurchaseManagement() {
  const [tab, setTab] = useState("orders"),
    [stats, setStats] = useState({}),
    [data, setData] = useState({
      orders: [],
      suppliers: [],
      products: [],
      statuses: [],
    });
  const [q, setQ] = useState(""),
    [status, setStatus] = useState(""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const [modal, setModal] = useState(null);
  const [form, setForm] = useState({});
  const [selectedOrder, setSelectedOrder] = useState(null);
  const load = async () => {
    try {
      setError("");
      const [s, d] = await Promise.all([
        getPurchaseSummary(),
        getPurchaseOrders({ q, status }),
      ]);
      setStats(s.stats);
      setData(d);
    } catch (e) {
      setError(e.response?.data?.detail || "Unable to load purchase data.");
    }
  };
  useEffect(() => {
    load();
  }, [status]);
  const suppliers = useMemo(() => data.suppliers || [], [data.suppliers]);
  const submitOrder = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await createPurchaseOrder({
        ...form,
        quantity: form.quantity || 1,
        unit_cost: form.unit_cost || 0,
      });
      setModal(null);
      setForm({});
      await load();
    } catch (e) {
      setError(e.response?.data?.detail || "Could not create purchase order.");
    } finally {
      setBusy(false);
    }
  };
  const submitSupplier = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await createPurchaseSupplier(form);
      setModal(null);
      setForm({});
      await load();
    } catch (e) {
      setError(e.response?.data?.detail || "Could not create supplier.");
    } finally {
      setBusy(false);
    }
  };
  const startReceive = (order) => {
    setSelectedOrder(order);
    setForm({
      received_date: new Date().toISOString().slice(0, 10),
      location: "",
      supplier_reference: "",
      items: (order.items || [])
        .filter((item) => Number(item.pending_quantity) > 0)
        .map((item) => ({
          purchase_item_id: item.id,
          received_quantity: item.pending_quantity,
        })),
    });
    setModal("receive");
  };
  const updateReceiptQuantity = (itemId, quantity) => {
    setForm((current) => ({
      ...current,
      items: (current.items || []).map((item) =>
        item.purchase_item_id === itemId
          ? { ...item, received_quantity: quantity }
          : item,
      ),
    }));
  };
  const submitReceipt = async (e) => {
    e.preventDefault();
    if (!selectedOrder) return;
    setBusy(true);
    setError("");
    try {
      await receivePurchaseOrder(selectedOrder.id, {
        received_date: form.received_date,
        location: form.location,
        supplier_reference: form.supplier_reference,
        items: form.items,
      });
      setModal(null);
      setSelectedOrder(null);
      setForm({});
      await load();
    } catch (e) {
      setError(e.response?.data?.detail || "Could not receive goods.");
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="space-y-5">
      <div className="relative overflow-hidden flex flex-wrap items-center justify-between gap-4 rounded-[24px] bg-gradient-to-br from-blue-700 via-indigo-700 to-violet-800 p-5 text-white shadow-xl shadow-indigo-900/15 sm:p-6">
        <div>
          <h1 className="text-2xl font-bold text-white">
            Purchase Management
          </h1>
          <p className="text-sm text-blue-100">
            Suppliers, purchase orders and goods receiving.
          </p>
        </div>
        <button
          onClick={() => {
            setForm({
              order_date: new Date().toISOString().slice(0, 10),
              status: "draft",
              discount: 0,
              tax: 0,
              quantity: 1,
              unit_cost: 0,
            });
            setModal("order");
          }}
          className="rounded-xl border border-white/40 bg-white/15 px-4 py-2.5 text-sm font-semibold text-white backdrop-blur-sm hover:bg-white/25"
        >
          + New Purchase
        </button>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        {[
          ["Draft", stats.draft],
          ["Open", stats.open_orders],
          ["Received", stats.received],
          ["Purchase Value", money(stats.total_value)],
          ["Active Suppliers", stats.suppliers],
        ].map(([a, b]) => (
          <div
            className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
            key={a}
          >
            <div className="text-xs font-semibold uppercase text-slate-400">
              {a}
            </div>
            <div className="mt-2 text-2xl font-bold">{b ?? 0}</div>
          </div>
        ))}
      </div>
      <div className="rounded-2xl border border-slate-200 bg-white p-4">
        <div className="flex flex-wrap gap-2 border-b border-slate-100 pb-3">
          <button
            onClick={() => setTab("orders")}
            className={`rounded-lg px-3 py-2 text-sm font-semibold ${tab === "orders" ? "bg-slate-900 text-white" : "text-slate-600"}`}
          >
            Purchase Orders
          </button>
          <button
            onClick={() => setTab("suppliers")}
            className={`rounded-lg px-3 py-2 text-sm font-semibold ${tab === "suppliers" ? "bg-slate-900 text-white" : "text-slate-600"}`}
          >
            Suppliers
          </button>
          <button
            onClick={() => {
              setForm({ name: "", status: "active" });
              setModal("supplier");
            }}
            className="ml-auto rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold"
          >
            + Supplier
          </button>
        </div>
        {error && (
          <div className="mt-3 rounded-xl bg-red-50 p-3 text-sm text-red-700">
            {error}
          </div>
        )}
        {tab === "orders" ? (
          <>
            <div className="flex flex-wrap gap-2 py-4">
              <input
                value={q}
                onChange={(e) => setQ(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && load()}
                placeholder="Search PO or supplier"
                className={input + " max-w-sm"}
              />
              <select
                value={status}
                onChange={(e) => setStatus(e.target.value)}
                className={input + " max-w-xs"}
              >
                <option value="">All statuses</option>
                {(data.statuses || []).map((x) => (
                  <option key={x.value} value={x.value}>
                    {x.label}
                  </option>
                ))}
              </select>
              <button
                onClick={load}
                className="rounded-xl border border-slate-200 px-4 py-2 text-sm font-semibold"
              >
                Search
              </button>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[850px] text-left text-sm">
                <thead className="text-xs uppercase text-slate-400">
                  <tr>
                    <th className="p-3">PO</th>
                    <th>Supplier</th>
                    <th>Order date</th>
                    <th>Status</th>
                    <th>Total</th>
                    <th>Items</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {(data.orders || []).map((o) => (
                    <tr className="border-t border-slate-100" key={o.id}>
                      <td className="p-3 font-semibold">{o.po_no}</td>
                      <td>{o.supplier.name}</td>
                      <td>{o.order_date}</td>
                      <td>
                        <span className="rounded-full bg-slate-100 px-2 py-1 text-xs">
                          {o.status_label}
                        </span>
                      </td>
                      <td>{money(o.total)}</td>
                      <td>
                        {o.items
                          ?.map(
                            (i) => `${i.product?.name || i.material_variant?.name || "-"} × ${i.quantity}`,
                          )
                          .join(", ")}
                      </td>
                      <td>
                        {o.status !== "received" &&
                          o.status !== "cancelled" && (
                            <button
                              onClick={() => startReceive(o)}
                              className="rounded-lg bg-emerald-50 px-3 py-1.5 text-xs font-semibold text-emerald-700"
                            >
                              Receive
                            </button>
                          )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        ) : (
          <div className="overflow-x-auto py-4">
            <table className="w-full min-w-[700px] text-left text-sm">
              <thead className="text-xs uppercase text-slate-400">
                <tr>
                  <th className="p-3">Supplier</th>
                  <th>Contact</th>
                  <th>Phone</th>
                  <th>Email</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {suppliers.map((s) => (
                  <tr className="border-t border-slate-100" key={s.id}>
                    <td className="p-3 font-semibold">{s.name}</td>
                    <td>{s.contact_person || "-"}</td>
                    <td>{s.phone || "-"}</td>
                    <td>{s.email || "-"}</td>
                    <td>{s.status_label}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      {modal === "receive" && selectedOrder && (
        <Modal title={`Receive Goods · ${selectedOrder.po_no}`} close={() => setModal(null)}>
          <form onSubmit={submitReceipt} className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="Received date">
                <input
                  type="date"
                  required
                  className={input}
                  value={form.received_date || ""}
                  onChange={(e) => setForm({ ...form, received_date: e.target.value })}
                />
              </Field>
              <Field label="Stock location (required for materials)">
                <input
                  className={input}
                  value={form.location || ""}
                  placeholder="Enter stock location"
                  onChange={(e) => setForm({ ...form, location: e.target.value })}
                />
              </Field>
              <div className="sm:col-span-2">
                <Field label="Supplier invoice / reference">
                  <input
                    className={input}
                    value={form.supplier_reference || ""}
                    onChange={(e) => setForm({ ...form, supplier_reference: e.target.value })}
                  />
                </Field>
              </div>
            </div>
            <div className="overflow-x-auto rounded-xl border border-slate-200">
              <table className="w-full min-w-[560px] text-left text-sm">
                <thead className="bg-slate-50 text-xs uppercase text-slate-500">
                  <tr>
                    <th className="p-3">Item</th>
                    <th className="p-3">Ordered</th>
                    <th className="p-3">Received</th>
                    <th className="p-3">Pending</th>
                    <th className="p-3">Receive now</th>
                  </tr>
                </thead>
                <tbody>
                  {(selectedOrder.items || [])
                    .filter((item) => Number(item.pending_quantity) > 0)
                    .map((item) => (
                      <tr key={item.id} className="border-t border-slate-100">
                        <td className="p-3 font-medium">
                          {item.product?.name || item.material_variant?.name || "Stock item"}
                        </td>
                        <td className="p-3">{item.quantity}</td>
                        <td className="p-3">{item.received_quantity}</td>
                        <td className="p-3 font-semibold">{item.pending_quantity}</td>
                        <td className="p-3">
                          <input
                            type="number"
                            step="0.01"
                            min="0"
                            max={item.pending_quantity}
                            required
                            className={input + " min-w-[110px]"}
                            value={
                              form.items?.find((line) => line.purchase_item_id === item.id)
                                ?.received_quantity ?? "0"
                            }
                            onChange={(e) => updateReceiptQuantity(item.id, e.target.value)}
                          />
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
            <p className="text-xs text-slate-500">
              Enter only the quantity physically received now. Any remaining quantity stays pending and can be received later in a separate receipt.
            </p>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setModal(null)}
                className="rounded-xl border px-4 py-2"
              >
                Cancel
              </button>
              <button
                disabled={busy}
                className="rounded-xl bg-slate-900 px-4 py-2 font-semibold text-white disabled:opacity-50"
              >
                {busy ? "Saving..." : "Save Goods Receipt"}
              </button>
            </div>
          </form>
        </Modal>
      )}
      {modal === "order" && (
        <Modal title="Create Purchase Order" close={() => setModal(null)}>
          <form onSubmit={submitOrder} className="grid gap-4 sm:grid-cols-2">
            <Field label="Supplier">
              <select
                required
                className={input}
                value={form.supplier || ""}
                onChange={(e) => setForm({ ...form, supplier: e.target.value })}
              >
                <option value="">Select supplier</option>
                {suppliers.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Product">
              <select
                required
                className={input}
                value={form.product || ""}
                onChange={(e) => setForm({ ...form, product: e.target.value })}
              >
                <option value="">Select product</option>
                {(data.products || []).map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} · {p.sku}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Order date">
              <input
                type="date"
                required
                className={input}
                value={form.order_date || ""}
                onChange={(e) =>
                  setForm({ ...form, order_date: e.target.value })
                }
              />
            </Field>
            <Field label="Expected date">
              <input
                type="date"
                className={input}
                value={form.expected_date || ""}
                onChange={(e) =>
                  setForm({ ...form, expected_date: e.target.value })
                }
              />
            </Field>
            <Field label="Quantity">
              <input
                type="number"
                step="0.01"
                min="0.01"
                required
                className={input}
                value={form.quantity || ""}
                onChange={(e) => setForm({ ...form, quantity: e.target.value })}
              />
            </Field>
            <Field label="Unit cost">
              <input
                type="number"
                step="0.01"
                min="0"
                required
                className={input}
                value={form.unit_cost || ""}
                onChange={(e) =>
                  setForm({ ...form, unit_cost: e.target.value })
                }
              />
            </Field>
            <Field label="Discount">
              <input
                type="number"
                step="0.01"
                min="0"
                className={input}
                value={form.discount || 0}
                onChange={(e) => setForm({ ...form, discount: e.target.value })}
              />
            </Field>
            <Field label="Tax">
              <input
                type="number"
                step="0.01"
                min="0"
                className={input}
                value={form.tax || 0}
                onChange={(e) => setForm({ ...form, tax: e.target.value })}
              />
            </Field>
            <div className="sm:col-span-2">
              {form.status === "sent" && <Field label="Approval reason (required if above Founder threshold)"><textarea className={input} rows="2" value={form.approval_reason || ""} onChange={(e) => setForm({ ...form, approval_reason: e.target.value })} /></Field>}
              <Field label="Notes">
                <textarea
                  className={input}
                  rows="3"
                  value={form.notes || ""}
                  onChange={(e) => setForm({ ...form, notes: e.target.value })}
                />
              </Field>
            </div>
            <div className="sm:col-span-2 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setModal(null)}
                className="rounded-xl border px-4 py-2"
              >
                Cancel
              </button>
              <button
                disabled={busy}
                className="rounded-xl bg-slate-900 px-4 py-2 font-semibold text-white"
              >
                Create
              </button>
            </div>
          </form>
        </Modal>
      )}
      {modal === "supplier" && (
        <Modal title="Add Supplier" close={() => setModal(null)}>
          <form onSubmit={submitSupplier} className="grid gap-4 sm:grid-cols-2">
            {[
              ["name", "Name"],
              ["contact_person", "Contact person"],
              ["phone", "Phone"],
              ["email", "Email"],
              ["tax_number", "Tax number"],
              ["payment_terms", "Payment terms"],
            ].map(([k, l]) => (
              <Field label={l} key={k}>
                <input
                  required={k === "name"}
                  className={input}
                  value={form[k] || ""}
                  onChange={(e) => setForm({ ...form, [k]: e.target.value })}
                />
              </Field>
            ))}
            <div className="sm:col-span-2">
              <Field label="Address">
                <textarea
                  className={input}
                  rows="2"
                  value={form.address || ""}
                  onChange={(e) =>
                    setForm({ ...form, address: e.target.value })
                  }
                />
              </Field>
            </div>
            <div className="sm:col-span-2 flex justify-end">
              <button className="rounded-xl bg-slate-900 px-4 py-2 font-semibold text-white">
                Save Supplier
              </button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
}
function Modal({ title, close, children }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4">
      <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-2xl bg-white p-5 shadow-2xl">
        <div className="mb-5 flex items-center justify-between">
          <h2 className="text-lg font-bold">{title}</h2>
          <button onClick={close} className="text-xl text-slate-400">
            ×
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
