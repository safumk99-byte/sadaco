import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import api from "../services/api";

export default function ProductDetail() {
  const { id } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [show, setShow] = useState(false);
  async function load() {
    try {
      setData((await api.get(`/products/${id}/`)).data);
    } catch (e) {
      setError(e.response?.data?.detail || "Unable to load product.");
    }
  }
  useEffect(() => {
    load();
  }, [id]);
  if (error)
    return <div className="rounded-xl bg-red-50 p-4 text-red-700">{error}</div>;
  if (!data)
    return <div className="p-8 text-center text-slate-500">Loading...</div>;
  const p = data.product;
  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-3">
        <div>
          <Link to="/products" className="text-sm text-slate-500">
            ← Products
          </Link>
          <h1 className="mt-2 text-2xl font-bold">{p.name}</h1>
          <p className="text-sm text-slate-500">
            {p.sku} · {p.category?.name}
          </p>
        </div>
        {data.can_manage && (
          <button
            onClick={() => setShow(true)}
            className="rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white"
          >
            Stock Transaction
          </button>
        )}
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card
          l="Current Stock"
          v={`${p.stock_quantity} ${p.unit}`}
          alert={p.is_low_stock}
        />
        <Card l="Cost Price" v={`₹${Number(p.cost_price).toFixed(2)}`} />
        <Card l="Low Stock At" v={`${p.low_stock_threshold} ${p.unit}`} />
        <Card l="Status" v={p.status_label} />
      </div>
      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="font-semibold">Description</h2>
        <p className="mt-2 whitespace-pre-wrap text-sm text-slate-600">
          {p.description || "No description."}
        </p>
      </div>
      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-100 p-5">
          <h2 className="font-semibold">Stock History</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[700px] text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase text-slate-500">
              <tr>
                <th className="px-5 py-3">Date</th>
                <th className="px-5 py-3">Type</th>
                <th className="px-5 py-3">Quantity</th>
                <th className="px-5 py-3">Balance</th>
                <th className="px-5 py-3">Reference</th>
                <th className="px-5 py-3">By</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data.transactions.map((t) => (
                <tr key={t.id}>
                  <td className="px-5 py-4">
                    {new Date(t.created_at).toLocaleString()}
                  </td>
                  <td className="px-5 py-4">{t.transaction_type_label}</td>
                  <td className="px-5 py-4">{t.quantity}</td>
                  <td className="px-5 py-4 font-medium">{t.balance_after}</td>
                  <td className="px-5 py-4">{t.reference || "—"}</td>
                  <td className="px-5 py-4">{t.created_by || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      {show && (
        <StockForm
          product={p}
          onClose={() => setShow(false)}
          onSaved={() => {
            setShow(false);
            load();
          }}
        />
      )}
    </div>
  );
}
function Card({ l, v, alert }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="text-xs uppercase tracking-wide text-slate-500">{l}</div>
      <div
        className={`mt-2 text-xl font-bold ${alert ? "text-red-600" : "text-slate-900"}`}
      >
        {v}
      </div>
    </div>
  );
}
function StockForm({ product, onClose, onSaved }) {
  const [f, setF] = useState({
    transaction_type: "in",
    quantity: "",
    reference: "",
    remarks: "",
  });
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    try {
      await api.post("/products/stock/transaction/", {
        product: product.id,
        ...f,
      });
      onSaved();
    } catch (e) {
      setErr(e.response?.data?.detail || "Unable to record transaction.");
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <form
        onSubmit={submit}
        className="w-full max-w-lg rounded-2xl bg-white p-5 shadow-xl"
      >
        <div className="mb-5 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold">Stock Transaction</h2>
            <p className="text-sm text-slate-500">
              {product.name} · Current {product.stock_quantity} {product.unit}
            </p>
          </div>
          <button type="button" onClick={onClose}>
            ✕
          </button>
        </div>
        <div className="space-y-4">
          <label className="block">
            <span className="mb-1 block text-sm font-medium">
              Transaction Type
            </span>
            <select
              value={f.transaction_type}
              onChange={(e) => setF({ ...f, transaction_type: e.target.value })}
              className="w-full rounded-xl border border-slate-300 px-3 py-2.5"
            >
              <option value="in">Stock In</option>
              <option value="out">Stock Out</option>
              <option value="adjustment">Adjustment</option>
            </select>
          </label>
          <label className="block">
            <span className="mb-1 block text-sm font-medium">Quantity</span>
            <input
              required
              min="0.01"
              step="0.01"
              type="number"
              value={f.quantity}
              onChange={(e) => setF({ ...f, quantity: e.target.value })}
              className="w-full rounded-xl border border-slate-300 px-3 py-2.5"
            />
          </label>
          <label className="block">
            <span className="mb-1 block text-sm font-medium">Reference</span>
            <input
              value={f.reference}
              onChange={(e) => setF({ ...f, reference: e.target.value })}
              className="w-full rounded-xl border border-slate-300 px-3 py-2.5"
            />
          </label>
          <label className="block">
            <span className="mb-1 block text-sm font-medium">Remarks</span>
            <textarea
              rows="3"
              value={f.remarks}
              onChange={(e) => setF({ ...f, remarks: e.target.value })}
              className="w-full rounded-xl border border-slate-300 px-3 py-2.5"
            />
          </label>
          {err && (
            <div className="rounded-xl bg-red-50 p-3 text-sm text-red-700">
              {err}
            </div>
          )}
          <div className="flex justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="rounded-xl border border-slate-300 px-4 py-2.5"
            >
              Cancel
            </button>
            <button
              disabled={busy}
              className="rounded-xl bg-slate-900 px-5 py-2.5 font-semibold text-white"
            >
              {busy ? "Saving..." : "Record Transaction"}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}
