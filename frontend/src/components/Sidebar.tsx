import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  LayoutDashboard, 
  ListFilter, 
  PlayCircle, 
  Sliders, 
  History, 
  Settings, 
  ShieldCheck,
  LogOut,
  Activity
} from 'lucide-react';
import { api } from '../services/api';
import type { Merchant, RazorpayStatus } from '../services/api';

interface SidebarProps {
  currentTab: string;
  setCurrentTab: (tab: string) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ currentTab, setCurrentTab }) => {
  const navigate = useNavigate();
  const [merchant, setMerchant] = useState<Merchant | null>(null);
  const [rzpStatus, setRzpStatus] = useState<RazorpayStatus>({ connected: false, mode: 'test' });

  useEffect(() => {
    // 1. Fetch merchant details
    api.getMerchantProfile()
      .then(setMerchant)
      .catch((err) => {
        console.error('Failed to load merchant profile:', err);
        // Clear expired tokens automatically
        api.logout();
        navigate('/login');
      });

    // 2. Fetch Razorpay connectivity status
    const checkStatus = () => {
      api.getRazorpayStatus()
        .then(setRzpStatus)
        .catch((err) => console.error('Failed to load Razorpay status:', err));
    };

    checkStatus();
    // Poll connection status every 10 seconds for real-time validation
    const interval = setInterval(checkStatus, 10000);
    return () => clearInterval(interval);
  }, [navigate]);

  const handleLogout = () => {
    api.logout();
    navigate('/login');
  };

  const menuItems = [
    { id: 'overview', label: 'Overview', icon: LayoutDashboard },
    { id: 'queue', label: 'Recovery Queue', icon: ListFilter },
    { id: 'simulator', label: 'Batch Simulator', icon: PlayCircle },
    { id: 'whatif', label: 'What-If Analyzer', icon: Sliders },
    { id: 'audit', label: 'Audit Trail', icon: History },
    { id: 'settings', label: 'Policy Rules', icon: Settings },
  ];

  return (
    <aside className="w-64 bg-slate-900 border-r border-slate-800 flex flex-col justify-between h-screen fixed left-0 top-0 z-20 select-none">
      <div className="flex flex-col">
        {/* Brand Header */}
        <div className="p-6 border-b border-slate-800 flex items-center space-x-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/25">
            <ShieldCheck className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-sm font-bold tracking-tight text-white leading-tight">RecoverAI</h1>
            <p className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider">Revenue Recovery</p>
          </div>
        </div>

        {/* User profile section */}
        {merchant && (
          <div className="px-6 py-4 border-b border-slate-800/60 bg-slate-950/20">
            <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block">Merchant Account</span>
            <span className="text-sm font-semibold text-slate-200 block truncate">{merchant.business_name}</span>
            <span className="text-[11px] text-slate-400 block truncate">{merchant.owner_name}</span>
          </div>
        )}

        {/* Integration Status indicators */}
        <div className="px-6 py-3 border-b border-slate-800/40 space-y-1.5 text-xs text-slate-400">
          <div className="flex items-center justify-between">
            <span className="flex items-center space-x-1.5">
              <Activity className="w-3.5 h-3.5 text-slate-500" />
              <span>Razorpay API</span>
            </span>
            <span className="flex items-center space-x-1">
              <span className={`w-1.5 h-1.5 rounded-full ${rzpStatus.connected ? 'bg-emerald-400' : 'bg-rose-500 animate-pulse'}`}></span>
              <span className={`text-[10px] font-bold ${rzpStatus.connected ? 'text-emerald-400' : 'text-rose-500'}`}>
                {rzpStatus.connected ? 'Connected' : 'Disconnected'}
              </span>
            </span>
          </div>
          
          <div className="flex items-center justify-between">
            <span>Environment</span>
            {merchant?.mode === 'real' ? (
              <span className="px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/20 text-[9px] text-emerald-400 font-extrabold uppercase">
                Real Test Mode
              </span>
            ) : (
              <span className="px-2 py-0.5 rounded bg-amber-500/10 border border-amber-500/20 text-[9px] text-amber-400 font-extrabold uppercase">
                Demo Mode
              </span>
            )}
          </div>
        </div>

        {/* Navigation Menu */}
        <nav className="mt-6 px-4 space-y-1">
          {menuItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentTab === item.id;
            
            // In REAL Mode, Batch Simulator is disabled or hid. The prompt says: "Separate DEMO and REAL. Batch simulator is demo/synthetic only. Metrics in REAL must be real."
            // Let's show simulator as disabled or restrict it in Real mode!
            const isRestricted = item.id === 'simulator' && merchant?.mode === 'real';
            
            return (
              <button
                key={item.id}
                onClick={() => {
                  if (!isRestricted) setCurrentTab(item.id);
                }}
                disabled={isRestricted}
                className={`w-full flex items-center space-x-3 px-4 py-3 rounded-lg text-sm font-medium transition-all duration-150 ${
                  isRestricted
                    ? 'opacity-40 cursor-not-allowed text-slate-600'
                    : isActive
                      ? 'bg-gradient-to-r from-cyan-500 to-blue-600 text-white shadow-lg shadow-cyan-500/15'
                      : 'text-slate-400 hover:bg-slate-800 hover:text-slate-100'
                }`}
              >
                <Icon className={`w-5 h-5 ${isActive && !isRestricted ? 'text-white' : 'text-slate-400'}`} />
                <span>{item.label}</span>
                {isRestricted && <span className="text-[9px] bg-slate-800 px-1 py-0.5 rounded text-slate-500">Demo Only</span>}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Footer Info & Logout */}
      <div className="p-4 border-t border-slate-800 flex flex-col space-y-3">
        <button 
          onClick={handleLogout}
          className="w-full flex items-center space-x-3 px-4 py-2.5 rounded-lg text-xs font-semibold text-slate-400 hover:bg-red-500/10 hover:text-red-400 transition-colors"
        >
          <LogOut className="w-4 h-4" />
          <span>Sign Out</span>
        </button>
      </div>
    </aside>
  );
};
