import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../services/api";

const statusLabel = { active: "Active", inactive: "Inactive" };

export default function ProductManagement() {
  const [data, setData] = useState({
    products: [],
    stats: {},
    categories: [],
    can_manage: false,
  });
  const [filters, setFilters] = useState({
    q: "",
    category: "",
    status: "",
    low_stock: "",
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [form, setForm] = useState(null);
  const [categoryForm, setCategoryForm] = useState(false);
  async function load() {
    setLoading(true);
    setError("");
    try {
      setData((await api.get("/products/", { params: filters })).data);
    } catch (e) {
      setError(e.response?.data?.detail || "Unable to load products.");
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    load();
  }, [filters.q, filters.category, filters.status, filters.low_stock]);
  const s = data.stats || {};
  return (
    <div className="space-y-6">
      <div className="relative overflow-hidden flex flex-col justify-between gap-4 rounded-[24px] bg-gradient-to-br from-blue-700 via-indigo-700 to-violet-800 p-5 text-white shadow-xl shadow-indigo-900/15 sm:flex-row sm:items-center sm:p-6">
        <div>
          <h1 className="text-2xl font-bold text-white">
            Products & Inventory
          </h1>
          <p className="text-sm text-blue-100">
            Manage internal products, materials, categories and stock.
          </p>
        </div>
        {data.can_manage && (
          <div className="flex gap-2">
            <button
              onClick={() => setCategoryForm(true)}
              className="rounded-xl border border-white/40 bg-white/15 px-4 py-2.5 text-sm font-semibold text-white backdrop-blur-sm hover:bg-white/25"
            >
              + Category
            </button>
            <button
              onClick={() => setForm({})}
              className="rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white"
            >
              + Add Product
            </button>
          </div>
        )}
      </div>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="Total Products" value={s.total_products ?? 0} />
        <Stat label="Active" value={s.active_products ?? 0} />
        <Stat label="Categories" value={s.categories ?? 0} />
        <Stat label="Low Stock" value={s.low_stock ?? 0} />
      </div>
      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="grid gap-3 md:grid-cols-4">
          <input
            value={filters.q}
            onChange={(e) => setFilters({ ...filters, q: e.target.value })}
            placeholder="Search name, SKU or category"
            className="rounded-xl border border-slate-300 px-3 py-2.5 text-sm md:col-span-2"
          />
          <select
            value={filters.category}
            onChange={(e) =>
              setFilters({ ...filters, category: e.target.value })
            }
            className="rounded-xl border border-slate-300 px-3 py-2.5 text-sm"
          >
            <option value="">All Categories</option>
            {data.categories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
          <select
            value={filters.status}
            onChange={(e) => setFilters({ ...filters, status: e.target.value })}
            className="rounded-xl border border-slate-300 px-3 py-2.5 text-sm"
          >
            <option value="">All Status</option>
            {Object.entries(statusLabel).map(([v, l]) => (
              <option key={v} value={v}>
                {l}
              </option>
            ))}
          </select>
        </div>
        <label className="mt-3 flex items-center gap-2 text-sm text-slate-600">
          <input
            type="checkbox"
            checked={filters.low_stock === "1"}
            onChange={(e) =>
              setFilters({ ...filters, low_stock: e.target.checked ? "1" : "" })
            }
          />{" "}
          Show low-stock items only
        </label>
      </div>
      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}
      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        {loading ? (
          <div className="p-8 text-center text-sm text-slate-500">
            Loading products...
          </div>
        ) : data.products.length === 0 ? (
          <div className="p-8 text-center text-sm text-slate-500">
            No products found.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[850px] text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase text-slate-500">
                <tr>
                  <th className="px-5 py-3">Product</th>
                  <th className="px-5 py-3">Category</th>
                  <th className="px-5 py-3">Cost</th>
                  <th className="px-5 py-3">Stock</th>
                  <th className="px-5 py-3">Status</th>
                  <th className="px-5 py-3"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data.products.map((p) => (
                  <tr key={p.id} className="hover:bg-slate-50">
                    <td className="px-5 py-4">
                      <Link
                        to={`/products/${p.id}`}
                        className="font-semibold text-slate-900 hover:underline"
                      >
                        {p.name}
                      </Link>
                      <div className="text-xs text-slate-500">{p.sku}</div>
                    </td>
                    <td className="px-5 py-4 text-slate-600">
                      {p.category?.name || "—"}
                    </td>
                    <td className="px-5 py-4">
                      ₹{Number(p.cost_price).toFixed(2)} / {p.unit}
                    </td>
                    <td className="px-5 py-4">
                      <span
                        className={
                          p.is_low_stock
                            ? "font-semibold text-red-600"
                            : "text-slate-700"
                        }
                      >
                        {p.stock_quantity}
                      </span>{" "}
                      <span className="text-xs text-slate-400">{p.unit}</span>
                    </td>
                    <td className="px-5 py-4">
                      <span
                        className={`rounded-full px-2.5 py-1 text-xs font-medium ${p.status === "active" ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-600"}`}
                      >
                        {p.status_label}
                      </span>
                    </td>
                    <td className="px-5 py-4 text-right">
                      <Link
                        to={`/products/${p.id}`}
                        className="font-medium text-slate-700"
                      >
                        View
                      </Link>
                      {data.can_manage && (
                        <button
                          onClick={() => setForm(p)}
                          className="ml-4 font-medium text-blue-600"
                        >
                          Edit
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      {form !== null && (
        <ProductForm
          initial={form}
          categories={data.categories}
          onClose={() => setForm(null)}
          onSaved={() => {
            setForm(null);
            load();
          }}
        />
      )}
      {categoryForm && (
        <CategoryForm
          onClose={() => setCategoryForm(false)}
          onSaved={() => {
            setCategoryForm(false);
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
function ProductForm({ initial, categories, onClose, onSaved }) {
  const [f, setF] = useState({
    name: initial.name || "",
    sku: initial.sku || "",
    category: initial.category?.id || "",
    description: initial.description || "",
    unit: initial.unit || "Piece",
    cost_price: initial.cost_price || "",
    stock_quantity: initial.stock_quantity || "",
    low_stock_threshold: initial.low_stock_threshold || "",
    status: initial.status || "active",
  });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const set = (k, v) => setF((x) => ({ ...x, [k]: v }));
  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setErr("");
    try {
      await api.post(
        initial.id ? `/products/${initial.id}/update/` : "/products/create/",
        f,
      );
      onSaved();
    } catch (e) {
      setErr(e.response?.data?.detail || "Unable to save product.");
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal
      title={initial.id ? "Edit Product" : "Add Product"}
      onClose={onClose}
    >
      <form onSubmit={submit} className="grid gap-4 md:grid-cols-2">
        {[
          ["name", "Product / Material Name"],
          ["sku", "SKU / Code"],
          ["unit", "Unit"],
          ["cost_price", "Cost Price"],
          ["stock_quantity", "Current / Opening Stock"],
          ["low_stock_threshold", "Low Stock Threshold"],
        ].map(([k, l]) => (
          <label key={k}>
            <span className="mb-1 block text-sm font-medium text-slate-700">
              {l}
            </span>
            <input
              required={["name", "sku"].includes(k)}
              type={
                k.includes("price") || k.includes("stock") ? "number" : "text"
              }
              step="0.01"
              value={f[k]}
              onChange={(e) => set(k, e.target.value)}
              className="w-full rounded-xl border border-slate-300 px-3 py-2.5"
              disabled={k === "stock_quantity" && !!initial.id}
            />
          </label>
        ))}
        <label>
          <span className="mb-1 block text-sm font-medium">Category</span>
          <select
            required
            value={f.category}
            onChange={(e) => set("category", e.target.value)}
            className="w-full rounded-xl border border-slate-300 px-3 py-2.5"
          >
            <option value="">Select category</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span className="mb-1 block text-sm font-medium">Status</span>
          <select
            value={f.status}
            onChange={(e) => set("status", e.target.value)}
            className="w-full rounded-xl border border-slate-300 px-3 py-2.5"
          >
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </select>
        </label>
        <label className="md:col-span-2">
          <span className="mb-1 block text-sm font-medium">Description</span>
          <textarea
            rows="3"
            value={f.description}
            onChange={(e) => set("description", e.target.value)}
            className="w-full rounded-xl border border-slate-300 px-3 py-2.5"
          />
        </label>
        {err && (
          <div className="md:col-span-2 rounded-xl bg-red-50 p-3 text-sm text-red-700">
            {err}
          </div>
        )}
        <Actions
          busy={busy}
          onClose={onClose}
          label={initial.id ? "Save Changes" : "Create Product"}
        />
      </form>
    </Modal>
  );
}
function CategoryForm({ onClose, onSaved }) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [err, setErr] = useState("");
  async function submit(e) {
    e.preventDefault();
    try {
      await api.post("/products/categories/create/", { name, description });
      onSaved();
    } catch (e) {
      setErr(e.response?.data?.detail || "Unable to create category.");
    }
  }
  return (
    <Modal title="Add Product Category" onClose={onClose}>
      <form onSubmit={submit} className="space-y-4">
        <label className="block">
          <span className="mb-1 block text-sm font-medium">Category Name</span>
          <input
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full rounded-xl border border-slate-300 px-3 py-2.5"
          />
        </label>
        <label className="block">
          <span className="mb-1 block text-sm font-medium">Description</span>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="w-full rounded-xl border border-slate-300 px-3 py-2.5"
          />
        </label>
        {err && (
          <div className="rounded-xl bg-red-50 p-3 text-sm text-red-700">
            {err}
          </div>
        )}
        <Actions busy={false} onClose={onClose} label="Create Category" />
      </form>
    </Modal>
  );
}
function Modal({ title, onClose, children }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="max-h-[92vh] w-full max-w-3xl overflow-y-auto rounded-2xl bg-white p-5 shadow-xl">
        <div className="mb-5 flex items-center justify-between">
          <h2 className="text-xl font-bold">{title}</h2>
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
function Actions({ busy, onClose, label }) {
  return (
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
        className="rounded-xl bg-slate-900 px-5 py-2.5 font-semibold text-white disabled:opacity-50"
      >
        {busy ? "Saving..." : label}
      </button>
    </div>
  );
}
