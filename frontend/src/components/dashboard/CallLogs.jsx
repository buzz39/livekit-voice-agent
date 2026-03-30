import React, { useState, useEffect } from 'react';
import { Search, FileText, Calendar, Clock, Phone, User, Building, X, ChevronDown } from 'lucide-react';
import { getRecentCalls, getTenants } from '../../api';

// Simple helper to format duration
const formatDuration = (seconds) => {
    if (!seconds) return '0s';
    const m = Math.floor(seconds / 60);
    const s = Math.round(seconds % 60);
    return `${m}m ${s}s`;
};

// Helper to format date
const formatDate = (dateString) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleString();
};

const CallDetailModal = ({ call, onClose }) => {
    if (!call) return null;

    let transcriptData = [];
    try {
        transcriptData = typeof call.transcript === 'string'
            ? JSON.parse(call.transcript)
            : (call.transcript || []);
    } catch (e) {
        console.error("Failed to parse transcript", e);
    }

    // Try to parse captured_data if it's a string
    let capturedData = call.captured_data || {};
    if (typeof capturedData === 'string') {
        try {
            capturedData = JSON.parse(capturedData);
        } catch (e) {
            console.error("Failed to parse captured_data", e);
        }
    }


    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
            <div className="bg-slate-900 border border-slate-700 rounded-xl shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden animate-in fade-in zoom-in duration-200">
                {/* Header */}
                <div className="flex justify-between items-center p-6 border-b border-slate-800 bg-slate-800/50">
                    <div>
                        <h2 className="text-xl font-bold text-white flex items-center gap-2">
                            <Phone className="w-5 h-5 text-indigo-400" />
                            {call.phone_number || 'Unknown Number'}
                        </h2>
                        <div className="text-sm text-slate-400 mt-1 flex items-center gap-4">
                            <span className="flex items-center gap-1"><Calendar className="w-3 h-3" /> {formatDate(call.created_at)}</span>
                            <span className="flex items-center gap-1"><Clock className="w-3 h-3" /> {formatDuration(call.duration_seconds)}</span>
                        </div>
                    </div>
                    <button onClick={onClose} className="text-slate-400 hover:text-white hover:bg-slate-700 p-2 rounded-full transition-colors">
                        <X className="w-6 h-6" />
                    </button>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-6 grid grid-cols-1 md:grid-cols-3 gap-6">
                    {/* Left Column: Details */}
                    <div className="space-y-6">
                        {/* Call Status Card */}
                        <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
                            <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">Call Status</h3>
                            <div className="space-y-2">
                                <div className="flex justify-between">
                                    <span className="text-slate-400 text-sm">Status</span>
                                    <span className={`px-2 py-0.5 rounded text-xs font-medium capitalize ${
                                        call.call_status === 'completed' ? 'bg-emerald-900/50 text-emerald-400' : 'bg-slate-700 text-slate-300'
                                    }`}>{call.call_status}</span>
                                </div>
                                <div className="flex justify-between">
                                    <span className="text-slate-400 text-sm">Interest Level</span>
                                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                                        call.interest_level === 'Hot' ? 'bg-red-900/50 text-red-400' :
                                        call.interest_level === 'Warm' ? 'bg-amber-900/50 text-amber-400' :
                                        'bg-blue-900/50 text-blue-400'
                                    }`}>{call.interest_level || 'N/A'}</span>
                                </div>
                            </div>
                        </div>

                        {/* Contact Info Card */}
                        <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
                            <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">Contact Info</h3>
                            <div className="space-y-3">
                                <div className="flex items-start gap-3">
                                    <Building className="w-4 h-4 text-slate-500 mt-1" />
                                    <div>
                                        <div className="text-xs text-slate-500">Business</div>
                                        <div className="text-sm text-slate-200">{call.business_name || 'N/A'}</div>
                                    </div>
                                </div>
                                <div className="flex items-start gap-3">
                                    <User className="w-4 h-4 text-slate-500 mt-1" />
                                    <div>
                                        <div className="text-xs text-slate-500">Contact Name</div>
                                        <div className="text-sm text-slate-200">{call.contact_name || 'N/A'}</div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Captured Data Card */}
                        <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
                            <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">Captured Data</h3>
                            {Object.keys(capturedData).length > 0 ? (
                                <div className="space-y-2">
                                    {Object.entries(capturedData).map(([key, value]) => (
                                        <div key={key} className="flex flex-col border-b border-slate-700/50 pb-2 last:border-0 last:pb-0">
                                            <span className="text-xs text-slate-500 capitalize">{key.replace(/_/g, ' ')}</span>
                                            <span className="text-sm text-slate-200 break-words">{String(value)}</span>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <div className="text-sm text-slate-500 italic">No data captured</div>
                            )}
                        </div>

                         {/* Notes Card */}
                         {call.notes && (
                            <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
                                <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">Notes</h3>
                                <p className="text-sm text-slate-300 whitespace-pre-wrap">{call.notes}</p>
                            </div>
                        )}

                        {/* Objection Card */}
                        {call.objection && (
                            <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
                                <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">Primary Objection</h3>
                                <p className="text-sm text-slate-300">{call.objection}</p>
                            </div>
                        )}
                    </div>

                    {/* Right Column: Transcript & Audio */}
                    <div className="md:col-span-2 flex flex-col gap-6 h-full min-h-0">
                        {/* Audio Player */}
                        {call.recording_url && (
                             <div className="bg-slate-800 p-4 rounded-lg border border-slate-700 flex flex-col gap-2">
                                <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider">Call Recording</h3>
                                <audio controls src={call.recording_url} className="w-full" />
                            </div>
                        )}

                        {/* Transcript */}
                        <div className="flex-1 bg-slate-950 rounded-lg border border-slate-800 flex flex-col min-h-0 overflow-hidden">
                            <div className="p-3 border-b border-slate-800 bg-slate-900/50 flex items-center gap-2">
                                <FileText className="w-4 h-4 text-slate-400" />
                                <span className="text-sm font-medium text-slate-300">Transcript</span>
                            </div>
                            <div className="flex-1 overflow-y-auto p-4 space-y-4">
                                {transcriptData.length > 0 ? (
                                    transcriptData.map((entry, i) => (
                                        <div key={i} className={`flex ${entry.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                                            <div className={`max-w-[80%] rounded-lg p-3 ${
                                                entry.role === 'user'
                                                ? 'bg-indigo-600/20 text-indigo-100 border border-indigo-500/30'
                                                : 'bg-slate-800 text-slate-200 border border-slate-700'
                                            }`}>
                                                <div className="text-xs opacity-50 mb-1 capitalize">{entry.role}</div>
                                                <div className="text-sm">{entry.text}</div>
                                            </div>
                                        </div>
                                    ))
                                ) : (
                                    <div className="flex items-center justify-center h-full text-slate-500 italic">
                                        No transcript available
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

const CallLogs = () => {
    const [calls, setCalls] = useState([]);
    const [loading, setLoading] = useState(true);
    const [selectedCall, setSelectedCall] = useState(null);
    const [searchTerm, setSearchTerm] = useState('');
    const [tenantId, setTenantId] = useState('');
    const [tenants, setTenants] = useState([]);

    useEffect(() => {
        loadCalls();
    }, [tenantId]);

    useEffect(() => {
        const loadTenants = async () => {
            const tenantList = await getTenants(false, 200);
            setTenants(Array.isArray(tenantList) ? tenantList : []);
        };
        loadTenants();
    }, []);

    const loadCalls = async () => {
        setLoading(true);
        try {
            // Fetch more calls than the default dashboard limit
            const data = await getRecentCalls(100, tenantId || null);
            setCalls(data || []);
        } catch (error) {
            console.error("Error loading calls:", error);
        } finally {
            setLoading(false);
        }
    };

    const filteredCalls = calls.filter(call => {
        const searchLower = searchTerm.toLowerCase();
        return (
            (call.phone_number && call.phone_number.toLowerCase().includes(searchLower)) ||
            (call.business_name && call.business_name.toLowerCase().includes(searchLower)) ||
            (call.contact_name && call.contact_name.toLowerCase().includes(searchLower)) ||
            (call.interest_level && call.interest_level.toLowerCase().includes(searchLower))
        );
    });

    return (
        <div className="h-full flex flex-col gap-6">
            <div className="flex justify-between items-center">
                <h1 className="text-2xl font-bold text-white">Call Logs</h1>
                <div className="flex gap-4">
                    <div className="relative">
                        <Search className="w-5 h-5 absolute left-3 top-2.5 text-slate-500" />
                        <input
                            type="text"
                            placeholder="Search logs..."
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                            className="bg-slate-900 border border-slate-800 text-white rounded-lg pl-10 pr-4 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 w-64"
                        />
                    </div>
                    <div className="relative">
                        <select
                            value={tenantId}
                            onChange={(e) => setTenantId(e.target.value)}
                            className="appearance-none bg-slate-900 border border-slate-800 text-white rounded-lg px-4 py-2 pr-9 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                        >
                            <option value="">All Tenants</option>
                            {tenants.map((tenant) => (
                                <option key={tenant.tenant_id} value={tenant.tenant_id}>
                                    {tenant.display_name || tenant.tenant_id}
                                </option>
                            ))}
                        </select>
                        <ChevronDown className="w-4 h-4 absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none" />
                    </div>
                </div>
            </div>

            <div className="flex-1 bg-slate-900 border border-slate-800 rounded-lg overflow-hidden flex flex-col">
                {/* Table Header */}
                <div className="grid grid-cols-12 gap-4 p-4 border-b border-slate-800 bg-slate-800/50 text-xs font-bold text-slate-400 uppercase tracking-wider">
                    <div className="col-span-3">Contact</div>
                    <div className="col-span-2">Date</div>
                    <div className="col-span-2">Duration</div>
                    <div className="col-span-2">Status</div>
                    <div className="col-span-2">Interest</div>
                    <div className="col-span-1 text-center">Actions</div>
                </div>

                {/* Table Body */}
                <div className="flex-1 overflow-y-auto">
                    {loading ? (
                        <div className="flex items-center justify-center h-64 text-slate-500">
                            Loading calls...
                        </div>
                    ) : filteredCalls.length > 0 ? (
                        filteredCalls.map((call) => (
                            <div
                                key={call.id}
                                onClick={() => setSelectedCall(call)}
                                className="grid grid-cols-12 gap-4 p-4 border-b border-slate-800 hover:bg-slate-800/50 transition-colors cursor-pointer group items-center"
                            >
                                <div className="col-span-3">
                                    <div className="font-medium text-white">{call.phone_number || 'Unknown'}</div>
                                    <div className="text-xs text-slate-500 truncate">{call.business_name || call.contact_name || '-'}</div>
                                </div>
                                <div className="col-span-2 text-sm text-slate-400">
                                    {formatDate(call.created_at)}
                                </div>
                                <div className="col-span-2 text-sm text-slate-400 font-mono">
                                    {formatDuration(call.duration_seconds)}
                                </div>
                                <div className="col-span-2">
                                    <span className={`px-2 py-1 rounded text-xs font-medium capitalize ${
                                        call.call_status === 'completed' ? 'bg-emerald-900/30 text-emerald-400' :
                                        call.call_status === 'failed' ? 'bg-red-900/30 text-red-400' :
                                        'bg-slate-800 text-slate-400'
                                    }`}>
                                        {call.call_status}
                                    </span>
                                </div>
                                <div className="col-span-2">
                                    <span className={`px-2 py-1 rounded text-xs font-medium ${
                                        call.interest_level === 'Hot' ? 'bg-red-900/30 text-red-400 border border-red-900/50' :
                                        call.interest_level === 'Warm' ? 'bg-amber-900/30 text-amber-400 border border-amber-900/50' :
                                        'text-slate-500'
                                    }`}>
                                        {call.interest_level || '-'}
                                    </span>
                                </div>
                                <div className="col-span-1 flex justify-center">
                                    <button className="text-slate-500 hover:text-indigo-400 p-2 rounded-full hover:bg-slate-800 transition-colors">
                                        <FileText className="w-4 h-4" />
                                    </button>
                                </div>
                            </div>
                        ))
                    ) : (
                        <div className="flex items-center justify-center h-64 text-slate-500">
                            No calls found matching your search.
                        </div>
                    )}
                </div>
            </div>

            {/* Modal */}
            {selectedCall && (
                <CallDetailModal call={selectedCall} onClose={() => setSelectedCall(null)} />
            )}
        </div>
    );
};

export default CallLogs;
