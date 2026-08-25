import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import type { DashboardSummary } from '../services/api';
import { 
  TrendingUp, 
  AlertTriangle, 
  CheckCircle, 
  HelpCircle, 
  ArrowUpRight, 
  Activity, 
  ShieldAlert, 
  Users 
} from 'lucide-react';
import { 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer, 
  BarChart, 
  Bar, 
  PieChart, 
  Pie, 
  Cell 
} from 'recharts';

export const Overview: React.FC = () => {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchSummary = async () => {
      try {
        setLoading(true);
        const data = await api.getDashboardSummary();
        setSummary(data);
        setError(null);
      } catch (err: any) {
        setError(err.message || 'Failed to load summary');
      } finally {
        setLoading(false);
      }
    };
    fetchSummary();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-100px)]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-accent-blue"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 bg-red-950/20 border border-red-800/40 rounded-xl text-red-400">
        <h3 className="text-lg font-bold mb-2">Error Loading Dashboard</h3>
        <p>{error}</p>
      </div>
    );
  }

  if (!summary) return null;

  // Formatting helper
  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(val);
  };

  const failureCategories = [
    { name: 'Timeout', count: 180, amount: 250000, color: '#3b82f6' },
    { name: 'Bank Decline', count: 140, amount: 480000, color: '#f59e0b' },
    { name: 'Cancelled', count: 120, amount: 180000, color: '#10b981' },
    { name: 'Auth Failure', count: 100, amount: 150000, color: '#8b5cf6' },
    { name: 'Gateway Error', count: 40, amount: 80000, color: '#6366f1' },
    { name: 'Expired Card', count: 20, amount: 40000, color: '#ef4444' },
    { name: 'Fraud Suspicion', count: 10, amount: 60000, color: '#ec4899' },
  ];

  const strategyBreakdown = [
    { name: 'Retry', value: summary.recovered_revenue * 0.45, color: '#10b981' },
    { name: 'Payment Link', value: summary.recovered_revenue * 0.35, color: '#3b82f6' },
    { name: 'Manual Review', value: summary.recovered_revenue * 0.20, color: '#f59e0b' },
  ];

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Top Welcome Title */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-3xl font-extrabold tracking-tight text-white font-sans">Revenue Recovery Overview</h2>
          <p className="text-slate-400 mt-1 text-sm">Real-time revenue loss monitoring, root-cause diagnosis, and automated interventions.</p>
        </div>
        <div className="flex items-center space-x-2 bg-slate-900 border border-slate-800 px-4 py-2 rounded-xl text-xs text-slate-300 font-semibold shadow-inner">
          <Activity className="w-4 h-4 text-accent-green animate-pulse" />
          <span>Monitoring Razorpay Live Webhooks</span>
        </div>
      </div>

      {/* Hero KPIs Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* Card 1: Revenue at Risk */}
        <div className="bg-slate-900 border border-slate-800/80 rounded-2xl p-6 relative overflow-hidden shadow-lg group hover:border-slate-700/60 transition-all duration-200">
          <div className="absolute top-0 right-0 w-24 h-24 bg-accent-orange/5 rounded-full blur-2xl group-hover:bg-accent-orange/10 transition-all duration-300"></div>
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Active Revenue at Risk</span>
            <div className="p-2.5 rounded-xl bg-accent-orange/10 text-accent-orange">
              <AlertTriangle className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-4">
            <h3 className="text-2xl font-bold text-white tracking-tight">{formatCurrency(summary.revenue_at_risk)}</h3>
            <p className="text-xs text-slate-500 mt-1 flex items-center space-x-1">
              <span>Awaiting recovery execution</span>
            </p>
          </div>
        </div>

        {/* Card 2: Expected Recovery */}
        <div className="bg-slate-900 border border-slate-800/80 rounded-2xl p-6 relative overflow-hidden shadow-lg group hover:border-slate-700/60 transition-all duration-200">
          <div className="absolute top-0 right-0 w-24 h-24 bg-accent-purple/5 rounded-full blur-2xl group-hover:bg-accent-purple/10 transition-all duration-300"></div>
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Expected Recovery (Yield)</span>
            <div className="p-2.5 rounded-xl bg-accent-purple/10 text-accent-purple">
              <TrendingUp className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-4">
            <h3 className="text-2xl font-bold text-white tracking-tight">{formatCurrency(summary.expected_recovery)}</h3>
            <p className="text-xs text-slate-500 mt-1">Weighted probability calculations</p>
          </div>
        </div>

        {/* Card 3: Recovered Revenue */}
        <div className="bg-slate-900 border border-slate-800/80 rounded-2xl p-6 relative overflow-hidden shadow-lg group hover:border-slate-700/60 transition-all duration-200">
          <div className="absolute top-0 right-0 w-24 h-24 bg-accent-green/5 rounded-full blur-2xl group-hover:bg-accent-green/10 transition-all duration-300"></div>
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Recovered Revenue</span>
            <div className="p-2.5 rounded-xl bg-accent-green/10 text-accent-green">
              <CheckCircle className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-4">
            <h3 className="text-2xl font-bold text-white tracking-tight">{formatCurrency(summary.recovered_revenue)}</h3>
            <p className="text-xs text-slate-500 mt-1 flex items-center space-x-1">
              <span className="text-accent-green font-semibold">Matched successfully</span>
            </p>
          </div>
        </div>

        {/* Card 4: Recovery Rate */}
        <div className="bg-slate-900 border border-slate-800/80 rounded-2xl p-6 relative overflow-hidden shadow-lg group hover:border-slate-700/60 transition-all duration-200">
          <div className="absolute top-0 right-0 w-24 h-24 bg-accent-blue/5 rounded-full blur-2xl group-hover:bg-accent-blue/10 transition-all duration-300"></div>
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Recovery Success Rate</span>
            <div className="p-2.5 rounded-xl bg-accent-blue/10 text-accent-blue">
              <ArrowUpRight className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-4">
            <h3 className="text-2xl font-bold text-white tracking-tight">{summary.recovery_rate}%</h3>
            <p className="text-xs text-slate-500 mt-1">Failed checks recovered successfully</p>
          </div>
        </div>
      </div>

      {/* Secondary Recovery Pipeline Metrics */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl flex items-center justify-between shadow">
          <div className="flex items-center space-x-4">
            <div className="p-3 rounded-xl bg-slate-800 text-slate-300">
              <Users className="w-6 h-6" />
            </div>
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Active Recoveries</p>
              <h4 className="text-lg font-bold text-white mt-0.5">{summary.active_recoveries} Cases</h4>
            </div>
          </div>
          <span className="text-xs text-slate-400 font-medium">In State Machine</span>
        </div>

        <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl flex items-center justify-between shadow">
          <div className="flex items-center space-x-4">
            <div className="p-3 rounded-xl bg-accent-orange/10 text-accent-orange">
              <HelpCircle className="w-6 h-6" />
            </div>
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Manual Review Escalations</p>
              <h4 className="text-lg font-bold text-white mt-0.5">{summary.manual_reviews} Cases</h4>
            </div>
          </div>
          <span className="text-xs text-slate-400 font-medium">Require Outreach</span>
        </div>

        <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl flex items-center justify-between shadow">
          <div className="flex items-center space-x-4">
            <div className="p-3 rounded-xl bg-red-950/30 text-accent-red">
              <ShieldAlert className="w-6 h-6" />
            </div>
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Blocked Actions (Policy Veto)</p>
              <h4 className="text-lg font-bold text-white mt-0.5">{summary.blocked_actions} Interventions</h4>
            </div>
          </div>
          <span className="text-xs text-slate-400 font-medium">Fraud/Expired Safe</span>
        </div>
      </div>

      {/* Recharts Analytics Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Failure Categories Chart */}
        <div className="bg-slate-900 border border-slate-800/80 p-6 rounded-2xl lg:col-span-2 shadow-lg">
          <h3 className="text-base font-bold text-white mb-6 tracking-tight">Failure Reason Breakdown</h3>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={failureCategories} margin={{ top: 10, right: 10, left: 10, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="name" stroke="#64748b" tick={{ fontSize: 11 }} angle={-15} textAnchor="end" height={50} />
                <YAxis stroke="#64748b" tick={{ fontSize: 11 }} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1e293b', borderRadius: '12px' }}
                  labelStyle={{ fontWeight: 'bold', color: '#fff' }}
                />
                <Bar dataKey="amount" fill="#3b82f6" radius={[6, 6, 0, 0]}>
                  {failureCategories.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Strategy Yield Chart */}
        <div className="bg-slate-900 border border-slate-800/80 p-6 rounded-2xl shadow-lg flex flex-col justify-between">
          <div>
            <h3 className="text-base font-bold text-white mb-6 tracking-tight">Recovery Yield by Strategy</h3>
            <div className="h-60 flex items-center justify-center">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={strategyBreakdown}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={85}
                    paddingAngle={5}
                    dataKey="value"
                  >
                    {strategyBreakdown.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1e293b', borderRadius: '12px' }}
                    formatter={(value: any) => formatCurrency(Number(value))}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
          {/* Custom Legends */}
          <div className="space-y-2 mt-4">
            {strategyBreakdown.map((item, idx) => (
              <div key={idx} className="flex items-center justify-between text-xs font-semibold">
                <div className="flex items-center space-x-2">
                  <div className="w-3 h-3 rounded-full" style={{ backgroundColor: item.color }}></div>
                  <span className="text-slate-400">{item.name}</span>
                </div>
                <span className="text-white">{formatCurrency(item.value)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
