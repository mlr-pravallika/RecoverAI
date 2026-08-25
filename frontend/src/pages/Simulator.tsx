import React, { useState } from 'react';
import { api } from '../services/api';
import type { SimulationResponse } from '../services/api';
import { 
  Play, 
  RefreshCw
} from 'lucide-react';
import { 
  PieChart, 
  Pie, 
  Cell, 
  Tooltip, 
  ResponsiveContainer, 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid 
} from 'recharts';

export const Simulator: React.FC = () => {
  const [numTxs, setNumTxs] = useState(250);
  const [preset, setPreset] = useState('balanced');
  const [simRunning, setSimRunning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState<SimulationResponse | null>(null);

  const startSimulation = async () => {
    try {
      setSimRunning(true);
      setResult(null);
      setProgress(10);
      
      // Simulate frontend progress loader
      const interval = setInterval(() => {
        setProgress((prev) => {
          if (prev >= 90) {
            clearInterval(interval);
            return 90;
          }
          return prev + 15;
        });
      }, 300);

      const res = await api.runSimulation(numTxs, preset);
      clearInterval(interval);
      setProgress(100);
      
      setTimeout(() => {
        setResult(res);
        setSimRunning(false);
        setProgress(0);
      }, 500);

    } catch (err) {
      alert("Simulation failed: " + err);
      setSimRunning(false);
      setProgress(0);
    }
  };

  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(val);
  };

  // Convert strategy stats for chart
  const getStrategyChartData = () => {
    if (!result) return [];
    return Object.entries(result.strategy_distribution).map(([name, val]) => ({
      name,
      value: val as number,
    }));
  };

  // Convert failure code stats for chart
  const getFailureChartData = () => {
    if (!result) return [];
    return Object.entries(result.failure_distribution).map(([name, count]) => ({
      name: name.replace('BAD_REQUEST_PAYMENT_', ''),
      count,
    }));
  };

  const COLORS = ['#10b981', '#3b82f6', '#f59e0b', '#ef4444'];

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Title */}
      <div>
        <h2 className="text-3xl font-extrabold tracking-tight text-white">Batch Recovery Simulator</h2>
        <p className="text-slate-400 mt-1 text-sm">Execute simulated recovery workflows across historical checkout drops to analyze yield, intervention cost, and safety guardrails.</p>
      </div>

      {/* Control Panel Card */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-lg">
        <h3 className="text-base font-bold text-white mb-4">Simulation Controls</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-end">
          <div>
            <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-2">Batch Size (Failed Transactions)</label>
            <select
              value={numTxs}
              onChange={(e) => setNumTxs(Number(e.target.value))}
              disabled={simRunning}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-accent-blue"
            >
              <option value={100}>100 Transactions</option>
              <option value={250}>250 Transactions</option>
              <option value={500}>500 Transactions</option>
              <option value={750}>750 Transactions</option>
            </select>
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-2">Compliance Policy Preset</label>
            <select
              value={preset}
              onChange={(e) => setPreset(e.target.value)}
              disabled={simRunning}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-accent-blue"
            >
              <option value="conservative">Conservative (Min Confidence 85%, Max ₹15k)</option>
              <option value="balanced">Balanced (Min Confidence 70%, Max ₹40k)</option>
              <option value="aggressive">Aggressive (Min Confidence 50%, Max ₹100k)</option>
            </select>
          </div>

          <div>
            <button
              onClick={startSimulation}
              disabled={simRunning}
              className="w-full bg-accent-blue hover:bg-accent-blueHover disabled:bg-slate-800 text-white font-bold py-2.5 rounded-xl text-sm flex items-center justify-center space-x-2 transition-all shadow-lg shadow-accent-blue/20"
            >
              {simRunning ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>Executing Interventions...</span>
                </>
              ) : (
                <>
                  <Play className="w-4 h-4" />
                  <span>Run Bounded Recovery</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Progress Bar */}
        {simRunning && (
          <div className="mt-6 space-y-2">
            <div className="flex justify-between text-xs font-semibold text-slate-400">
              <span>Running model inference and policy audits...</span>
              <span>{progress}%</span>
            </div>
            <div className="w-full h-2 bg-slate-950 rounded-full overflow-hidden">
              <div 
                className="h-full bg-accent-blue transition-all duration-300 rounded-full" 
                style={{ width: `${progress}%` }}
              ></div>
            </div>
          </div>
        )}
      </div>

      {/* Output Results Panel */}
      {result && (
        <div className="space-y-8 animate-fadeIn">
          {/* Main KPI Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">Revenue At Risk</span>
              <h4 className="text-2xl font-bold text-white mt-2">{formatCurrency(result.revenue_at_risk)}</h4>
              <p className="text-xs text-slate-500 mt-1">From {result.transactions_analyzed} analyzed drops</p>
            </div>

            <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">Actual Money Recovered</span>
              <h4 className="text-2xl font-bold text-accent-green mt-2">{formatCurrency(result.recovered_revenue)}</h4>
              <p className="text-xs text-slate-500 mt-1">Credited to Razorpay Test Mode</p>
            </div>

            <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">Net Recovery Rate</span>
              <h4 className="text-2xl font-bold text-white mt-2">{result.recovery_rate}%</h4>
              <p className="text-xs text-slate-500 mt-1">Intervention success ratio</p>
            </div>

            <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">Policy Safety blocks</span>
              <h4 className="text-2xl font-bold text-accent-red mt-2">{result.unsafe_actions_prevented} cases</h4>
              <p className="text-xs text-slate-500 mt-1">Fraud/unauthorized vetoes</p>
            </div>
          </div>

          {/* secondary stats and charts grid */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Strategy distribution pie chart */}
            <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl shadow">
              <h3 className="text-sm font-bold text-white mb-4">Intervention Distribution</h3>
              <div className="h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={getStrategyChartData()}
                      cx="50%"
                      cy="50%"
                      innerRadius={50}
                      outerRadius={75}
                      paddingAngle={4}
                      dataKey="value"
                    >
                      {getStrategyChartData().map((_, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1e293b', borderRadius: '12px' }} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="space-y-1.5 mt-2">
                {getStrategyChartData().map((item, idx) => (
                  <div key={idx} className="flex justify-between text-xs font-medium">
                    <div className="flex items-center space-x-1.5">
                      <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: COLORS[idx % COLORS.length] }}></div>
                      <span className="text-slate-400">{item.name}</span>
                    </div>
                    <span className="text-white font-semibold">{item.value} times</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Failure category analysis */}
            <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl shadow lg:col-span-2">
              <h3 className="text-sm font-bold text-white mb-4">Simulation Failure Code Yield</h3>
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={getFailureChartData()}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis dataKey="name" stroke="#64748b" tick={{ fontSize: 10 }} />
                    <YAxis stroke="#64748b" tick={{ fontSize: 10 }} />
                    <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1e293b', borderRadius: '12px' }} />
                    <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
