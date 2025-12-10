'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { LayoutDashboard, Users, Phone, Settings, Database } from 'lucide-react';
import { clsx } from 'clsx';

const navigation = [
    { name: 'Overview', href: '/dashboard', icon: LayoutDashboard },
    { name: 'Agents', href: '/dashboard/agents', icon: Users },
    { name: 'Call Logs', href: '/dashboard/calls', icon: Phone },
    { name: 'Database', href: '/dashboard/database', icon: Database },
    // { name: 'Settings', href: '/dashboard/settings', icon: Settings },
];

export function Sidebar() {
    const pathname = usePathname();

    return (
        <div className="flex h-full w-64 flex-col border-r bg-white dark:bg-black dark:border-zinc-800">
            <div className="flex h-16 shrink-0 items-center px-6 border-b dark:border-zinc-800">
                <h1 className="text-xl font-bold tracking-tight text-zinc-900 dark:text-white">Voice Agent</h1>
            </div>
            <nav className="flex-1 space-y-1 px-4 py-4">
                {navigation.map((item) => {
                    const isActive = pathname === item.href;
                    return (
                        <Link
                            key={item.name}
                            href={item.href}
                            className={clsx(
                                isActive
                                    ? 'bg-zinc-100 text-zinc-900 dark:bg-zinc-800 dark:text-white'
                                    : 'text-zinc-600 hover:bg-zinc-50 hover:text-zinc-900 dark:text-zinc-400 dark:hover:bg-zinc-900 dark:hover:text-white',
                                'group flex items-center rounded-md px-3 py-2 text-sm font-medium transition-colors'
                            )}
                        >
                            <item.icon
                                className={clsx(
                                    isActive ? 'text-zinc-900 dark:text-white' : 'text-zinc-400 group-hover:text-zinc-500 dark:text-zinc-500 dark:group-hover:text-zinc-300',
                                    'mr-3 h-5 w-5 shrink-0'
                                )}
                                aria-hidden="true"
                            />
                            {item.name}
                        </Link>
                    );
                })}
            </nav>
        </div>
    );
}
