export default function DashboardPage() {
    return (
        <div className="grid gap-6">
            <div className="rounded-lg border bg-white p-6 shadow-sm dark:bg-zinc-900 dark:border-zinc-800">
                <h3 className="text-lg font-medium text-zinc-900 dark:text-white">Welcome to your Voice Agent Dashboard</h3>
                <p className="mt-2 text-zinc-500 dark:text-zinc-400">
                    Select "Agents" from the sidebar to manage your agents or "Call Logs" to view history.
                </p>
            </div>
        </div>
    );
}
