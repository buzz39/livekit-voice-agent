import React, { useRef, useEffect } from 'react';
import { Terminal as TerminalIcon } from 'lucide-react';

const getEmptyStateMessage = (status) => {
  if (status === 'connecting') {
    return 'Connecting the call and waiting for the first transcript...';
  }

  if (status === 'active') {
    return 'The call is live. New transcript lines will appear here automatically.';
  }

  return 'No active call yet. Start an outbound call to see the live transcript.';
};

const Terminal = ({ logs = [], status = 'idle' }) => {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden flex flex-col h-full shadow-lg shadow-black/50">
      <div className="bg-slate-950 p-2 border-b border-slate-800 flex items-center justify-between px-4">
        <div className="flex items-center gap-2 text-slate-400">
          <TerminalIcon size={16} />
          <span className="text-xs font-mono font-bold uppercase tracking-wider">Live Transcript</span>
        </div>
        <div className="flex gap-1.5">
          <div className="w-3 h-3 rounded-full bg-red-500/20 border border-red-500/50"></div>
          <div className="w-3 h-3 rounded-full bg-yellow-500/20 border border-yellow-500/50"></div>
          <div className="w-3 h-3 rounded-full bg-green-500/20 border border-green-500/50"></div>
        </div>
      </div>

      <div className="flex-1 p-4 overflow-y-auto font-mono text-sm space-y-3 bg-black/50">
        {logs.length === 0 ? (
            <div className="text-slate-600 italic text-center mt-10">{getEmptyStateMessage(status)}</div>
        ) : (
            logs.map((log, index) => (
            <div key={index} className="flex gap-4 animate-in fade-in slide-in-from-bottom-2 duration-300">
                <div className={`min-w-[80px] text-xs uppercase tracking-wider font-bold ${log.role === 'agent' ? 'text-indigo-400' : 'text-emerald-400'}`}>
                {log.timestamp} {log.role === 'agent' ? 'AGENT' : 'USER'}
                </div>
                <div className="text-slate-300">
                <span className={log.role === 'agent' ? 'text-indigo-200' : 'text-emerald-200'}>&gt;</span> {log.text}
                </div>
            </div>
            ))
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
};

export default Terminal;
