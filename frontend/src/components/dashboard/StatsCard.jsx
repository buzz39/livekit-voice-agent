import React from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const data = [
  { name: '10:00', value: 4000 },
  { name: '10:05', value: 3000 },
  { name: '10:10', value: 2000 },
  { name: '10:15', value: 2780 },
  { name: '10:20', value: 1890 },
  { name: '10:25', value: 2390 },
  { name: '10:30', value: 3490 },
];

const StatsCard = ({ title, value, subtext, chartColor = "#6366f1" }) => {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-5 flex flex-col justify-between h-full">
      <div>
        <h3 className="text-slate-400 text-sm font-medium uppercase tracking-wider">{title}</h3>
        <div className="mt-2 text-3xl font-bold text-white">{value}</div>
        <div className="text-emerald-400 text-xs mt-1 font-medium">{subtext}</div>
      </div>

      <div className="h-24 mt-4 -mx-2 w-full min-w-0">
        <ResponsiveContainer width="100%" height="100%" minWidth={0}>
          <AreaChart data={data}>
            <defs>
              <linearGradient id={`color${title.replace(/\s/g, '')}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={chartColor} stopOpacity={0.3} />
                <stop offset="95%" stopColor={chartColor} stopOpacity={0} />
              </linearGradient>
            </defs>
            <Area
              type="monotone"
              dataKey="value"
              stroke={chartColor}
              strokeWidth={2}
              fillOpacity={1}
              fill={`url(#color${title.replace(/\s/g, '')})`}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default StatsCard;
