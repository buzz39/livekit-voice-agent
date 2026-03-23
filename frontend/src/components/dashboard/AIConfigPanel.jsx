import React, { useState, useEffect } from 'react';
import {
  Plus, Save, Trash2, Cpu, ChevronDown, X,
  CheckCircle, AlertCircle,
} from 'lucide-react';
import { getAllAiConfigs, upsertAiConfig, deleteAiConfig } from '../../api';

const LLM_PROVIDERS = ['openai', 'groq'];
const STT_PROVIDERS = ['deepgram', 'sarvam'];
const TTS_PROVIDERS = ['openai', 'cartesia', 'deepgram', 'sarvam'];

const defaultForm = {
  name: '',
  llm_provider: 'openai', llm_model: 'gpt-4o-mini', llm_temperature: 0.7,
  stt_provider: 'deepgram', stt_model: 'nova-3', stt_language: 'en-US',
  tts_provider: 'openai', tts_model: 'tts-1', tts_voice: 'alloy', tts_language: '', tts_speed: 1.0,
  vad_silence_threshold: 0.5, vad_sensitivity: 0.5, vad_interruption_threshold: 0.5,
  is_active: true,
};

export default function AIConfigPanel() {
  const [configs, setConfigs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(null);
  const [form, setForm] = useState({ ...defaultForm });
  const [showForm, setShowForm] = useState(false);
  const [toast, setToast] = useState(null);

  const showToast = (msg, type = 'success') => { setToast({ msg, type }); setTimeout(() => setToast(null), 3000); };

  const load = async () => {
    setLoading(true);
    setConfigs(await getAllAiConfigs());
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const handleSelect = (config) => {
    setSelected(config.name);
    setForm({ ...defaultForm, ...config });
    setShowForm(true);
  };

  const handleNew = () => {
    setSelected(null);
    setForm({ ...defaultForm });
    setShowForm(true);
  };

  const handleSave = async () => {
    if (!form.name.trim()) { showToast('Name is required', 'error'); return; }
    try {
      await upsertAiConfig(form);
      showToast('AI config saved');
      setShowForm(false);
      load();
    } catch { showToast('Failed to save', 'error'); }
  };

  const handleDelete = async (name) => {
    if (!window.confirm(`Delete AI config "${name}"?`)) return;
    try {
      await deleteAiConfig(name);
      showToast('AI config deleted');
      if (selected === name) { setSelected(null); setShowForm(false); }
      load();
    } catch { showToast('Failed to delete', 'error'); }
  };

  const f = (field, value) => setForm(prev => ({ ...prev, [field]: value }));

  return (
    <div className="flex flex-col h-full gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white">AI Configurations</h2>
          <p className="text-sm text-slate-400">Manage LLM, STT, TTS and VAD settings for your agents</p>
        </div>
        <button onClick={handleNew} className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 rounded-lg text-sm font-medium text-white">
          <Plus size={16} /> New Config
        </button>
      </div>

      {toast && <Toast toast={toast} />}

      <div className="flex-1 grid grid-cols-12 gap-4 min-h-0">
        {/* Config List */}
        <div className="col-span-12 lg:col-span-4 overflow-y-auto space-y-2 pr-1">
          {loading ? (
            <div className="text-slate-500 text-sm text-center py-8">Loading...</div>
          ) : configs.length === 0 ? (
            <div className="text-slate-500 text-sm text-center py-8">No AI configs found.</div>
          ) : (
            configs.map(c => (
              <div key={c.name} onClick={() => handleSelect(c)}
                className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                  selected === c.name ? 'bg-indigo-500/10 border-indigo-500/40' : 'bg-slate-900 border-slate-800 hover:border-slate-600'
                }`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Cpu size={14} className="text-cyan-400" />
                    <span className="text-sm font-semibold text-white">{c.name}</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className={`text-[10px] px-1.5 py-0.5 rounded ${c.is_active ? 'bg-emerald-500/20 text-emerald-400' : 'bg-slate-700 text-slate-400'}`}>
                      {c.is_active ? 'active' : 'inactive'}
                    </span>
                    <button onClick={(e) => { e.stopPropagation(); handleDelete(c.name); }}
                      className="p-1 rounded hover:bg-slate-700 text-slate-500 hover:text-red-400">
                      <Trash2 size={12} />
                    </button>
                  </div>
                </div>
                <div className="mt-1.5 flex flex-wrap gap-1.5">
                  <Badge label={`LLM: ${c.llm_provider}/${c.llm_model}`} color="indigo" />
                  <Badge label={`TTS: ${c.tts_provider}`} color="cyan" />
                  <Badge label={`STT: ${c.stt_provider}`} color="amber" />
                </div>
              </div>
            ))
          )}
        </div>

        {/* Editor */}
        <div className="col-span-12 lg:col-span-8 bg-slate-900 border border-slate-800 rounded-lg overflow-y-auto">
          {showForm ? (
            <div className="p-5 space-y-5">
              <div className="flex items-center justify-between">
                <h3 className="text-white font-semibold">{selected ? `Edit: ${selected}` : 'New AI Config'}</h3>
                <button onClick={() => setShowForm(false)} className="text-slate-400 hover:text-white p-1"><X size={18} /></button>
              </div>

              <Field label="Config Name" required>
                <input value={form.name} onChange={(e) => f('name', e.target.value)}
                  placeholder="e.g. hindi_groq_sarvam" className={inputClass} disabled={!!selected} />
              </Field>

              {/* LLM Section */}
              <SectionTitle title="LLM (Language Model)" />
              <div className="grid grid-cols-3 gap-3">
                <Field label="Provider">
                  <SelectField value={form.llm_provider} onChange={(v) => f('llm_provider', v)} options={LLM_PROVIDERS} />
                </Field>
                <Field label="Model">
                  <input value={form.llm_model} onChange={(e) => f('llm_model', e.target.value)} className={inputClass} />
                </Field>
                <Field label="Temperature">
                  <input type="number" step="0.1" min="0" max="2" value={form.llm_temperature} onChange={(e) => f('llm_temperature', parseFloat(e.target.value))} className={inputClass} />
                </Field>
              </div>

              {/* STT Section */}
              <SectionTitle title="STT (Speech-to-Text)" />
              <div className="grid grid-cols-3 gap-3">
                <Field label="Provider">
                  <SelectField value={form.stt_provider} onChange={(v) => f('stt_provider', v)} options={STT_PROVIDERS} />
                </Field>
                <Field label="Model">
                  <input value={form.stt_model} onChange={(e) => f('stt_model', e.target.value)} className={inputClass} />
                </Field>
                <Field label="Language">
                  <input value={form.stt_language} onChange={(e) => f('stt_language', e.target.value)} placeholder="en-US" className={inputClass} />
                </Field>
              </div>

              {/* TTS Section */}
              <SectionTitle title="TTS (Text-to-Speech)" />
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                <Field label="Provider">
                  <SelectField value={form.tts_provider} onChange={(v) => f('tts_provider', v)} options={TTS_PROVIDERS} />
                </Field>
                <Field label="Model">
                  <input value={form.tts_model} onChange={(e) => f('tts_model', e.target.value)} className={inputClass} />
                </Field>
                <Field label="Voice">
                  <input value={form.tts_voice} onChange={(e) => f('tts_voice', e.target.value)} className={inputClass} />
                </Field>
                <Field label="Speed">
                  <input type="number" step="0.1" min="0.5" max="2" value={form.tts_speed} onChange={(e) => f('tts_speed', parseFloat(e.target.value))} className={inputClass} />
                </Field>
              </div>

              {/* VAD Section */}
              <SectionTitle title="VAD (Voice Activity Detection)" />
              <div className="grid grid-cols-3 gap-3">
                <Field label="Silence Threshold">
                  <input type="number" step="0.1" min="0" max="1" value={form.vad_silence_threshold} onChange={(e) => f('vad_silence_threshold', parseFloat(e.target.value))} className={inputClass} />
                </Field>
                <Field label="Sensitivity">
                  <input type="number" step="0.1" min="0" max="1" value={form.vad_sensitivity} onChange={(e) => f('vad_sensitivity', parseFloat(e.target.value))} className={inputClass} />
                </Field>
                <Field label="Interruption Threshold">
                  <input type="number" step="0.1" min="0" max="1" value={form.vad_interruption_threshold} onChange={(e) => f('vad_interruption_threshold', parseFloat(e.target.value))} className={inputClass} />
                </Field>
              </div>

              <div className="flex items-center gap-2">
                <input type="checkbox" checked={form.is_active} onChange={(e) => f('is_active', e.target.checked)}
                  className="rounded bg-slate-800 border-slate-600" />
                <label className="text-sm text-slate-300">Active</label>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button onClick={() => setShowForm(false)} className={btnSecondary}>Cancel</button>
                <button onClick={handleSave} className={btnPrimary}><Save size={14} className="inline mr-1" />Save Config</button>
              </div>
            </div>
          ) : (
            <div className="flex-1 flex items-center justify-center text-slate-500 text-sm h-full min-h-[300px]">
              <div className="text-center">
                <Cpu size={32} className="mx-auto mb-3 text-slate-600" />
                <p>Select a config to edit, or create a new one</p>
              </div>
            </div>
          )}
        </div>
      </div>
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

function Field({ label, required, children }) {
  return (
    <div>
      <label className="block text-xs font-medium text-slate-400 mb-1">
        {label} {required && <span className="text-red-400">*</span>}
      </label>
      {children}
    </div>
  );
}

function SelectField({ value, onChange, options }) {
  return (
    <div className="relative">
      <select value={value} onChange={(e) => onChange(e.target.value)}
        className={`${inputClass} appearance-none pr-8`}>
        {options.map(o => <option key={o} value={o}>{o}</option>)}
      </select>
      <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
    </div>
  );
}

function SectionTitle({ title }) {
  return <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider border-b border-slate-800 pb-1">{title}</h4>;
}

function Badge({ label, color }) {
  const colors = {
    indigo: 'bg-indigo-500/20 text-indigo-300',
    cyan: 'bg-cyan-500/20 text-cyan-300',
    amber: 'bg-amber-500/20 text-amber-300',
  };
  return <span className={`text-[10px] px-1.5 py-0.5 rounded ${colors[color] || colors.indigo}`}>{label}</span>;
}
