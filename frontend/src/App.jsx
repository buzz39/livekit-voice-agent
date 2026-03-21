import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useUser, SignIn, SignUp } from '@stackframe/react';
import DashboardLayout from './components/layout/DashboardLayout';
import Terminal from './components/dashboard/Terminal';
import StatsCard from './components/dashboard/StatsCard';
import RiskBadge from './components/dashboard/RiskBadge';
import ActiveCallPanel from './components/dashboard/ActiveCallPanel';
import PromptPanel from './components/dashboard/PromptPanel';
import CallLogs from './components/dashboard/CallLogs';
import Analytics from './components/dashboard/Analytics';
import Calendar from './components/dashboard/Calendar';
import LandingPage from './pages/LandingPage';
import { apiEvents, getStats, getRecentCalls, startOutboundCall } from './api';

// Protected route wrapper
const ProtectedRoute = ({ children }) => {
  const user = useUser();
  if (user === undefined) {
    // Still loading
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-slate-400 text-sm animate-pulse">Loading...</div>
      </div>
    );
  }
  if (!user) {
    return <Navigate to="/sign-in" replace />;
  }
  return children;
};

// Stack Auth sign-in page wrapper
const SignInPage = () => {
  const user = useUser();
  if (user) return <Navigate to="/dashboard" replace />;
  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-white">Welcome back</h1>
          <p className="text-slate-400 text-sm mt-1">Sign in to your Aisha AI account</p>
        </div>
        <SignIn />
      </div>
    </div>
  );
};

// Stack Auth sign-up page wrapper
const SignUpPage = () => {
  const user = useUser();
  if (user) return <Navigate to="/dashboard" replace />;
  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-white">Get started free</h1>
          <p className="text-slate-400 text-sm mt-1">Create your Aisha AI account</p>
        </div>
        <SignUp />
      </div>
    </div>
  );
};

// Main dashboard content
function Dashboard() {
  const [currentView, setCurrentView] = useState('command-center');
  const [callStatus, setCallStatus] = useState('idle');
  const [logs, setLogs] = useState([]);
  const [stats, setStats] = useState(null);
  const [recentCalls, setRecentCalls] = useState([]);
  const [riskLevel, setRiskLevel] = useState('low');
  const [bannerMessage, setBannerMessage] = useState('');

  useEffect(() => {
    let timeoutId;

    const handleApiError = (event) => {
      setBannerMessage(event.detail?.message || 'Something went wrong. Please try again.');
      clearTimeout(timeoutId);
      timeoutId = setTimeout(() => setBannerMessage(''), 5000);
    };

    apiEvents.addEventListener('error', handleApiError);

    return () => {
      clearTimeout(timeoutId);
      apiEvents.removeEventListener('error', handleApiError);
    };
  }, []);

  useEffect(() => {
    async function fetchData() {
      const statsData = await getStats();
      if (statsData) setStats(statsData);

      const callsData = await getRecentCalls();
      if (callsData) setRecentCalls(callsData);
    }
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (callStatus === 'active' || callStatus === 'connecting') {
      const pollCall = async () => {
        const calls = await getRecentCalls(1);
        if (calls && calls.length > 0) {
          const latestCall = calls[0];
          if (latestCall.transcript) {
            try {
              const transcript = typeof latestCall.transcript === 'string'
                ? JSON.parse(latestCall.transcript)
                : latestCall.transcript;
              const newLogs = transcript.map(entry => ({
                role: entry.role,
                text: entry.text,
                timestamp: new Date().toLocaleTimeString([], { hour12: false })
              }));
              setLogs(newLogs);
            } catch (e) {
              console.error("Error parsing transcript", e);
            }
          }
          if (latestCall.interest_level) {
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

  const handleStartCall = async (number, businessName, agentSlug, fromNumber) => {
    setCallStatus('connecting');
    setLogs([{
      role: 'system',
      text: `Initiating call to ${number}${fromNumber ? ` from ${fromNumber}` : ''}...`,
      timestamp: new Date().toLocaleTimeString([], { hour12: false })
    }]);
    try {
      await startOutboundCall(number, businessName, agentSlug, fromNumber);
      setTimeout(() => setCallStatus('active'), 2000);
      setLogs(prev => [...prev, {
        role: 'system',
        text: 'Call queued successfully.',
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
    getRecentCalls().then(setRecentCalls);
    getStats().then(setStats);
  };

  const formatDuration = (seconds) => {
    if (!seconds) return '0s';
    const m = Math.floor(seconds / 60);
    const s = Math.round(seconds % 60);
    return `${m}m ${s}s`;
  };

  return (
    <DashboardLayout activeTab={currentView} onTabChange={setCurrentView}>
      {bannerMessage && (
        <div className="mb-6 rounded-lg border border-amber-500/20 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
          {bannerMessage}
        </div>
      )}

      {currentView === 'command-center' && (
        <div className="grid grid-cols-12 gap-6 h-[calc(100vh-6rem)]">
          <div className="col-span-12 grid grid-cols-1 md:grid-cols-4 gap-6 h-32 md:h-40">
            <StatsCard title="Total Calls" value={stats ? stats.total_calls : "..."} subtext={stats ? "Last 7 days" : "Loading..."} chartColor="#10b981" />
            <StatsCard title="Avg Duration" value={stats ? formatDuration(stats.avg_duration) : "..."} subtext={stats ? "Last 7 days" : "Loading..."} chartColor="#6366f1" />
            <StatsCard title="Emails Captured" value={stats ? stats.emails_captured : "..."} subtext={stats ? "Last 7 days" : "Loading..."} chartColor="#f59e0b" />
            <div className="bg-slate-900 border border-slate-800 rounded-lg p-5 flex flex-col justify-center items-center h-full">
              <div className="text-slate-400 text-sm font-medium uppercase tracking-wider mb-2">Current Risk Level</div>
              <RiskBadge level={riskLevel} />
            </div>
          </div>

          <div className="col-span-12 md:col-span-8 h-full flex flex-col gap-6" style={{ height: 'calc(100% - 11rem)' }}>
            <div className="flex-1 min-h-0">
              <Terminal logs={logs} status={callStatus} />
            </div>
          </div>

          <div className="col-span-12 md:col-span-4 h-full flex flex-col gap-6" style={{ height: 'calc(100% - 11rem)' }}>
            <div className="flex-shrink-0">
              <ActiveCallPanel status={callStatus} onStartCall={handleStartCall} onEndCall={handleEndCall} />
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
                  <div className="text-center text-slate-500 text-sm py-4">No recent calls found.</div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {currentView === 'settings' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 h-[calc(100vh-6rem)]">
          <div className="h-full"><PromptPanel /></div>
          <div className="bg-slate-900 border border-slate-800 rounded-lg p-6 flex items-center justify-center text-slate-500">
            More settings coming soon...
          </div>
        </div>
      )}

      {currentView === 'call-logs' && <CallLogs />}
      {currentView === 'analytics' && <Analytics />}
      {currentView === 'calendar' && <Calendar />}
      {currentView === 'database' && (
        <div className="flex items-center justify-center h-full text-slate-500">Work in progress...</div>
      )}
    </DashboardLayout>
  );
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/sign-in" element={<SignInPage />} />
        <Route path="/sign-up" element={<SignUpPage />} />
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          }
        />
        {/* Redirect unknown routes to landing */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
