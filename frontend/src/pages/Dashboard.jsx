import { useEffect, useState } from "react";
import { getDashboard } from "../services/api";

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    getDashboard()
      .then(setData)
      .catch((err) =>
        setError(err.response?.data?.detail || "Unable to load dashboard."),
      );
  }, []);

  if (error)
    return <div className="rounded-xl bg-red-50 p-5 text-red-700">{error}</div>;
  if (!data) return <div className="text-slate-500">Loading dashboard…</div>;

  const cards = [
    ["Staff", data.stats.total_staff, "People"],
    ["Active Staff", data.stats.active_staff, "Currently active"],
    ["Products", data.stats.total_products, "Catalog items"],
    ["Low Stock", data.stats.low_stock, "Needs attention"],
    ["Customers", data.stats.customers, "Registered customers"],
    ["Active Orders", data.stats.active_orders, "In progress"],
    ["New Enquiries", data.stats.new_enquiries, "Awaiting follow-up"],
    ["Open Tasks", data.stats.open_tasks, "Pending work"],
  ];

  return (
    <div className="space-y-6">
      <section className="overflow-hidden rounded-2xl bg-slate-900 p-6 text-white shadow-lg sm:p-8">
        <div className="flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm font-medium text-slate-300">
              SADACO Management System
            </p>
            <h1 className="mt-1 text-3xl font-bold tracking-tight sm:text-4xl">
              Good to see you 👋
            </h1>
            <p className="mt-2 max-w-2xl text-sm text-slate-300">
              Here is your current business overview. Monitor operations and act
              on items that need attention.
            </p>
          </div>
          <div className="rounded-xl bg-white/10 px-4 py-3 text-sm backdrop-blur-sm">
            <div className="text-slate-400">Overview</div>
            <div className="mt-1 font-semibold">Today&apos;s Operations</div>
          </div>
        </div>
      </section>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {cards.map(([label, value, hint], index) => (
          <div
            key={label}
            className="group rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="text-sm font-medium text-slate-500">{label}</p>
                <p className="mt-2 text-3xl font-bold tracking-tight text-slate-900">
                  {value ?? 0}
                </p>
                <p className="mt-1 text-xs text-slate-400">{hint}</p>
              </div>
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-slate-100 text-sm font-bold text-slate-600">
                {String(index + 1).padStart(2, "0")}
              </div>
            </div>
          </div>
        ))}
      </section>

      <section className="grid gap-6 lg:grid-cols-3">
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm lg:col-span-2">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h2 className="text-lg font-bold text-slate-900">
                Business Overview
              </h2>
              <p className="mt-1 text-sm text-slate-500">
                Key operational indicators at a glance.
              </p>
            </div>
            <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">
              Live data
            </span>
          </div>
          <div className="mt-6 grid gap-3 sm:grid-cols-2">
            {[
              ["Inventory", data.stats.total_products, "Products in catalog"],
              ["Workforce", data.stats.active_staff, "Active staff members"],
              ["Customers", data.stats.customers, "Customer accounts"],
              ["Orders", data.stats.active_orders, "Active orders"],
            ].map(([title, value, text]) => (
              <div key={title} className="rounded-xl bg-slate-50 p-4">
                <div className="flex items-center justify-between gap-3">
                  <span className="text-sm font-medium text-slate-600">
                    {title}
                  </span>
                  <span className="text-xl font-bold text-slate-900">
                    {value ?? 0}
                  </span>
                </div>
                <p className="mt-1 text-xs text-slate-400">{text}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-bold text-slate-900">
            Attention Required
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            Items that may need follow-up.
          </p>
          <div className="mt-5 space-y-3">
            <div className="rounded-xl border border-amber-100 bg-amber-50 p-4">
              <div className="flex justify-between gap-3">
                <span className="text-sm font-semibold text-amber-900">
                  Low Stock
                </span>
                <span className="font-bold text-amber-900">
                  {data.stats.low_stock ?? 0}
                </span>
              </div>
              <p className="mt-1 text-xs text-amber-700">
                Products below stock threshold.
              </p>
            </div>
            <div className="rounded-xl border border-blue-100 bg-blue-50 p-4">
              <div className="flex justify-between gap-3">
                <span className="text-sm font-semibold text-blue-900">
                  New Enquiries
                </span>
                <span className="font-bold text-blue-900">
                  {data.stats.new_enquiries ?? 0}
                </span>
              </div>
              <p className="mt-1 text-xs text-blue-700">
                Enquiries awaiting response.
              </p>
            </div>
            <div className="rounded-xl border border-violet-100 bg-violet-50 p-4">
              <div className="flex justify-between gap-3">
                <span className="text-sm font-semibold text-violet-900">
                  Open Tasks
                </span>
                <span className="font-bold text-violet-900">
                  {data.stats.open_tasks ?? 0}
                </span>
              </div>
              <p className="mt-1 text-xs text-violet-700">
                Tasks still in progress.
              </p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
