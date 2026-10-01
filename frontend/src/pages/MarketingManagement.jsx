import { useEffect, useState } from "react";
import {
  getMarketingDashboard,
  createCampaign,
  createMarketingContent,
  createMarketingLead,
} from "../services/api";

const emptyData = {
  stats: { active_campaigns: 0, published: 0, leads: 0, converted: 0 },
  campaigns: [],
  contents: [],
  leads: [],
  options: { customers: [], enquiries: [], campaigns: [] },
};

export default function MarketingManagement() {
  const [d, setD] = useState(emptyData);
  const [tab, setTab] = useState("campaigns");
  const [form, setForm] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      setD(await getMarketingDashboard());
    } catch (e) {
      setError(e?.response?.data?.detail || "Unable to load marketing data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const save = async () => {
    try {
      if (tab === "campaigns") await createCampaign(form);
      if (tab === "content") await createMarketingContent(form);
      if (tab === "leads") await createMarketingLead(form);
      setForm({});
      await load();
    } catch (e) {
      setError(e?.response?.data?.detail || "Unable to save this item.");
    }
  };

  const stats = [
    ["active_campaigns", "Active Campaigns"],
    ["published", "Published"],
    ["leads", "Leads"],
    ["converted", "Converted"],
  ];
  const tabs = [
    ["campaigns", "Campaigns"],
    ["content", "Content"],
    ["leads", "Leads"],
  ];
  return (
    <div className="space-y-6">
      <div className="relative overflow-hidden rounded-[28px] bg-gradient-to-br from-blue-700 via-indigo-700 to-violet-800 p-5 text-white shadow-xl shadow-indigo-900/15 sm:p-6">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-blue-100">Growth & Engagement</p>
            <h1 className="mt-1 text-2xl font-bold tracking-tight sm:text-3xl">Marketing & Business Development</h1>
            <p className="mt-2 text-sm text-indigo-100">Manage campaigns, content and business leads.</p>
          </div>
        <button className="rounded-xl border border-white/30 bg-white/10 px-4 py-2.5 text-sm font-semibold text-white backdrop-blur-sm transition hover:bg-white/20" onClick={load} disabled={loading}>
          {loading ? "Loading…" : "Refresh"}
        </button>
        </div>
      </div>
      {error && (
        <div className="card border border-red-200 text-red-700">{error}</div>
      )}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {stats.map(([k, l]) => (
          <div className="card" key={k}>
            <div className="muted text-xs">{l}</div>
            <div className="text-2xl font-bold mt-1">{d.stats?.[k] || 0}</div>
          </div>
        ))}
      </div>
      <div className="flex flex-wrap gap-2">
        {tabs.map(([k, l]) => (
          <button
            className={tab === k ? "btn-primary" : "btn"}
            onClick={() => setTab(k)}
            key={k}
          >
            {l}
          </button>
        ))}
      </div>
      <div className="card">
        <div className="grid md:grid-cols-3 gap-3">
          {tab === "campaigns" && (
            <>
              <Input l="Campaign name" k="name" f={form} s={setForm} />
              <Input l="Channel" k="channel" f={form} s={setForm} />
              <Input
                l="Target segment"
                k="target_segment"
                f={form}
                s={setForm}
              />
              <Input
                l="Start"
                k="start_date"
                type="date"
                f={form}
                s={setForm}
              />
              <Input l="End" k="end_date" type="date" f={form} s={setForm} />
              <Input l="Budget" k="budget" type="number" f={form} s={setForm} />
              <Select
                l="Status"
                k="status"
                opts={["planned", "active", "completed", "cancelled"]}
                f={form}
                s={setForm}
              />
            </>
          )}
          {tab === "content" && (
            <>
              <Input l="Title" k="title" f={form} s={setForm} />
              <Input l="Channel" k="channel" f={form} s={setForm} />
              <Select
                l="Campaign"
                k="campaign_id"
                opts={d.options?.campaigns?.map((x) => x.id) || []}
                labels={d.options?.campaigns?.map((x) => x.name) || []}
                f={form}
                s={setForm}
              />
              <Input
                l="Content date"
                k="content_date"
                type="date"
                f={form}
                s={setForm}
              />
              <Select
                l="Status"
                k="status"
                opts={["idea", "planned", "published"]}
                f={form}
                s={setForm}
              />
              <Input l="URL" k="content_url" f={form} s={setForm} />
            </>
          )}
          {tab === "leads" && (
            <>
              <Input l="Source" k="source" f={form} s={setForm} />
              <Select
                l="Customer"
                k="customer_id"
                opts={d.options?.customers?.map((x) => x.id) || []}
                labels={d.options?.customers?.map((x) => x.name) || []}
                f={form}
                s={setForm}
              />
              <Select
                l="Campaign"
                k="campaign_id"
                opts={d.options?.campaigns?.map((x) => x.id) || []}
                labels={d.options?.campaigns?.map((x) => x.name) || []}
                f={form}
                s={setForm}
              />
              <Select
                l="Status"
                k="status"
                opts={["new", "contacted", "converted", "lost"]}
                f={form}
                s={setForm}
              />
            </>
          )}
        </div>
        <button className="btn-primary mt-4" onClick={save}>
          Save {tab}
        </button>
      </div>
      <div className="card overflow-x-auto">
        {loading ? (
          <div className="muted py-8 text-center">Loading marketing data…</div>
        ) : tab === "campaigns" && !d.campaigns.length ? (
          <Empty text="No campaigns yet." />
        ) : tab === "content" && !d.contents.length ? (
          <Empty text="No marketing content yet." />
        ) : tab === "leads" && !d.leads.length ? (
          <Empty text="No leads yet." />
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr>
                <th>Name / Title</th>
                <th>Channel / Source</th>
                <th>Status</th>
                <th>Date</th>
              </tr>
            </thead>
            <tbody>
              {tab === "campaigns" &&
                d.campaigns.map((x) => (
                  <tr key={x.id}>
                    <td>{x.name}</td>
                    <td>{x.channel}</td>
                    <td>{x.status}</td>
                    <td>{x.start_date || "—"}</td>
                  </tr>
                ))}
              {tab === "content" &&
                d.contents.map((x) => (
                  <tr key={x.id}>
                    <td>{x.title}</td>
                    <td>{x.channel}</td>
                    <td>{x.status}</td>
                    <td>{x.content_date || "—"}</td>
                  </tr>
                ))}
              {tab === "leads" &&
                d.leads.map((x) => (
                  <tr key={x.id}>
                    <td>{x.customer || "Lead"}</td>
                    <td>{x.source}</td>
                    <td>{x.status}</td>
                    <td>{x.captured_on || "—"}</td>
                  </tr>
                ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

function Empty({ text }) {
  return <div className="py-10 text-center muted">{text}</div>;
}
function Input({ l, k, f, s, type = "text" }) {
  return (
    <label className="field">
      {l}
      <input
        type={type}
        value={f[k] || ""}
        onChange={(e) => s({ ...f, [k]: e.target.value })}
      />
    </label>
  );
}
function Select({ l, k, opts = [], labels = [], f, s }) {
  return (
    <label className="field">
      {l}
      <select
        value={f[k] || ""}
        onChange={(e) => s({ ...f, [k]: e.target.value })}
      >
        <option value="">Select</option>
        {opts.map((x, i) => (
          <option key={x} value={x}>
            {labels[i] || x}
          </option>
        ))}
      </select>
    </label>
  );
}
