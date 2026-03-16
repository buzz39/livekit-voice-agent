import React from 'react';
import { Activity, Phone, Database, LayoutDashboard, Settings, BarChart, Calendar, LogOut, ChevronDown } from 'lucide-react';
import { useClerk, useUser } from '@clerk/clerk-react';

const DashboardLayout = ({ children, activeTab = 'command-center', onTabChange }) => {
  const { signOut } = useClerk();
  const { user } = useUser();

  const handleSignOut = () => {
    signOut({ redirectUrl: '/' });
  };

  const initials = user
    ? `${user.firstName?.[0] || ''}${user.lastName?.[0] || ''}`.toUpperCase() || user.emailAddresses?.[0]?.emailAddress?.[0]?.toUpperCase() || 'U'
    : 'U';

  return (
    <div className="flex h-screen bg-slate-950 text-white overflow-hidden">
      {/* Sidebar */}
      <aside className="w-16 md:w-64 bg-slate-900 border-r border-slate-800 flex flex-col">
        <div className="p-4 flex items-center gap-2 border-b border-slate-800">
          <Activity className="w-6 h-6 text-indigo-500" />
          <span className="font-bold text-xl hidden md:block">Aisha AI</span>
        </div>

        <nav className="flex-1 p-4 space-y-2">
          <NavItem
            icon={<LayoutDashboard />}
            label="Command Center"
            active={activeTab === 'command-center'}
            onClick={() => onTabChange && onTabChange('command-center')}
          />
          <NavItem
            icon={<BarChart />}
            label="Analytics"
            active={activeTab === 'analytics'}
            onClick={() => onTabChange && onTabChange('analytics')}
          />
          <NavItem
            icon={<Phone />}
            label="Call Logs"
            active={activeTab === 'call-logs'}
            onClick={() => onTabChange && onTabChange('call-logs')}
          />
          <NavItem
            icon={<Calendar />}
            label="Calendar"
            active={activeTab === 'calendar'}
            onClick={() => onTabChange && onTabChange('calendar')}
          />
          <NavItem
            icon={<Database />}
            label="Database"
            active={activeTab === 'database'}
            onClick={() => onTabChange && onTabChange('database')}
          />
          <NavItem
            icon={<Settings />}
            label="Settings"
            active={activeTab === 'settings'}
            onClick={() => onTabChange && onTabChange('settings')}
          />
        </nav>

        {/* User footer */}
        <div className="p-4 border-t border-slate-800">
          <div className="flex items-center gap-2">
            {user?.imageUrl ? (
              <img
                src={user.imageUrl}
                alt="Avatar"
                className="w-8 h-8 rounded-full object-cover"
              />
            ) : (
              <div className="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center flex-shrink-0">
                <span className="font-bold text-xs">{initials}</span>
              </div>
            )}
            <div className="hidden md:block flex-1 min-w-0">
              <div className="text-sm font-medium truncate">
                {user?.fullName || user?.emailAddresses?.[0]?.emailAddress || 'User'}
              </div>
              <div className="text-xs text-slate-400 truncate">
                {user?.emailAddresses?.[0]?.emailAddress || ''}
              </div>
            </div>
            <button
              onClick={handleSignOut}
              title="Sign Out"
              className="hidden md:flex items-center justify-center w-7 h-7 rounded-md text-slate-400 hover:text-red-400 hover:bg-slate-800 transition-colors flex-shrink-0"
            >
              <LogOut size={15} />
            </button>
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

const NavItem = ({ icon, label, active, onClick }) => {
  return (
    <div
      onClick={onClick}
      className={`flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-colors ${active ? 'bg-indigo-500/10 text-indigo-400' : 'text-slate-400 hover:bg-slate-800 hover:text-slate-100'}`}
    >
      {React.cloneElement(icon, { size: 20 })}
      <span className="hidden md:block font-medium">{label}</span>
    </div>
  );
};

export default DashboardLayout;
