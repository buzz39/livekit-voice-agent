'use client';

import { useState } from 'react';
import { updateAgent, triggerOutboundCall } from '@/utils/actions';
import { Save, Loader2, Plus, Trash2, Phone } from 'lucide-react';
import WebhookManager from './WebhookManager';

export default function AgentEditor({ agent, slug }: { agent: any, slug: string }) {
    const [activeTab, setActiveTab] = useState('general');
    const [isSaving, setIsSaving] = useState(false);
    const [showCallModal, setShowCallModal] = useState(false);
    const [testPhoneNumber, setTestPhoneNumber] = useState('');
    const [isCalling, setIsCalling] = useState(false);

    // Local state for form
    const [formData, setFormData] = useState({
        opening_line: agent.opening_line || '',
        mcp_endpoint_url: agent.mcp_endpoint_url || '',
        prompt: agent.prompt || '',
        ai_config: {
            llm_model: agent.ai_config?.llm_model || 'gpt-4o-mini',
            stt_model: agent.ai_config?.stt_model || 'nova-3',
            tts_voice: agent.ai_config?.tts_voice || 'a0e99841-438c-4a64-b679-ae501e7d6091',
            tts_speed: agent.ai_config?.tts_speed || 1.0
        },
        data_schema: agent.data_schema || []
    });

    const handleSave = async () => {
        setIsSaving(true);
        try {
            await updateAgent(slug, formData);
            // show toast ideally
        } catch (e) {
            console.error(e);
            alert("Failed to save");
        } finally {
            setIsSaving(false);
        }
    };

    const handleTestCall = async () => {
        setIsCalling(true);
        try {
            await triggerOutboundCall(testPhoneNumber, slug);
            setShowCallModal(false);
            alert(`Call initiated to ${testPhoneNumber}`);
        } catch (e) {
            console.error(e);
            alert("Failed to initiate call");
        } finally {
            setIsCalling(false);
        }
    };

    const tabs = [
        { id: 'general', label: 'General' },
        { id: 'ai', label: 'Voice & AI' },
        { id: 'instructions', label: 'Instructions' },
        { id: 'schema', label: 'Data Schema' },
        { id: 'webhooks', label: 'Webhooks' },
    ];

    return (
        <div className="flex flex-col h-full bg-white dark:bg-zinc-900 rounded-lg shadow-sm border dark:border-zinc-800 overflow-hidden">
            {/* Header/Tabs */}
            <div className="flex items-center justify-between border-b px-6 py-3 dark:border-zinc-800">
                <div className="flex space-x-6">
                    {tabs.map(tab => (
                        <button
                            key={tab.id}
                            onClick={() => setActiveTab(tab.id)}
                            className={`pb-3 text-sm font-medium transition-colors border-b-2 ${activeTab === tab.id
                                ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                                : 'border-transparent text-zinc-500 hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-zinc-300'
                                }`}
                        >
                            {tab.label}
                        </button>
                    ))}
                </div>
                <button
                    onClick={handleSave}
                    disabled={isSaving}
                    className="flex items-center gap-2 rounded-md bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-800 disabled:opacity-50 dark:bg-white dark:text-black dark:hover:bg-zinc-200"
                >
                    {isSaving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                    Save Changes
                </button>
                <button
                    onClick={() => setShowCallModal(true)}
                    className="flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 dark:bg-blue-600 dark:hover:bg-blue-500"
                >
                    <Phone className="h-4 w-4" />
                    Test Call
                </button>
            </div>

            {/* Content Area */}
            <div className="flex-1 overflow-y-auto p-6">
                {activeTab === 'general' && (
                    <div className="space-y-4 max-w-2xl">
                        <div>
                            <label className="block text-sm font-medium text-zinc-700 dark:text-zinc-300">Opening Line</label>
                            <textarea
                                className="mt-1 w-full rounded-md border border-zinc-300 p-2 text-sm dark:border-zinc-700 dark:bg-zinc-800"
                                rows={3}
                                value={formData.opening_line}
                                onChange={e => setFormData({ ...formData, opening_line: e.target.value })}
                            />
                            <p className="mt-1 text-xs text-zinc-500">The first sentence the agent will say when the call connects.</p>
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-zinc-700 dark:text-zinc-300">MCP Endpoint URL</label>
                            <input
                                type="url"
                                className="mt-1 w-full rounded-md border border-zinc-300 p-2 text-sm dark:border-zinc-700 dark:bg-zinc-800"
                                value={formData.mcp_endpoint_url}
                                onChange={e => setFormData({ ...formData, mcp_endpoint_url: e.target.value })}
                                placeholder="https://your-n8n-instance.com/webhook/..."
                            />
                        </div>
                    </div>
                )}

                {activeTab === 'ai' && (
                    <div className="space-y-4 max-w-2xl">
                        <div>
                            <label className="block text-sm font-medium text-zinc-700 dark:text-zinc-300">LLM Model</label>
                            <select
                                className="mt-1 w-full rounded-md border border-zinc-300 p-2 text-sm dark:border-zinc-700 dark:bg-zinc-800"
                                value={formData.ai_config.llm_model}
                                onChange={e => setFormData({ ...formData, ai_config: { ...formData.ai_config, llm_model: e.target.value } })}
                            >
                                <option value="gpt-4o-mini">GPT-4o Mini</option>
                                <option value="gpt-4o">GPT-4o</option>
                            </select>
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-zinc-700 dark:text-zinc-300">Voice ID (Cartesia)</label>
                            <input
                                className="mt-1 w-full rounded-md border border-zinc-300 p-2 text-sm dark:border-zinc-700 dark:bg-zinc-800"
                                value={formData.ai_config.tts_voice}
                                onChange={e => setFormData({ ...formData, ai_config: { ...formData.ai_config, tts_voice: e.target.value } })}
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-zinc-700 dark:text-zinc-300">Speed (0.5 - 2.0)</label>
                            <input
                                type="number"
                                step="0.1"
                                className="mt-1 w-full rounded-md border border-zinc-300 p-2 text-sm dark:border-zinc-700 dark:bg-zinc-800"
                                value={formData.ai_config.tts_speed}
                                onChange={e => setFormData({ ...formData, ai_config: { ...formData.ai_config, tts_speed: parseFloat(e.target.value) } })}
                            />
                        </div>
                    </div>
                )}

                {activeTab === 'instructions' && (
                    <div className="h-full flex flex-col">
                        <label className="block text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-2">System Prompt / Instructions</label>
                        <textarea
                            className="flex-1 w-full rounded-md border border-zinc-300 p-4 font-mono text-sm dark:border-zinc-700 dark:bg-zinc-800"
                            value={formData.prompt}
                            onChange={e => setFormData({ ...formData, prompt: e.target.value })}
                        />
                    </div>
                )}

                {activeTab === 'schema' && (
                    <div className="space-y-4 max-w-3xl">
                        <div className="flex justify-between items-center">
                            <h3 className="text-sm font-medium">Data Collection Fields</h3>
                            <button
                                onClick={() => setFormData({
                                    ...formData,
                                    data_schema: [...formData.data_schema, { field_name: '', description: '', field_type: 'string' }]
                                })}
                                className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-700"
                            >
                                <Plus className="h-3 w-3" /> Add Field
                            </button>
                        </div>

                        {formData.data_schema.map((field: any, idx: number) => (
                            <div key={idx} className="flex gap-2 items-start p-3 bg-zinc-50 rounded-md border dark:bg-zinc-800/50 dark:border-zinc-700">
                                <div className="flex-1 space-y-2">
                                    <input
                                        className="w-full rounded border p-1 text-xs dark:bg-zinc-900"
                                        placeholder="Field Name (e.g. email)"
                                        value={field.field_name}
                                        onChange={e => {
                                            const newSchema = [...formData.data_schema];
                                            newSchema[idx].field_name = e.target.value;
                                            setFormData({ ...formData, data_schema: newSchema });
                                        }}
                                    />
                                    <input
                                        className="w-full rounded border p-1 text-xs dark:bg-zinc-900"
                                        placeholder="Description (e.g. The user's email address)"
                                        value={field.description}
                                        onChange={e => {
                                            const newSchema = [...formData.data_schema];
                                            newSchema[idx].description = e.target.value;
                                            setFormData({ ...formData, data_schema: newSchema });
                                        }}
                                    />
                                </div>
                                <button
                                    onClick={() => {
                                        const newSchema = formData.data_schema.filter((_: any, i: number) => i !== idx);
                                        setFormData({ ...formData, data_schema: newSchema });
                                    }}
                                    className="p-1 text-zinc-400 hover:text-red-500"
                                >
                                    <Trash2 className="h-4 w-4" />
                                </button>
                            </div>
                        ))}
                    </div>
                )}

                {activeTab === 'webhooks' && (
                    <WebhookManager webhooks={agent.webhooks || []} slug={slug} />
                )}
            </div>
            {/* Test Call Modal */}
            {showCallModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
                    <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-lg dark:bg-zinc-900">
                        <h3 className="text-lg font-medium text-zinc-900 dark:text-white">Test Call</h3>
                        <p className="mt-1 text-sm text-zinc-500">Enter a phone number to test this agent.</p>

                        <div className="mt-4 space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-zinc-700 dark:text-zinc-300">Phone Number</label>
                                <input
                                    type="tel"
                                    className="mt-1 w-full rounded-md border border-zinc-300 p-2 text-sm dark:border-zinc-700 dark:bg-zinc-800"
                                    placeholder="+15550001234"
                                    value={testPhoneNumber}
                                    onChange={(e) => setTestPhoneNumber(e.target.value)}
                                />
                            </div>

                            <div className="flex justify-end gap-3">
                                <button
                                    onClick={() => setShowCallModal(false)}
                                    className="rounded-md px-4 py-2 text-sm font-medium text-zinc-600 hover:bg-zinc-100 dark:text-zinc-300 dark:hover:bg-zinc-800"
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={handleTestCall}
                                    disabled={isCalling || !testPhoneNumber}
                                    className="flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                                >
                                    {isCalling ? <Loader2 className="h-4 w-4 animate-spin" /> : <Phone className="h-4 w-4" />}
                                    Call Now
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
