'use client';

import { useState } from 'react';
import { Trash2, Plus, Loader2 } from 'lucide-react';
import { addWebhook, deleteWebhook } from '@/utils/actions';

export default function WebhookManager({ webhooks, slug }: { webhooks: any[], slug: string }) {
    const [localWebhooks, setLocalWebhooks] = useState(webhooks);
    const [isAdding, setIsAdding] = useState(false);
    const [newWebhook, setNewWebhook] = useState({ url: '', event_type: 'call.completed' });

    const handleAdd = async () => {
        if (!newWebhook.url) return;
        setIsAdding(true);
        try {
            const added = await addWebhook(slug, newWebhook.url, newWebhook.event_type);
            setLocalWebhooks([...localWebhooks, added]);
            setNewWebhook({ url: '', event_type: 'call.completed' });
        } catch (e) {
            console.error(e);
            alert("Failed to add webhook");
        } finally {
            setIsAdding(false);
        }
    };

    const handleDelete = async (id: number) => {
        try {
            await deleteWebhook(id);
            setLocalWebhooks(localWebhooks.filter(w => w.id !== id));
        } catch (e) {
            console.error(e);
            alert("Failed to delete webhook");
        }
    };

    return (
        <div className="space-y-6 max-w-3xl">
            <div className="bg-zinc-50 dark:bg-zinc-800/50 p-4 rounded-lg border border-dashed border-zinc-300 dark:border-zinc-700">
                <h4 className="text-sm font-medium mb-3">Add New Webhook</h4>
                <div className="flex gap-3">
                    <select
                        className="rounded-md border border-zinc-300 p-2 text-sm dark:border-zinc-700 dark:bg-zinc-800"
                        value={newWebhook.event_type}
                        onChange={e => setNewWebhook({ ...newWebhook, event_type: e.target.value })}
                    >
                        <option value="call.completed">Call Completed</option>
                        <option value="lead.captured">Lead Captured</option>
                    </select>
                    <input
                        className="flex-1 rounded-md border border-zinc-300 p-2 text-sm dark:border-zinc-700 dark:bg-zinc-800"
                        placeholder="https://api.yourdomain.com/webhook"
                        value={newWebhook.url}
                        onChange={e => setNewWebhook({ ...newWebhook, url: e.target.value })}
                    />
                    <button
                        onClick={handleAdd}
                        disabled={isAdding || !newWebhook.url}
                        className="flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                    >
                        {isAdding ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
                        Add
                    </button>
                </div>
            </div>

            <div className="space-y-2">
                {localWebhooks.map((webhook) => (
                    <div key={webhook.id} className="flex items-center justify-between p-4 bg-white dark:bg-zinc-900 border rounded-lg dark:border-zinc-800">
                        <div>
                            <div className="flex items-center gap-2">
                                <span className="text-sm font-semibold text-zinc-900 dark:text-white">
                                    {webhook.event_type}
                                </span>
                                <span className="px-2 py-0.5 rounded-full bg-green-100 text-green-800 text-xs dark:bg-green-900/30 dark:text-green-400">
                                    Active
                                </span>
                            </div>
                            <p className="text-xs text-zinc-500 font-mono mt-1">{webhook.target_url}</p>
                        </div>
                        <button
                            onClick={() => handleDelete(webhook.id)}
                            className="p-2 text-zinc-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/10 rounded-md transition-colors"
                        >
                            <Trash2 className="h-4 w-4" />
                        </button>
                    </div>
                ))}
                {localWebhooks.length === 0 && (
                    <p className="text-center text-sm text-zinc-500 py-8 italic">No webhooks configured</p>
                )}
            </div>
        </div>
    );
}
