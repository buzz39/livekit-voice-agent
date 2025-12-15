import React from 'react';
import { Activity, Phone, Database, LayoutDashboard } from 'lucide-react';

const DashboardLayout = ({ children }) => {
  return (
    <div className="flex h-screen bg-slate-950 text-white overflow-hidden">
      {/* Sidebar */}
      <aside className="w-16 md:w-64 bg-slate-900 border-r border-slate-800 flex flex-col">
        <div className="p-4 flex items-center gap-2 border-b border-slate-800">
          <Activity className="w-6 h-6 text-indigo-500" />
          <span className="font-bold text-xl hidden md:block">Vaani</span>
        </div>

        <nav className="flex-1 p-4 space-y-2">
          <NavItem icon={<LayoutDashboard />} label="Command Center" active />
          <NavItem icon={<Phone />} label="Call Logs" />
          <NavItem icon={<Database />} label="Database" />
        </nav>

        <div className="p-4 border-t border-slate-800">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center">
              <span className="font-bold text-xs">AD</span>
            </div>
            <div className="hidden md:block">
              <div className="text-sm font-medium">Admin User</div>
              <div className="text-xs text-slate-400">admin@vaani.ai</div>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-auto bg-slate-950 p-4 md:p-8">
        <div className="max-w-7xl mx-auto h-full">
          {children}
        </div>
      </main>
    </div>
  );
};

const NavItem = ({ icon, label, active }) => {
  return (
    <div className={`flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-colors ${active ? 'bg-indigo-500/10 text-indigo-400' : 'text-slate-400 hover:bg-slate-800 hover:text-slate-100'}`}>
      {React.cloneElement(icon, { size: 20 })}
      <span className="hidden md:block font-medium">{label}</span>
    </div>
  );
};

export default DashboardLayout;
