import { useEffect, useState } from "react";
import {
  createExpense,
  createExpenseCategory,
  createSupplierPayment,
  getExpenses,
  getFinanceDashboard,
  getReceivables,
  getReconciliation,
  getSupplierPayments,
} from "../services/api";
const money = (v) =>
  `₹ ${Number(v || 0).toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;
const input =
  "w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100";
const Field = ({ label, children }) => (
  <label className="block">
    <span className="mb-1 block text-xs font-semibold text-slate-500">
      {label}
    </span>
    {children}
  </label>
);
export default function FinanceManagement() {
  const [tab, setTab] = useState("overview"),
    [stats, setStats] = useState({}),
    [tx, setTx] = useState([]),
    [expenses, setExpenses] = useState({ expenses: [], categories: [] }),
    [receivables, setReceivables] = useState({ rows: [] }),
    [supplier, setSupplier] = useState({ payments: [], due: [] }),
    [recon, setRecon] = useState({ by_method: [], transactions: [] }),
    [modal, setModal] = useState(null),
    [form, setForm] = useState({}),
    [error, setError] = useState("");
  const load = async () => {
    try {
      setError("");
      const [d, e, r, s, c] = await Promise.all([
        getFinanceDashboard(),
        getExpenses(),
        getReceivables(),
        getSupplierPayments(),
        getReconciliation(),
      ]);
      setStats(d.stats);
      setTx(d.transactions);
      setExpenses(e);
      setReceivables(r);
      setSupplier(s);
      setRecon(c);
    } catch (e) {
      setError(e.response?.data?.detail || "Unable to load finance data.");
    }
  };
  useEffect(() => {
    load();
  }, []);
  const submitExpense = async (e) => {
    e.preventDefault();
    try {
      await createExpense(form);
      setModal(null);
      setForm({});
      await load();
    } catch (e) {
      setError(e.response?.data?.detail || "Could not record expense.");
    }
  };
  const submitCategory = async (e) => {
    e.preventDefault();
    try {
      await createExpenseCategory(form);
      setModal(null);
      setForm({});
      await load();
    } catch (e) {
      setError(e.response?.data?.detail || "Could not create category.");
    }
  };
  const submitSupplierPayment = async (e) => {
    e.preventDefault();
    try {
      await createSupplierPayment(form);
      setModal(null);
      setForm({});
      await load();
    } catch (e) {
      setError(
        e.response?.data?.detail || "Could not record supplier payment.",
      );
    }
  };
  return (
    <div className="space-y-5">
      <div className="relative overflow-hidden rounded-[28px] bg-gradient-to-br from-blue-700 via-indigo-700 to-violet-800 p-5 text-white shadow-xl shadow-indigo-900/15 sm:p-6">
        <div className="relative flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-blue-100">Finance Control Center</p>
            <h1 className="mt-1 text-2xl font-bold tracking-tight sm:text-3xl">Finance & Accounts</h1>
            <p className="mt-1 text-sm text-indigo-100">Income, expenses, receivables, supplier dues and reconciliation.</p>
          </div>
          <div className="rounded-2xl border border-white/20 bg-white/10 px-4 py-3 text-sm backdrop-blur-sm">
            <div className="text-blue-100">Financial workspace</div>
            <div className="font-semibold">Cash flow & controls</div>
          </div>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <button
            onClick={() => { setForm({ expense_date: new Date().toISOString().slice(0, 10), status: "paid", payment_method: "cash" }); setModal("expense"); }}
            className="rounded-xl bg-white px-4 py-2.5 text-sm font-bold text-indigo-700 shadow-sm transition hover:bg-indigo-50"
          >
            + Expense
          </button>
          <button
            onClick={() => { setForm({ name: "", is_active: true }); setModal("category"); }}
            className="rounded-xl border border-white/30 bg-white/10 px-4 py-2.5 text-sm font-semibold text-white backdrop-blur-sm transition hover:bg-white/20"
          >
            + Category
          </button>
        </div>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        {[
          ["Income", stats.income],
          ["Expenses", stats.expenses],
          ["Balance", stats.balance],
          ["Receivable", stats.receivable],
          ["Supplier Due", stats.supplier_due],
        ].map(([a, b]) => (
          <div
            key={a}
            className="relative overflow-hidden rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
          >
            <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-blue-500 via-indigo-500 to-violet-500" />
            <div className="text-xs font-semibold uppercase text-slate-400">
              {a}
            </div>
            <div className="mt-2 text-xl font-bold">{money(b)}</div>
          </div>
        ))}
      </div>
      <div className="rounded-2xl border border-slate-200 bg-white p-4">
        <div className="flex flex-wrap gap-2 border-b border-slate-100 pb-3">
          {[
            ["overview", "Overview"],
            ["expenses", "Expenses"],
            ["receivables", "Receivables"],
            ["supplier", "Supplier Payments"],
            ["reconciliation", "Reconciliation"],
          ].map(([k, l]) => (
            <button
              key={k}
              onClick={() => setTab(k)}
              className={`rounded-lg px-3 py-2 text-sm font-semibold ${tab === k ? "bg-slate-900 text-white" : "text-slate-600"}`}
            >
              {l}
            </button>
          ))}
          {tab === "supplier" && (
            <button
              onClick={() => setModal("supplierPayment")}
              className="ml-auto rounded-lg border px-3 py-2 text-sm font-semibold"
            >
              + Supplier Payment
            </button>
          )}
        </div>
        {error && (
          <div className="mt-3 rounded-xl bg-red-50 p-3 text-sm text-red-700">
            {error}
          </div>
        )}
        {tab === "overview" && (
          <div className="py-4 overflow-x-auto">
            <h3 className="mb-3 font-semibold">Recent Transactions</h3>
            <Table
              headers={[
                "No",
                "Date",
                "Type",
                "Description",
                "Method",
                "Amount",
              ]}
              rows={tx.map((x) => [
                x.transaction_no,
                x.date,
                x.type_label,
                x.description || "-",
                x.payment_method,
                money(x.amount),
              ])}
            />
          </div>
        )}
        {tab === "expenses" && (
          <div className="py-4 overflow-x-auto">
            <Table
              headers={[
                "Expense",
                "Date",
                "Category",
                "Description",
                "Method",
                "Status",
                "Amount",
              ]}
              rows={expenses.expenses.map((x) => [
                x.expense_no,
                x.expense_date,
                x.category.name,
                x.description || "-",
                x.payment_method,
                x.status_label,
                money(x.amount),
              ])}
            />
          </div>
        )}
        {tab === "receivables" && (
          <div className="py-4 overflow-x-auto">
            <Table
              headers={["Order", "Customer", "Total", "Received", "Balance"]}
              rows={receivables.rows.map((x) => [
                x.order.order_no,
                x.order.customer,
                money(x.order.total),
                money(x.received),
                money(x.balance),
              ])}
            />
          </div>
        )}
        {tab === "supplier" && (
          <div className="py-4 space-y-5 overflow-x-auto">
            <h3 className="font-semibold">Outstanding Supplier Dues</h3>
            <Table
              headers={["PO", "Supplier", "Total", "Paid", "Balance"]}
              rows={supplier.due.map((x) => [
                x.order.po_no,
                x.order.supplier,
                money(x.order.total),
                money(x.paid),
                money(x.balance),
              ])}
            />
            <h3 className="font-semibold">Recent Payments</h3>
            <Table
              headers={[
                "Payment",
                "PO",
                "Supplier",
                "Date",
                "Method",
                "Status",
                "Amount",
              ]}
              rows={supplier.payments.map((x) => [
                x.payment_no,
                x.purchase_order.po_no,
                x.purchase_order.supplier,
                x.payment_date,
                x.payment_method,
                x.status_label,
                money(x.amount),
              ])}
            />
          </div>
        )}
        {tab === "reconciliation" && (
          <div className="py-4 space-y-5 overflow-x-auto">
            <Table
              headers={["Method", "Income", "Expense", "Net"]}
              rows={recon.by_method.map((x) => [
                x.payment_method,
                money(x.income),
                money(x.expense),
                money(x.net),
              ])}
            />
            <Table
              headers={["No", "Date", "Type", "Method", "Reference", "Amount"]}
              rows={recon.transactions.map((x) => [
                x.transaction_no,
                x.date,
                x.type_label,
                x.payment_method,
                x.reference || "-",
                money(x.amount),
              ])}
            />
          </div>
        )}
      </div>
      {modal === "expense" && (
        <Modal title="Record Expense" close={() => setModal(null)}>
          <form onSubmit={submitExpense} className="grid gap-4 sm:grid-cols-2">
            <Field label="Category">
              <select
                required
                className={input}
                value={form.category || ""}
                onChange={(e) => setForm({ ...form, category: e.target.value })}
              >
                <option value="">Select category</option>
                {expenses.categories.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Amount">
              <input
                required
                type="number"
                min="0.01"
                step="0.01"
                className={input}
                value={form.amount || ""}
                onChange={(e) => setForm({ ...form, amount: e.target.value })}
              />
            </Field>
            <Field label="Date">
              <input
                required
                type="date"
                className={input}
                value={form.expense_date || ""}
                onChange={(e) =>
                  setForm({ ...form, expense_date: e.target.value })
                }
              />
            </Field>
            <Field label="Payment method">
              <select
                className={input}
                value={form.payment_method || "cash"}
                onChange={(e) =>
                  setForm({ ...form, payment_method: e.target.value })
                }
              >
                {["cash", "upi", "bank", "card", "other"].map((x) => (
                  <option key={x}>{x}</option>
                ))}
              </select>
            </Field>
            <Field label="Reference">
              <input
                className={input}
                value={form.reference || ""}
                onChange={(e) =>
                  setForm({ ...form, reference: e.target.value })
                }
              />
            </Field>
            <Field label="Status">
              <select
                className={input}
                value={form.status || "paid"}
                onChange={(e) => setForm({ ...form, status: e.target.value })}
              >
                <option value="paid">Paid</option>
                <option value="draft">Draft</option>
                <option value="cancelled">Cancelled</option>
              </select>
            </Field>
            <div className="sm:col-span-2">
              <Field label="Description">
                <textarea
                  className={input}
                  rows="3"
                  value={form.description || ""}
                  onChange={(e) =>
                    setForm({ ...form, description: e.target.value })
                  }
                />
              </Field>
            </div>
            <div className="sm:col-span-2 text-right">
              <button className="rounded-xl bg-slate-900 px-4 py-2 font-semibold text-white">
                Save Expense
              </button>
            </div>
          </form>
        </Modal>
      )}
      {modal === "category" && (
        <Modal title="Expense Category" close={() => setModal(null)}>
          <form onSubmit={submitCategory} className="space-y-4">
            <Field label="Category name">
              <input
                required
                className={input}
                value={form.name || ""}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
              />
            </Field>
            <label className="flex gap-2 text-sm">
              <input
                type="checkbox"
                checked={form.is_active !== false}
                onChange={(e) =>
                  setForm({ ...form, is_active: e.target.checked })
                }
              />{" "}
              Active
            </label>
            <button className="rounded-xl bg-slate-900 px-4 py-2 font-semibold text-white">
              Create
            </button>
          </form>
        </Modal>
      )}
      {modal === "supplierPayment" && (
        <Modal title="Supplier Payment" close={() => setModal(null)}>
          <SupplierPaymentForm
            supplier={supplier}
            form={form}
            setForm={setForm}
            submit={submitSupplierPayment}
          />
        </Modal>
      )}
    </div>
  );
}
function SupplierPaymentForm({ supplier, form, setForm, submit }) {
  return (
    <form onSubmit={submit} className="space-y-4">
      <Field label="Purchase order">
        <select
          required
          className={input}
          value={form.purchase_order || ""}
          onChange={(e) => setForm({ ...form, purchase_order: e.target.value })}
        >
          <option value="">Select PO</option>
          {supplier.due.map((x) => (
            <option key={x.order.id} value={x.order.id}>
              {x.order.po_no} · {x.order.supplier} · Due {money(x.balance)}
            </option>
          ))}
        </select>
      </Field>
      <Field label="Amount">
        <input
          required
          type="number"
          min="0.01"
          step="0.01"
          className={input}
          value={form.amount || ""}
          onChange={(e) => setForm({ ...form, amount: e.target.value })}
        />
      </Field>
      <Field label="Payment date">
        <input
          required
          type="date"
          className={input}
          value={form.payment_date || new Date().toISOString().slice(0, 10)}
          onChange={(e) => setForm({ ...form, payment_date: e.target.value })}
        />
      </Field>
      <Field label="Method">
        <select
          className={input}
          value={form.payment_method || "cash"}
          onChange={(e) => setForm({ ...form, payment_method: e.target.value })}
        >
          {["cash", "upi", "bank", "card", "other"].map((x) => (
            <option key={x}>{x}</option>
          ))}
        </select>
      </Field>
      <Field label="Reference">
        <input
          className={input}
          value={form.reference || ""}
          onChange={(e) => setForm({ ...form, reference: e.target.value })}
        />
      </Field>
      <button className="rounded-xl bg-slate-900 px-4 py-2 font-semibold text-white">
        Record Payment
      </button>
    </form>
  );
}
function Table({ headers, rows }) {
  return (
    <table className="w-full min-w-[700px] text-left text-sm">
      <thead className="text-xs uppercase text-slate-400">
        <tr>
          {headers.map((h) => (
            <th className="p-3" key={h}>
              {h}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((r, i) => (
          <tr className="border-t border-slate-100" key={i}>
            {r.map((c, j) => (
              <td className="p-3" key={j}>
                {c}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
function Modal({ title, close, children }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4">
      <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-2xl bg-white p-5 shadow-2xl">
        <div className="mb-5 flex justify-between">
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
