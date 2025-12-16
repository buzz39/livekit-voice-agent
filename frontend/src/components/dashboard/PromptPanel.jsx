import React, { useState, useEffect } from 'react';
import { Save, AlertCircle, CheckCircle } from 'lucide-react';
import { getActivePrompt, updateActivePrompt, getAllPrompts } from '../../api';

export default function PromptPanel() {
  const [prompt, setPrompt] = useState('');
  const [selectedPromptName, setSelectedPromptName] = useState('default_roofing_agent');
  const [availablePrompts, setAvailablePrompts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState(null); // 'success', 'error'
  const [message, setMessage] = useState('');

  useEffect(() => {
    fetchPrompts();
  }, []);

  useEffect(() => {
    loadPrompt(selectedPromptName);
  }, [selectedPromptName]);

  const fetchPrompts = async () => {
    const prompts = await getAllPrompts();
    if (prompts && prompts.length > 0) {
      setAvailablePrompts(prompts);
      // Optional: Set default selection if current one isn't in list,
      // but we default to 'default_roofing_agent' which should exist.
    }
  };

  const loadPrompt = async (name) => {
    setLoading(true);
    const data = await getActivePrompt(name);
    if (data) {
      setPrompt(data.content);
    } else {
      setPrompt('');
    }
    setLoading(false);
  };

  const handleSave = async () => {
    setSaving(true);
    setStatus(null);
    try {
      await updateActivePrompt(prompt, selectedPromptName);
      setStatus('success');
      setMessage('Prompt updated successfully');
      setTimeout(() => setStatus(null), 3000);
    } catch (error) {
      setStatus('error');
      setMessage('Failed to update prompt');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-6 flex flex-col h-full">
      <div className="flex justify-between items-center mb-4">
        <div className="flex items-center gap-4">
            <h3 className="text-slate-400 text-xs font-bold uppercase tracking-wider">Agent Prompt</h3>
            <select
                value={selectedPromptName}
                onChange={(e) => setSelectedPromptName(e.target.value)}
                className="bg-slate-800 text-slate-200 text-xs border border-slate-700 rounded px-2 py-1 focus:outline-none focus:border-indigo-500"
            >
                {availablePrompts.length > 0 ? (
                    availablePrompts.map((p) => (
                        <option key={p.name} value={p.name}>
                            {p.name}
                        </option>
                    ))
                ) : (
                    <option value="default_roofing_agent">Default</option>
                )}
            </select>
        </div>
        {status && (
          <div className={`text-xs flex items-center gap-1 ${status === 'success' ? 'text-emerald-400' : 'text-red-400'}`}>
            {status === 'success' ? <CheckCircle size={14} /> : <AlertCircle size={14} />}
            {message}
          </div>
        )}
      </div>

      <div className="flex-1 min-h-0 relative">
        {loading ? (
            <div className="flex items-center justify-center h-full text-slate-500 text-sm">Loading...</div>
        ) : (
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              className="w-full h-full bg-slate-800 text-slate-200 p-4 rounded border border-slate-700 focus:outline-none focus:border-indigo-500 font-mono text-sm resize-none"
              placeholder="Enter system prompt..."
            />
        )}
      </div>

      <div className="mt-4 flex justify-end">
        <button
          onClick={handleSave}
          disabled={saving || loading}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium rounded transition-colors"
        >
          {saving ? 'Saving...' : (
             <>
               <Save size={16} />
               Save Changes
             </>
          )}
        </button>
      </div>
    </div>
  );
}
