import React, { useState, useEffect } from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, Legend } from 'recharts';
import { getAnalyticsVolume, getStats } from '../../api';
import StatsCard from './StatsCard';
import { Calendar, RefreshCcw } from 'lucide-react';

const Analytics = () => {
    const [data, setData] = useState([]);
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);
    const [timeRange, setTimeRange] = useState(30);

    useEffect(() => {
        loadData();
    }, [timeRange]);

    const loadData = async () => {
        setLoading(true);
        try {
            const [volumeData, statsData] = await Promise.all([
                getAnalyticsVolume(timeRange),
                getStats(timeRange)
            ]);

            // Transform data to add cost
            const processedData = (volumeData || []).map(day => ({
                ...day,
                cost: ((day.count * (day.avg_duration || 0)) / 60 * 0.15).toFixed(2), // $0.15/min est
                avg_duration: Math.round(day.avg_duration || 0)
            }));

            setData(processedData);
            setStats(statsData);
        } catch (error) {
            console.error("Error loading analytics:", error);
        } finally {
            setLoading(false);
        }
    };

    // Helpler for formatting duration
    const formatDuration = (seconds) => {
        if (!seconds) return '0s';
        const m = Math.floor(seconds / 60);
        const s = Math.round(seconds % 60);
        return `${m}m ${s}s`;
    };

    // Calculate total cost (Estimate)
    // Assuming $0.05/min roughly for everything
    const totalMinutes = data.reduce((acc, curr) => acc + (curr.avg_duration * curr.count) / 60, 0);
    const estimatedCost = (totalMinutes * 0.15).toFixed(2); // $0.15/min (LiveKit + OpenAI + SIP)

    return (
        <div className="h-full flex flex-col gap-6 overflow-y-auto pr-2">
            <div className="flex justify-between items-center">
                <h1 className="text-2xl font-bold text-white">Analytics Overview</h1>
                <div className="flex gap-4">
                    <select
                        value={timeRange}
                        onChange={(e) => setTimeRange(Number(e.target.value))}
                        className="bg-slate-900 border border-slate-800 text-white rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    >
                        <option value={7}>Last 7 Days</option>
                        <option value={30}>Last 30 Days</option>
                        <option value={90}>Last 3 Months</option>
                    </select>
                    <button
                        onClick={loadData}
                        className="bg-slate-800 hover:bg-slate-700 text-white p-2 rounded-lg transition-colors border border-slate-700"
                    >
                        <RefreshCcw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
                    </button>
                </div>
            </div>

            {/* Key Metrics */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                <StatsCard
                    title="Total Calls"
                    value={data.reduce((acc, curr) => acc + Number(curr.count), 0)}
                    subtext={`In last ${timeRange} days`}
                    chartColor="#8b5cf6"
                />
                <StatsCard
                    title="Total Minutes"
                    value={Math.round(totalMinutes)}
                    subtext="Billed Duration"
                    chartColor="#10b981"
                />
                <StatsCard
                    title="Est. Cost"
                    value={`$${estimatedCost}`}
                    subtext="Estimated Usage"
                    chartColor="#f59e0b"
                />
                <StatsCard
                    title="Success Rate"
                    value={`${data.reduce((acc, curr) => acc + Number(curr.count), 0) > 0
                        ? Math.round((data.reduce((acc, curr) => acc + Number(curr.completed), 0) / data.reduce((acc, curr) => acc + Number(curr.count), 0)) * 100)
                        : 0}%`}
                    subtext="Completed Calls"
                    chartColor="#3b82f6"
                />
            </div>

            {/* Charts Row 1 */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-80">
                {/* Call Volume Chart */}
                <div className="bg-slate-900 border border-slate-800 rounded-lg p-6 flex flex-col">
                    <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-4">Daily Call Volume</h3>
                    <div className="flex-1 min-h-0">
                        <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={data}>
                                <defs>
                                    <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.3} />
                                        <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                                <XAxis
                                    dataKey="date"
                                    stroke="#64748b"
                                    fontSize={12}
                                    tickLine={false}
                                    axisLine={false}
                                    interval={timeRange > 30 ? 6 : 2}
                                />
                                <YAxis
                                    stroke="#64748b"
                                    fontSize={12}
                                    tickLine={false}
                                    axisLine={false}
                                />
                                <Tooltip
                                    contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1e293b', color: '#f8fafc' }}
                                    itemStyle={{ color: '#cbd5e1' }}
                                />
                                <Area
                                    type="monotone"
                                    dataKey="count"
                                    stroke="#8b5cf6"
                                    strokeWidth={2}
                                    fillOpacity={1}
                                    fill="url(#colorCount)"
                                    name="Total Calls"
                                />
                                <Area
                                    type="monotone"
                                    dataKey="completed"
                                    stroke="#10b981"
                                    strokeWidth={2}
                                    fillOpacity={0}
                                    name="Completed Calls"
                                />
                            </AreaChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Avg Duration Chart */}
                <div className="bg-slate-900 border border-slate-800 rounded-lg p-6 flex flex-col">
                    <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-4">Average Call Duration (Seconds)</h3>
                    <div className="flex-1 min-h-0">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={data}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                                <XAxis
                                    dataKey="date"
                                    stroke="#64748b"
                                    fontSize={12}
                                    tickLine={false}
                                    axisLine={false}
                                    interval={timeRange > 30 ? 6 : 2}
                                />
                                <YAxis
                                    stroke="#64748b"
                                    fontSize={12}
                                    tickLine={false}
                                    axisLine={false}
                                />
                                <Tooltip
                                    contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1e293b', color: '#f8fafc' }}
                                    itemStyle={{ color: '#cbd5e1' }}
                                    formatter={(value) => `${Math.round(value)}s`}
                                />
                                <Bar dataKey="avg_duration" fill="#3b82f6" radius={[4, 4, 0, 0]} name="Avg Duration" />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 gap-6">
                <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
                    <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-4">Cost Analysis (Daily)</h3>
                    <div className="h-60">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={data}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                                <XAxis
                                    dataKey="date"
                                    stroke="#64748b"
                                    fontSize={12}
                                    tickLine={false}
                                    axisLine={false}
                                    interval={timeRange > 30 ? 6 : 2}
                                />
                                <YAxis
                                    stroke="#64748b"
                                    fontSize={12}
                                    tickLine={false}
                                    axisLine={false}
                                    tickFormatter={(val) => `$${val}`}
                                />
                                <Tooltip
                                    contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1e293b', color: '#f8fafc' }}
                                    formatter={(value) => `$${Number(value).toFixed(2)}`}
                                />
                                <Legend />
                                <Bar
                                    dataKey="cost"
                                    fill="#f59e0b"
                                    radius={[4, 4, 0, 0]}
                                    name="Est. Cost"
                                />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Analytics;
