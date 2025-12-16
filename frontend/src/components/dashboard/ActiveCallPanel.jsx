import React, { useState } from 'react';
import { Phone, Mic, MicOff, PhoneOff } from 'lucide-react';

const ActiveCallPanel = ({ status, onStartCall, onEndCall }) => {
  const [phoneNumber, setPhoneNumber] = useState('');
  const [businessName, setBusinessName] = useState('');
  const [agentSlug, setAgentSlug] = useState('roofing_agent');

  const isCallActive = status === 'active';

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-6 flex flex-col gap-6 h-full">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-white">Active Call Control</h2>
        <div className={`px-2 py-1 rounded text-xs font-bold uppercase ${isCallActive ? 'bg-emerald-500/20 text-emerald-400 animate-pulse' : 'bg-slate-700 text-slate-400'}`}>
          {isCallActive ? 'Live' : 'Ready'}
        </div>
      </div>

      <div className="flex-1 flex flex-col items-center justify-center gap-6">
        {isCallActive ? (
          <div className="text-center space-y-2">
            <div className="w-24 h-24 rounded-full bg-indigo-500/20 flex items-center justify-center mx-auto relative">
                <div className="absolute inset-0 rounded-full border border-indigo-500/50 animate-ping"></div>
                <Phone className="w-10 h-10 text-indigo-400" />
            </div>
            <div className="text-2xl font-mono text-white mt-4">00:45</div>
            <div className="text-slate-400 text-sm">Connected to +1 (555) 123-4567</div>
          </div>
        ) : (
          <div className="w-full max-w-xs space-y-4">
            <input
              type="tel"
              placeholder="Enter phone number..."
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              value={phoneNumber}
              onChange={(e) => setPhoneNumber(e.target.value)}
            />
            <input
              type="text"
              placeholder="Enter business name..."
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              value={businessName}
              onChange={(e) => setBusinessName(e.target.value)}
            />
            <input
              type="text"
              placeholder="Enter agent slug..."
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              value={agentSlug}
              onChange={(e) => setAgentSlug(e.target.value)}
            />
            <button
              onClick={() => onStartCall(phoneNumber, businessName, agentSlug)}
              className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-3 px-4 rounded-lg flex items-center justify-center gap-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              disabled={!phoneNumber}
            >
              <Phone size={18} />
              Start Outbound Call
            </button>
          </div>
        )}
      </div>

      {isCallActive && (
        <div className="grid grid-cols-2 gap-3">
          <button className="bg-slate-800 hover:bg-slate-700 text-white p-3 rounded-lg flex items-center justify-center gap-2 transition-colors">
            <MicOff size={18} />
            Mute
          </button>
          <button
            onClick={onEndCall}
            className="bg-red-500/10 hover:bg-red-500/20 text-red-500 border border-red-500/20 p-3 rounded-lg flex items-center justify-center gap-2 transition-colors"
          >
            <PhoneOff size={18} />
            End Call
          </button>
        </div>
      )}
    </div>
  );
};

export default ActiveCallPanel;
