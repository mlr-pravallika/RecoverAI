import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import { Sliders, Save, Sparkles, Send } from 'lucide-react';

export const Settings: React.FC = () => {
  const [maxRetries, setMaxRetries] = useState(3);
  const [minConfidence, setMinConfidence] = useState(0.70);
  const [windowHours, setWindowHours] = useState(72);
  const [maxAmount, setMaxAmount] = useState(40000);
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Load configuration
  useEffect(() => {
    const loadConfig = async () => {
      try {
        const config = await api.getPolicyConfig();
        setMaxRetries(config.max_retries);
        setMinConfidence(config.min_confidence);
        setWindowHours(config.recovery_window_hours);
        setMaxAmount(config.max_automated_amount);
      } catch (err) {
        console.error(err);
      }
    };
    loadConfig();
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setSaving(true);
      await api.updatePolicyConfig({
        max_retries: maxRetries,
        min_confidence: minConfidence,
        recovery_window_hours: windowHours,
        max_automated_amount: maxAmount
      });
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err) {
      alert("Failed to update config: " + err);
    } finally {
      setSaving(false);
    }
  };

  const handleSimulateScenario = async (scenario: string) => {
    try {
      const res = await api.triggerDemoFailure(scenario);
      alert(`Demo transaction triggered successfully!\nID: ${res.transaction_id}\nScenario: ${res.description}\nPolicy Result: ${res.analysis.policy_decision}`);
    } catch (err) {
      alert("Simulation failed: " + err);
    }
  };

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Title */}
      <div>
        <h2 className="text-3xl font-extrabold tracking-tight text-white">System Settings & Controls</h2>
        <p className="text-slate-400 mt-1 text-sm">Manage active compliance rules and trigger custom failure scenarios for testing.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Left Side: Rule Engine Policy Config Editor */}
        <form onSubmit={handleSave} className="bg-slate-900 border border-slate-800 p-6 rounded-2xl space-y-6 shadow-lg">
          <div className="flex items-center space-x-2 border-b border-slate-800 pb-3">
            <Sliders className="w-5 h-5 text-accent-blue" />
            <h3 className="text-base font-bold text-white">Active Policy Configurations</h3>
          </div>

          <div className="space-y-4">
            <div>
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-2">Max Automated Retries</label>
              <input
                type="number"
                min="1"
                max="5"
                value={maxRetries}
                onChange={(e) => setMaxRetries(Number(e.target.value))}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2 text-sm text-slate-200 focus:outline-none focus:border-accent-blue"
              />
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-2">Min ML Confidence Threshold</label>
              <input
                type="number"
                min="0.1"
                max="1.0"
                step="0.05"
                value={minConfidence}
                onChange={(e) => setMinConfidence(Number(e.target.value))}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2 text-sm text-slate-200 focus:outline-none focus:border-accent-blue"
              />
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-2">Max Automated Recovery Amount (₹)</label>
              <input
                type="number"
                min="1000"
                max="100000"
                step="5000"
                value={maxAmount}
                onChange={(e) => setMaxAmount(Number(e.target.value))}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2 text-sm text-slate-200 focus:outline-none focus:border-accent-blue"
              />
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-2">Recovery Window Hours</label>
              <input
                type="number"
                min="12"
                max="168"
                step="12"
                value={windowHours}
                onChange={(e) => setWindowHours(Number(e.target.value))}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2 text-sm text-slate-200 focus:outline-none focus:border-accent-blue"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={saving}
            className="w-full bg-accent-blue hover:bg-accent-blueHover text-white font-bold py-2.5 rounded-xl text-sm flex items-center justify-center space-x-2 transition-all shadow-lg shadow-accent-blue/20"
          >
            <Save className="w-4 h-4" />
            <span>{saving ? 'Saving...' : 'Save Rules Config'}</span>
          </button>

          {saveSuccess && (
            <div className="text-xs text-accent-green font-bold text-center mt-2 animate-pulse">
              Configurations saved and applied to live policy check engine!
            </div>
          )}
        </form>

        {/* Right Side: Demo Trigger Panel */}
        <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl space-y-6 shadow-lg">
          <div className="flex items-center space-x-2 border-b border-slate-800 pb-3">
            <Sparkles className="w-5 h-5 text-accent-orange" />
            <h3 className="text-base font-bold text-white">Trigger Demo Failure Scenarios</h3>
          </div>

          <p className="text-xs text-slate-400 font-medium leading-relaxed">
            Click any failure scenario to trigger a simulated webhook payload. This will instantly seed a failed transaction and invoke the orchestrator state machine.
          </p>

          <div className="space-y-3">
            {/* Case A: Temporary failure -> RETRY */}
            <div className="p-3 bg-slate-950 border border-slate-850 hover:border-slate-700/60 rounded-xl flex items-center justify-between text-xs transition-colors">
              <div>
                <span className="font-bold text-white block">Case A: Temporary Network failure</span>
                <span className="text-slate-500 font-medium block mt-0.5">Recommended: RETRY | Expects success</span>
              </div>
              <button
                onClick={() => handleSimulateScenario('CASE_A')}
                className="p-2 rounded bg-accent-blue/10 hover:bg-accent-blue/20 text-accent-blue font-bold flex items-center space-x-1.5 transition-colors"
              >
                <Send className="w-3.5 h-3.5" />
                <span>Trigger</span>
              </button>
            </div>

            {/* Case C: Permanent expired card */}
            <div className="p-3 bg-slate-950 border border-slate-850 hover:border-slate-700/60 rounded-xl flex items-center justify-between text-xs transition-colors">
              <div>
                <span className="font-bold text-white block">Case C: Card Expired decline</span>
                <span className="text-slate-500 font-medium block mt-0.5">Recommended: STOP | Permanent decline check</span>
              </div>
              <button
                onClick={() => handleSimulateScenario('CASE_C')}
                className="p-2 rounded bg-accent-blue/10 hover:bg-accent-blue/20 text-accent-blue font-bold flex items-center space-x-1.5 transition-colors"
              >
                <Send className="w-3.5 h-3.5" />
                <span>Trigger</span>
              </button>
            </div>

            {/* Case D: Fraud suspected */}
            <div className="p-3 bg-slate-950 border border-slate-850 hover:border-slate-700/60 rounded-xl flex items-center justify-between text-xs transition-colors">
              <div>
                <span className="font-bold text-white block">Case D: Risk Threshold exceeded</span>
                <span className="text-slate-500 font-medium block mt-0.5">Recommended: STOP | Fraud prevention veto</span>
              </div>
              <button
                onClick={() => handleSimulateScenario('CASE_D')}
                className="p-2 rounded bg-accent-blue/10 hover:bg-accent-blue/20 text-accent-blue font-bold flex items-center space-x-1.5 transition-colors"
              >
                <Send className="w-3.5 h-3.5" />
                <span>Trigger</span>
              </button>
            </div>

            {/* Case E: High-value decline -> MANUAL REVIEW */}
            <div className="p-3 bg-slate-950 border border-slate-850 hover:border-slate-700/60 rounded-xl flex items-center justify-between text-xs transition-colors">
              <div>
                <span className="font-bold text-white block">Case E: High Value decline</span>
                <span className="text-slate-500 font-medium block mt-0.5">Recommended: MANUAL REVIEW | High threshold veto</span>
              </div>
              <button
                onClick={() => handleSimulateScenario('CASE_E')}
                className="p-2 rounded bg-accent-blue/10 hover:bg-accent-blue/20 text-accent-blue font-bold flex items-center space-x-1.5 transition-colors"
              >
                <Send className="w-3.5 h-3.5" />
                <span>Trigger</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
