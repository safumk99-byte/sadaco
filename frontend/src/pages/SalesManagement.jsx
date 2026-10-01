import { useEffect, useMemo, useState } from "react";
import api from "../services/api";

const tabs = [
  ["overview", "Overview"],
  ["customers", "Customers"],
  ["enquiries", "Enquiries"],
  ["quotations", "Quotations"],
  ["orders", "Orders"],
];
const money = (v) =>
  `₹${Number(v || 0).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

export default function SalesManagement() {
  const [tab, setTab] = useState("overview");
  const [summary, setSummary] = useState(null);
  const [data, setData] = useState({
    customers: [],
    enquiries: [],
    quotations: [],
    orders: [],
    can_manage: false,
    statuses: [],
  });
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [form, setForm] = useState(null);
  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const s = await api.get("/sales/summary/");
      setSummary(s.data);
      const [c, e, qu, o] = await Promise.all([
        api.get("/sales/customers/", { params: { q } }),
        api.get("/sales/enquiries/", { params: { q, status } }),
        api.get("/sales/quotations/", { params: { q, status } }),
        api.get("/sales/orders/", { params: { q, status } }),
      ]);
      setData({
        customers: c.data.customers,
        enquiries: e.data.enquiries,
        quotations: qu.data.quotations,
        orders: o.data.orders,
        can_manage: c.data.can_manage,
        statuses: e.data.statuses,
      });
    } catch (e) {
      setError(e.response?.data?.detail || "Unable to load sales data.");
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    load();
  }, [q, status]);
  const list = useMemo(
    () =>
      ({
        customers: data.customers,
        enquiries: data.enquiries,
        quotations: data.quotations,
        orders: data.orders,
      })[tab] || [],
    [tab, data],
  );
  return (
    <div className="space-y-6">
      <header className="relative overflow-hidden flex flex-col justify-between gap-4 rounded-[24px] bg-gradient-to-br from-blue-700 via-indigo-700 to-violet-800 p-5 text-white shadow-xl shadow-indigo-900/15 sm:flex-row sm:items-center sm:p-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Sales & CRM</h1>
          <p className="text-sm text-blue-100">
            Customer → Enquiry → Quotation → Order workflow.
          </p>
        </div>
        {data.can_manage && (
          <button
            onClick={() =>
              setForm({
                type:
                  tab === "customers"
                    ? "customer"
                    : tab === "enquiries"
                      ? "enquiry"
                      : tab === "quotations"
                        ? "quotation"
                        : "order",
              })
            }
            className="rounded-xl border border-white/40 bg-white/15 px-4 py-2.5 text-sm font-semibold text-white backdrop-blur-sm hover:bg-white/25"
          >
            +{" "}
            {tab === "customers"
              ? "Customer"
              : tab === "enquiries"
                ? "Enquiry"
                : tab === "quotations"
                  ? "Quotation"
                  : "Sales Order"}
          </button>
        )}
      </header>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
        <Stat label="Active Customers" value={summary?.stats?.customers ?? 0} />
        <Stat
          label="New Enquiries"
          value={summary?.stats?.new_enquiries ?? 0}
        />
        <Stat label="Open Quotations" value={summary?.stats?.quotations ?? 0} />
        <Stat label="Open Orders" value={summary?.stats?.open_orders ?? 0} />
        <Stat
          label="Pending Requests"
          value={summary?.stats?.pending_requests ?? 0}
        />
      </div>
      <div className="flex gap-1 overflow-x-auto rounded-2xl border border-slate-200 bg-white p-1 shadow-sm">
        {tabs.map(([v, l]) => (
          <button
            key={v}
            onClick={() => {
              setTab(v);
              setStatus("");
            }}
            className={`whitespace-nowrap rounded-xl px-4 py-2.5 text-sm font-semibold ${tab === v ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-100"}`}
          >
            {l}
          </button>
        ))}
      </div>
      {tab === "overview" ? (
        <Overview summary={summary} />
      ) : (
        <>
          <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="grid gap-3 md:grid-cols-3">
              <input
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Search customer, enquiry, quotation or order..."
                className="rounded-xl border border-slate-300 px-3 py-2.5 text-sm md:col-span-2"
              />
              <select
                value={status}
                onChange={(e) => setStatus(e.target.value)}
                className="rounded-xl border border-slate-300 px-3 py-2.5 text-sm"
              >
                <option value="">All Status</option>
                {(tab === "enquiries"
                  ? data.statuses
                  : tab === "quotations"
                    ? [
                        "draft",
                        "sent",
                        "approved",
                        "rejected",
                        "expired",
                        "converted",
                      ].map((x) => ({ value: x, label: x.replace("_", " ") }))
                    : tab === "orders"
                      ? [
                          "confirmed",
                          "design_pending",
                          "production_pending",
                          "in_production",
                          "ready",
                          "delivered",
                          "cancelled",
                        ].map((x) => ({
                          value: x,
                          label: x.replaceAll("_", " "),
                        }))
                      : []
                ).map((x) => (
                  <option key={x.value} value={x.value}>
                    {x.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
          {error && (
            <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">
              {error}
            </div>
          )}
          <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
            {loading ? (
              <div className="p-10 text-center text-sm text-slate-500">
                Loading sales...
              </div>
            ) : (
              <SalesTable
                tab={tab}
                rows={list}
                onEdit={(x) =>
                  setForm({
                    type:
                      tab === "customers"
                        ? "customer"
                        : tab === "enquiries"
                          ? "enquiry"
                          : tab === "quotations"
                            ? "quotation"
                            : "order",
                    initial: x,
                  })
                }
              />
            )}
          </div>
        </>
      )}
      {form && (
        <SalesForm
          type={form.type}
          initial={form.initial}
          customers={data.customers}
          onClose={() => setForm(null)}
          onSaved={() => {
            setForm(null);
            load();
          }}
        />
      )}
    </div>
  );
}
function Stat({ label, value }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="text-xs font-medium uppercase tracking-wide text-slate-500">
        {label}
      </div>
      <div className="mt-2 text-2xl font-bold text-slate-900">{value}</div>
    </div>
  );
}
function Overview({ summary }) {
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Panel title="Recent Enquiries">
        <div className="space-y-3">
          {summary?.recent_enquiries?.length ? (
            summary.recent_enquiries.map((x) => (
              <div
                key={x.id}
                className="flex justify-between gap-3 rounded-xl bg-slate-50 p-3"
              >
                <div>
                  <div className="font-semibold">{x.enquiry_no}</div>
                  <div className="text-sm text-slate-500">
                    {x.customer.name} · {x.product_type}
                  </div>
                </div>
                <span className="rounded-full bg-white px-2.5 py-1 text-xs font-medium text-slate-600">
                  {x.status_label}
                </span>
              </div>
            ))
          ) : (
            <Empty />
          )}
        </div>
      </Panel>
      <Panel title="Recent Orders">
        <div className="space-y-3">
          {summary?.recent_orders?.length ? (
            summary.recent_orders.map((x) => (
              <div
                key={x.id}
                className="flex justify-between gap-3 rounded-xl bg-slate-50 p-3"
              >
                <div>
                  <div className="font-semibold">{x.order_no}</div>
                  <div className="text-sm text-slate-500">
                    {x.customer.name} · {money(x.confirmed_price)}
                  </div>
                </div>
                <span className="rounded-full bg-white px-2.5 py-1 text-xs font-medium text-slate-600">
                  {x.status_label}
                </span>
              </div>
            ))
          ) : (
            <Empty />
          )}
        </div>
      </Panel>
    </div>
  );
}
function Panel({ title, children }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="mb-4 font-bold text-slate-900">{title}</h2>
      {children}
    </div>
  );
}
function Empty() {
  return (
    <div className="py-6 text-center text-sm text-slate-500">
      No records found.
    </div>
  );
}
function SalesTable({ tab, rows, onEdit }) {
  if (!rows.length) return <Empty />;
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[760px] text-left text-sm">
        <thead className="bg-slate-50 text-xs uppercase text-slate-500">
          <tr>
            {tab === "customers" ? (
              <>
                <th className="px-5 py-3">Customer</th>
                <th>Phone</th>
                <th>Status</th>
              </>
            ) : tab === "enquiries" ? (
              <>
                <th className="px-5 py-3">Enquiry</th>
                <th>Customer</th>
                <th>Product</th>
                <th>Status</th>
              </>
            ) : tab === "quotations" ? (
              <>
                <th className="px-5 py-3">Quotation</th>
                <th>Customer</th>
                <th>Value</th>
                <th>Status</th>
              </>
            ) : (
              <>
                <th className="px-5 py-3">Order</th>
                <th>Customer</th>
                <th>Value</th>
                <th>Delivery</th>
                <th>Status</th>
              </>
            )}
            <th></th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {rows.map((x) => (
            <tr key={x.id} className="hover:bg-slate-50">
              {tab === "customers" ? (
                <>
                  <td className="px-5 py-4 font-semibold">
                    {x.name}
                    <div className="text-xs font-normal text-slate-500">
                      {x.email || "No email"}
                    </div>
                  </td>
                  <td>{x.phone}</td>
                  <td>
                    <Badge value={x.status_label} />
                  </td>
                </>
              ) : tab === "enquiries" ? (
                <>
                  <td className="px-5 py-4 font-semibold">{x.enquiry_no}</td>
                  <td>{x.customer.name}</td>
                  <td>
                    {x.product_type}
                    <div className="text-xs text-slate-500">
                      Qty {x.quantity}
                    </div>
                  </td>
                  <td>
                    <Badge value={x.status_label} />
                  </td>
                </>
              ) : tab === "quotations" ? (
                <>
                  <td className="px-5 py-4 font-semibold">{x.quotation_no}</td>
                  <td>{x.customer.name}</td>
                  <td>{money(x.quoted_price)}</td>
                  <td>
                    <Badge value={x.status_label} />
                  </td>
                </>
              ) : (
                <>
                  <td className="px-5 py-4 font-semibold">{x.order_no}</td>
                  <td>{x.customer.name}</td>
                  <td>{money(x.confirmed_price)}</td>
                  <td>{x.delivery_date || "—"}</td>
                  <td>
                    <Badge value={x.status_label} />
                  </td>
                </>
              )}
              <td className="px-5 py-4 text-right">
                {
                  <button
                    onClick={() => onEdit(x)}
                    className="font-semibold text-blue-600"
                  >
                    Edit
                  </button>
                }
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
function Badge({ value }) {
  return (
    <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700">
      {value}
    </span>
  );
}

function SalesForm({ type, initial = {}, customers, onClose, onSaved }) {
  const defaults = {
    customer: {
      name: "",
      phone: "",
      alternate_phone: "",
      email: "",
      address: "",
      status: "active",
      notes: "",
    },
    enquiry: {
      customer: "",
      channel: "phone",
      product_type: "",
      quantity: "1",
      design_reference: "",
      deadline: "",
      budget_range: "",
      expected_delivery_date: "",
      status: "new",
      requirement: "",
      response_time_note: "",
    },
    quotation: {
      customer: "",
      enquiry: "",
      order_request: "",
      item_description: "",
      quantity: "1",
      material_cost: "0",
      labour_cost: "0",
      machine_cost: "0",
      finishing_cost: "0",
      packaging_cost: "0",
      delivery_cost: "0",
      quoted_price: "0",
      delivery_timeline: "",
      advance_required: "0",
      valid_until: "",
      status: "draft",
      notes: "",
    },
    order: {
      customer: "",
      quotation: "",
      item_description: "",
      quantity: "1",
      confirmed_price: "0",
      design_reference: "",
      delivery_date: "",
      deadline: "",
      responsible_staff: "",
      advance_required: "0",
      status: "confirmed",
      notes: "",
    },
  };
  const [f, setF] = useState({
    ...defaults[type],
    ...(initial && type === "customer" ? initial : {}),
  });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const set = (k, v) => setF((x) => ({ ...x, [k]: v }));
  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setErr("");
    try {
      const base = `/sales/${type === "customer" ? "customers" : type === "enquiry" ? "enquiries" : type === "quotation" ? "quotations" : "orders"}`;
      await api.post(
        initial?.id ? `${base}/${initial.id}/update/` : `${base}/create/`,
        f,
      );
      onSaved();
    } catch (e) {
      setErr(
        e.response?.data?.detail ||
          Object.values(e.response?.data?.errors || {})?.[0]?.[0]?.message ||
          "Unable to save record.",
      );
    } finally {
      setBusy(false);
    }
  };
  return (
    <Modal
      title={`${initial?.id ? "Edit" : "Add"} ${type[0].toUpperCase() + type.slice(1)}`}
      onClose={onClose}
    >
      <form onSubmit={submit} className="grid gap-4 md:grid-cols-2">
        {type === "customer" ? (
          <>
            <Field
              label="Name"
              value={f.name}
              set={(v) => set("name", v)}
              required
            />
            <Field
              label="Phone"
              value={f.phone}
              set={(v) => set("phone", v)}
              required
            />
            <Field
              label="Alternate Phone"
              value={f.alternate_phone}
              set={(v) => set("alternate_phone", v)}
            />
            <Field label="Email" value={f.email} set={(v) => set("email", v)} />
            <Field
              label="Status"
              value={f.status}
              set={(v) => set("status", v)}
              select
              options={["active", "inactive"]}
            />
            <Field
              label="Address"
              value={f.address}
              set={(v) => set("address", v)}
              area
            />
            <Field
              label="Notes"
              value={f.notes}
              set={(v) => set("notes", v)}
              area
            />
          </>
        ) : type === "enquiry" ? (
          <>
            <Select
              label="Customer"
              value={f.customer}
              set={(v) => set("customer", v)}
              options={customers.map((x) => [x.id, x.name])}
            />
            <Select
              label="Channel"
              value={f.channel}
              set={(v) => set("channel", v)}
              options={[
                "phone",
                "whatsapp",
                "instagram",
                "facebook",
                "walk_in",
                "referral",
                "other",
              ].map((x) => [x, x.replace("_", " ")])}
            />
            <Field
              label="Product / Requirement"
              value={f.product_type}
              set={(v) => set("product_type", v)}
              required
            />
            <Field
              label="Quantity"
              value={f.quantity}
              set={(v) => set("quantity", v)}
              number
            />
            <Field
              label="Deadline"
              value={f.deadline}
              set={(v) => set("deadline", v)}
              date
            />
            <Field
              label="Expected Delivery"
              value={f.expected_delivery_date}
              set={(v) => set("expected_delivery_date", v)}
              date
            />
            <Field
              label="Budget Range"
              value={f.budget_range}
              set={(v) => set("budget_range", v)}
            />
            <Field
              label="Requirement"
              value={f.requirement}
              set={(v) => set("requirement", v)}
              area
            />
            <Field
              label="Design Reference"
              value={f.design_reference}
              set={(v) => set("design_reference", v)}
            />
          </>
        ) : type === "quotation" ? (
          <>
            <Select
              label="Customer"
              value={f.customer}
              set={(v) => set("customer", v)}
              options={customers.map((x) => [x.id, x.name])}
            />
            <Field
              label="Item Description"
              value={f.item_description}
              set={(v) => set("item_description", v)}
              required
            />
            <Field
              label="Quantity"
              value={f.quantity}
              set={(v) => set("quantity", v)}
              number
            />
            {[
              "material_cost",
              "labour_cost",
              "machine_cost",
              "finishing_cost",
              "packaging_cost",
              "delivery_cost",
              "quoted_price",
              "advance_required",
            ].map((k) => (
              <Field
                key={k}
                label={k.replaceAll("_", " ")}
                value={f[k]}
                set={(v) => set(k, v)}
                number
              />
            ))}
            <Field
              label="Delivery Timeline"
              value={f.delivery_timeline}
              set={(v) => set("delivery_timeline", v)}
            />
            <Field
              label="Valid Until"
              value={f.valid_until}
              set={(v) => set("valid_until", v)}
              date
            />
            <Select
              label="Status"
              value={f.status}
              set={(v) => set("status", v)}
              options={[
                "draft",
                "sent",
                "approved",
                "rejected",
                "expired",
                "converted",
              ].map((x) => [x, x.replace("_", " ")])}
            />
            <Field
              label="Notes"
              value={f.notes}
              set={(v) => set("notes", v)}
              area
            />
          </>
        ) : (
          <>
            <Select
              label="Customer"
              value={f.customer}
              set={(v) => set("customer", v)}
              options={customers.map((x) => [x.id, x.name])}
            />
            <Field
              label="Item Description"
              value={f.item_description}
              set={(v) => set("item_description", v)}
              required
            />
            <Field
              label="Quantity"
              value={f.quantity}
              set={(v) => set("quantity", v)}
              number
            />
            <Field
              label="Confirmed Price"
              value={f.confirmed_price}
              set={(v) => set("confirmed_price", v)}
              number
            />
            <Field
              label="Advance Required"
              value={f.advance_required}
              set={(v) => set("advance_required", v)}
              number
            />
            <Field
              label="Deadline"
              value={f.deadline}
              set={(v) => set("deadline", v)}
              date
            />
            <Field
              label="Delivery Date"
              value={f.delivery_date}
              set={(v) => set("delivery_date", v)}
              date
            />
            <Select
              label="Status"
              value={f.status}
              set={(v) => set("status", v)}
              options={[
                "confirmed",
                "design_pending",
                "production_pending",
                "in_production",
                "ready",
                "delivered",
                "cancelled",
              ].map((x) => [x, x.replaceAll("_", " ")])}
            />
            <Field
              label="Design Reference"
              value={f.design_reference}
              set={(v) => set("design_reference", v)}
            />
            <Field
              label="Notes"
              value={f.notes}
              set={(v) => set("notes", v)}
              area
            />
          </>
        )}
        {err && (
          <div className="md:col-span-2 rounded-xl bg-red-50 p-3 text-sm text-red-700">
            {err}
          </div>
        )}
        <div className="flex justify-end gap-3 md:col-span-2">
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
            {busy ? "Saving..." : "Save"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
function Field({
  label,
  value,
  set,
  required = false,
  number = false,
  date = false,
  area = false,
}) {
  return (
    <label className={area ? "md:col-span-2" : ""}>
      <span className="mb-1 block text-sm font-medium capitalize text-slate-700">
        {label}
      </span>
      {area ? (
        <textarea
          rows="3"
          value={value || ""}
          onChange={(e) => set(e.target.value)}
          className="w-full rounded-xl border border-slate-300 px-3 py-2.5"
        />
      ) : (
        <input
          required={required}
          type={number ? "number" : date ? "date" : "text"}
          step={number ? "0.01" : undefined}
          value={value || ""}
          onChange={(e) => set(e.target.value)}
          className="w-full rounded-xl border border-slate-300 px-3 py-2.5"
        />
      )}
    </label>
  );
}
function Select({ label, value, set, options }) {
  return (
    <label>
      <span className="mb-1 block text-sm font-medium capitalize text-slate-700">
        {label}
      </span>
      <select
        required={!value && label === "Customer"}
        value={value || ""}
        onChange={(e) => set(e.target.value)}
        className="w-full rounded-xl border border-slate-300 px-3 py-2.5"
      >
        <option value="">Select {label}</option>
        {options.map(([v, l]) => (
          <option key={v} value={v}>
            {l}
          </option>
        ))}
      </select>
    </label>
  );
}
function Modal({ title, onClose, children }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="max-h-[92vh] w-full max-w-4xl overflow-y-auto rounded-2xl bg-white p-5 shadow-xl">
        <div className="mb-5 flex items-center justify-between">
          <h2 className="text-xl font-bold text-slate-900">{title}</h2>
          <button
            onClick={onClose}
            className="rounded-lg px-3 py-2 text-slate-500 hover:bg-slate-100"
          >
            ✕
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
