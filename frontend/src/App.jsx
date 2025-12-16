import React, { useState, useEffect } from 'react';
import DashboardLayout from './components/layout/DashboardLayout';
import Terminal from './components/dashboard/Terminal';
import StatsCard from './components/dashboard/StatsCard';
import RiskBadge from './components/dashboard/RiskBadge';
import ActiveCallPanel from './components/dashboard/ActiveCallPanel';
import { getStats, getRecentCalls, startOutboundCall } from './api';

function App() {
  const [callStatus, setCallStatus] = useState('idle'); // idle, connecting, active, ended
  const [logs, setLogs] = useState([]);
  const [stats, setStats] = useState(null);
  const [recentCalls, setRecentCalls] = useState([]);
  const [riskLevel, setRiskLevel] = useState('low');

  // Fetch stats and recent calls on mount
  useEffect(() => {
    async function fetchData() {
      const statsData = await getStats();
      if (statsData) setStats(statsData);

      const callsData = await getRecentCalls();
      if (callsData) setRecentCalls(callsData);
    }
    fetchData();
    // Refresh every 30 seconds
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  // Poll for active call updates
  useEffect(() => {
    if (callStatus === 'active' || callStatus === 'connecting') {
        // If we don't have a call ID yet, we might need one.
        // For this demo, let's assume we are watching the *latest* call if we just started one.
        // In a real app, startOutboundCall should return the call ID.
        // Since startOutboundCall returns { data: request.model_dump() }, it doesn't give ID immediately because it's queued.
        // But for the purpose of "Make it work with DB", let's assume we poll the *latest* call from DB
        // and check if it's 'in-progress' or 'queued'.

        const pollCall = async () => {
             const calls = await getRecentCalls(1);
             if (calls && calls.length > 0) {
                 const latestCall = calls[0];
                 // Update logs if we have a transcript
                 if (latestCall.transcript) {
                     try {
                         const transcript = typeof latestCall.transcript === 'string'
                            ? JSON.parse(latestCall.transcript)
                            : latestCall.transcript;

                         // Map transcript to logs format
                         const newLogs = transcript.map(entry => ({
                             role: entry.role,
                             text: entry.text,
                             timestamp: new Date().toLocaleTimeString([], { hour12: false }) // Or use entry timestamp if available
                         }));
                         setLogs(newLogs);
                     } catch (e) {
                         console.error("Error parsing transcript", e);
                     }
                 }

                 if (latestCall.interest_level) {
                     // Map interest level to risk? Or use objection?
                     // Vaani maps risk. Let's map interest level for now.
                     // Hot -> Low Risk, Warm -> Medium, Cold -> High? Or vice versa depending on context (Debt collection: Hot = PTP = Low Risk)
                     if (latestCall.interest_level === 'Hot') setRiskLevel('low');
                     else if (latestCall.interest_level === 'Warm') setRiskLevel('medium');
                     else setRiskLevel('high');
                 }
             }
        };

        const interval = setInterval(pollCall, 2000);
        return () => clearInterval(interval);
    }
  }, [callStatus]);

  const handleStartCall = async (number, businessName, agentSlug) => {
    setCallStatus('connecting');
    setLogs([{
      role: 'system',
      text: `Initiating call to ${number}...`,
      timestamp: new Date().toLocaleTimeString([], { hour12: false })
    }]);

    try {
      await startOutboundCall(number, businessName, agentSlug);
      // Wait a bit then switch to active
      setTimeout(() => setCallStatus('active'), 2000);

      setLogs(prev => [...prev, {
        role: 'system',
        text: `Call queued successfully.`,
        timestamp: new Date().toLocaleTimeString([], { hour12: false })
      }]);
    } catch (error) {
      setCallStatus('idle');
      setLogs(prev => [...prev, {
        role: 'system',
        text: `Error starting call: ${error.message}`,
        timestamp: new Date().toLocaleTimeString([], { hour12: false })
      }]);
    }
  };

  const handleEndCall = () => {
    setCallStatus('idle');
    setLogs(prev => [...prev, {
      role: 'system',
      text: 'Call ended.',
      timestamp: new Date().toLocaleTimeString([], { hour12: false })
    }]);
    // Refresh stats immediately
    getRecentCalls().then(setRecentCalls);
    getStats().then(setStats);
  };

  // Helper to format duration
  const formatDuration = (seconds) => {
      if (!seconds) return '0s';
      const m = Math.floor(seconds / 60);
      const s = Math.round(seconds % 60);
      return `${m}m ${s}s`;
  };

  return (
    <DashboardLayout>
      <div className="grid grid-cols-12 gap-6 h-[calc(100vh-6rem)]">
        {/* Top Row: Stats */}
        <div className="col-span-12 grid grid-cols-1 md:grid-cols-4 gap-6 h-32 md:h-40">
          <StatsCard
            title="Total Calls"
            value={stats ? stats.total_calls : "..."}
            subtext={stats ? "Last 7 days" : "Loading..."}
            chartColor="#10b981"
          />
          <StatsCard
            title="Avg Duration"
            value={stats ? formatDuration(stats.avg_duration) : "..."}
            subtext={stats ? "Last 7 days" : "Loading..."}
            chartColor="#6366f1"
          />
          <StatsCard
            title="Emails Captured"
            value={stats ? stats.emails_captured : "..."}
            subtext={stats ? "Last 7 days" : "Loading..."}
            chartColor="#f59e0b"
          />
          <div className="bg-slate-900 border border-slate-800 rounded-lg p-5 flex flex-col justify-center items-center h-full">
            <div className="text-slate-400 text-sm font-medium uppercase tracking-wider mb-2">Current Risk Level</div>
            <RiskBadge level={riskLevel} />
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
            <div className="flex-shrink-0">
                <ActiveCallPanel
                    status={callStatus}
                    onStartCall={handleStartCall}
                    onEndCall={handleEndCall}
                />
            </div>

            <div className="flex-1 bg-slate-900 border border-slate-800 rounded-lg p-6 overflow-y-auto min-h-0">
                <h3 className="text-slate-400 text-xs font-bold uppercase tracking-wider mb-4">Recent Calls</h3>
                <div className="space-y-4">
                    {recentCalls.map((call) => (
                        <div key={call.id} className="p-3 bg-slate-800 rounded border border-slate-700">
                            <div className="flex justify-between items-start mb-1">
                                <div className="font-medium text-white text-sm">{call.phone_number || 'Unknown'}</div>
                                <div className={`text-xs px-2 py-0.5 rounded ${call.call_status === 'completed' ? 'bg-emerald-900 text-emerald-400' : 'bg-slate-700 text-slate-400'}`}>
                                    {call.call_status}
                                </div>
                            </div>
                            <div className="flex justify-between text-xs text-slate-400">
                                <span>{call.business_name || 'No Business'}</span>
                                <span>{call.duration_seconds ? `${call.duration_seconds}s` : '-'}</span>
                            </div>
                            <div className="text-xs text-slate-500 mt-1">
                                {call.created_at ? new Date(call.created_at).toLocaleString() : ''}
                            </div>
                            {call.recording_url && (
                                <div className="mt-2">
                                    <audio controls src={call.recording_url} className="w-full h-8" />
                                </div>
                            )}
                        </div>
                    ))}
                    {recentCalls.length === 0 && (
                        <div className="text-center text-slate-500 text-sm py-4">
                            No recent calls found.
                        </div>
                    )}
                </div>
            </div>
        </div>
      </div>
    </DashboardLayout>
  );
}

export default App;
