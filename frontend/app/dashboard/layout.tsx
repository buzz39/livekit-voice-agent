'use client';

import { Sidebar } from '@/components/Sidebar';
// import { UserButton, useUser } from '@stackframe/stack';

export default function DashboardLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    // const user = useUser({ or: 'redirect' });
    const user = { displayName: 'Dev User' };

    return (
        <div className="flex h-screen overflow-hidden bg-zinc-50 dark:bg-zinc-950">
            <Sidebar />
            <div className="flex flex-1 flex-col overflow-hidden">
                <header className="flex h-16 shrink-0 items-center justify-between border-b bg-white px-6 dark:bg-black dark:border-zinc-800">
                    <h2 className="text-lg font-semibold text-zinc-900 dark:text-white">Dashboard</h2>
                    <div className="flex items-center gap-4">
                        <span className="text-sm text-zinc-500 dark:text-zinc-400">
                            {user ? `Hello, ${user.displayName || 'User'}` : ''}
                        </span>
                        {/* <UserButton /> */}
                    </div>
                </header>
                <main className="flex-1 overflow-y-auto p-6">
                    {children}
                </main>
            </div>
        </div>
    );
}
