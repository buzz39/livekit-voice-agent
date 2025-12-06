import { getAgentDetails } from '@/utils/actions';
import AgentEditor from '@/components/agents/AgentEditor';
import { notFound } from 'next/navigation';

export default async function AgentDetailsPage({ params }: { params: Promise<{ slug: string }> }) {
    const { slug } = await params;
    const agent = await getAgentDetails(slug);

    if (!agent) {
        notFound();
    }

    return (
        <div className="flex flex-col h-[calc(100vh-100px)]">
            <div className="mb-6">
                <h1 className="text-2xl font-bold dark:text-white">{agent.slug}</h1>
                <p className="text-sm text-zinc-500 dark:text-zinc-400">Manage configuration, voice, and instructions</p>
            </div>
            <div className="flex-1 min-h-0">
                <AgentEditor agent={agent} slug={slug} />
            </div>
        </div>
    );
}

