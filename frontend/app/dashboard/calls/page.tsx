export const dynamic = 'force-dynamic';

import { getCallLogs } from '@/utils/actions';
import { Clock, Phone, FileText } from 'lucide-react';

export default async function CallsPage() {
    let calls: any[] = [];
    try {
        calls = await getCallLogs();
    } catch (e) {
        console.error("Failed to load call logs", e);
    }

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <h1 className="text-2xl font-bold dark:text-white">Call Logs</h1>
            </div>

            <div className="rounded-xl border bg-white shadow-sm dark:bg-zinc-900 dark:border-zinc-800 overflow-hidden">
                <table className="min-w-full divide-y divide-zinc-200 dark:divide-zinc-800">
                    <thead className="bg-zinc-50 dark:bg-zinc-800/50">
                        <tr>
                            <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-zinc-500 dark:text-zinc-400">Date & Time</th>
                            <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-zinc-500 dark:text-zinc-400">Contact</th>
                            <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-zinc-500 dark:text-zinc-400">Duration</th>
                            <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-zinc-500 dark:text-zinc-400">Status</th>
                            <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-zinc-500 dark:text-zinc-400">Interest</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-zinc-200 bg-white dark:divide-zinc-800 dark:bg-zinc-900">
                        {calls.map((call: any) => (
                            <tr key={call.id} className="hover:bg-zinc-50 dark:hover:bg-zinc-800/50">
                                <td className="whitespace-nowrap px-6 py-4 text-sm text-zinc-500 dark:text-zinc-400">
                                    {new Date(call.created_at).toLocaleString()}
                                </td>
                                <td className="whitespace-nowrap px-6 py-4">
                                    <div className="flex flex-col">
                                        <span className="text-sm font-medium text-zinc-900 dark:text-white">{call.phone_number}</span>
                                        <span className="text-xs text-zinc-500">{call.business_name}</span>
                                    </div>
                                </td>
                                <td className="whitespace-nowrap px-6 py-4 text-sm text-zinc-500 dark:text-zinc-400">
                                    {call.duration_seconds}s
                                </td>
                                <td className="whitespace-nowrap px-6 py-4">
                                    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${call.call_status === 'completed' ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400' :
                                            call.call_status === 'failed' ? 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400' :
                                                'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400'
                                        }`}>
                                        {call.call_status}
                                    </span>
                                </td>
                                <td className="whitespace-nowrap px-6 py-4 text-sm text-zinc-500 dark:text-zinc-400">
                                    {call.interest_level || '-'}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
                {calls.length === 0 && (
                    <div className="p-12 text-center text-zinc-500">
                        No calls found.
                    </div>
                )}
            </div>
        </div>
    );
}
