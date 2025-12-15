export const dynamic = 'force-dynamic';

import { getAgents, createAgent } from '@/utils/actions';
import Link from 'next/link';
import { Plus, Bot } from 'lucide-react';

export default async function AgentsPage() {
    let agents: any[] = [];
    try {
        agents = await getAgents();
    } catch (e) {
        console.error("Failed to load agents", e);
        // Fallback or empty state
    }

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <h1 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-500 to-purple-500">My Agents</h1>
            </div>

            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                {/* Create New Agent Card */}
                <div className="group relative overflow-hidden rounded-xl border border-dashed border-zinc-300 bg-white p-6 transition-all hover:border-blue-500 dark:border-zinc-700 dark:bg-zinc-900/50">
                    <h3 className="mb-4 text-lg font-medium text-zinc-900 dark:text-white">Create New Agent</h3>
                    <form action={createAgent} className="space-y-3">
                        <input
                            name="name"
                            placeholder="Agent Name"
                            required
                            className="w-full rounded-md border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm outline-none focus:border-blue-500 dark:border-zinc-800 dark:bg-zinc-900 dark:text-white"
                        />
                        <input
                            name="slug"
                            placeholder="Unique Slug (e.g. support-bot)"
                            required
                            className="w-full rounded-md border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm outline-none focus:border-blue-500 dark:border-zinc-800 dark:bg-zinc-900 dark:text-white"
                        />
                        <button type="submit" className="flex w-full items-center justify-center gap-2 rounded-md bg-blue-600 py-2 text-sm font-medium text-white hover:bg-blue-700">
                            <Plus className="h-4 w-4" /> Create Agent
                        </button>
                    </form>
                </div>

                {/* Existing Agents */}
                {agents.map((agent: any) => (
                    <Link
                        key={agent.slug}
                        href={`/dashboard/agents/${agent.slug}`}
                        className="group relative flex flex-col justify-between overflow-hidden rounded-xl border bg-white p-6 shadow-sm transition-all hover:shadow-md dark:border-zinc-800 dark:bg-zinc-900"
                    >
                        <div>
                            <div className="mb-4 inline-flex h-10 w-10 items-center justify-center rounded-lg bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400">
                                <Bot className="h-6 w-6" />
                            </div>
                            <h3 className="text-lg font-semibold text-zinc-900 dark:text-white">{agent.slug}</h3>
                            <p className="mt-1 text-sm text-zinc-500 line-clamp-2 dark:text-zinc-400">
                                {agent.opening_line || "No opening line configured"}
                            </p>
                        </div>
                        <div className="mt-4 flex items-center gap-2 text-xs font-medium text-zinc-500">
                            <span className={`h-2 w-2 rounded-full ${agent.is_active ? 'bg-green-500' : 'bg-red-500'}`}></span>
                            {agent.is_active ? 'Active' : 'Inactive'}
                        </div>
                    </Link>
                ))
                }
            </div >
        </div >
    );
}
