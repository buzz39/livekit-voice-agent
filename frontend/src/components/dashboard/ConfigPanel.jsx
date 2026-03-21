import React, { useState } from 'react';
import { Settings, X, ChevronDown } from 'lucide-react';
import { saveAgentConfig } from '../../api';

const DEFAULT_SYSTEM_PROMPT = `You are {agent_name}, a friendly and professional AI assistant calling on behalf of {company_name}.
You speak in Hinglish (mix of Hindi and English) by default. Adapt to the customer's language preference.

Your goal is to:
1. Greet the lead warmly
2. Ask if it's a good time to talk
3. Understand their needs and qualify the lead
4. Book a callback or next step

Keep it conversational, natural, and never pushy. If they're not interested, thank them politely and end the call.

Opening: "Hello! Main {agent_name} bol rahi hoon, {company_name} se. Kya abhi thodi der baat ho sakti hai?"`;


const ConfigPanel = ({ initialConfig, onClose, onSave }) => {
  const [config, setConfig] = useState({
    company_name: '',
    agent_name: 'Aisha',
    system_prompt: DEFAULT_SYSTEM_PROMPT,
    tts_provider: 'cartesia',
    language: 'hinglish',
    llm_provider: 'openai',
    ...initialConfig,
  });
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState(null);

  const handleChange = (field, value) => {
    setConfig(prev => ({ ...prev, [field]: value }));
    setSaved(false);
  };

  const handleSave = async () => {
    if (!config.company_name.trim()) {
      setError('Company name is required.');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await saveAgentConfig(config);
      setSaved(true);
      if (onSave) onSave(config);
    } catch {
      setError('Failed to save config. Check server connection.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="relative bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 sticky top-0 bg-slate-900 z-10">
          <div className="flex items-center gap-3">
            <Settings className="text-indigo-400" size={20} />
            <h2 className="text-lg font-semibold text-white">Agent Configuration</h2>
          </div>
          {onClose && (
            <button
              onClick={onClose}
              className="text-slate-400 hover:text-white transition-colors rounded-lg p-1"
            >
              <X size={20} />
            </button>
          )}
        </div>

        {/* Body */}
        <div className="px-6 py-5 space-y-5">
          {/* Company Name */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">
              Company Name <span className="text-red-400">*</span>
            </label>
            <input
              type="text"
              placeholder="e.g. Prestige Realty"
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              value={config.company_name}
              onChange={e => handleChange('company_name', e.target.value)}
            />
            <p className="text-xs text-slate-500 mt-1">Used in agent intro: "Hello, I'm calling from {'{company_name}'}"</p>
          </div>

          {/* Agent Name */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">Agent Name</label>
            <input
              type="text"
              placeholder="e.g. Aisha"
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              value={config.agent_name}
              onChange={e => handleChange('agent_name', e.target.value)}
            />
          </div>

          {/* System Prompt */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">System Prompt</label>
            <textarea
              rows={10}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 font-mono text-sm resize-y"
              value={config.system_prompt}
              onChange={e => handleChange('system_prompt', e.target.value)}
            />
            <p className="text-xs text-slate-500 mt-1">
              Use <code className="bg-slate-800 px-1 rounded text-indigo-300">{'{company_name}'}</code> and{' '}
              <code className="bg-slate-800 px-1 rounded text-indigo-300">{'{agent_name}'}</code> as placeholders.
            </p>
          </div>

          {/* LLM Provider */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">LLM Provider</label>
              <div className="relative">
                <select
                  className="w-full appearance-none bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 pr-8"
                  value={config.llm_provider}
                  onChange={e => handleChange('llm_provider', e.target.value)}
                >
                  <option value="openai">OpenAI</option>
                  <option value="groq">Groq</option>
                </select>
                <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
              </div>
            </div>
            {/* Empty div for spacing/alignment, or another option if needed */}
            <div></div>
          </div>

          {/* TTS Provider + Language (side by side) */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">TTS Provider</label>
              <div className="relative">
                <select
                  className="w-full appearance-none bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 pr-8"
                  value={config.tts_provider}
                  onChange={e => handleChange('tts_provider', e.target.value)}
                >
                  <option value="cartesia">Cartesia</option>
                  <option value="sarvam">Sarvam AI</option>
                  <option value="deepgram">Deepgram</option>
                </select>
                <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">Language</label>
              <div className="relative">
                <select
                  className="w-full appearance-none bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 pr-8"
                  value={config.language}
                  onChange={e => handleChange('language', e.target.value)}
                >
                  <option value="hinglish">Hinglish</option>
                  <option value="english">English</option>
                  <option value="hindi">Hindi</option>
                </select>
                <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
              </div>
            </div>
          </div>

          {/* Error */}
          {error && (
            <div className="text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-2">
              {error}
            </div>
          )}

          {/* Success */}
          {saved && (
            <div className="text-sm text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 rounded-lg px-4 py-2">
              ✓ Configuration saved! You can now start the call.
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-slate-800 flex justify-end gap-3 sticky bottom-0 bg-slate-900">
          {onClose && (
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors text-sm"
            >
              Cancel
            </button>
          )}
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-6 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold rounded-lg transition-colors text-sm flex items-center gap-2"
          >
            {saving ? (
              <>
                <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Saving...
              </>
            ) : saved ? (
              '✓ Saved'
            ) : (
              'Save & Start Call'
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export { DEFAULT_SYSTEM_PROMPT };
export default ConfigPanel;
