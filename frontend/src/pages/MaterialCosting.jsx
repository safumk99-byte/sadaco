import { useEffect, useState } from "react";
import api from "../services/api";

const tabs = [["materials","Material Master"],["machines","Machine Rates"],["staff","Staff Salary"],["reconciliation","Stock Reconciliation"],["opening","Opening Stock Costing"]];
const money = (value) => value === "" || value == null ? "—" : `₹${Number(value).toLocaleString("en-IN",{minimumFractionDigits:2,maximumFractionDigits:2})}`;

export default function MaterialCosting() {
  const [tab,setTab] = useState("materials");
  const [materials,setMaterials] = useState([]);
  const [rates,setRates] = useState([]);
  const [staff,setStaff] = useState([]);
  const [canManage,setCanManage] = useState(false);
  const [busy,setBusy] = useState(false);
  const [error,setError] = useState("");
  const [notice,setNotice] = useState("");
  const [editing,setEditing] = useState(null);
  const [filter,setFilter] = useState("");
  const [form,setForm] = useState({});
  const [machineForm,setMachineForm] = useState({operation:"laser_cutting",rate:"",unit:"minute"});
  const [machineEditing,setMachineEditing] = useState(null);
  const [reconciliation,setReconciliation] = useState({items:[],count:0,reconciled_count:0,mismatch_count:0,unbatched_count:0});
  const [reconLoading,setReconLoading] = useState(false);
  const [openingItems,setOpeningItems] = useState([]);
  const [openingLoading,setOpeningLoading] = useState(false);
  const [openingDrafts,setOpeningDrafts] = useState({});

  async function load() {
    setError("");
    try {
      const [m,r,s] = await Promise.all([
        api.get("/costing/materials/"), api.get("/costing/machine-rates/"), api.get("/costing/staff/")
      ]);
      setMaterials(m.data.materials || []); setRates(r.data.rates || []); setStaff(s.data.staff || []);
      setCanManage(Boolean(m.data.can_manage && r.data.can_manage && s.data.can_manage));
    } catch(e) { setError(e.response?.data?.detail || "Unable to load costing master data."); }
  }
  useEffect(()=>{load();},[]);
  useEffect(()=>{
    if(tab!=="reconciliation") return;
    let active=true;
    setReconLoading(true);
    api.get("/inventory/materials/reconciliation/")
      .then(({data})=>{if(active)setReconciliation(data);})
      .catch(e=>{if(active)setError(e.response?.data?.detail||"Unable to load stock reconciliation.");})
      .finally(()=>{if(active)setReconLoading(false);});
    return ()=>{active=false;};
  },[tab]);
  async function loadUncostedOpeningStock(){
    setOpeningLoading(true);setError("");
    try{const {data}=await api.get("/inventory/materials/opening-batches/unpriced/");setOpeningItems(data.items||[]);}
    catch(e){setError(e.response?.data?.detail||"Unable to load uncosted opening stock.");}
    finally{setOpeningLoading(false);}
  }
  useEffect(()=>{if(tab==="opening")loadUncostedOpeningStock();},[tab]);
  async function assignOpeningCost(movementId){
    const draft=openingDrafts[movementId]||{};
    setBusy(true);setError("");setNotice("");
    try{
      await api.post(`/inventory/materials/opening-batches/${movementId}/cost/`,draft);
      setNotice("Verified opening-stock cost batch registered.");
      setOpeningDrafts(old=>({...old,[movementId]:{unit_cost:"",cost_source_reference:""}}));
      await loadUncostedOpeningStock();
    }catch(e){setError(e.response?.data?.detail||"Unable to register opening-stock cost.");}
    finally{setBusy(false);}
  }
  const setField=(key,value)=>setForm(old=>({...old,[key]:value}));
  function startNew(){setEditing("new");setForm({material_name:"",brand:"",thickness_mm:"",variant:"",colour:"na",sheet_width_ft:"8",sheet_height_ft:"4",purchase_rate:"",retail_rate:"",unit:"Sheet",is_active:true});}
  function startEdit(item){setEditing(item.id);setForm({...item});}
  async function saveMaterial(e){
    e.preventDefault();setBusy(true);setError("");setNotice("");
    try{
      await api.post(editing==="new"?"/costing/materials/create/":`/costing/materials/${editing}/update/`,form);
      setEditing(null);setNotice("Material master saved.");await load();
    }catch(e){setError(e.response?.data?.detail||"Unable to save material.");}
    finally{setBusy(false);}
  }
  async function saveMachine(e){
    e.preventDefault();setBusy(true);setError("");setNotice("");
    try{await api.post(machineEditing?`/costing/machine-rates/${machineEditing}/update/`:"/costing/machine-rates/create/",machineForm);setMachineEditing(null);setMachineForm({operation:"laser_cutting",rate:"",unit:"minute"});setNotice("Machine rate saved.");await load();}
    catch(e){setError(e.response?.data?.detail||"Unable to save machine rate.");}finally{setBusy(false);}
  }
  async function saveStaff(id,paymentType,salary,workingDays,productiveHours){
    setError("");setNotice("");
    try{await api.post(`/costing/staff/${id}/compensation/`,{payment_type:paymentType,monthly_salary:salary,working_days_per_month:workingDays,productive_hours_per_day:productiveHours});setNotice("Staff compensation updated.");await load();}
    catch(e){setError(e.response?.data?.detail||"Unable to save staff compensation.");}
  }
  const visible=materials.filter(x=>[x.material_name,x.brand,x.thickness_mm,x.variant,x.colour_label].join(" ").toLowerCase().includes(filter.toLowerCase()));
  return <div className="space-y-6">
    <header className="rounded-3xl bg-gradient-to-br from-slate-900 via-indigo-950 to-blue-900 p-6 text-white">
      <p className="text-xs font-bold uppercase tracking-[.2em] text-blue-200">SADACO • Cost Control</p>
      <h1 className="mt-2 text-2xl font-bold sm:text-3xl">Material Master & Job Costing</h1>
      <p className="mt-2 max-w-3xl text-sm text-blue-100">Purchase rates, retail rates, sheet-area costing, machine charges and staff compensation. All rates remain editable by authorized management.</p>
    </header>
    <div className="flex flex-wrap gap-2 rounded-2xl border border-slate-200 bg-white p-2">
      {tabs.filter(([key])=>key!=="opening"||canManage).map(([key,label])=><button key={key} onClick={()=>setTab(key)} className={`rounded-xl px-4 py-2.5 text-sm font-semibold ${tab===key?"bg-indigo-600 text-white":"text-slate-600 hover:bg-slate-100"}`}>{label}</button>)}
    </div>
    {error&&<div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}
    {notice&&<div className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">{notice}</div>}
    {tab==="materials"&&<section className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row">
        <input value={filter} onChange={e=>setFilter(e.target.value)} placeholder="Search material, brand, thickness or variant" className="min-w-0 flex-1 rounded-xl border border-slate-300 px-4 py-3 text-sm"/>
        {canManage&&<button onClick={startNew} className="rounded-xl bg-slate-900 px-5 py-3 text-sm font-semibold text-white">+ Add Material Variant</button>}
      </div>
      <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white">
        <table className="w-full min-w-[1050px] text-left text-sm">
          <thead className="bg-slate-50 text-xs uppercase text-slate-500"><tr>{["Material","Brand","Thickness","Variant / Colour","Sheet","Purchase Rate","₹ / Sq.ft","Retail Rate","Stock",""].map(x=><th key={x} className="px-4 py-3">{x}</th>)}</tr></thead>
          <tbody className="divide-y divide-slate-100">{visible.map(x=><tr key={x.id} className="hover:bg-slate-50">
            <td className="px-4 py-3 font-semibold text-slate-900">{x.material_name}</td><td className="px-4 py-3">{x.brand||"—"}</td><td className="px-4 py-3">{x.thickness_mm?x.thickness_mm+" mm":"—"}</td>
            <td className="px-4 py-3">{[x.variant,x.colour_label==="Not applicable"?"":x.colour_label].filter(Boolean).join(" / ")||"—"}</td>
            <td className="px-4 py-3">{x.sheet_width_ft} × {x.sheet_height_ft} ft</td><td className="px-4 py-3 font-semibold">{money(x.purchase_rate)}</td>
            <td className="px-4 py-3">{money(x.purchase_rate_sqft)}</td><td className="px-4 py-3">{money(x.retail_rate)}</td><td className="px-4 py-3">{x.stock_quantity} {x.unit}</td>
            <td className="px-4 py-3 text-right">{canManage&&<button onClick={()=>startEdit(x)} className="font-semibold text-indigo-600">Edit</button>}</td>
          </tr>)}</tbody>
        </table>
        {!visible.length&&<p className="p-8 text-center text-sm text-slate-500">No material variants found.</p>}
      </div>
      <p className="text-xs text-slate-500">Sq.ft rate is calculated automatically from purchase rate ÷ sheet area. Retail rates and unavailable supplier rates are intentionally left blank.</p>
    </section>}
    {tab==="machines"&&<section className="space-y-4">
      {canManage&&<form onSubmit={saveMachine} className="grid gap-3 rounded-2xl border border-slate-200 bg-white p-4 sm:grid-cols-5">
        <select value={machineForm.operation} onChange={e=>setMachineForm({...machineForm,operation:e.target.value,unit:e.target.value==="cnc_cutting"?"sqft":"minute"})} className="rounded-xl border border-slate-300 px-3 py-2.5 text-sm"><option value="laser_cutting">Laser Cutting</option><option value="laser_engraving">Laser Engraving</option><option value="cnc_cutting">CNC Cutting</option></select>
        <input value={machineForm.material_name||""} onChange={e=>setMachineForm({...machineForm,material_name:e.target.value})} placeholder="Material (e.g. Multy Wood)" className="rounded-xl border border-slate-300 px-3 py-2.5 text-sm"/>
        <input value={machineForm.thickness_mm||""} onChange={e=>setMachineForm({...machineForm,thickness_mm:e.target.value})} placeholder="Thickness mm" type="number" step="0.01" className="rounded-xl border border-slate-300 px-3 py-2.5 text-sm"/>
        <input required value={machineForm.rate} onChange={e=>setMachineForm({...machineForm,rate:e.target.value})} placeholder="Rate ₹" type="number" min="0" step="0.01" className="rounded-xl border border-slate-300 px-3 py-2.5 text-sm"/>
        <button disabled={busy} className="rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white">{machineEditing?"Save Rate":"Add Rate"}</button>
      </form>}
      <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white"><table className="w-full min-w-[650px] text-left text-sm">
        <thead className="bg-slate-50 text-xs uppercase text-slate-500"><tr><th className="px-4 py-3">Operation</th><th className="px-4 py-3">Material</th><th className="px-4 py-3">Thickness</th><th className="px-4 py-3">Rate</th><th className="px-4 py-3">Unit</th><th className="px-4 py-3"></th></tr></thead>
        <tbody className="divide-y divide-slate-100">{rates.map(x=><tr key={x.id}><td className="px-4 py-3 font-semibold">{x.operation_label}</td><td className="px-4 py-3">{x.material_name||"All materials"}</td><td className="px-4 py-3">{x.thickness_mm?x.thickness_mm+" mm":"—"}</td><td className="px-4 py-3">{money(x.rate)}</td><td className="px-4 py-3">/{x.unit}</td><td className="px-4 py-3 text-right">{canManage&&<button onClick={()=>{setMachineEditing(x.id);setMachineForm({operation:x.operation,material_name:x.material_name,thickness_mm:x.thickness_mm,rate:x.rate,unit:x.unit});}} className="font-semibold text-indigo-600">Edit</button>}</td></tr>)}</tbody>
      </table></div>
    </section>}
    {tab==="reconciliation"&&<section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div><h2 className="text-lg font-bold text-slate-900">Material Stock Reconciliation</h2>
          <p className="mt-1 text-sm text-slate-500">Compare department stock balances with movement history and receipt-batch quantities. This report is read-only.</p></div>
        <button onClick={()=>{setReconLoading(true);api.get("/inventory/materials/reconciliation/").then(({data})=>setReconciliation(data)).catch(e=>setError(e.response?.data?.detail||"Unable to refresh reconciliation.")).finally(()=>setReconLoading(false));}} disabled={reconLoading} className="rounded-xl border border-slate-300 px-4 py-2.5 text-sm font-semibold text-slate-700 disabled:opacity-50">{reconLoading?"Checking…":"Refresh"}</button>
      </div>
      <div className="grid gap-3 sm:grid-cols-3">
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4"><p className="text-xs font-semibold uppercase tracking-wide text-emerald-700">Reconciled</p><p className="mt-1 text-2xl font-bold text-emerald-900">{reconciliation.reconciled_count||0}</p></div>
        <div className="rounded-2xl border border-red-200 bg-red-50 p-4"><p className="text-xs font-semibold uppercase tracking-wide text-red-700">Mismatches</p><p className="mt-1 text-2xl font-bold text-red-900">{reconciliation.mismatch_count||0}</p></div>
        <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4"><p className="text-xs font-semibold uppercase tracking-wide text-amber-700">Unbatched Balances</p><p className="mt-1 text-2xl font-bold text-amber-900">{reconciliation.unbatched_count||0}</p></div>
      </div>
      <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white">
        {reconLoading?<p className="p-8 text-center text-sm text-slate-500">Reconciling stock records…</p>:<table className="w-full min-w-[1050px] text-left text-sm">
          <thead className="bg-slate-50 text-xs uppercase text-slate-500"><tr>{["Department / Location","Material","Recorded Stock","Movement Expected","Difference","Receipt Lot Stock","Unbatched","Status"].map(x=><th key={x} className="px-4 py-3">{x}</th>)}</tr></thead>
          <tbody className="divide-y divide-slate-100">{(reconciliation.items||[]).map(x=><tr key={x.balance_id} className="hover:bg-slate-50">
            <td className="px-4 py-3"><div className="font-semibold">{x.department}</div><div className="text-xs text-slate-500">{x.location}</div></td>
            <td className="px-4 py-3">{x.material}</td>
            <td className="px-4 py-3 font-semibold tabular-nums">{x.recorded_balance}</td>
            <td className="px-4 py-3 tabular-nums">{x.movement_expected_balance}</td>
            <td className="px-4 py-3 tabular-nums">{x.movement_difference}</td>
            <td className="px-4 py-3 tabular-nums">{x.receipt_lot_remaining}</td>
            <td className="px-4 py-3 tabular-nums">{x.unbatched_quantity}</td>
            <td className="px-4 py-3"><div className={x.reconciled?"font-semibold text-emerald-700":"font-semibold text-red-700"}>{x.reconciled?"Reconciled":"Mismatch"}</div>{x.unbatched_warning&&<div className="mt-1 text-xs text-amber-700">Unbatched / uncosted stock</div>}{x.lot_mismatches?.length>0&&<div className="mt-1 text-xs text-red-700">{x.lot_mismatches.length} lot issue(s)</div>}</td>
          </tr>)}</tbody>
        </table>}
        {!reconLoading&&!(reconciliation.items||[]).length&&<p className="p-8 text-center text-sm text-slate-500">No material stock balances found for this access scope.</p>}
      </div>
      <p className="text-xs text-slate-500">Wastage is recorded as an annotation because stock was already deducted when material was issued. Opening or legacy stock without a receipt lot is shown separately; this report never changes stock automatically.{reconciliation.truncated?" Only the first 500 balances are shown.":""}</p>
    </section>}
    {tab==="opening"&&<section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div><h2 className="text-lg font-bold text-slate-900">Uncosted Opening Stock</h2>
          <p className="mt-1 max-w-3xl text-sm text-slate-500">Assign a cost only when supported by an actual invoice, approved valuation sheet or other verified cost record. No rate is estimated or copied from the current material master.</p></div>
        <button onClick={loadUncostedOpeningStock} disabled={openingLoading} className="rounded-xl border border-slate-300 px-4 py-2.5 text-sm font-semibold text-slate-700 disabled:opacity-50">{openingLoading?"Loading…":"Refresh"}</button>
      </div>
      <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">Opening stock without a verified unit cost remains unbatched and cannot be issued to a production job. A costed opening batch keeps the original opening movement and source reference for audit.</div>
      {openingLoading?<div className="rounded-2xl border bg-white p-8 text-center text-sm text-slate-500">Loading opening movements…</div>:
      <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white">
        <table className="w-full min-w-[1050px] text-left text-sm">
          <thead className="bg-slate-50 text-xs uppercase text-slate-500"><tr>{["Opening Movement","Department / Location","Material","Quantity","Existing Reference","Verified Unit Cost (₹)","Cost Evidence Reference","Action"].map(x=><th key={x} className="px-4 py-3">{x}</th>)}</tr></thead>
          <tbody className="divide-y divide-slate-100">{openingItems.map(x=>{
            const draft=openingDrafts[x.movement_id]||{unit_cost:"",cost_source_reference:""};
            return <tr key={x.movement_id}>
              <td className="px-4 py-4 font-semibold">#{x.movement_id}<div className="text-xs font-normal text-slate-500">{new Date(x.created_at).toLocaleDateString()}</div></td>
              <td className="px-4 py-4">{x.department}<div className="text-xs text-slate-500">{x.location}</div></td>
              <td className="px-4 py-4">{x.material}</td>
              <td className="px-4 py-4 font-semibold tabular-nums">{x.quantity}</td>
              <td className="px-4 py-4">{x.reference||"—"}</td>
              <td className="px-4 py-4"><input type="number" min="0" step="0.01" value={draft.unit_cost} onChange={e=>setOpeningDrafts(old=>({...old,[x.movement_id]:{...draft,unit_cost:e.target.value}}))} placeholder="Enter actual rate" className="w-36 rounded-lg border border-slate-300 px-3 py-2"/></td>
              <td className="px-4 py-4"><input value={draft.cost_source_reference} maxLength={160} onChange={e=>setOpeningDrafts(old=>({...old,[x.movement_id]:{...draft,cost_source_reference:e.target.value}}))} placeholder="Invoice / valuation ref" className="w-56 rounded-lg border border-slate-300 px-3 py-2"/></td>
              <td className="px-4 py-4"><button disabled={busy||draft.unit_cost===""||!draft.cost_source_reference?.trim()} onClick={()=>assignOpeningCost(x.movement_id)} className="rounded-lg bg-indigo-600 px-3 py-2 text-xs font-semibold text-white disabled:opacity-40">Register Cost</button></td>
            </tr>;
          })}</tbody>
        </table>
        {!openingItems.length&&<p className="p-8 text-center text-sm text-slate-500">No uncosted opening movements found.</p>}
      </div>}
    </section>}
    {tab==="staff"&&<section className="space-y-3">
      <div className="rounded-2xl border border-blue-100 bg-blue-50 p-4 text-sm text-blue-900">Hourly cost = monthly salary ÷ monthly productive hours. Default basis: 26 working days × 8.25 productive hours = 214.5 hours. Authorized managers can adjust the working basis. Salary is a company expense; job labour allocation must not add the salary expense a second time.</div>
      <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white"><table className="w-full min-w-[750px] text-left text-sm">
        <thead className="bg-slate-50 text-xs uppercase text-slate-500"><tr><th className="px-4 py-3">Staff</th><th className="px-4 py-3">Staff ID</th><th className="px-4 py-3">Payment Type</th><th className="px-4 py-3">Monthly Salary</th><th className="px-4 py-3">Productive Basis</th><th className="px-4 py-3">Hourly Cost</th><th className="px-4 py-3">Action</th></tr></thead>
        <tbody className="divide-y divide-slate-100">{staff.map(x=><StaffRow key={x.staff_id} item={x} canManage={canManage} onSave={saveStaff}/>)}</tbody>
      </table></div>
    </section>}
    {editing!==null&&<div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/50 p-4"><form onSubmit={saveMaterial} className="max-h-[92vh] w-full max-w-3xl space-y-4 overflow-y-auto rounded-2xl bg-white p-5 shadow-2xl">
      <div className="flex items-center justify-between"><h2 className="text-xl font-bold">{editing==="new"?"Add Material Variant":"Edit Material Variant"}</h2><button type="button" onClick={()=>setEditing(null)} className="rounded-lg px-3 py-2 hover:bg-slate-100">✕</button></div>
      <div className="grid gap-3 sm:grid-cols-2">
        {[
          ["material_name","Material Name","text"],["brand","Brand","text"],["thickness_mm","Thickness (mm)","number"],["variant","Variant / Supplier Code","text"],["sheet_width_ft","Sheet Width (ft)","number"],["sheet_height_ft","Sheet Height (ft)","number"],["purchase_rate","Purchase Rate (₹)","number"],["retail_rate","Retail Rate (₹)","number"],["supplier_name","Supplier","text"],["stock_quantity","Stock Quantity","number"]
        ].map(([key,label,type])=><label key={key} className="text-sm font-medium text-slate-700">{label}<input type={type} step="0.01" value={form[key]??""} onChange={e=>setField(key,e.target.value)} className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2.5"/></label>)}
        <label className="text-sm font-medium text-slate-700">Colour<select value={form.colour||"na"} onChange={e=>setField("colour",e.target.value)} className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2.5"><option value="na">Not applicable</option><option value="clear">Clear</option><option value="colour">Colour</option></select></label>
        <label className="text-sm font-medium text-slate-700">Unit<input value={form.unit||"Sheet"} onChange={e=>setField("unit",e.target.value)} className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2.5"/></label>
      </div>
      <div className="flex justify-end gap-2"><button type="button" onClick={()=>setEditing(null)} className="rounded-xl border px-4 py-2.5">Cancel</button><button disabled={busy} className="rounded-xl bg-indigo-600 px-5 py-2.5 font-semibold text-white">{busy?"Saving…":"Save Material"}</button></div>
    </form></div>}
  </div>;
}

function StaffRow({item,canManage,onSave}){
  const [type,setType]=useState(item.payment_type||"monthly");
  const [salary,setSalary]=useState(item.monthly_salary||"");
  const [days,setDays]=useState(String(item.working_days_per_month||26));
  const [hours,setHours]=useState(String(item.productive_hours_per_day||"8.25"));
  return <tr><td className="px-4 py-3 font-semibold">{item.name}</td><td className="px-4 py-3">{item.staff_code}</td>
    <td className="px-4 py-3">{canManage?<select value={type} onChange={e=>setType(e.target.value)} className="rounded-lg border px-2 py-2"><option value="monthly">Monthly salary</option><option value="per_work">Per work</option></select>:type||"Not set"}</td>
    <td className="px-4 py-3">{type==="monthly"&&canManage?<input type="number" min="0" step="0.01" value={salary} onChange={e=>setSalary(e.target.value)} className="w-32 rounded-lg border px-2 py-2"/>:type==="monthly"?money(item.monthly_salary):"—"}</td>
    <td className="px-4 py-3">{type==="monthly"&&canManage?<div className="flex items-center gap-1"><input aria-label="Working days per month" title="Working days per month" type="number" min="1" max="31" value={days} onChange={e=>setDays(e.target.value)} className="w-16 rounded-lg border px-2 py-2"/><span>×</span><input aria-label="Productive hours per day" title="Productive hours per day" type="number" min="0.01" step="0.01" value={hours} onChange={e=>setHours(e.target.value)} className="w-20 rounded-lg border px-2 py-2"/><span className="text-xs text-slate-500">h</span></div>:type==="monthly"?`${item.working_hours_month||"214.5"} h/month`:"—"}</td>
    <td className="px-4 py-3">{type==="monthly"?money(item.hourly_cost):"Work-based"}</td>
    <td className="px-4 py-3">{canManage&&<button onClick={()=>onSave(item.staff_id,type,salary,days,hours)} className="font-semibold text-indigo-600">Save</button>}</td></tr>;
}
