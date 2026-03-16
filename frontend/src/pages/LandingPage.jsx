import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Activity, Phone, BarChart2, Shield, Zap, Users } from 'lucide-react';

const LandingPage = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      {/* Nav */}
      <nav className="flex items-center justify-between px-8 py-5 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <Activity className="w-6 h-6 text-indigo-400" />
          <span className="font-bold text-xl text-white">Aisha AI</span>
        </div>
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/sign-in')}
            className="text-slate-300 hover:text-white transition-colors text-sm font-medium"
          >
            Sign In
          </button>
          <button
            onClick={() => navigate('/sign-up')}
            className="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          >
            Get Started
          </button>
        </div>
      </nav>

      {/* Hero */}
      <div className="flex flex-col items-center justify-center text-center px-6 pt-24 pb-20">
        <div className="inline-flex items-center gap-2 bg-indigo-500/10 border border-indigo-500/20 rounded-full px-4 py-1.5 text-indigo-400 text-sm font-medium mb-8">
          <Zap className="w-4 h-4" />
          AI-Powered Voice Agents — Now Live
        </div>

        <h1 className="text-5xl md:text-7xl font-bold leading-tight max-w-4xl mb-6 bg-gradient-to-br from-white to-slate-400 bg-clip-text text-transparent">
          AI-powered outbound voice agents for real estate, insurance &amp; more
        </h1>

        <p className="text-slate-400 text-lg md:text-xl max-w-2xl mb-10">
          Aisha AI makes hundreds of outbound calls a day, qualifies leads, books appointments, and reports back — so your team focuses only on hot prospects.
        </p>

        <div className="flex flex-col sm:flex-row gap-4">
          <button
            onClick={() => navigate('/sign-up')}
            className="bg-indigo-600 hover:bg-indigo-500 text-white px-8 py-4 rounded-xl text-lg font-semibold transition-all hover:scale-105 shadow-lg shadow-indigo-500/20"
          >
            Get Started Free →
          </button>
          <button
            onClick={() => navigate('/sign-in')}
            className="bg-slate-800 hover:bg-slate-700 text-white px-8 py-4 rounded-xl text-lg font-semibold transition-colors border border-slate-700"
          >
            Sign In
          </button>
        </div>
      </div>

      {/* Feature Cards */}
      <div className="max-w-6xl mx-auto px-6 pb-24">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <FeatureCard
            icon={<Phone className="w-6 h-6 text-indigo-400" />}
            title="Automated Outbound Calls"
            description="Your AI agent calls leads, handles objections, and qualifies prospects 24/7 — without human intervention."
          />
          <FeatureCard
            icon={<BarChart2 className="w-6 h-6 text-emerald-400" />}
            title="Real-time Analytics"
            description="Track call volumes, duration, lead quality, and conversion rates from a single dashboard."
          />
          <FeatureCard
            icon={<Users className="w-6 h-6 text-amber-400" />}
            title="Calendar Integration"
            description="Aisha books appointments directly into your calendar during calls. No back-and-forth."
          />
        </div>
      </div>

      {/* Footer */}
      <div className="border-t border-slate-800 py-8 text-center text-slate-500 text-sm">
        © 2025 Aisha AI · Built for high-performers
      </div>
    </div>
  );
};

const FeatureCard = ({ icon, title, description }) => (
  <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 hover:border-slate-700 transition-colors">
    <div className="w-10 h-10 rounded-lg bg-slate-800 flex items-center justify-center mb-4">
      {icon}
    </div>
    <h3 className="font-semibold text-white mb-2">{title}</h3>
    <p className="text-slate-400 text-sm leading-relaxed">{description}</p>
  </div>
);

export default LandingPage;
