import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../services/api";

export default function StockManagement() {
  const [data, setData] = useState({ transactions: [], can_manage: false });
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  async function load() {
    setLoading(true);
    try {
      setData((await api.get("/products/stock/", { params: { q } })).data);
    } catch (e) {
      setError(e.response?.data?.detail || "Unable to load stock history.");
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    load();
  }, [q]);
  return (
    <div className="space-y-6">
      <div>
        <Link to="/products" className="text-sm text-slate-500">
          ← Products
        </Link>
        <h1 className="mt-2 text-2xl font-bold">Stock Management</h1>
        <p className="text-sm text-slate-500">
          Review stock movements across internal products.
        </p>
      </div>
      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search product, SKU or reference"
          className="w-full rounded-xl border border-slate-300 px-3 py-2.5 text-sm md:max-w-xl"
        />
      </div>
      {error && (
        <div className="rounded-xl bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}
      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-100 bg-slate-50 px-5 py-3 text-xs font-semibold uppercase tracking-wide text-slate-500">
          Stock Movement History
        </div>
        {loading ? (
          <div className="p-8 text-center text-slate-500">
            Loading stock history...
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[850px] text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase text-slate-500">
                <tr>
                  <th className="px-5 py-3">Date</th>
                  <th className="px-5 py-3">Product</th>
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
                    <td className="px-5 py-4">
                      <Link
                        to={`/products/${t.product.id}`}
                        className="font-semibold hover:underline"
                      >
                        {t.product.name}
                      </Link>
                      <div className="text-xs text-slate-500">
                        {t.product.sku}
                      </div>
                    </td>
                    <td className="px-5 py-4">{t.transaction_type_label}</td>
                    <td className="px-5 py-4">{t.quantity}</td>
                    <td className="px-5 py-4 font-semibold">
                      {t.balance_after}
                    </td>
                    <td className="px-5 py-4">{t.reference || "—"}</td>
                    <td className="px-5 py-4">{t.created_by || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
