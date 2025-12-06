import Link from "next/link";
import { ArrowRight, Mic, Shield, Zap } from "lucide-react";

export default function Home() {
  return (
    <div className="min-h-screen bg-black text-white selection:bg-blue-500/30">
      {/* Navigation */}
      <nav className="border-b border-white/10 bg-black/50 backdrop-blur-xl sticky top-0 z-50">
        <div className="container mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2 font-bold text-xl tracking-tighter">
            <div className="h-8 w-8 rounded-lg bg-blue-600 flex items-center justify-center">
              <Mic className="h-5 w-5 text-white" />
            </div>
            VoiceAgent<span className="text-blue-500">.ai</span>
          </div>
          <div className="flex items-center gap-4">
            <Link
              href="/handler/sign-in"
              className="text-sm font-medium text-zinc-400 hover:text-white transition-colors"
            >
              Sign In
            </Link>
            <Link
              href="/dashboard/agents"
              className="text-sm font-medium bg-white text-black px-4 py-2 rounded-full hover:bg-zinc-200 transition-colors"
            >
              Get Started
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <main className="container mx-auto px-6 pt-32 pb-20">
        <div className="max-w-4xl mx-auto text-center space-y-8">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-blue-500/30 bg-blue-500/10 text-blue-400 text-sm font-medium">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-500"></span>
            </span>
            LiveKit Powered Telephony
          </div>

          <h1 className="text-5xl md:text-7xl font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-b from-white to-white/50">
            Build Voice Agents <br />
            <span className="text-blue-500">In Minutes, Not Weeks</span>
          </h1>

          <p className="text-xl text-zinc-400 max-w-2xl mx-auto leading-relaxed">
            Deploy intelligent conversational AI agents that handle calls, capture leads, and sync data instantly. Powered by LLMs and real-time audio infrastructure.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4">
            <Link
              href="/dashboard/agents"
              className="h-12 px-8 rounded-full bg-blue-600 hover:bg-blue-500 text-white font-medium flex items-center gap-2 transition-all hover:scale-105"
            >
              Launch Console <ArrowRight className="h-4 w-4" />
            </Link>
            <a
              href="https://docs.livekit.io"
              target="_blank"
              rel="noopener noreferrer"
              className="h-12 px-8 rounded-full border border-white/10 hover:bg-white/5 text-white font-medium flex items-center gap-2 transition-colors"
            >
              Read Documentation
            </a>
          </div>
        </div>

        {/* Features Grid */}
        <div className="grid md:grid-cols-3 gap-8 mt-32 border-t border-white/10 pt-20">
          <div className="space-y-4">
            <div className="h-12 w-12 rounded-xl bg-purple-500/10 flex items-center justify-center border border-purple-500/20">
              <Zap className="h-6 w-6 text-purple-400" />
            </div>
            <h3 className="text-xl font-semibold">Low Latency AI</h3>
            <p className="text-zinc-400 leading-relaxed">
              Optimized for real-time conversation with sub-second response times using the latest VAD and LLM models.
            </p>
          </div>
          <div className="space-y-4">
            <div className="h-12 w-12 rounded-xl bg-emerald-500/10 flex items-center justify-center border border-emerald-500/20">
              <Shield className="h-6 w-6 text-emerald-400" />
            </div>
            <h3 className="text-xl font-semibold">Secure & Scalable</h3>
            <p className="text-zinc-400 leading-relaxed">
              Enterprise-grade security with multi-tenant isolation, managed via Neon DB and robust authentication.
            </p>
          </div>
          <div className="space-y-4">
            <div className="h-12 w-12 rounded-xl bg-orange-500/10 flex items-center justify-center border border-orange-500/20">
              <Mic className="h-6 w-6 text-orange-400" />
            </div>
            <h3 className="text-xl font-semibold">Natural Voices</h3>
            <p className="text-zinc-400 leading-relaxed">
              Clone voices or use premium pre-built ones. Agents sound human, handle interruptions, and express emotion.
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
