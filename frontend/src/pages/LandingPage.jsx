import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Activity, Phone, BarChart2, Shield, Zap, Users, Globe, Brain,
  MessageSquare, Calendar, ChevronDown, ChevronUp, ArrowRight,
  Headphones, Settings, Database, Clock, TrendingUp, Building2,
  Home, Briefcase, GraduationCap, Stethoscope, Car, ShoppingBag,
  CheckCircle2, Star, PlayCircle, Mic, Bot
} from 'lucide-react';

/* ------------------------------------------------------------------ */
/*  LANDING PAGE                                                       */
/* ------------------------------------------------------------------ */
const LandingPage = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-slate-950 text-white overflow-x-hidden">
      <Navbar navigate={navigate} />
      <Hero navigate={navigate} />
      <LogoBar />
      <Features />
      <HowItWorks />
      <LanguageSection />
      <UseCases />
      <Testimonials />
      <WhyAisha />
      <FAQ />
      <FinalCTA navigate={navigate} />
      <Footer navigate={navigate} />
    </div>
  );
};

/* ------------------------------------------------------------------ */
/*  NAVBAR                                                             */
/* ------------------------------------------------------------------ */
const Navbar = ({ navigate }) => {
  const [mobileOpen, setMobileOpen] = useState(false);
  return (
    <nav className="sticky top-0 z-50 backdrop-blur-xl bg-slate-950/80 border-b border-slate-800/60">
      <div className="max-w-7xl mx-auto flex items-center justify-between px-6 py-4">
        <div className="flex items-center gap-2 cursor-pointer" onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}>
          <Activity className="w-7 h-7 text-indigo-400" />
          <span className="font-bold text-xl tracking-tight">Aisha AI</span>
        </div>

        {/* Desktop links */}
        <div className="hidden md:flex items-center gap-8 text-sm text-slate-400">
          <a href="#features" className="hover:text-white transition-colors">Features</a>
          <a href="#how-it-works" className="hover:text-white transition-colors">How It Works</a>
          <a href="#use-cases" className="hover:text-white transition-colors">Industries</a>
          <a href="#faq" className="hover:text-white transition-colors">FAQ</a>
        </div>

        <div className="hidden md:flex items-center gap-3">
          <button onClick={() => navigate('/sign-in')} className="text-slate-300 hover:text-white transition-colors text-sm font-medium px-4 py-2">
            Sign In
          </button>
          <button onClick={() => navigate('/sign-up')} className="bg-indigo-600 hover:bg-indigo-500 text-white px-5 py-2.5 rounded-lg text-sm font-semibold transition-colors">
            Book a Demo
          </button>
        </div>

        {/* Mobile hamburger */}
        <button className="md:hidden text-slate-300" onClick={() => setMobileOpen(!mobileOpen)}>
          <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            {mobileOpen
              ? <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              : <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />}
          </svg>
        </button>
      </div>

      {/* Mobile menu */}
      {mobileOpen && (
        <div className="md:hidden border-t border-slate-800 px-6 py-4 space-y-3 bg-slate-950">
          <a href="#features" className="block text-slate-300 hover:text-white text-sm">Features</a>
          <a href="#how-it-works" className="block text-slate-300 hover:text-white text-sm">How It Works</a>
          <a href="#use-cases" className="block text-slate-300 hover:text-white text-sm">Industries</a>
          <a href="#faq" className="block text-slate-300 hover:text-white text-sm">FAQ</a>
          <div className="pt-3 border-t border-slate-800 flex flex-col gap-2">
            <button onClick={() => navigate('/sign-in')} className="text-slate-300 text-sm text-left">Sign In</button>
            <button onClick={() => navigate('/sign-up')} className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-semibold w-full">Book a Demo</button>
          </div>
        </div>
      )}
    </nav>
  );
};

/* ------------------------------------------------------------------ */
/*  HERO                                                               */
/* ------------------------------------------------------------------ */
const Hero = ({ navigate }) => (
  <section className="relative px-6 pt-20 pb-28 md:pt-32 md:pb-36">
    {/* Background glow */}
    <div className="absolute inset-0 -z-10">
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[800px] h-[500px] bg-indigo-600/10 rounded-full blur-[120px]" />
    </div>

    <div className="max-w-5xl mx-auto text-center">
      <div className="inline-flex items-center gap-2 bg-indigo-500/10 border border-indigo-500/20 rounded-full px-4 py-1.5 text-indigo-400 text-sm font-medium mb-8">
        <Zap className="w-4 h-4" />
        AI Voice Agents Built for India
      </div>

      <h1 className="text-4xl sm:text-5xl md:text-7xl font-bold leading-[1.1] mb-6 bg-gradient-to-br from-white via-slate-200 to-slate-500 bg-clip-text text-transparent">
        Your AI employee that calls, qualifies &amp; converts — in every Indian language
      </h1>

      <p className="text-slate-400 text-lg md:text-xl max-w-3xl mx-auto mb-10 leading-relaxed">
        Aisha AI handles hundreds of outbound calls daily, speaks Hindi, English, Hinglish &amp; 10+ regional languages, qualifies leads, handles objections, and books meetings — so your team only talks to hot prospects.
      </p>

      <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-12">
        <button
          onClick={() => navigate('/sign-up')}
          className="group bg-indigo-600 hover:bg-indigo-500 text-white px-8 py-4 rounded-xl text-lg font-semibold transition-all hover:scale-[1.02] shadow-lg shadow-indigo-600/25 flex items-center gap-2"
        >
          Book a Free Demo
          <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
        </button>
        <button
          onClick={() => navigate('/sign-in')}
          className="bg-slate-800/60 hover:bg-slate-800 text-white px-8 py-4 rounded-xl text-lg font-semibold transition-colors border border-slate-700/60 flex items-center gap-2"
        >
          <PlayCircle className="w-5 h-5 text-indigo-400" />
          Watch It In Action
        </button>
      </div>

      {/* Trust line */}
      <p className="text-slate-500 text-sm">
        Every solution is custom-built for your business. No cookie-cutter plans.
      </p>
    </div>
  </section>
);

/* ------------------------------------------------------------------ */
/*  LOGO BAR / SOCIAL PROOF                                            */
/* ------------------------------------------------------------------ */
const LogoBar = () => (
  <section className="border-y border-slate-800/60 py-10 bg-slate-900/30">
    <div className="max-w-5xl mx-auto px-6 text-center">
      <p className="text-slate-500 text-xs uppercase tracking-widest font-medium mb-8">
        Trusted by teams across India
      </p>
      <div className="flex flex-wrap items-center justify-center gap-x-12 gap-y-6 text-slate-600">
        {['Real Estate Firms', 'Insurance Companies', 'EdTech Platforms', 'Healthcare Clinics', 'Auto Dealerships', 'D2C Brands'].map((name) => (
          <span key={name} className="text-sm font-semibold tracking-wide whitespace-nowrap">{name}</span>
        ))}
      </div>
    </div>
  </section>
);

/* ------------------------------------------------------------------ */
/*  FEATURES                                                           */
/* ------------------------------------------------------------------ */
const features = [
  {
    icon: <Phone className="w-6 h-6" />,
    color: 'text-indigo-400',
    bg: 'bg-indigo-500/10',
    title: 'Automated Outbound Calling',
    desc: 'Aisha dials your lead list, introduces your business, handles objections, and qualifies — all without human intervention.'
  },
  {
    icon: <Globe className="w-6 h-6" />,
    color: 'text-emerald-400',
    bg: 'bg-emerald-500/10',
    title: '10+ Indian Languages',
    desc: 'Hindi, English, Hinglish, Tamil, Telugu, Bengali, Marathi, Gujarati, Kannada, Malayalam, Punjabi and more.'
  },
  {
    icon: <Brain className="w-6 h-6" />,
    color: 'text-violet-400',
    bg: 'bg-violet-500/10',
    title: 'Custom AI Personality',
    desc: 'We craft a unique voice persona, script, and objection-handling flow tailored to your product and audience.'
  },
  {
    icon: <BarChart2 className="w-6 h-6" />,
    color: 'text-amber-400',
    bg: 'bg-amber-500/10',
    title: 'Real-time Dashboard',
    desc: 'Track every call — duration, transcript, sentiment, lead score, and conversion — from one unified analytics panel.'
  },
  {
    icon: <Settings className="w-6 h-6" />,
    color: 'text-cyan-400',
    bg: 'bg-cyan-500/10',
    title: 'CRM & Webhook Integration',
    desc: 'Push qualified leads directly to your CRM, Google Sheets, or any tool via webhooks and APIs — no manual data entry.'
  },
  {
    icon: <Shield className="w-6 h-6" />,
    color: 'text-rose-400',
    bg: 'bg-rose-500/10',
    title: 'Enterprise-grade Security',
    desc: 'End-to-end encryption, SOC 2 practices, GDPR-ready data handling. Your customer data stays yours.'
  },
];

const Features = () => (
  <section id="features" className="py-24 px-6">
    <div className="max-w-6xl mx-auto">
      <div className="text-center mb-16">
        <p className="text-indigo-400 text-sm font-semibold uppercase tracking-widest mb-3">Capabilities</p>
        <h2 className="text-3xl md:text-5xl font-bold mb-4">Everything you need to automate outbound</h2>
        <p className="text-slate-400 max-w-2xl mx-auto">Each deployment is bespoke — we configure the AI, scripts, languages, and integrations to match your exact workflow.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {features.map((f) => (
          <div key={f.title} className="group bg-slate-900/60 border border-slate-800 rounded-2xl p-6 hover:border-slate-700 hover:bg-slate-900 transition-all duration-300">
            <div className={`w-12 h-12 rounded-xl ${f.bg} flex items-center justify-center mb-5 ${f.color}`}>
              {f.icon}
            </div>
            <h3 className="text-lg font-semibold text-white mb-2">{f.title}</h3>
            <p className="text-slate-400 text-sm leading-relaxed">{f.desc}</p>
          </div>
        ))}
      </div>
    </div>
  </section>
);

/* ------------------------------------------------------------------ */
/*  HOW IT WORKS                                                       */
/* ------------------------------------------------------------------ */
const steps = [
  { num: '01', title: 'Discovery Call', desc: 'We learn your business, target audience, language needs, and sales workflow.', icon: <Headphones className="w-6 h-6" /> },
  { num: '02', title: 'Custom Build', desc: 'Our team configures the AI persona, call scripts, objection flows, and integrations — tailored 100% to you.', icon: <Settings className="w-6 h-6" /> },
  { num: '03', title: 'Test & Refine', desc: 'We run pilot calls, refine the AI based on real conversations, and fine-tune until conversion rates shine.', icon: <Mic className="w-6 h-6" /> },
  { num: '04', title: 'Go Live & Scale', desc: 'Launch your AI agent. Monitor results on the dashboard. Scale from 100 to 10,000 calls/day effortlessly.', icon: <TrendingUp className="w-6 h-6" /> },
];

const HowItWorks = () => (
  <section id="how-it-works" className="py-24 px-6 bg-slate-900/30">
    <div className="max-w-5xl mx-auto">
      <div className="text-center mb-16">
        <p className="text-indigo-400 text-sm font-semibold uppercase tracking-widest mb-3">Process</p>
        <h2 className="text-3xl md:text-5xl font-bold mb-4">How we build your AI agent</h2>
        <p className="text-slate-400 max-w-2xl mx-auto">No off-the-shelf templates. Every agent is handcrafted for your business.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        {steps.map((s) => (
          <div key={s.num} className="relative flex gap-5 bg-slate-900/60 border border-slate-800 rounded-2xl p-6 hover:border-indigo-500/30 transition-colors">
            <div className="flex-shrink-0 w-14 h-14 rounded-xl bg-indigo-500/10 flex items-center justify-center text-indigo-400">
              {s.icon}
            </div>
            <div>
              <span className="text-indigo-500 text-xs font-bold tracking-widest">{s.num}</span>
              <h3 className="text-lg font-semibold text-white mt-1 mb-2">{s.title}</h3>
              <p className="text-slate-400 text-sm leading-relaxed">{s.desc}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  </section>
);

/* ------------------------------------------------------------------ */
/*  LANGUAGE SECTION                                                   */
/* ------------------------------------------------------------------ */
const languages = [
  'Hindi', 'English', 'Hinglish', 'Bengali', 'Tamil', 'Telugu',
  'Marathi', 'Gujarati', 'Kannada', 'Malayalam', 'Punjabi', 'Odia'
];

const LanguageSection = () => (
  <section className="py-24 px-6">
    <div className="max-w-5xl mx-auto text-center">
      <p className="text-emerald-400 text-sm font-semibold uppercase tracking-widest mb-3">Multilingual</p>
      <h2 className="text-3xl md:text-5xl font-bold mb-4">Speaks your customer's language</h2>
      <p className="text-slate-400 max-w-2xl mx-auto mb-12">Aisha switches languages mid-call if needed. Your customers feel understood — not sold to.</p>

      <div className="flex flex-wrap items-center justify-center gap-3">
        {languages.map((lang) => (
          <span key={lang} className="bg-slate-800/60 border border-slate-700/60 rounded-full px-5 py-2.5 text-sm font-medium text-slate-300 hover:border-emerald-500/40 hover:text-emerald-400 transition-colors cursor-default">
            {lang}
          </span>
        ))}
      </div>
    </div>
  </section>
);

/* ------------------------------------------------------------------ */
/*  USE CASES / INDUSTRIES                                             */
/* ------------------------------------------------------------------ */
const useCases = [
  { icon: <Home className="w-6 h-6" />, name: 'Real Estate', desc: 'Qualify site-visit leads, follow up with fence-sitters, and book property tours on autopilot.' },
  { icon: <Shield className="w-6 h-6" />, name: 'Insurance', desc: 'Run renewal reminders, policy cross-sell campaigns, and claims follow-ups at scale.' },
  { icon: <GraduationCap className="w-6 h-6" />, name: 'EdTech', desc: 'Convert course inquiries into enrollments with persuasive multilingual follow-up calls.' },
  { icon: <Stethoscope className="w-6 h-6" />, name: 'Healthcare', desc: 'Appointment reminders, patient follow-ups, and health camp registrations — all automated.' },
  { icon: <Car className="w-6 h-6" />, name: 'Automotive', desc: 'Service reminders, test-drive bookings, and festive campaign calls handled by AI.' },
  { icon: <ShoppingBag className="w-6 h-6" />, name: 'D2C / E-commerce', desc: 'COD confirmation, cart-abandonment calls, and upsell campaigns in the customer\'s language.' },
];

const UseCases = () => (
  <section id="use-cases" className="py-24 px-6 bg-slate-900/30">
    <div className="max-w-6xl mx-auto">
      <div className="text-center mb-16">
        <p className="text-amber-400 text-sm font-semibold uppercase tracking-widest mb-3">Industries</p>
        <h2 className="text-3xl md:text-5xl font-bold mb-4">Built for your industry</h2>
        <p className="text-slate-400 max-w-2xl mx-auto">We don't offer a one-size-fits-all product. Every deployment is configured for your specific industry, audience, and objectives.</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        {useCases.map((uc) => (
          <div key={uc.name} className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 hover:border-amber-500/30 transition-colors">
            <div className="w-12 h-12 rounded-xl bg-amber-500/10 text-amber-400 flex items-center justify-center mb-4">
              {uc.icon}
            </div>
            <h3 className="text-lg font-semibold text-white mb-2">{uc.name}</h3>
            <p className="text-slate-400 text-sm leading-relaxed">{uc.desc}</p>
          </div>
        ))}
      </div>
    </div>
  </section>
);

/* ------------------------------------------------------------------ */
/*  TESTIMONIALS                                                       */
/* ------------------------------------------------------------------ */
const testimonials = [
  {
    quote: "Aisha handles 400+ calls/day for our real estate projects. Our site-visit bookings went up 3x in the first month.",
    name: 'Rahul M.',
    role: 'Sales Head, Realty Group',
    stars: 5
  },
  {
    quote: "We were spending ₹4L/month on a telecalling team. Aisha replaced 80% of that workload and the quality is better.",
    name: 'Priya S.',
    role: 'Founder, InsureTech Startup',
    stars: 5
  },
  {
    quote: "The Hindi + English code-switching is incredible. Our customers in tier-2 cities actually prefer talking to Aisha.",
    name: 'Vikram T.',
    role: 'COO, EdTech Platform',
    stars: 5
  },
];

const Testimonials = () => (
  <section className="py-24 px-6">
    <div className="max-w-6xl mx-auto">
      <div className="text-center mb-16">
        <p className="text-violet-400 text-sm font-semibold uppercase tracking-widest mb-3">Testimonials</p>
        <h2 className="text-3xl md:text-5xl font-bold mb-4">What our clients say</h2>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {testimonials.map((t, i) => (
          <div key={i} className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 flex flex-col">
            <div className="flex gap-1 mb-4">
              {Array.from({ length: t.stars }).map((_, j) => (
                <Star key={j} className="w-4 h-4 text-amber-400 fill-amber-400" />
              ))}
            </div>
            <p className="text-slate-300 text-sm leading-relaxed flex-1 mb-6">"{t.quote}"</p>
            <div>
              <p className="text-white font-semibold text-sm">{t.name}</p>
              <p className="text-slate-500 text-xs">{t.role}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  </section>
);

/* ------------------------------------------------------------------ */
/*  WHY AISHA (VALUE PROPS)                                            */
/* ------------------------------------------------------------------ */
const whyItems = [
  { text: '100% custom-built for your business — no generic templates' },
  { text: 'Dedicated onboarding & prompt engineering team' },
  { text: 'Real-time analytics dashboard included' },
  { text: 'CRM, webhook, and API integrations at no extra cost' },
  { text: 'Scales from 100 to 10,000+ calls/day' },
  { text: 'Pay only for what you use — no lock-in contracts' },
];

const WhyAisha = () => (
  <section className="py-24 px-6 bg-slate-900/30">
    <div className="max-w-5xl mx-auto">
      <div className="grid md:grid-cols-2 gap-12 items-center">
        <div>
          <p className="text-indigo-400 text-sm font-semibold uppercase tracking-widest mb-3">Why Aisha AI</p>
          <h2 className="text-3xl md:text-4xl font-bold mb-4">Custom solutions, not cookie-cutter plans</h2>
          <p className="text-slate-400 leading-relaxed mb-8">
            We don't believe in one-price-fits-all SaaS tiers. Your business is unique — your AI agent should be too. We work with you to design, build, and optimize an agent that fits your exact needs and budget.
          </p>
          <ul className="space-y-3">
            {whyItems.map((item, i) => (
              <li key={i} className="flex items-start gap-3">
                <CheckCircle2 className="w-5 h-5 text-emerald-400 flex-shrink-0 mt-0.5" />
                <span className="text-slate-300 text-sm">{item.text}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Stats panel */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-8">
          <div className="grid grid-cols-2 gap-8">
            <StatBlock value="10+" label="Languages Supported" />
            <StatBlock value="50K+" label="Calls Made" />
            <StatBlock value="3x" label="Avg. Lead Conversion" />
            <StatBlock value="24/7" label="Always Available" />
          </div>
        </div>
      </div>
    </div>
  </section>
);

const StatBlock = ({ value, label }) => (
  <div className="text-center">
    <p className="text-3xl md:text-4xl font-bold bg-gradient-to-r from-indigo-400 to-violet-400 bg-clip-text text-transparent">{value}</p>
    <p className="text-slate-500 text-xs mt-1 font-medium">{label}</p>
  </div>
);

/* ------------------------------------------------------------------ */
/*  FAQ                                                                */
/* ------------------------------------------------------------------ */
const faqs = [
  { q: 'Do you have fixed pricing plans?', a: 'No. Every business has different needs — different call volumes, languages, integrations, and workflows. We build a custom proposal after understanding your requirements on a free discovery call.' },
  { q: 'How long does it take to go live?', a: 'Most clients are live within 5–7 business days. Complex multi-language setups with deep CRM integrations may take 2 weeks.' },
  { q: 'Can Aisha handle inbound calls too?', a: 'Yes. While our core strength is outbound, we can configure Aisha to handle inbound IVR, lead routing, and customer support calls as well.' },
  { q: 'What languages does Aisha support?', a: 'Hindi, English, Hinglish, Bengali, Tamil, Telugu, Marathi, Gujarati, Kannada, Malayalam, Punjabi, Odia — and we\'re adding more. Aisha can also switch languages mid-call.' },
  { q: 'How does billing work?', a: 'We offer flexible usage-based billing. You pay based on call volume, features used, and the level of customization — no upfront lock-in or hidden fees.' },
  { q: 'Can I integrate Aisha with my CRM?', a: 'Absolutely. We integrate with Salesforce, HubSpot, Zoho, Google Sheets, and any platform that supports webhooks or REST APIs.' },
];

const FAQ = () => {
  const [openIdx, setOpenIdx] = useState(null);
  return (
    <section id="faq" className="py-24 px-6">
      <div className="max-w-3xl mx-auto">
        <div className="text-center mb-16">
          <p className="text-cyan-400 text-sm font-semibold uppercase tracking-widest mb-3">FAQ</p>
          <h2 className="text-3xl md:text-5xl font-bold mb-4">Common questions</h2>
        </div>

        <div className="space-y-3">
          {faqs.map((f, i) => (
            <div key={i} className="border border-slate-800 rounded-xl overflow-hidden">
              <button
                onClick={() => setOpenIdx(openIdx === i ? null : i)}
                className="w-full flex items-center justify-between px-6 py-4 text-left hover:bg-slate-900/40 transition-colors"
              >
                <span className="text-sm font-medium text-white pr-4">{f.q}</span>
                {openIdx === i
                  ? <ChevronUp className="w-4 h-4 text-slate-400 flex-shrink-0" />
                  : <ChevronDown className="w-4 h-4 text-slate-400 flex-shrink-0" />}
              </button>
              {openIdx === i && (
                <div className="px-6 pb-4">
                  <p className="text-slate-400 text-sm leading-relaxed">{f.a}</p>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

/* ------------------------------------------------------------------ */
/*  FINAL CTA                                                          */
/* ------------------------------------------------------------------ */
const FinalCTA = ({ navigate }) => (
  <section className="py-24 px-6">
    <div className="max-w-4xl mx-auto text-center">
      <div className="bg-gradient-to-br from-indigo-600/20 via-violet-600/10 to-slate-900 border border-indigo-500/20 rounded-3xl p-12 md:p-16">
        <Bot className="w-12 h-12 text-indigo-400 mx-auto mb-6" />
        <h2 className="text-3xl md:text-5xl font-bold mb-4">Ready to automate your outbound?</h2>
        <p className="text-slate-400 max-w-xl mx-auto mb-8 leading-relaxed">
          Tell us about your business, and we'll design a custom AI voice agent that works exactly the way you need. No commitments — just a conversation.
        </p>
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <button
            onClick={() => navigate('/sign-up')}
            className="group bg-indigo-600 hover:bg-indigo-500 text-white px-8 py-4 rounded-xl text-lg font-semibold transition-all hover:scale-[1.02] shadow-lg shadow-indigo-600/25 flex items-center gap-2"
          >
            Book a Free Discovery Call
            <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
          </button>
        </div>
        <p className="text-slate-500 text-xs mt-6">No fixed pricing. No generic plans. 100% custom.</p>
      </div>
    </div>
  </section>
);

/* ------------------------------------------------------------------ */
/*  FOOTER                                                             */
/* ------------------------------------------------------------------ */
const Footer = ({ navigate }) => (
  <footer className="border-t border-slate-800/60 py-12 px-6">
    <div className="max-w-6xl mx-auto">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-10 mb-10">
        {/* Branding */}
        <div className="md:col-span-1">
          <div className="flex items-center gap-2 mb-3">
            <Activity className="w-6 h-6 text-indigo-400" />
            <span className="font-bold text-lg">Aisha AI</span>
          </div>
          <p className="text-slate-500 text-sm leading-relaxed">
            AI voice agents custom-built for Indian businesses. Automate outbound. Multiply revenue.
          </p>
        </div>

        {/* Links */}
        <div>
          <h4 className="text-white text-sm font-semibold mb-4">Product</h4>
          <ul className="space-y-2 text-sm text-slate-400">
            <li><a href="#features" className="hover:text-white transition-colors">Features</a></li>
            <li><a href="#how-it-works" className="hover:text-white transition-colors">How It Works</a></li>
            <li><a href="#use-cases" className="hover:text-white transition-colors">Industries</a></li>
            <li><a href="#faq" className="hover:text-white transition-colors">FAQ</a></li>
          </ul>
        </div>

        <div>
          <h4 className="text-white text-sm font-semibold mb-4">Company</h4>
          <ul className="space-y-2 text-sm text-slate-400">
            <li><a href="#" className="hover:text-white transition-colors">About</a></li>
            <li><a href="#" className="hover:text-white transition-colors">Blog</a></li>
            <li><a href="#" className="hover:text-white transition-colors">Careers</a></li>
            <li><a href="#" className="hover:text-white transition-colors">Contact</a></li>
          </ul>
        </div>

        <div>
          <h4 className="text-white text-sm font-semibold mb-4">Legal</h4>
          <ul className="space-y-2 text-sm text-slate-400">
            <li><a href="#" className="hover:text-white transition-colors">Privacy Policy</a></li>
            <li><a href="#" className="hover:text-white transition-colors">Terms of Service</a></li>
            <li><a href="#" className="hover:text-white transition-colors">Refund Policy</a></li>
          </ul>
        </div>
      </div>

      <div className="border-t border-slate-800 pt-8 flex flex-col md:flex-row items-center justify-between gap-4">
        <p className="text-slate-500 text-sm">&copy; {new Date().getFullYear()} Aisha AI. All rights reserved.</p>
        <p className="text-slate-600 text-xs">Made with purpose for Indian businesses</p>
      </div>
    </div>
  </footer>
);

export default LandingPage;
