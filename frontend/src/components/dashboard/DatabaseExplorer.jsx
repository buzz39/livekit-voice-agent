import React, { useState, useEffect } from 'react';
import {
  Bot, Plus, Save, Trash2, Database, Columns, ChevronDown,
  CheckCircle, AlertCircle, X,
} from 'lucide-react';
import {
  getAgents, upsertAgent, deleteAgent,
  getDataSchemas, createDataSchemaField, deleteDataSchemaField,
} from '../../api';

export default function DatabaseExplorer() {
  const [tab, setTab] = useState('agents'); // 'agents' | 'schemas'

  return (
    <div className="flex flex-col h-full gap-4">
      <div>
        <h2 className="text-xl font-bold text-white">Database</h2>
        <p className="text-sm text-slate-400">Manage agent configurations and data collection schemas</p>
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 bg-slate-900 p-1 rounded-lg w-fit">
        <TabBtn active={tab === 'agents'} onClick={() => setTab('agents')} icon={<Bot size={14} />} label="Agent Configs" />
        <TabBtn active={tab === 'schemas'} onClick={() => setTab('schemas')} icon={<Columns size={14} />} label="Data Schemas" />
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto">
        {tab === 'agents' ? <AgentsPanel /> : <SchemasPanel />}
      </div>
    </div>
  );
}

function TabBtn({ active, onClick, icon, label }) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
        active ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white hover:bg-slate-800'
      }`}
    >
      {icon} {label}
    </button>
  );
}

// ========== Agents Panel ==========
function AgentsPanel() {
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ slug: '', owner_id: '', opening_line: '', mcp_endpoint_url: '', is_active: true });
  const [toast, setToast] = useState(null);

  const showToast = (msg, type = 'success') => { setToast({ msg, type }); setTimeout(() => setToast(null), 3000); };

  const load = async () => {
    setLoading(true);
    setAgents(await getAgents());
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const handleSave = async () => {
    if (!form.slug.trim()) { showToast('Slug is required', 'error'); return; }
    try {
      await upsertAgent(form);
      showToast('Agent saved');
      setShowForm(false);
      setForm({ slug: '', owner_id: '', opening_line: '', mcp_endpoint_url: '', is_active: true });
      load();
    } catch { showToast('Failed to save', 'error'); }
  };

  const handleEdit = (agent) => {
    setForm(agent);
    setShowForm(true);
  };

  const handleDelete = async (slug) => {
    if (!window.confirm(`Delete agent "${slug}"?`)) return;
    try {
      await deleteAgent(slug);
      showToast('Agent deleted');
      load();
    } catch { showToast('Failed to delete', 'error'); }
  };

  return (
    <div className="space-y-4">
      {toast && <Toast toast={toast} />}

      <div className="flex justify-end">
        <button onClick={() => { setForm({ slug: '', owner_id: '', opening_line: '', mcp_endpoint_url: '', is_active: true }); setShowForm(true); }}
          className="flex items-center gap-2 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 rounded-lg text-sm text-white">
          <Plus size={14} /> Add Agent
        </button>
      </div>

      {/* Agent cards */}
      {loading ? (
        <div className="text-slate-500 text-sm text-center py-8">Loading...</div>
      ) : agents.length === 0 ? (
        <div className="text-slate-500 text-sm text-center py-8">No agent configs yet.</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {agents.map(a => (
            <div key={a.slug} className="bg-slate-900 border border-slate-800 rounded-lg p-4 hover:border-slate-600 transition-colors">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Bot size={16} className="text-indigo-400" />
                  <span className="text-sm font-semibold text-white">{a.slug}</span>
                  <span className={`text-[10px] px-1.5 py-0.5 rounded ${a.is_active ? 'bg-emerald-500/20 text-emerald-400' : 'bg-slate-700 text-slate-400'}`}>
                    {a.is_active ? 'active' : 'inactive'}
                  </span>
                </div>
                <div className="flex gap-1">
                  <button onClick={() => handleEdit(a)} className="p-1 rounded hover:bg-slate-700 text-slate-400 hover:text-indigo-400"><Save size={13} /></button>
                  <button onClick={() => handleDelete(a.slug)} className="p-1 rounded hover:bg-slate-700 text-slate-400 hover:text-red-400"><Trash2 size={13} /></button>
                </div>
              </div>
              {a.opening_line && <p className="mt-2 text-xs text-slate-400 italic">"{a.opening_line}"</p>}
              {a.mcp_endpoint_url && <p className="mt-1 text-[10px] text-slate-500 truncate">MCP: {a.mcp_endpoint_url}</p>}
            </div>
          ))}
        </div>
      )}

      {/* Form modal */}
      {showForm && (
        <Modal title={form.slug ? `Edit Agent: ${form.slug}` : 'New Agent'} onClose={() => setShowForm(false)}>
          <div className="space-y-3">
            <Field label="Slug (unique ID)" required>
              <input value={form.slug} onChange={(e) => setForm(f => ({ ...f, slug: e.target.value }))}
                placeholder="e.g. solar_sales_agent" className={inputClass} disabled={agents.some(a => a.slug === form.slug)} />
            </Field>
            <Field label="Opening Line">
              <textarea value={form.opening_line || ''} onChange={(e) => setForm(f => ({ ...f, opening_line: e.target.value }))}
                rows={3} placeholder="Hello! Main Aisha bol rahi hoon..." className={inputClass} />
            </Field>
            <Field label="MCP Endpoint URL">
              <input value={form.mcp_endpoint_url || ''} onChange={(e) => setForm(f => ({ ...f, mcp_endpoint_url: e.target.value }))}
                placeholder="https://..." className={inputClass} />
            </Field>
            <div className="flex items-center gap-2">
              <input type="checkbox" checked={form.is_active} onChange={(e) => setForm(f => ({ ...f, is_active: e.target.checked }))}
                className="rounded bg-slate-800 border-slate-600" />
              <label className="text-sm text-slate-300">Active</label>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button onClick={() => setShowForm(false)} className={btnSecondary}>Cancel</button>
              <button onClick={handleSave} className={btnPrimary}>Save Agent</button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}

// ========== Data Schemas Panel ==========
function SchemasPanel() {
  const [schemas, setSchemas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterSlug, setFilterSlug] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ slug: '', field_name: '', field_type: 'string', description: '' });
  const [toast, setToast] = useState(null);

  const showToast = (msg, type = 'success') => { setToast({ msg, type }); setTimeout(() => setToast(null), 3000); };

  const load = async () => {
    setLoading(true);
    setSchemas(await getDataSchemas(filterSlug || null));
    setLoading(false);
  };

  useEffect(() => { load(); }, [filterSlug]);

  const handleCreate = async () => {
    if (!form.slug.trim() || !form.field_name.trim()) { showToast('Slug and field name required', 'error'); return; }
    try {
      await createDataSchemaField(form);
      showToast('Field added');
      setShowForm(false);
      setForm({ slug: '', field_name: '', field_type: 'string', description: '' });
      load();
    } catch { showToast('Failed to add', 'error'); }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this field?')) return;
    try {
      await deleteDataSchemaField(id);
      showToast('Field deleted');
      load();
    } catch { showToast('Failed to delete', 'error'); }
  };

  // Group by slug
  const grouped = schemas.reduce((acc, s) => {
    (acc[s.slug] = acc[s.slug] || []).push(s);
    return acc;
  }, {});

  return (
    <div className="space-y-4">
      {toast && <Toast toast={toast} />}

      <div className="flex items-center justify-between flex-wrap gap-3">
        <input
          value={filterSlug}
          onChange={(e) => setFilterSlug(e.target.value)}
          placeholder="Filter by agent slug..."
          className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 w-64"
        />
        <button onClick={() => setShowForm(true)}
          className="flex items-center gap-2 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 rounded-lg text-sm text-white">
          <Plus size={14} /> Add Field
        </button>
      </div>

      {loading ? (
        <div className="text-slate-500 text-sm text-center py-8">Loading...</div>
      ) : Object.keys(grouped).length === 0 ? (
        <div className="text-slate-500 text-sm text-center py-8">No data schemas defined.</div>
      ) : (
        Object.entries(grouped).map(([slug, fields]) => (
          <div key={slug} className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden">
            <div className="px-4 py-2 border-b border-slate-800 flex items-center gap-2">
              <Database size={14} className="text-indigo-400" />
              <span className="text-sm font-semibold text-white">{slug}</span>
              <span className="text-xs text-slate-500">{fields.length} field{fields.length !== 1 ? 's' : ''}</span>
            </div>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-xs text-slate-500 uppercase">
                  <th className="text-left px-4 py-2">Field</th>
                  <th className="text-left px-4 py-2">Type</th>
                  <th className="text-left px-4 py-2">Description</th>
                  <th className="w-10"></th>
                </tr>
              </thead>
              <tbody>
                {fields.map(f => (
                  <tr key={f.id} className="border-t border-slate-800/50 hover:bg-slate-800/30">
                    <td className="px-4 py-2 text-white font-mono">{f.field_name}</td>
                    <td className="px-4 py-2 text-slate-400">{f.field_type}</td>
                    <td className="px-4 py-2 text-slate-400">{f.description || '—'}</td>
                    <td className="px-2 py-2">
                      <button onClick={() => handleDelete(f.id)} className="p-1 rounded hover:bg-slate-700 text-slate-500 hover:text-red-400">
                        <Trash2 size={12} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))
      )}

      {/* Add field modal */}
      {showForm && (
        <Modal title="Add Data Schema Field" onClose={() => setShowForm(false)}>
          <div className="space-y-3">
            <Field label="Agent Slug" required>
              <input value={form.slug} onChange={(e) => setForm(f => ({ ...f, slug: e.target.value }))}
                placeholder="e.g. default_roofing_agent" className={inputClass} />
            </Field>
            <Field label="Field Name" required>
              <input value={form.field_name} onChange={(e) => setForm(f => ({ ...f, field_name: e.target.value }))}
                placeholder="e.g. roof_age" className={inputClass} />
            </Field>
            <Field label="Type">
              <div className="relative">
                <select value={form.field_type} onChange={(e) => setForm(f => ({ ...f, field_type: e.target.value }))}
                  className={`${inputClass} appearance-none pr-8`}>
                  <option value="string">string</option>
                  <option value="number">number</option>
                  <option value="boolean">boolean</option>
                  <option value="date">date</option>
                  <option value="email">email</option>
                  <option value="phone">phone</option>
                </select>
                <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
              </div>
            </Field>
            <Field label="Description">
              <input value={form.description} onChange={(e) => setForm(f => ({ ...f, description: e.target.value }))}
                placeholder="What should the AI ask for?" className={inputClass} />
            </Field>
            <div className="flex justify-end gap-2 pt-2">
              <button onClick={() => setShowForm(false)} className={btnSecondary}>Cancel</button>
              <button onClick={handleCreate} className={btnPrimary}>Add Field</button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}

// --- Shared tiny components ---
const inputClass = 'w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500';
const btnPrimary = 'px-4 py-2 bg-indigo-600 hover:bg-indigo-700 rounded-lg text-sm font-medium text-white transition-colors';
const btnSecondary = 'px-4 py-2 rounded-lg text-sm text-slate-400 hover:text-white hover:bg-slate-800 transition-colors';

function Toast({ toast }) {
  return (
    <div className={`fixed top-4 right-4 z-50 flex items-center gap-2 px-4 py-2 rounded-lg text-sm border ${
      toast.type === 'error' ? 'bg-red-500/10 border-red-500/30 text-red-300' : 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
    }`}>
      {toast.type === 'error' ? <AlertCircle size={14} /> : <CheckCircle size={14} />}
      {toast.msg}
    </div>
  );
}

function Modal({ title, onClose, children }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="relative bg-slate-900 border border-slate-700 rounded-xl shadow-2xl w-full max-w-lg mx-4 max-h-[85vh] overflow-y-auto">
        <div className="flex items-center justify-between px-5 py-3 border-b border-slate-800 sticky top-0 bg-slate-900 z-10">
          <h3 className="text-white font-semibold">{title}</h3>
          <button onClick={onClose} className="text-slate-400 hover:text-white p-1"><X size={18} /></button>
        </div>
        <div className="px-5 py-4">{children}</div>
      </div>
    </div>
  );
}

function Field({ label, required, children }) {
  return (
    <div>
      <label className="block text-sm font-medium text-slate-300 mb-1">
        {label} {required && <span className="text-red-400">*</span>}
      </label>
      {children}
    </div>
  );
}
