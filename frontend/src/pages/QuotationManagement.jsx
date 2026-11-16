import { useEffect, useMemo, useState } from "react";
import api from "../services/api";
import { useAuth } from "../context/AuthContext";

const categories = [
  ["material", "Material"], ["labour", "Labour"], ["machine", "Machine"],
  ["finishing", "Finishing"], ["packing", "Packing"], ["delivery_installation", "Delivery / Installation"],
];
const money = (value) => `₹${Number(value || 0).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const blankLine = () => ({ category: "material", description: "", dimensions: "", quantity: "1", unit: "Nos", unit_price: "0" });
const blankQuote = () => ({
  customer: "", item_description: "", dimensions: "", quantity: "1",
  advance_required: "0", delivery_timeline: "", valid_until: "", terms: "", notes: "",
  discount_type: "percentage", discount_value: "0", line_items: [blankLine()],
});

export default function QuotationManagement() {
  const { user } = useAuth();
  const isFounder = user?.is_superuser || user?.role === "super_admin";
  const [quotations, setQuotations] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [products, setProducts] = useState([]);
  const [config, setConfig] = useState(null);
  const [canManage, setCanManage] = useState(false);
  const [canConfigure, setCanConfigure] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [editor, setEditor] = useState(null);
  const [configOpen, setConfigOpen] = useState(false);
  const [detail, setDetail] = useState(null);
  const [busyId, setBusyId] = useState(null);

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const [q, c, customersResponse, productsResponse] = await Promise.all([
        api.get("/sales/quotations/"),
        api.get("/sales/quotations/configuration/"),
        api.get("/sales/customers/"),
        api.get("/sales/quotations/products/"),
      ]);
      setQuotations(q.data.quotations || []);
      setCanManage(Boolean(q.data.can_manage));
      setConfig(c.data.configuration);
      setCanConfigure(Boolean(c.data.can_configure));
      setCustomers(customersResponse.data.customers || []);
      setProducts(productsResponse.data.products || []);
    } catch (e) {
      setError(e.response?.data?.detail || "Unable to load quotation workspace.");
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load(); }, []);

  const pendingCount = useMemo(() => quotations.filter((q) => q.status === "pending_approval").length, [quotations]);
  const openEditor = async (quotation) => {
    if (!quotation) {
      setEditor({ initial: null, form: blankQuote() });
      return;
    }
    try {
      const response = await api.get(`/sales/quotations/${quotation.id}/detail/`);
      const q = response.data.quotation;
      setEditor({ initial: q, form: {
        customer: String(q.customer.id), product: q.product?.id ? String(q.product.id) : "", item_description: q.item_description, dimensions: q.dimensions || "",
        quantity: q.quantity, discount_type: q.discount_type || "percentage", discount_value: q.discount_value ?? q.discount_percent ?? "0", advance_required: q.advance_required,
        delivery_timeline: q.delivery_timeline || "", valid_until: q.valid_until || "", terms: q.terms || "",
        notes: q.notes || "", line_items: q.line_items.map((x) => ({
          category: x.category, description: x.description, dimensions: x.dimensions || "",
          quantity: x.quantity, unit: x.unit || "", unit_price: x.unit_price,
        })),
      }});
    } catch (e) {
      setError(e.response?.data?.detail || "Unable to open quotation.");
    }
  };
  const refreshDetail = async (id) => {
    const response = await api.get(`/sales/quotations/${id}/detail/`);
    setDetail(response.data.quotation);
  };
  const runAction = async (id, action, notes = "") => {
    setBusyId(id);
    setError("");
    try {
      if (action === "submit") await api.post(`/sales/quotations/${id}/submit/`, {});
      else await api.post(`/sales/quotations/${id}/approval/`, { action, notes });
      await load();
      if (detail?.id === id) await refreshDetail(id);
    } catch (e) {
      setError(e.response?.data?.detail || "Unable to update quotation.");
    } finally {
      setBusyId(null);
    }
  };
  const downloadPdf = async (id) => {
    setBusyId(id);
    try {
      const response = await api.get(`/sales/quotations/${id}/pdf/`, { responseType: "blob" });
      const url = window.URL.createObjectURL(response.data);
      const link = document.createElement("a");
      link.href = url;
      link.download = `Quotation-${id}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      setError(e.response?.data?.detail || "Unable to generate quotation PDF.");
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="space-y-6">
      <header className="flex flex-col justify-between gap-4 rounded-3xl bg-gradient-to-br from-slate-900 via-blue-950 to-indigo-900 p-6 text-white shadow-xl sm:flex-row sm:items-center">
        <div>
          <p className="text-xs font-bold uppercase tracking-[.2em] text-blue-200">Sales · Phase 1</p>
          <h1 className="mt-1 text-2xl font-bold">Quotation Management</h1>
          <p className="mt-1 text-sm text-blue-100">Itemized pricing, discount approvals and customer-ready PDF quotations.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {canConfigure && <button onClick={() => setConfigOpen(true)} className="rounded-xl border border-white/30 px-4 py-2.5 text-sm font-semibold hover:bg-white/10">Quotation Settings</button>}
          {canManage && <button onClick={() => openEditor(null)} className="rounded-xl bg-white px-4 py-2.5 text-sm font-bold text-slate-900 hover:bg-blue-50">+ New Quotation</button>}
        </div>
      </header>

      {error && <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}
      <div className="grid gap-3 sm:grid-cols-3">
        <Stat label="Total Quotations" value={quotations.length} />
        <Stat label="Pending Approval" value={pendingCount} />
        <Stat label="Tax Configuration" value={config?.tax_rate == null ? "Not configured" : `${config.tax_rate}%`} />
      </div>
      {!config?.is_configured_for_sending && <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">Founder must configure the tax rate before any quotation can be sent. Draft quotations can still be prepared.</div>}

      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 p-4">
          <div><h2 className="font-bold text-slate-900">Quotation Register</h2><p className="text-xs text-slate-500">Drafts, approval queue and customer responses</p></div>
          <button onClick={load} className="rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-50">Refresh</button>
        </div>
        {loading ? <div className="p-10 text-center text-sm text-slate-500">Loading quotations...</div> : quotations.length === 0 ? <div className="p-10 text-center text-sm text-slate-500">No quotations found.</div> : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase text-slate-500"><tr><th className="px-5 py-3">Quotation</th><th>Customer</th><th>Total</th><th>Validity</th><th>Status</th><th className="px-5 py-3 text-right">Actions</th></tr></thead>
              <tbody className="divide-y divide-slate-100">
                {quotations.map((q) => <tr key={q.id} className="hover:bg-slate-50">
                  <td className="px-5 py-4 font-semibold text-slate-900">{q.quotation_no}<div className="text-xs font-normal text-slate-500">{q.item_description}</div></td>
                  <td>{q.customer.name}</td><td className="font-semibold">{money(q.quoted_price)}</td><td>{q.valid_until || "—"}</td>
                  <td><Status value={q.status_label || q.status} /></td>
                  <td className="px-5 py-4"><div className="flex justify-end gap-3">
                    <button onClick={() => refreshDetail(q.id).then(setDetail).catch(() => setError("Unable to load quotation details."))} className="font-semibold text-indigo-600">View</button>
                    {canManage && q.status === "draft" && <button onClick={() => openEditor(q)} className="font-semibold text-blue-600">Edit</button>}
                    {canManage && q.status === "draft" && <button disabled={busyId === q.id} onClick={() => runAction(q.id, "submit")} className="font-semibold text-emerald-700">Submit</button>}
                    {canConfigure && q.status === "pending_approval" && <button onClick={() => refreshDetail(q.id).then(setDetail)} className="font-semibold text-amber-700">Review</button>}
                    {["sent", "accepted", "approved"].includes(q.status) && <button disabled={busyId === q.id} onClick={() => downloadPdf(q.id)} className="font-semibold text-slate-700">PDF</button>}
                  </div></td>
                </tr>)}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {editor && <QuotationEditor
        initial={editor.initial} form={editor.form} customers={customers} products={products} config={config}
        onClose={() => setEditor(null)}
        onSave={async (payload) => {
          try {
            const response = editor.initial
              ? await api.post(`/sales/quotations/${editor.initial.id}/update-workflow/`, payload)
              : await api.post("/sales/quotations/create-workflow/", payload);
            setEditor(null);
            await load();
            setDetail(response.data.quotation);
          } catch (e) {
            throw new Error(e.response?.data?.detail || "Unable to save quotation.");
          }
        }}
      />}
      {configOpen && <ConfigurationEditor config={config} onClose={() => setConfigOpen(false)} onSaved={async () => { setConfigOpen(false); await load(); }} />}
      {detail && <QuotationDetail
        quotation={detail} canManage={canManage} canApprove={canConfigure}
        busy={busyId === detail.id} onClose={() => setDetail(null)}
        onAction={(action, notes) => runAction(detail.id, action, notes)}
        onPdf={() => downloadPdf(detail.id)}
      />}
    </div>
  );
}

function Stat({ label, value }) {
  return <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"><div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</div><div className="mt-2 text-xl font-bold text-slate-900">{value}</div></div>;
}
function Status({ value }) {
  const tone = String(value).toLowerCase().includes("pending") ? "bg-amber-100 text-amber-800" : ["sent", "accepted", "approved"].some(x => String(value).toLowerCase().includes(x)) ? "bg-emerald-100 text-emerald-800" : "bg-slate-100 text-slate-700";
  return <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${tone}`}>{value}</span>;
}

function QuotationEditor({ initial, form: initialForm, customers, products, config, onClose, onSave }) {
  const [form, setForm] = useState(initialForm);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const set = (key, value) => setForm((old) => ({ ...old, [key]: value }));
  const updateLine = (index, key, value) => set("line_items", form.line_items.map((line, i) => i === index ? { ...line, [key]: value } : line));
  const subtotal = form.line_items.reduce((sum, line) => sum + Number(line.quantity || 0) * Number(line.unit_price || 0), 0);
  const discount = form.discount_type === "amount" ? Number(form.discount_value || 0) : subtotal * Number(form.discount_value || 0) / 100;
  const taxRate = config?.tax_rate == null ? null : Number(config.tax_rate);
  const tax = taxRate == null ? null : (subtotal - discount) * taxRate / 100;
  const total = subtotal - discount + (tax || 0);
  const submit = async (event) => {
    event.preventDefault(); setBusy(true); setError("");
    try { await onSave(form); } catch (e) { setError(e.message); } finally { setBusy(false); }
  };
  return <Modal title={initial ? `Edit ${initial.quotation_no}` : "Create Quotation"} onClose={onClose}>
    <form onSubmit={submit} className="space-y-5">
      <div className="grid gap-3 md:grid-cols-2">
        <Select label="Customer" required value={form.customer} onChange={(v) => set("customer", v)} options={customers.map(c => [String(c.id), c.name])} />
        <Select label="Standard Product (optional)" value={form.product} onChange={(v) => {
          const selected = products.find((product) => String(product.id) === v);
          setForm((old) => ({ ...old, product: v, item_description: selected ? selected.name : old.item_description }));
        }} options={products.map(product => [String(product.id), product.name + " · " + product.sku])} />
        <Field label="Product / Service (custom or selected)" required value={form.item_description} onChange={(v) => set("item_description", v)} />
        <Field label="Dimensions" value={form.dimensions} onChange={(v) => set("dimensions", v)} />
        <Field label="Overall Quantity" type="number" min="0.001" step="0.001" value={form.quantity} onChange={(v) => set("quantity", v)} />
        <Field label="Valid Until" required type="date" value={form.valid_until} onChange={(v) => set("valid_until", v)} />
        <Field label="Delivery / Installation Timeline" value={form.delivery_timeline} onChange={(v) => set("delivery_timeline", v)} />
      </div>
      <div className="space-y-3">
        <div className="flex items-center justify-between"><h3 className="font-bold text-slate-900">Itemized Pricing</h3><button type="button" onClick={() => set("line_items", [...form.line_items, blankLine()])} className="rounded-lg border border-slate-300 px-3 py-2 text-xs font-semibold">+ Add Line</button></div>
        {form.line_items.map((line, index) => <div key={index} className="rounded-xl border border-slate-200 p-3">
          <div className="mb-3 flex items-center justify-between"><span className="text-xs font-bold uppercase text-slate-500">Line {index + 1}</span>{form.line_items.length > 1 && <button type="button" onClick={() => set("line_items", form.line_items.filter((_, i) => i !== index))} className="text-xs font-semibold text-red-600">Remove</button>}</div>
          <div className="grid gap-3 md:grid-cols-2">
            <Select label="Category" value={line.category} onChange={(v) => updateLine(index, "category", v)} options={categories} />
            <Field label="Description" required value={line.description} onChange={(v) => updateLine(index, "description", v)} />
            <Field label="Dimensions" value={line.dimensions} onChange={(v) => updateLine(index, "dimensions", v)} />
            <div className="grid grid-cols-3 gap-2">
              <Field label="Qty" type="number" min="0.001" step="0.001" value={line.quantity} onChange={(v) => updateLine(index, "quantity", v)} />
              <Field label="Unit" value={line.unit} onChange={(v) => updateLine(index, "unit", v)} />
              <Field label="Unit Price" type="number" min="0" step="0.01" value={line.unit_price} onChange={(v) => updateLine(index, "unit_price", v)} />
            </div>
            <div className="flex items-end justify-end text-sm font-bold text-slate-800">Line Total: {money(Number(line.quantity || 0) * Number(line.unit_price || 0))}</div>
          </div>
        </div>)}
      </div>
      <div className="grid gap-3 rounded-xl bg-slate-50 p-4 md:grid-cols-2">
        <Select label="Discount Type" value={form.discount_type} onChange={(v) => set("discount_type", v)} options={[["percentage", "Percentage"], ["amount", "Fixed Amount (₹)"]]} />
        <Field label={form.discount_type === "amount" ? "Discount Amount (₹)" : "Discount (%)"} type="number" min="0" max={form.discount_type === "percentage" ? "100" : undefined} step="0.01" value={form.discount_value} onChange={(v) => set("discount_value", v)} />
        <Field label="Advance Required (₹)" type="number" min="0" step="0.01" value={form.advance_required} onChange={(v) => set("advance_required", v)} />
        <div className="space-y-1 text-sm md:col-span-2">
          <div className="flex justify-between"><span>Subtotal</span><b>{money(subtotal)}</b></div>
          <div className="flex justify-between"><span>Discount</span><b>− {money(discount)}</b></div>
          {taxRate == null ? <div className="text-xs text-amber-700">Tax rate has not been configured. Sending is disabled until Founder sets it.</div> : <div className="flex justify-between"><span>{config.tax_label || "Tax"} ({taxRate}%)</span><b>{money(tax)}</b></div>}
          <div className="flex justify-between border-t border-slate-200 pt-2 text-base"><span className="font-bold">Estimated Total</span><b>{money(total)}</b></div>
          {discount > 0 && (!config?.manager_discount_limit_type || config?.manager_discount_limit_value == null) && <div className="text-xs text-amber-700">Founder must configure the Manager Discount Limit and select its unit before a discounted quotation can be submitted.</div>}
        </div>
      </div>
      <Field label="Terms & Conditions" area value={form.terms} onChange={(v) => set("terms", v)} />
      <Field label="Internal Notes" area value={form.notes} onChange={(v) => set("notes", v)} />
      {error && <div className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</div>}
      <div className="flex justify-end gap-2"><button type="button" onClick={onClose} className="rounded-xl border border-slate-300 px-4 py-2.5 text-sm">Cancel</button><button disabled={busy} className="rounded-xl bg-slate-900 px-5 py-2.5 text-sm font-bold text-white">{busy ? "Saving..." : "Save Draft"}</button></div>
    </form>
  </Modal>;
}

function ConfigurationEditor({ config, onClose, onSaved }) {
  const [form, setForm] = useState({
    company_name: config?.company_name || "SADACO GROUP OF COMPANIES",
    company_address: config?.company_address || "", company_phone: config?.company_phone || "",
    company_email: config?.company_email || "", company_website: config?.company_website || "",
    tax_label: config?.tax_label || "", tax_rate: config?.tax_rate ?? "",
    manager_discount_limit_type: config?.manager_discount_limit_type || "",
    manager_discount_limit_value: config?.manager_discount_limit_value ?? "",
    default_terms: config?.default_terms || "", default_validity_days: config?.default_validity_days ?? "",
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const set = (key, value) => setForm((old) => ({ ...old, [key]: value }));
  const save = async (event) => {
    event.preventDefault(); setBusy(true); setError("");
    try { await api.post("/sales/quotations/configuration/", form); await onSaved(); }
    catch (e) { setError(e.response?.data?.detail || "Unable to save quotation settings."); }
    finally { setBusy(false); }
  };
  return <Modal title="Founder · Quotation Settings" onClose={onClose}>
    <form onSubmit={save} className="space-y-4">
      <h3 className="font-bold text-slate-900">Company Details for PDF</h3>
      <div className="grid gap-3 md:grid-cols-2">
        <Field label="Company Name" required value={form.company_name} onChange={(v) => set("company_name", v)} />
        <Field label="Phone" value={form.company_phone} onChange={(v) => set("company_phone", v)} />
        <Field label="Email" value={form.company_email} onChange={(v) => set("company_email", v)} />
        <Field label="Website" value={form.company_website} onChange={(v) => set("company_website", v)} />
        <Field label="Address" area value={form.company_address} onChange={(v) => set("company_address", v)} />
      </div>
      <h3 className="border-t border-slate-100 pt-4 font-bold text-slate-900">Tax & Discount Authority</h3>
      <div className="grid gap-3 md:grid-cols-2">
        <Field label="Tax Label" placeholder="Enter tax name" value={form.tax_label} onChange={(v) => set("tax_label", v)} />
        <Field label="Tax Rate (%)" type="number" min="0" max="100" step="0.01" placeholder="Not configured" value={form.tax_rate} onChange={(v) => set("tax_rate", v)} />
        <Select label="Manager Discount Limit Type" value={form.manager_discount_limit_type} onChange={(v) => set("manager_discount_limit_type", v)} options={[["percentage", "Percentage"], ["amount", "Fixed Amount (₹)"]]} />
        <Field label={form.manager_discount_limit_type === "amount" ? "Manager Discount Limit (₹)" : "Manager Discount Limit (%)"} type="number" min="0" step="0.01" placeholder="Not configured" value={form.manager_discount_limit_value} onChange={(v) => set("manager_discount_limit_value", v)} />
        <Field label="Default Validity (days)" type="number" min="1" step="1" value={form.default_validity_days} onChange={(v) => set("default_validity_days", v)} />
      </div>
      <Field label="Default Terms & Conditions" area value={form.default_terms} onChange={(v) => set("default_terms", v)} />
      {error && <div className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</div>}
      <div className="flex justify-end gap-2"><button type="button" onClick={onClose} className="rounded-xl border border-slate-300 px-4 py-2.5 text-sm">Cancel</button><button disabled={busy} className="rounded-xl bg-slate-900 px-5 py-2.5 text-sm font-bold text-white">{busy ? "Saving..." : "Save Settings"}</button></div>
    </form>
  </Modal>;
}

function QuotationDetail({ quotation, canManage, canApprove, busy, onClose, onAction, onPdf }) {
  const [notes, setNotes] = useState("");
  return <Modal title={quotation.quotation_no} onClose={onClose}>
    <div className="mb-4 flex flex-wrap items-center justify-between gap-3"><div><div className="text-lg font-bold">{quotation.customer.name}</div><div className="text-sm text-slate-500">{quotation.customer.phone} · {quotation.customer.email}</div></div><Status value={quotation.status.replaceAll("_", " ")} /></div>
    <div className="mb-4 grid gap-3 sm:grid-cols-3"><Stat label="Subtotal" value={money(quotation.subtotal)} /><Stat label="Discount" value={money(quotation.discount_amount)} /><Stat label="Quotation Total" value={money(quotation.quoted_price)} /></div>
    <div className="overflow-x-auto rounded-xl border border-slate-200"><table className="w-full text-sm"><thead className="bg-slate-50"><tr><th className="p-3 text-left">Category / Description</th><th className="p-3 text-right">Qty</th><th className="p-3 text-right">Unit Price</th><th className="p-3 text-right">Amount</th></tr></thead><tbody>{quotation.line_items.map((line) => <tr key={line.id} className="border-t border-slate-100"><td className="p-3"><b>{line.category_label}</b><div className="text-xs text-slate-500">{line.description} {line.dimensions && `· ${line.dimensions}`}</div></td><td className="p-3 text-right">{line.quantity} {line.unit}</td><td className="p-3 text-right">{money(line.unit_price)}</td><td className="p-3 text-right font-semibold">{money(line.line_total)}</td></tr>)}</tbody></table></div>
    <div className="mt-4 space-y-1 text-sm"><div className="flex justify-between"><span>Discount {quotation.discount_type === "amount" ? "(fixed amount)" : `(${quotation.discount_percent}%)`}</span><b>− {money(quotation.discount_amount)}</b></div><div className="flex justify-between"><span>Tax {quotation.tax_rate == null ? "(not configured)" : `(${quotation.tax_rate}%)`}</span><b>{money(quotation.tax_amount)}</b></div><div className="flex justify-between"><span>Advance Required</span><b>{money(quotation.advance_required)}</b></div><div className="flex justify-between"><span>Valid Until</span><b>{quotation.valid_until || "—"}</b></div></div>
    {quotation.terms && <div className="mt-4 rounded-xl bg-slate-50 p-3 text-sm"><b>Terms & Conditions</b><p className="mt-1 whitespace-pre-wrap">{quotation.terms}</p></div>}
    {quotation.approval_history?.length > 0 && <div className="mt-4"><h3 className="font-bold">Approval History</h3><div className="mt-2 space-y-2">{quotation.approval_history.map((event, i) => <div key={i} className="rounded-lg border border-slate-200 p-3 text-sm"><b>{event.action}</b> · {event.performed_by}<div className="text-xs text-slate-500">{new Date(event.created_at).toLocaleString()} · Discount {event.discount_percent}%</div>{event.notes && <p>{event.notes}</p>}</div>)}</div></div>}
    {canApprove && quotation.status === "pending_approval" && <div className="mt-5 space-y-3 rounded-xl border border-amber-200 bg-amber-50 p-4"><h3 className="font-bold text-amber-900">Founder Approval Required</h3><textarea value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Approval / rejection note" rows="2" className="w-full rounded-lg border border-amber-200 bg-white p-3 text-sm" /><div className="flex justify-end gap-2"><button disabled={busy} onClick={() => onAction("reject", notes)} className="rounded-lg border border-red-300 px-4 py-2 text-sm font-semibold text-red-700">Reject</button><button disabled={busy} onClick={() => onAction("approve", notes)} className="rounded-lg bg-emerald-700 px-4 py-2 text-sm font-semibold text-white">Approve & Send</button></div></div>}
    <div className="mt-5 flex justify-end gap-2">{["sent", "accepted", "approved"].includes(quotation.status) && <button onClick={onPdf} className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-semibold">Download PDF</button>}<button onClick={onClose} className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white">Close</button></div>
  </Modal>;
}

function Field({ label, value, onChange, type = "text", required = false, min, max, step, placeholder, area = false }) {
  return <label className="block"><span className="mb-1 block text-xs font-semibold text-slate-600">{label}</span>{area ? <textarea rows="3" required={required} value={value ?? ""} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} className="w-full rounded-xl border border-slate-300 px-3 py-2.5 text-sm" /> : <input type={type} required={required} min={min} max={max} step={step} value={value ?? ""} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} className="w-full rounded-xl border border-slate-300 px-3 py-2.5 text-sm" />}</label>;
}
function Select({ label, value, onChange, options, required = false }) {
  return <label className="block"><span className="mb-1 block text-xs font-semibold text-slate-600">{label}</span><select required={required} value={value ?? ""} onChange={(e) => onChange(e.target.value)} className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm"><option value="">Select {label}</option>{options.map(([v, text]) => <option key={v} value={v}>{text}</option>)}</select></label>;
}
function Modal({ title, onClose, children }) {
  return <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/50 p-3"><div className="max-h-[94vh] w-full max-w-5xl overflow-y-auto rounded-2xl bg-white p-5 shadow-2xl"><div className="mb-5 flex items-center justify-between"><h2 className="text-lg font-bold text-slate-900">{title}</h2><button onClick={onClose} className="rounded-lg px-3 py-2 text-slate-500 hover:bg-slate-100">✕</button></div>{children}</div></div>;
}
