import React from 'react';
import { ShieldAlert, ShieldCheck, Shield } from 'lucide-react';

const RiskBadge = ({ level = 'low' }) => {
  const configs = {
    high: {
      color: 'bg-red-500/10 text-red-500 border-red-500/20',
      icon: ShieldAlert,
      label: 'High Risk'
    },
    medium: {
      color: 'bg-orange-500/10 text-orange-500 border-orange-500/20',
      icon: Shield,
      label: 'Medium Risk'
    },
    low: {
      color: 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20',
      icon: ShieldCheck,
      label: 'Low Risk'
    }
  };

  const config = configs[level];
  const Icon = config.icon;

  return (
    <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full border ${config.color} w-fit`}>
      <Icon size={16} />
      <span className="text-xs font-bold uppercase tracking-wider">{config.label}</span>
    </div>
  );
};

export default RiskBadge;
