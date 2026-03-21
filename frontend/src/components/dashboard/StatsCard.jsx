import React from 'react';

const StatsCard = ({ title, value, subtext, chartColor = "#6366f1" }) => {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-5 flex flex-col justify-between h-full">
      <div>
        <h3 className="text-slate-400 text-sm font-medium uppercase tracking-wider">{title}</h3>
        <div className="mt-2 text-3xl font-bold text-white">{value}</div>
        <div className="text-emerald-400 text-xs mt-1 font-medium">{subtext}</div>
      </div>

      <div className="h-6 mt-4 w-full min-w-0 flex items-end gap-[2px]">
        {/* Simple decorative bar visualization using the accent color */}
        {[0.4, 0.6, 0.35, 0.7, 0.5, 0.8, 0.65, 0.9, 0.55, 0.75].map((h, i) => (
          <div
            key={i}
            className="flex-1 rounded-sm"
            style={{ height: `${h * 100}%`, backgroundColor: chartColor, opacity: 0.3 + (i / 15) }}
          />
        ))}
      </div>
    </div>
  );
};

export default StatsCard;
