import { useEffect, useMemo, useState } from "react";
import { getReportsDashboard } from "../services/api";

const moneyKeys = new Set([
  "order_revenue",
  "payments",
  "paid_expenses",
  "purchase_value",
]);
const cards = [
  ["orders", "Orders"],
  ["order_revenue", "Order Revenue"],
  ["payments", "Payments"],
  ["enquiries", "Enquiries"],
  ["quotations", "Quotations"],
  ["customers", "New Customers"],
  ["stock_in", "Stock In"],
  ["stock_out", "Stock Out"],
  ["active_staff", "Active Staff"],
  ["present", "Present"],
  ["absent", "Absent"],
  ["leave", "Leave"],
  ["overdue", "Overdue Tasks"],
  ["low_stock", "Low Stock"],
  ["purchase_open", "Open Purchases"],
  ["paid_expenses", "Paid Expenses"],
  ["delivery_pending", "Pending Delivery"],
  ["active_campaigns", "Active Campaigns"],
  ["open_leads", "Open Leads"],
];

const money = (value) =>
  `₹ ${Number(value || 0).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const titleCase = (value) =>
  String(value || "Unknown")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());

export default function ReportsManagement() {
  const [data, setData] = useState({
    stats: {},
    order_status: [],
    enquiry_status: [],
    top_products: [],
  });
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      setData(await getReportsDashboard({ start, end }));
    } catch (err) {
      setError(
        err?.response?.data?.detail || "Unable to load reports right now.",
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);
  const stats = data.stats || {};
  const maxOrder = useMemo(
    () =>
      Math.max(
        1,
        ...(data.order_status || []).map((x) => Number(x.total || 0)),
      ),
    [data.order_status],
  );
  const maxEnquiry = useMemo(
    () =>
      Math.max(
        1,
        ...(data.enquiry_status || []).map((x) => Number(x.total || 0)),
      ),
    [data.enquiry_status],
  );

  return (
    <div className="space-y-6 pb-8">
      <div className="relative overflow-hidden rounded-[28px] bg-gradient-to-br from-blue-700 via-indigo-700 to-violet-800 p-5 text-white shadow-xl shadow-indigo-900/15 sm:p-6">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
          <div>
            <div className="flex items-center gap-3">
              <span className="inline-flex h-11 w-11 items-center justify-center rounded-2xl border border-white/20 bg-white/10 text-sm font-black backdrop-blur-sm">R</span>
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.2em] text-blue-100">Business Intelligence</p>
                <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">Reports & Analytics</h1>
              </div>
            </div>
            <p className="mt-3 max-w-2xl text-sm text-indigo-100">A consolidated view of sales, finance, stock, operations and people.</p>
          </div>
          <div className="flex flex-wrap items-end gap-2 rounded-2xl border border-white/15 bg-white/10 p-3 backdrop-blur-sm">
          <label className="text-xs font-medium text-slate-500">
            From
            <input
              className="mt-1 rounded-xl border border-white/20 bg-white/10 px-3 py-2 text-sm text-white outline-none backdrop-blur-sm focus:border-white/50 focus:ring-2 focus:ring-white/20"
              type="date"
              value={start}
              onChange={(e) => setStart(e.target.value)}
            />
          </label>
          <label className="text-xs font-medium text-slate-500">
            To
            <input
              className="mt-1 rounded-xl border border-white/20 bg-white/10 px-3 py-2 text-sm text-white outline-none backdrop-blur-sm focus:border-white/50 focus:ring-2 focus:ring-white/20"
              type="date"
              value={end}
              onChange={(e) => setEnd(e.target.value)}
            />
          </label>
          <button
            className="btn-primary h-10"
            onClick={load}
            disabled={loading}
          >
            {loading ? "Loading…" : "Apply"}
          </button>
          <button
            className="btn h-10"
            onClick={() => {
              setStart("");
              setEnd("");
              setTimeout(load, 0);
            }}
          >
            Reset
          </button>
        </div>
        </div>
      </div>

      {error && (
        <div className="card border border-red-200 bg-red-50 text-red-700">
          {error}
        </div>
      )}
      <div className="flex flex-wrap gap-2 text-xs text-slate-500">
        <span className="rounded-full bg-slate-100 px-3 py-1.5">
          Period: {data.start || "—"} → {data.end || "—"}
        </span>
        <span className="rounded-full bg-emerald-50 text-emerald-700 px-3 py-1.5">
          Live business data
        </span>
      </div>

      <section className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-3">
        {cards.map(([key, label]) => (
          <div className="relative overflow-hidden rounded-2xl border border-slate-200 bg-white p-4 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md" key={key}>
            <div className="muted text-xs">{label}</div>
            <div className="mt-2 text-xl font-bold tracking-tight">
              {moneyKeys.has(key) ? money(stats[key]) : (stats[key] ?? 0)}
            </div>
          </div>
        ))}
      </section>
      <div className="grid xl:grid-cols-2 gap-4">
        <section className="card">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="font-semibold">Order Status</h2>
              <p className="muted text-xs">Orders within the selected period</p>
            </div>
            <span className="text-xs text-slate-400">
              {(data.order_status || []).length} statuses
            </span>
          </div>
          <div className="space-y-4">
            {(data.order_status || []).length ? (
              data.order_status.map((item) => (
                <div key={item.status}>
                  <div className="flex justify-between text-sm mb-1">
                    <span>{titleCase(item.status)}</span>
                    <b>{item.total}</b>
                  </div>
                  <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
                    <div
                      className="h-full rounded-full bg-slate-900"
                      style={{
                        width: `${(Number(item.total) / maxOrder) * 100}%`,
                      }}
                    />
                  </div>
                </div>
              ))
            ) : (
              <p className="muted text-sm">No order data for this period.</p>
            )}
          </div>
        </section>

        <section className="card">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="font-semibold">Enquiry Status</h2>
              <p className="muted text-xs">Lead and enquiry pipeline</p>
            </div>
          </div>
          <div className="space-y-4">
            {(data.enquiry_status || []).length ? (
              data.enquiry_status.map((item) => (
                <div key={item.status}>
                  <div className="flex justify-between text-sm mb-1">
                    <span>{titleCase(item.status)}</span>
                    <b>{item.total}</b>
                  </div>
                  <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
                    <div
                      className="h-full rounded-full bg-indigo-500"
                      style={{
                        width: `${(Number(item.total) / maxEnquiry) * 100}%`,
                      }}
                    />
                  </div>
                </div>
              ))
            ) : (
              <p className="muted text-sm">No enquiry data for this period.</p>
            )}
          </div>
        </section>
      </div>

      <section className="card overflow-hidden">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
          <div>
            <h2 className="font-semibold">Top Stock Products</h2>
            <p className="muted text-xs">Highest current stock levels</p>
          </div>
          <span className="text-xs text-slate-400">Top 5</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left text-xs text-slate-500">
                <th className="py-3 pr-4">Product</th>
                <th className="py-3 pr-4">SKU</th>
                <th className="py-3 pr-4 text-right">Stock</th>
                <th className="py-3 text-right">Selling Price</th>
              </tr>
            </thead>
            <tbody>
              {(data.top_products || []).length ? (
                data.top_products.map((product) => (
                  <tr
                    className="border-b last:border-0"
                    key={product.sku || product.name}
                  >
                    <td className="py-3 pr-4 font-medium">{product.name}</td>
                    <td className="py-3 pr-4 text-slate-500">
                      {product.sku || "—"}
                    </td>
                    <td className="py-3 pr-4 text-right font-semibold">
                      {product.stock_quantity ?? 0}
                    </td>
                    <td className="py-3 text-right">
                      {money(product.selling_price)}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="4" className="py-8 text-center muted">
                    No product data available.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div className="card border-l-4 border-l-emerald-500">
          <div className="muted text-xs">Attendance</div>
          <div className="mt-2 font-semibold">{stats.present ?? 0} Present</div>
          <div className="text-xs text-slate-500 mt-1">
            {stats.absent ?? 0} absent · {stats.leave ?? 0} leave
          </div>
        </div>
        <div className="card border-l-4 border-l-amber-500">
          <div className="muted text-xs">Inventory Alert</div>
          <div className="mt-2 font-semibold">
            {stats.low_stock ?? 0} Low Stock
          </div>
          <div className="text-xs text-slate-500 mt-1">
            Review replenishment needs
          </div>
        </div>
        <div className="card border-l-4 border-l-blue-500">
          <div className="muted text-xs">Delivery</div>
          <div className="mt-2 font-semibold">
            {stats.delivery_pending ?? 0} Pending
          </div>
          <div className="text-xs text-slate-500 mt-1">
            Pending, scheduled, ready or out
          </div>
        </div>
      </section>
    </div>
  );
}
