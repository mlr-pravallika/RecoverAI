import React from 'react';
import { 
  LayoutDashboard, 
  ListFilter, 
  PlayCircle, 
  Sliders, 
  History, 
  Settings, 
  ShieldCheck 
} from 'lucide-react';

interface SidebarProps {
  currentTab: string;
  setCurrentTab: (tab: string) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ currentTab, setCurrentTab }) => {
  const menuItems = [
    { id: 'overview', label: 'Overview', icon: LayoutDashboard },
    { id: 'queue', label: 'Recovery Queue', icon: ListFilter },
    { id: 'simulator', label: 'Batch Simulator', icon: PlayCircle },
    { id: 'whatif', label: 'What-If Analyzer', icon: Sliders },
    { id: 'audit', label: 'Audit Trail', icon: History },
    { id: 'settings', label: 'Policy Rules', icon: Settings },
  ];

  return (
    <aside className="w-64 bg-slate-900 border-r border-slate-800 flex flex-col justify-between h-screen fixed left-0 top-0 z-20">
      <div className="flex flex-col">
        {/* Brand Header */}
        <div className="p-6 border-b border-slate-800 flex items-center space-x-3">
          <div className="w-8 h-8 rounded-lg bg-accent-blue flex items-center justify-center">
            <ShieldCheck className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold tracking-tight text-white">RecoverAI</h1>
            <p className="text-xs text-slate-400 font-medium">AI Revenue Recovery</p>
          </div>
        </div>

        {/* Navigation Menu */}
        <nav className="mt-6 px-4 space-y-1">
          {menuItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setCurrentTab(item.id)}
                className={`w-full flex items-center space-x-3 px-4 py-3 rounded-lg text-sm font-medium transition-all duration-150 ${
                  isActive
                    ? 'bg-accent-blue text-white shadow-lg shadow-accent-blue/20'
                    : 'text-slate-400 hover:bg-slate-800 hover:text-slate-100'
                }`}
              >
                <Icon className={`w-5 h-5 ${isActive ? 'text-white' : 'text-slate-400'}`} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>
      </div>

      {/* Footer Info */}
      <div className="p-6 border-t border-slate-800">
        <div className="flex items-center justify-between text-xs text-slate-500 font-medium">
          <span>Razorpay Buildathon</span>
          <span className="px-2 py-0.5 rounded bg-slate-800 text-[10px] text-accent-blue font-semibold">Test Mode</span>
        </div>
      </div>
    </aside>
  );
};
