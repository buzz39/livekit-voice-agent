import React, { useMemo, useState } from 'react';
import { Phone, PhoneOff, Settings } from 'lucide-react';
import ConfigPanel from './ConfigPanel';
import { saveAgentConfig } from '../../api';

const AGENT_CONFIG_STORAGE_KEY = 'aisha-agent-config';

const normalizePhoneNumber = (value) => value.replace(/[^\d+]/g, '');

const isValidE164PhoneNumber = (value) => /^\+[1-9]\d{7,14}$/.test(value);

const ActiveCallPanel = ({ status, onStartCall, onEndCall }) => {
  const [phoneNumber, setPhoneNumber] = useState('');
  const [showConfig, setShowConfig] = useState(false);
  const [agentConfig, setAgentConfig] = useState(() => {
    if (typeof window === 'undefined') {
      return null;
    }

    try {
      const savedConfig = window.localStorage.getItem(AGENT_CONFIG_STORAGE_KEY);
      return savedConfig ? JSON.parse(savedConfig) : null;
    } catch (error) {
      console.error('Failed to restore saved agent config:', error);
      return null;
    }
  });
  const [callError, setCallError] = useState('');

  const isCallActive = status === 'active';
  const isConnecting = status === 'connecting';
  const normalizedPhoneNumber = useMemo(() => normalizePhoneNumber(phoneNumber.trim()), [phoneNumber]);
  const hasPhoneNumber = normalizedPhoneNumber.length > 0;
  const phoneError = hasPhoneNumber && !isValidE164PhoneNumber(normalizedPhoneNumber)
    ? 'Use international format, for example +14155552671.'
    : '';

  const handleConfigSaved = (config) => {
    setAgentConfig(config);
    setCallError('');

    if (typeof window !== 'undefined') {
      window.localStorage.setItem(AGENT_CONFIG_STORAGE_KEY, JSON.stringify(config));
    }
  };

  const handleStartCall = async () => {
    if (!hasPhoneNumber || phoneError) return;

    setCallError('');

    try {
      if (agentConfig) {
        await saveAgentConfig(agentConfig);
      }

      await onStartCall(
        normalizedPhoneNumber,
        agentConfig?.company_name || '',
        agentConfig?.agent_slug || 'default_roofing_agent'
      );
    } catch (error) {
      setCallError(error?.message || 'Unable to start the call right now.');
    }
  };

  return (
    <>
      {showConfig && (
        <ConfigPanel
          initialConfig={agentConfig}
          onClose={() => setShowConfig(false)}
          onSave={handleConfigSaved}
        />
      )}

      <div className="bg-slate-900 border border-slate-800 rounded-lg p-6 flex flex-col gap-6">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-white">Active Call Control</h2>
          <div className={`px-2 py-1 rounded text-xs font-bold uppercase ${isCallActive ? 'bg-emerald-500/20 text-emerald-400 animate-pulse' : isConnecting ? 'bg-yellow-500/20 text-yellow-400 animate-pulse' : 'bg-slate-700 text-slate-400'}`}>
            {isCallActive ? 'Live' : isConnecting ? 'Connecting' : 'Ready'}
          </div>
        </div>

        <div className="flex flex-col items-center gap-5">
          {isCallActive ? (
            <div className="text-center space-y-2">
              <div className="w-24 h-24 rounded-full bg-indigo-500/20 flex items-center justify-center mx-auto relative">
                <div className="absolute inset-0 rounded-full border border-indigo-500/50 animate-ping"></div>
                <Phone className="w-10 h-10 text-indigo-400" />
              </div>
              <div className="text-2xl font-mono text-white mt-4">Calling...</div>
              {agentConfig?.company_name && (
                <div className="text-slate-400 text-sm">Agent: {agentConfig.agent_name || 'Aisha'} · {agentConfig.company_name}</div>
              )}
              <div className="text-slate-500 text-xs">{normalizedPhoneNumber || phoneNumber}</div>
            </div>
          ) : (
            <div className="w-full space-y-3">
              <input
                type="tel"
                placeholder="e.g. +14155552671"
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                value={phoneNumber}
                onChange={(e) => {
                  setPhoneNumber(e.target.value);
                  setCallError('');
                }}
              />
              <p className="text-xs text-slate-500">
                Enter the customer number in E.164 format so the call can be routed correctly.
              </p>
              {phoneError && (
                <div className="rounded-lg border border-amber-500/20 bg-amber-500/10 px-3 py-2 text-sm text-amber-100">
                  {phoneError}
                </div>
              )}

              {agentConfig && (
                <div className="bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 text-sm">
                  <div className="flex justify-between items-center">
                    <div>
                      <span className="text-slate-400">Agent: </span>
                      <span className="text-white">{agentConfig.agent_name || 'Aisha'}</span>
                      {agentConfig.company_name && (
                        <>
                          <span className="text-slate-500 mx-1">·</span>
                          <span className="text-slate-400">Company: </span>
                          <span className="text-white">{agentConfig.company_name}</span>
                        </>
                      )}
                    </div>
                    <button
                      onClick={() => setShowConfig(true)}
                      className="text-indigo-400 hover:text-indigo-300 text-xs underline underline-offset-2"
                    >
                      Edit
                    </button>
                  </div>
                  <div className="mt-1 text-xs text-slate-500">
                    TTS: <span className="text-slate-400 capitalize">{agentConfig.tts_provider}</span>
                    <span className="mx-1">·</span>
                    Lang: <span className="text-slate-400 capitalize">{agentConfig.language}</span>
                  </div>
                </div>
              )}

              {!agentConfig && (
                <button
                  onClick={() => setShowConfig(true)}
                  className="w-full bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 hover:text-white font-medium py-2.5 px-4 rounded-lg flex items-center justify-center gap-2 transition-colors text-sm"
                >
                  <Settings size={16} />
                  Configure Agent (Company, Prompt, TTS)
                </button>
              )}

              {callError && (
                <div className="rounded-lg border border-red-500/20 bg-red-500/10 px-3 py-2 text-sm text-red-200">
                  {callError}
                </div>
              )}

              <button
                onClick={handleStartCall}
                className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-3 px-4 rounded-lg flex items-center justify-center gap-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                disabled={!hasPhoneNumber || Boolean(phoneError) || isConnecting}
              >
                <Phone size={18} />
                {isConnecting ? 'Connecting...' : 'Start Outbound Call'}
              </button>
            </div>
          )}
        </div>

        {isCallActive && (
          <div className="space-y-3">
            <div className="rounded-lg border border-slate-700 bg-slate-800/70 px-4 py-3 text-sm text-slate-300">
              The live transcript refreshes automatically every few seconds while the call is running.
            </div>
            <button
              onClick={onEndCall}
              className="w-full bg-red-500/10 hover:bg-red-500/20 text-red-500 border border-red-500/20 p-3 rounded-lg flex items-center justify-center gap-2 transition-colors"
            >
              <PhoneOff size={18} />
              End Call
            </button>
          </div>
        )}
      </div>
    </>
  );
};

export default ActiveCallPanel;
