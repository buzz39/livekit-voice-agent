export default function DashboardPage() {
    return (
        <div className="space-y-6">
            <h1 className="text-3xl font-bold dark:text-white">Dashboard Overview</h1>
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                <div className="rounded-lg border bg-white p-6 shadow-sm dark:bg-zinc-900 dark:border-zinc-800">
                    <h3 className="text-lg font-medium text-zinc-900 dark:text-white">Agents</h3>
                    <p className="mt-2 text-zinc-500 dark:text-zinc-400">
                        Create, manage and test your AI Voice Agents.
                    </p>
                    <a href="/dashboard/agents" className="mt-4 inline-block text-sm font-medium text-blue-600 hover:text-blue-500">
                        Manage Agents &rarr;
                    </a>
                </div>
                <div className="rounded-lg border bg-white p-6 shadow-sm dark:bg-zinc-900 dark:border-zinc-800">
                    <h3 className="text-lg font-medium text-zinc-900 dark:text-white">Call Logs</h3>
                    <p className="mt-2 text-zinc-500 dark:text-zinc-400">
                        View transcripts, recordings and analysis of your calls.
                    </p>
                    <a href="/dashboard/calls" className="mt-4 inline-block text-sm font-medium text-blue-600 hover:text-blue-500">
                        View History &rarr;
                    </a>
                </div>
                <div className="rounded-lg border bg-white p-6 shadow-sm dark:bg-zinc-900 dark:border-zinc-800">
                    <h3 className="text-lg font-medium text-zinc-900 dark:text-white">Database</h3>
                    <p className="mt-2 text-zinc-500 dark:text-zinc-400">
                        Directly inspect and modify the underlying database tables.
                    </p>
                    <a href="/dashboard/database" className="mt-4 inline-block text-sm font-medium text-blue-600 hover:text-blue-500">
                        Open Editor &rarr;
                    </a>
                </div>
            </div>
        </div>
    );
}
