import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import type { WhatIfResponse } from '../services/api';
import { Sliders, BarChart2 } from 'lucide-react';

export const WhatIf: React.FC = () => {
  const [maxRetries, setMaxRetries] = useState(3);
  const [minConfidence, setMinConfidence] = useState(0.70);
  const [windowHours, setWindowHours] = useState(72);
  const [maxAmount, setMaxAmount] = useState(40000);
  
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<WhatIfResponse | null>(null);

  const calculateWhatIf = async () => {
    try {
      setLoading(true);
      const data = await api.runWhatIf({
        max_retries: maxRetries,
        min_confidence: minConfidence,
        recovery_window_hours: windowHours,
        max_automated_amount: maxAmount
      });
      setResult(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    calculateWhatIf();
  }, [maxRetries, minConfidence, windowHours, maxAmount]);

  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(val);
  };

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Title */}
      <div>
        <h2 className="text-3xl font-extrabold tracking-tight text-white">What-If Policy Analyzer</h2>
        <p className="text-slate-400 mt-1 text-sm">Fine-tune recovery rules and observe the direct impact on money recovered vs merchant outreach overhead.</p>
      </div>

      {/* Grid: Sliders on left, Results on right */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Side: Sliders Controls */}
        <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl space-y-6 shadow-lg h-fit">
          <div className="flex items-center space-x-2 border-b border-slate-800 pb-3">
            <Sliders className="w-5 h-5 text-accent-blue" />
            <h3 className="text-sm font-bold text-white uppercase tracking-wider">Policy Variables</h3>
          </div>

          {/* Slider 1: Max Retries */}
          <div>
            <div className="flex justify-between text-xs font-semibold mb-2">
              <span className="text-slate-400">Max Auto Retries</span>
              <span className="text-white">{maxRetries} attempts</span>
            </div>
            <input
              type="range"
              min="1"
              max="5"
              value={maxRetries}
              onChange={(e) => setMaxRetries(Number(e.target.value))}
              className="w-full h-1 bg-slate-950 rounded-lg appearance-none cursor-pointer accent-accent-blue"
            />
          </div>

          {/* Slider 2: Confidence Threshold */}
          <div>
            <div className="flex justify-between text-xs font-semibold mb-2">
              <span className="text-slate-400">Min ML Confidence</span>
              <span className="text-white">{Math.round(minConfidence * 100)}%</span>
            </div>
            <input
              type="range"
              min="0.10"
              max="0.95"
              step="0.05"
              value={minConfidence}
              onChange={(e) => setMinConfidence(Number(e.target.value))}
              className="w-full h-1 bg-slate-950 rounded-lg appearance-none cursor-pointer accent-accent-blue"
            />
          </div>

          {/* Slider 3: Max Automated Amount */}
          <div>
            <div className="flex justify-between text-xs font-semibold mb-2">
              <span className="text-slate-400">Max Automated Amount</span>
              <span className="text-white">{formatCurrency(maxAmount)}</span>
            </div>
            <input
              type="range"
              min="5000"
              max="150000"
              step="5000"
              value={maxAmount}
              onChange={(e) => setMaxAmount(Number(e.target.value))}
              className="w-full h-1 bg-slate-950 rounded-lg appearance-none cursor-pointer accent-accent-blue"
            />
          </div>

          {/* Slider 4: Recovery Window */}
          <div>
            <div className="flex justify-between text-xs font-semibold mb-2">
              <span className="text-slate-400">Recovery Window Hours</span>
              <span className="text-white">{windowHours} hours</span>
            </div>
            <input
              type="range"
              min="24"
              max="168"
              step="12"
              value={windowHours}
              onChange={(e) => setWindowHours(Number(e.target.value))}
              className="w-full h-1 bg-slate-950 rounded-lg appearance-none cursor-pointer accent-accent-blue"
            />
          </div>
        </div>

        {/* Right Side: Comparisons List & Summary */}
        <div className="lg:col-span-2 space-y-6">
          {loading && !result ? (
            <div className="p-12 text-center text-slate-500 font-medium">Running What-If calculations...</div>
          ) : result ? (
            <div className="space-y-6">
              {/* Custom Policy Yield Card */}
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 relative overflow-hidden shadow-lg">
                <div className="absolute top-0 right-0 w-32 h-32 bg-accent-blue/5 rounded-full blur-3xl"></div>
                <div className="flex items-center space-x-2 text-xs font-bold text-accent-blue uppercase tracking-widest mb-3">
                  <BarChart2 className="w-4 h-4" />
                  <span>Predicted Outcome</span>
                </div>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
                  <div>
                    <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">Recovered Revenue</span>
                    <h4 className="text-xl font-bold text-white mt-1">{formatCurrency(result.current.recovered_revenue)}</h4>
                  </div>
                  <div>
                    <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">Recovery Rate</span>
                    <h4 className="text-xl font-bold text-accent-green mt-1">{result.current.recovery_rate}%</h4>
                  </div>
                  <div>
                    <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">Manual outreach load</span>
                    <h4 className="text-xl font-bold text-accent-orange mt-1">{result.current.manual_review_rate.toFixed(1)}%</h4>
                  </div>
                  <div>
                    <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">Fraud Shielded</span>
                    <h4 className="text-xl font-bold text-accent-red mt-1">{result.current.blocked_actions_count} blocked</h4>
                  </div>
                </div>
                <div className="p-3 bg-slate-950/60 border border-slate-850 rounded-xl mt-4 text-xs text-slate-400 font-medium">
                  {result.explanation}
                </div>
              </div>

              {/* Comparison Presets Grid */}
              <div className="space-y-3">
                <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Compare Presets</h4>
                
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {result.presets.map((p, idx) => {
                    const isBalanced = p.preset_name === 'Balanced';
                    return (
                      <div 
                        key={idx} 
                        className={`bg-slate-900 border rounded-xl p-4 shadow transition-all duration-200 ${
                          isBalanced ? 'border-accent-blue/50' : 'border-slate-800'
                        }`}
                      >
                        <div className="flex justify-between items-center mb-3">
                          <span className="text-xs font-bold text-white uppercase tracking-wider">{p.preset_name}</span>
                          {isBalanced && (
                            <span className="px-2 py-0.5 rounded bg-accent-blue/10 text-[9px] text-accent-blue font-bold">RECOMMENDED</span>
                          )}
                        </div>
                        <div className="space-y-2 text-xs">
                          <div className="flex justify-between text-slate-500 font-medium">
                            <span>Max Retries</span>
                            <span className="text-slate-300 font-semibold">{p.max_retries} attempts</span>
                          </div>
                          <div className="flex justify-between text-slate-500 font-medium">
                            <span>Min Conf.</span>
                            <span className="text-slate-300 font-semibold">{Math.round(p.min_confidence * 100)}%</span>
                          </div>
                          <div className="flex justify-between text-slate-500 font-medium">
                            <span>Max Amt</span>
                            <span className="text-slate-300 font-semibold">{formatCurrency(p.max_automated_amount)}</span>
                          </div>
                          <hr className="border-slate-800 my-1" />
                          <div className="flex justify-between text-slate-400 font-semibold">
                            <span>Recovery Rate</span>
                            <span className="text-accent-green font-bold">{p.recovery_rate}%</span>
                          </div>
                          <div className="flex justify-between text-slate-400 font-semibold">
                            <span>Outreach Load</span>
                            <span className="text-accent-orange font-bold">{p.manual_review_rate.toFixed(0)}%</span>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
};
