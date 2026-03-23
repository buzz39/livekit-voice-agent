import React, { useState, useEffect } from 'react';
import {
  Plus, Trash2, Shield, ChevronDown, X, Save,
  CheckCircle, AlertCircle,
} from 'lucide-react';
import { getObjections, upsertObjection, deleteObjection, getAgents } from '../../api';

export default function ObjectionManager() {
  const [objections, setObjections] = useState([]);
  const [agents, setAgents] = useState([]);
  const [filterSlug, setFilterSlug] = useState('');
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ objection_text: '', response_text: '', agent_slug: '' });
  const [toast, setToast] = useState(null);

  const showToast = (msg, type = 'success') => { setToast({ msg, type }); setTimeout(() => setToast(null), 3000); };

  const load = async () => {
    setLoading(true);
    const [objList, agentList] = await Promise.all([
      getObjections(filterSlug || null),
      getAgents(),
    ]);
    setObjections(objList);
    setAgents(agentList);
    setLoading(false);
  };

  useEffect(() => { load(); }, [filterSlug]);

  const handleSave = async () => {
    if (!form.objection_text.trim()) { showToast('Objection text is required', 'error'); return; }
    try {
      await upsertObjection({
        objection_text: form.objection_text,
        response_text: form.response_text,
        agent_slug: form.agent_slug || null,
      });
      showToast('Objection saved');
      setShowForm(false);
      setForm({ objection_text: '', response_text: '', agent_slug: '' });
      load();
    } catch { showToast('Failed to save', 'error'); }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this objection handler?')) return;
    try {
      await deleteObjection(id);
      showToast('Objection deleted');
      load();
    } catch { showToast('Failed to delete', 'error'); }
  };

  const handleEdit = (obj) => {
    setForm({
      objection_text: obj.objection_text,
      response_text: obj.response_text || '',
      agent_slug: obj.agent_slug || '',
    });
    setShowForm(true);
  };

  return (
    <div className="flex flex-col h-full gap-4">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-xl font-bold text-white">Objection Handlers</h2>
          <p className="text-sm text-slate-400">Define how the AI should respond to common objections</p>
        </div>
        <button onClick={() => { setForm({ objection_text: '', response_text: '', agent_slug: '' }); setShowForm(true); }}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 rounded-lg text-sm font-medium text-white">
          <Plus size={16} /> Add Objection
        </button>
      </div>

      {toast && <Toast toast={toast} />}

      {/* Filter */}
      <div className="flex items-center gap-3">
        <div className="relative">
          <select value={filterSlug} onChange={(e) => setFilterSlug(e.target.value)}
            className="appearance-none bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 pr-8 text-sm text-white focus:outline-none focus:border-indigo-500">
            <option value="">All Agents</option>
            {agents.map(a => <option key={a.slug} value={a.slug}>{a.slug}</option>)}
          </select>
          <ChevronDown size={14} className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
        </div>
        <span className="text-xs text-slate-500">{objections.length} objection{objections.length !== 1 ? 's' : ''}</span>
      </div>

      {/* Objections list */}
      <div className="flex-1 overflow-y-auto space-y-2">
        {loading ? (
          <div className="text-slate-500 text-sm text-center py-8">Loading...</div>
        ) : objections.length === 0 ? (
          <div className="text-slate-500 text-sm text-center py-8">
            No objection handlers yet. Add one to help the AI handle pushback.
          </div>
        ) : (
          objections.map(obj => (
            <div key={obj.id} className="bg-slate-900 border border-slate-800 rounded-lg p-4 hover:border-slate-600 transition-colors">
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <Shield size={14} className="text-amber-400 flex-shrink-0" />
                    <span className="text-sm font-medium text-white">{obj.objection_text}</span>
                    {obj.frequency > 0 && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300">
                        {obj.frequency}x
                      </span>
                    )}
                  </div>
                  {obj.response_text && (
                    <p className="text-xs text-slate-400 mt-1 ml-5">
                      <span className="text-emerald-400 font-medium">Response: </span>{obj.response_text}
                    </p>
                  )}
                  {obj.agent_slug && (
                    <p className="text-[10px] text-slate-500 mt-1 ml-5">Agent: {obj.agent_slug}</p>
                  )}
                </div>
                <div className="flex gap-1 flex-shrink-0">
                  <button onClick={() => handleEdit(obj)} className="p-1 rounded hover:bg-slate-700 text-slate-400 hover:text-indigo-400">
                    <Save size={13} />
                  </button>
                  <button onClick={() => handleDelete(obj.id)} className="p-1 rounded hover:bg-slate-700 text-slate-400 hover:text-red-400">
                    <Trash2 size={13} />
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Form modal */}
      {showForm && (
        <Modal title="Objection Handler" onClose={() => setShowForm(false)}>
          <div className="space-y-4">
            <Field label="Objection Text" required>
              <input value={form.objection_text} onChange={(e) => setForm(f => ({ ...f, objection_text: e.target.value }))}
                placeholder="e.g. I am not interested" className={inputClass} />
            </Field>
            <Field label="Suggested Response">
              <textarea value={form.response_text} onChange={(e) => setForm(f => ({ ...f, response_text: e.target.value }))}
                rows={4} placeholder="How should the AI respond to this objection?" className={inputClass} />
            </Field>
            <Field label="Agent (optional)">
              <div className="relative">
                <select value={form.agent_slug} onChange={(e) => setForm(f => ({ ...f, agent_slug: e.target.value }))}
                  className={`${inputClass} appearance-none pr-8`}>
                  <option value="">All agents</option>
                  {agents.map(a => <option key={a.slug} value={a.slug}>{a.slug}</option>)}
                </select>
                <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
              </div>
            </Field>
            <div className="flex justify-end gap-2 pt-2">
              <button onClick={() => setShowForm(false)} className={btnSecondary}>Cancel</button>
              <button onClick={handleSave} className={btnPrimary}>Save</button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}

// --- Shared components ---
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
