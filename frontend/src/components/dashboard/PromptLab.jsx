import React, { useState, useEffect, useCallback } from 'react';
import {
  Plus, Save, Trash2, Copy, Search, Phone, X, ChevronDown,
  CheckCircle, AlertCircle, FileText, Tag, Zap,
} from 'lucide-react';
import {
  getAllPrompts, getPromptById, createPrompt, patchPrompt,
  deletePrompt, clonePrompt, getIndustries, startTestCall,
} from '../../api';

const INDUSTRY_COLORS = {
  roofing: 'bg-orange-500/20 text-orange-300 border-orange-500/30',
  solar: 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30',
  hvac: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30',
  insurance: 'bg-blue-500/20 text-blue-300 border-blue-500/30',
  realestate: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
  healthcare: 'bg-rose-500/20 text-rose-300 border-rose-500/30',
  fintech: 'bg-violet-500/20 text-violet-300 border-violet-500/30',
  general: 'bg-slate-500/20 text-slate-300 border-slate-500/30',
};

function industryBadgeClass(industry) {
  return INDUSTRY_COLORS[industry?.toLowerCase()] || INDUSTRY_COLORS.general;
}

export default function PromptLab() {
  // --- State ---
  const [prompts, setPrompts] = useState([]);
  const [industries, setIndustries] = useState([]);
  const [filterIndustry, setFilterIndustry] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);

  // Editor state
  const [editing, setEditing] = useState(null); // full prompt object or null
  const [editorDirty, setEditorDirty] = useState(false);

  // Create modal
  const [showCreate, setShowCreate] = useState(false);
  const [newPrompt, setNewPrompt] = useState({ name: '', content: '', industry: 'general', description: '' });

  // Clone modal
  const [cloneSource, setCloneSource] = useState(null);
  const [cloneData, setCloneData] = useState({ new_name: '', new_industry: '' });

  // Test call modal
  const [testTarget, setTestTarget] = useState(null);
  const [testPhone, setTestPhone] = useState('');
  const [testFrom, setTestFrom] = useState('');

  // Feedback
  const [toast, setToast] = useState(null);

  const showToast = (msg, type = 'success') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3000);
  };

  // --- Data loading ---
  const loadData = useCallback(async () => {
    setLoading(true);
    const [promptsList, industryList] = await Promise.all([
      getAllPrompts(filterIndustry || undefined),
      getIndustries(),
    ]);
    setPrompts(promptsList || []);
    setIndustries(industryList || []);
    setLoading(false);
  }, [filterIndustry]);

  useEffect(() => { loadData(); }, [loadData]);

  const filteredPrompts = prompts.filter(p => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      p.name?.toLowerCase().includes(q) ||
      p.description?.toLowerCase().includes(q) ||
      p.industry?.toLowerCase().includes(q)
    );
  });

  // --- Handlers ---
  const handleSelect = async (prompt) => {
    const full = await getPromptById(prompt.id);
    if (full) {
      setEditing(full);
      setEditorDirty(false);
    }
  };

  const handleEditorChange = (field, value) => {
    setEditing(prev => ({ ...prev, [field]: value }));
    setEditorDirty(true);
  };

  const handleSave = async () => {
    if (!editing) return;
    try {
      await patchPrompt(editing.id, {
        name: editing.name,
        content: editing.content,
        industry: editing.industry,
        description: editing.description,
        is_active: editing.is_active,
      });
      setEditorDirty(false);
      showToast('Prompt saved');
      loadData();
    } catch {
      showToast('Failed to save', 'error');
    }
  };

  const handleCreate = async () => {
    if (!newPrompt.name.trim() || !newPrompt.content.trim()) {
      showToast('Name and content are required', 'error');
      return;
    }
    try {
      await createPrompt(newPrompt);
      setShowCreate(false);
      setNewPrompt({ name: '', content: '', industry: 'general', description: '' });
      showToast('Prompt created');
      loadData();
    } catch {
      showToast('Failed to create', 'error');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this prompt?')) return;
    try {
      await deletePrompt(id);
      if (editing?.id === id) setEditing(null);
      showToast('Prompt deleted');
      loadData();
    } catch {
      showToast('Failed to delete', 'error');
    }
  };

  const handleClone = async () => {
    if (!cloneSource || !cloneData.new_name.trim()) return;
    try {
      await clonePrompt(cloneSource.id, cloneData.new_name, cloneData.new_industry || cloneSource.industry);
      setCloneSource(null);
      setCloneData({ new_name: '', new_industry: '' });
      showToast('Prompt cloned');
      loadData();
    } catch {
      showToast('Failed to clone', 'error');
    }
  };

  const handleTestCall = async () => {
    if (!testTarget || !testPhone.trim()) return;
    try {
      await startTestCall({
        phone_number: testPhone,
        prompt_id: testTarget.id,
        from_number: testFrom || null,
      });
      showToast(`Test call queued using "${testTarget.name}"`);
      setTestTarget(null);
      setTestPhone('');
      setTestFrom('');
    } catch (e) {
      showToast(e.message || 'Failed to start test call', 'error');
    }
  };

  const handleToggleActive = async (prompt) => {
    try {
      await patchPrompt(prompt.id, { is_active: !prompt.is_active });
      showToast(prompt.is_active ? 'Prompt deactivated' : 'Prompt activated');
      loadData();
    } catch {
      showToast('Failed to toggle', 'error');
    }
  };

  // --- Render ---
  return (
    <div className="flex flex-col h-full gap-4">
      {/* Toast */}
      {toast && (
        <div className={`fixed top-4 right-4 z-50 flex items-center gap-2 px-4 py-2 rounded-lg text-sm border ${
          toast.type === 'error'
            ? 'bg-red-500/10 border-red-500/30 text-red-300'
            : 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
        }`}>
          {toast.type === 'error' ? <AlertCircle size={14} /> : <CheckCircle size={14} />}
          {toast.msg}
        </div>
      )}

      {/* Header row */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-xl font-bold text-white">Prompt Lab</h2>
          <p className="text-sm text-slate-400">Create, edit and test prompts for any industry</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 rounded-lg text-sm font-medium text-white transition-colors"
        >
          <Plus size={16} /> New Prompt
        </button>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="relative flex-1 min-w-[200px] max-w-xs">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            placeholder="Search prompts..."
            className="w-full bg-slate-900 border border-slate-700 rounded-lg pl-9 pr-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
        <div className="relative">
          <select
            value={filterIndustry}
            onChange={(e) => setFilterIndustry(e.target.value)}
            className="appearance-none bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 pr-8 text-sm text-white focus:outline-none focus:border-indigo-500"
          >
            <option value="">All Industries</option>
            {industries.map(ind => (
              <option key={ind} value={ind}>{ind}</option>
            ))}
          </select>
          <ChevronDown size={14} className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
        </div>
        <span className="text-xs text-slate-500">{filteredPrompts.length} prompt{filteredPrompts.length !== 1 ? 's' : ''}</span>
      </div>

      {/* Main split: list + editor */}
      <div className="flex-1 grid grid-cols-12 gap-4 min-h-0">
        {/* Prompt list */}
        <div className="col-span-12 lg:col-span-4 overflow-y-auto space-y-2 pr-1">
          {loading ? (
            <div className="text-slate-500 text-sm text-center py-8">Loading prompts...</div>
          ) : filteredPrompts.length === 0 ? (
            <div className="text-slate-500 text-sm text-center py-8">
              No prompts found. Create one to get started.
            </div>
          ) : (
            filteredPrompts.map(p => (
              <div
                key={p.id}
                onClick={() => handleSelect(p)}
                className={`group p-3 rounded-lg border cursor-pointer transition-colors ${
                  editing?.id === p.id
                    ? 'bg-indigo-500/10 border-indigo-500/40'
                    : 'bg-slate-900 border-slate-800 hover:border-slate-600'
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 min-w-0">
                    <FileText size={14} className="text-slate-400 flex-shrink-0" />
                    <span className="text-sm font-medium text-white truncate">{p.name}</span>
                  </div>
                  <div className="flex items-center gap-1 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={(e) => { e.stopPropagation(); setTestTarget(p); }}
                      title="Test call"
                      className="p-1 rounded hover:bg-slate-700 text-slate-400 hover:text-emerald-400"
                    >
                      <Phone size={13} />
                    </button>
                    <button
                      onClick={(e) => { e.stopPropagation(); setCloneSource(p); }}
                      title="Clone"
                      className="p-1 rounded hover:bg-slate-700 text-slate-400 hover:text-indigo-400"
                    >
                      <Copy size={13} />
                    </button>
                    <button
                      onClick={(e) => { e.stopPropagation(); handleDelete(p.id); }}
                      title="Delete"
                      className="p-1 rounded hover:bg-slate-700 text-slate-400 hover:text-red-400"
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                </div>
                <div className="mt-1.5 flex items-center gap-2">
                  <span className={`text-[10px] px-1.5 py-0.5 rounded border ${industryBadgeClass(p.industry)}`}>
                    {p.industry || 'general'}
                  </span>
                  {!p.is_active && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded border bg-slate-700/50 text-slate-400 border-slate-600">
                      inactive
                    </span>
                  )}
                </div>
                {p.description && (
                  <p className="mt-1 text-xs text-slate-500 truncate">{p.description}</p>
                )}
              </div>
            ))
          )}
        </div>

        {/* Editor panel */}
        <div className="col-span-12 lg:col-span-8 flex flex-col bg-slate-900 border border-slate-800 rounded-lg overflow-hidden">
          {editing ? (
            <>
              {/* Editor header */}
              <div className="flex items-center justify-between px-5 py-3 border-b border-slate-800 flex-shrink-0">
                <div className="flex items-center gap-3 min-w-0">
                  <input
                    value={editing.name}
                    onChange={(e) => handleEditorChange('name', e.target.value)}
                    className="bg-transparent text-white font-semibold text-lg border-none focus:outline-none focus:ring-0 min-w-0 w-auto"
                    style={{ width: `${Math.max(editing.name.length, 10)}ch` }}
                  />
                  <span className={`text-[10px] px-1.5 py-0.5 rounded border ${industryBadgeClass(editing.industry)}`}>
                    {editing.industry}
                  </span>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <button
                    onClick={() => handleToggleActive(editing)}
                    className={`px-2 py-1 rounded text-xs font-medium ${
                      editing.is_active
                        ? 'bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30'
                        : 'bg-slate-700 text-slate-400 hover:bg-slate-600'
                    }`}
                  >
                    {editing.is_active ? 'Active' : 'Inactive'}
                  </button>
                  <button
                    onClick={() => setTestTarget(editing)}
                    className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium bg-emerald-600 hover:bg-emerald-700 text-white transition-colors"
                  >
                    <Zap size={12} /> Test Call
                  </button>
                  <button
                    onClick={handleSave}
                    disabled={!editorDirty}
                    className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium bg-indigo-600 hover:bg-indigo-700 disabled:opacity-40 text-white transition-colors"
                  >
                    <Save size={12} /> Save
                  </button>
                </div>
              </div>

              {/* Meta row */}
              <div className="flex items-center gap-4 px-5 py-2 border-b border-slate-800/50 flex-shrink-0">
                <div className="flex items-center gap-1">
                  <Tag size={12} className="text-slate-500" />
                  <select
                    value={editing.industry || 'general'}
                    onChange={(e) => handleEditorChange('industry', e.target.value)}
                    className="bg-transparent text-xs text-slate-300 border-none focus:outline-none cursor-pointer"
                  >
                    {[...new Set([...industries, editing.industry || 'general', 'general'])].sort().map(ind => (
                      <option key={ind} value={ind}>{ind}</option>
                    ))}
                    <option value="__new">+ New industry...</option>
                  </select>
                </div>
                <input
                  value={editing.description || ''}
                  onChange={(e) => handleEditorChange('description', e.target.value)}
                  placeholder="Short description..."
                  className="flex-1 bg-transparent text-xs text-slate-400 border-none focus:outline-none focus:text-slate-200 placeholder-slate-600"
                />
              </div>

              {/* Content editor */}
              <div className="flex-1 min-h-0">
                <textarea
                  value={editing.content || ''}
                  onChange={(e) => handleEditorChange('content', e.target.value)}
                  className="w-full h-full bg-slate-950 text-slate-200 p-5 font-mono text-sm resize-none focus:outline-none border-none"
                  placeholder="Write your system prompt here..."
                />
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center text-slate-500 text-sm">
              <div className="text-center">
                <FileText size={32} className="mx-auto mb-3 text-slate-600" />
                <p>Select a prompt to edit, or create a new one</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ====== MODALS ====== */}

      {/* Create Prompt Modal */}
      {showCreate && (
        <Modal title="Create New Prompt" onClose={() => setShowCreate(false)}>
          <div className="space-y-4">
            <Field label="Name" required>
              <input value={newPrompt.name} onChange={(e) => setNewPrompt(p => ({ ...p, name: e.target.value }))}
                placeholder="e.g. solar_sales_hindi" className={inputClass} />
            </Field>
            <Field label="Industry">
              <input value={newPrompt.industry} onChange={(e) => setNewPrompt(p => ({ ...p, industry: e.target.value }))}
                placeholder="e.g. solar" className={inputClass} list="industry-list" />
              <datalist id="industry-list">
                {industries.map(i => <option key={i} value={i} />)}
              </datalist>
            </Field>
            <Field label="Description">
              <input value={newPrompt.description} onChange={(e) => setNewPrompt(p => ({ ...p, description: e.target.value }))}
                placeholder="Brief description" className={inputClass} />
            </Field>
            <Field label="Prompt Content" required>
              <textarea value={newPrompt.content} onChange={(e) => setNewPrompt(p => ({ ...p, content: e.target.value }))}
                rows={10} placeholder="You are an AI sales agent for..." className={`${inputClass} font-mono`} />
            </Field>
            <div className="flex justify-end gap-2 pt-2">
              <button onClick={() => setShowCreate(false)} className={btnSecondary}>Cancel</button>
              <button onClick={handleCreate} className={btnPrimary}>Create Prompt</button>
            </div>
          </div>
        </Modal>
      )}

      {/* Clone Prompt Modal */}
      {cloneSource && (
        <Modal title={`Clone "${cloneSource.name}"`} onClose={() => setCloneSource(null)}>
          <div className="space-y-4">
            <Field label="New Name" required>
              <input value={cloneData.new_name} onChange={(e) => setCloneData(d => ({ ...d, new_name: e.target.value }))}
                placeholder="e.g. hvac_sales_agent" className={inputClass} />
            </Field>
            <Field label="Industry">
              <input value={cloneData.new_industry} onChange={(e) => setCloneData(d => ({ ...d, new_industry: e.target.value }))}
                placeholder={cloneSource.industry || 'general'} className={inputClass} list="industry-list-clone" />
              <datalist id="industry-list-clone">
                {industries.map(i => <option key={i} value={i} />)}
              </datalist>
            </Field>
            <div className="flex justify-end gap-2 pt-2">
              <button onClick={() => setCloneSource(null)} className={btnSecondary}>Cancel</button>
              <button onClick={handleClone} className={btnPrimary}>Clone</button>
            </div>
          </div>
        </Modal>
      )}

      {/* Test Call Modal */}
      {testTarget && (
        <Modal title={`Test Call — ${testTarget.name}`} onClose={() => setTestTarget(null)}>
          <div className="space-y-4">
            <div className="bg-slate-800 rounded-lg p-3 text-xs text-slate-300">
              <span className={`inline-block px-1.5 py-0.5 rounded border mr-2 ${industryBadgeClass(testTarget.industry)}`}>
                {testTarget.industry || 'general'}
              </span>
              This will trigger an outbound call using the selected prompt.
            </div>
            <Field label="Phone Number (E.164)" required>
              <input value={testPhone} onChange={(e) => setTestPhone(e.target.value)}
                placeholder="+919876543210" className={inputClass} />
            </Field>
            <Field label="From Number (optional)">
              <input value={testFrom} onChange={(e) => setTestFrom(e.target.value)}
                placeholder="+911171366938" className={inputClass} />
            </Field>
            <div className="flex justify-end gap-2 pt-2">
              <button onClick={() => setTestTarget(null)} className={btnSecondary}>Cancel</button>
              <button onClick={handleTestCall} disabled={!testPhone.trim()}
                className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-40 rounded-lg text-sm font-medium text-white transition-colors">
                <Phone size={14} /> Start Test Call
              </button>
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
