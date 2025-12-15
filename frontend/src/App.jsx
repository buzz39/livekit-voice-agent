import React, { useState, useEffect } from 'react';
import DashboardLayout from './components/layout/DashboardLayout';
import Terminal from './components/dashboard/Terminal';
import StatsCard from './components/dashboard/StatsCard';
import RiskBadge from './components/dashboard/RiskBadge';
import ActiveCallPanel from './components/dashboard/ActiveCallPanel';

function App() {
  const [callStatus, setCallStatus] = useState('idle'); // idle, connecting, active, ended
  const [logs, setLogs] = useState([]);

  // Simulation of logs coming in
  useEffect(() => {
    if (callStatus === 'active') {
      const interval = setInterval(() => {
        const newLog = Math.random() > 0.5 ? {
          role: 'agent',
          text: 'This is the AI agent speaking, how can I help you today?',
          timestamp: new Date().toLocaleTimeString([], { hour12: false })
        } : {
          role: 'user',
          text: 'I am calling to discuss my recent payment.',
          timestamp: new Date().toLocaleTimeString([], { hour12: false })
        };

        setLogs(prev => [...prev, newLog]);
      }, 3000);

      return () => clearInterval(interval);
    }
  }, [callStatus]);

  const handleStartCall = (number) => {
    setCallStatus('connecting');
    setTimeout(() => {
      setCallStatus('active');
      setLogs([{
        role: 'system',
        text: `Dialing ${number}...`,
        timestamp: new Date().toLocaleTimeString([], { hour12: false })
      }]);
    }, 1500);
  };

  const handleEndCall = () => {
    setCallStatus('idle');
    setLogs(prev => [...prev, {
      role: 'system',
      text: 'Call ended.',
      timestamp: new Date().toLocaleTimeString([], { hour12: false })
    }]);
  };

  return (
    <DashboardLayout>
      <div className="grid grid-cols-12 gap-6 h-[calc(100vh-6rem)]">
        {/* Top Row: Stats */}
        <div className="col-span-12 grid grid-cols-1 md:grid-cols-4 gap-6 h-32 md:h-40">
          <StatsCard title="Recovery Rate" value="68.4%" subtext="+2.4% vs last week" chartColor="#10b981" />
          <StatsCard title="Avg Call Duration" value="3m 42s" subtext="-12s vs last week" chartColor="#6366f1" />
          <StatsCard title="Active Calls" value="12" subtext="3 agents idle" chartColor="#f59e0b" />
          <div className="bg-slate-900 border border-slate-800 rounded-lg p-5 flex flex-col justify-center items-center h-full">
            <div className="text-slate-400 text-sm font-medium uppercase tracking-wider mb-2">Current Risk Level</div>
            <RiskBadge level="low" />
          </div>
        </div>

        {/* Middle Row: Main Content */}
        <div className="col-span-12 md:col-span-8 h-full flex flex-col gap-6" style={{ height: 'calc(100% - 11rem)' }}>
           {/* Terminal takes up most space */}
           <div className="flex-1 min-h-0">
             <Terminal logs={logs} />
           </div>
        </div>

        {/* Right Column: Controls & Details */}
        <div className="col-span-12 md:col-span-4 h-full flex flex-col gap-6" style={{ height: 'calc(100% - 11rem)' }}>
            <div className="h-1/2">
                <ActiveCallPanel
                    status={callStatus}
                    onStartCall={handleStartCall}
                    onEndCall={handleEndCall}
                />
            </div>

            <div className="h-1/2 bg-slate-900 border border-slate-800 rounded-lg p-6 overflow-y-auto">
                <h3 className="text-slate-400 text-xs font-bold uppercase tracking-wider mb-4">Debtor Profile</h3>
                <div className="space-y-4">
                    <div>
                        <div className="text-xs text-slate-500">Name</div>
                        <div className="font-medium text-white">John Doe</div>
                    </div>
                    <div>
                        <div className="text-xs text-slate-500">Account ID</div>
                        <div className="font-mono text-sm text-slate-300">#8992-3321</div>
                    </div>
                    <div>
                        <div className="text-xs text-slate-500">Total Outstanding</div>
                        <div className="font-bold text-emerald-400">$1,250.00</div>
                    </div>
                    <div>
                        <div className="text-xs text-slate-500">Last Contact</div>
                        <div className="text-sm text-slate-300">2 days ago via Email</div>
                    </div>
                    <div className="pt-2 border-t border-slate-800">
                        <div className="text-xs text-slate-500 mb-2">Tags</div>
                        <div className="flex flex-wrap gap-2">
                            <span className="px-2 py-1 bg-slate-800 rounded text-xs text-slate-300 border border-slate-700">Strategic Defaulter</span>
                            <span className="px-2 py-1 bg-slate-800 rounded text-xs text-slate-300 border border-slate-700">High Net Worth</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
      </div>
    </DashboardLayout>
  );
}

export default App;
