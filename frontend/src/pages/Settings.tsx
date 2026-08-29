import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import type { RazorpayStatus, Merchant } from '../services/api';
import { Sliders, Save, Sparkles, Send, ShieldCheck, RefreshCw, CheckCircle, AlertTriangle } from 'lucide-react';

export const Settings: React.FC = () => {
  const [maxRetries, setMaxRetries] = useState(3);
  const [minConfidence, setMinConfidence] = useState(0.70);
  const [windowHours, setWindowHours] = useState(72);
  const [maxAmount, setMaxAmount] = useState(40000);
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Merchant & Razorpay integration states
  const [merchant, setMerchant] = useState<Merchant | null>(null);
  const [rzpStatus, setRzpStatus] = useState<RazorpayStatus>({ connected: false, mode: 'test' });
  const [checkingRzp, setCheckingRzp] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [syncStats, setSyncStats] = useState<any>(null);
  const [syncError, setSyncError] = useState<string | null>(null);

  const [geminiStatus, setGeminiStatus] = useState<{
    connected: boolean;
    active_model: string;
    error?: string;
    sdk: string;
    last_verified_at?: string;
  }>({
    connected: false,
    active_model: 'None',
    error: 'GEMINI: NOT CONFIGURED',
    sdk: 'google-genai',
    last_verified_at: undefined
  });
  const [checkingGemini, setCheckingGemini] = useState(false);

  const [modelsList, setModelsList] = useState<Array<{ name: string; display_name: string; description: string; verified: boolean; supports_recoverai: boolean }>>([]);
  const [loadingModels, setLoadingModels] = useState(false);
  const [selectedModel, setSelectedModel] = useState<string>('');
  const [verifyingModelName, setVerifyingModelName] = useState<string>('');

  // Load configuration
  const loadConfig = async () => {
    try {
      const config = await api.getPolicyConfig();
      setMaxRetries(config.max_retries);
      setMinConfidence(config.min_confidence);
      setWindowHours(config.recovery_window_hours);
      setMaxAmount(config.max_automated_amount);
      
      const profile = await api.getMerchantProfile();
      setMerchant(profile);

      const status = await api.getRazorpayStatus();
      setRzpStatus(status);

      const gem = await api.getGeminiStatus();
      setGeminiStatus(gem);

      const modelsRes = await api.getGeminiModels();
      setModelsList(modelsRes.models);
      setSelectedModel(modelsRes.active_model);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
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

  const handleVerifyConnection = async () => {
    setCheckingRzp(true);
    try {
      const status = await api.getRazorpayStatus();
      setRzpStatus(status);
    } catch (err: any) {
      alert("Connection check failed: " + err.message);
    } finally {
      setCheckingRzp(false);
    }
  };

  const handleVerifyGemini = async () => {
    setCheckingGemini(true);
    try {
      const status = await api.getGeminiStatus();
      setGeminiStatus(status);
      if (status.connected) {
        alert("Gemini AI API connection successful!");
      } else {
        alert("Gemini connection validation failed:\n" + (status.error || "Unknown error"));
      }
    } catch (err: any) {
      alert("Gemini connection check failed: " + err.message);
    } finally {
      setCheckingGemini(false);
    }
  };

  const handleRefreshModels = async () => {
    setLoadingModels(true);
    try {
      const modelsRes = await api.getGeminiModels();
      setModelsList(modelsRes.models);
      setSelectedModel(modelsRes.active_model);
      alert("Model catalog refreshed successfully!");
    } catch (err: any) {
      alert("Failed to refresh models: " + err.message);
    } finally {
      setLoadingModels(false);
    }
  };

  const handleSelectModel = async () => {
    if (!selectedModel) return;
    try {
      const res = await api.selectGeminiModel(selectedModel);
      if (res.success) {
        alert(`Active model successfully updated to: ${res.active_model}`);
        loadConfig();
      }
    } catch (err: any) {
      alert("Failed to update active model: " + err.message);
    }
  };

  const handleVerifySpecificModel = async (modelName: string) => {
    setVerifyingModelName(modelName);
    try {
      const res = await api.verifyGeminiModel(modelName);
      if (res.verified) {
        alert(`Model ${modelName} verified successfully! Compatible with RecoverAI.`);
        const modelsRes = await api.getGeminiModels();
        setModelsList(modelsRes.models);
      } else {
        alert(`Model ${modelName} verification failed:\n${res.error || 'Unknown error'}`);
      }
    } catch (err: any) {
      alert(`Error verifying model ${modelName}: ` + err.message);
    } finally {
      setVerifyingModelName('');
    }
  };

  const handleSyncData = async () => {
    setSyncing(true);
    setSyncError(null);
    setSyncStats(null);
    try {
      const stats = await api.syncRazorpay();
      setSyncStats({
        timestamp: new Date().toLocaleTimeString(),
        fetched: stats.fetched,
        created: stats.created,
        updated: stats.updated,
        duplicates: stats.duplicates
      });
    } catch (err: any) {
      setSyncError(err.message || "Failed to synchronize test payments.");
    } finally {
      setSyncing(false);
    }
  };

  const handleModeToggle = async (newMode: string) => {
    try {
      const res = await api.updateMerchantMode(newMode);
      if (res.success) {
        // Reload settings or profile state to reflect environment updates
        loadConfig();
        // Force window refresh to let sidebar and dashboard re-fetch using the new mode
        window.location.reload();
      }
    } catch (err: any) {
      alert("Mode switch failed: " + err.message);
    }
  };

  return (
    <div className="space-y-8 animate-fadeIn select-none">
      
      {/* Title */}
      <div>
        <h2 className="text-3xl font-extrabold tracking-tight text-white">System Settings & Controls</h2>
        <p className="text-slate-400 mt-1 text-sm">Manage payment gateway connections, switch environment modes, and configure active policy rules.</p>
      </div>

      {/* Connection & Mode Integration Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Environment Mode Switcher */}
        <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl space-y-6 shadow-lg flex flex-col justify-between">
          <div>
            <div className="flex items-center space-x-2 border-b border-slate-800/80 pb-3">
              <ShieldCheck className="w-5 h-5 text-cyan-400" />
              <h3 className="text-base font-bold text-white">Active Environment Mode</h3>
            </div>
            
            <p className="text-xs text-slate-400 font-medium leading-relaxed mt-4">
              Toggle between **Demo Mode** (which renders pre-populated synthetic transaction sets) and **Real Test Mode** (which secures, synchs, and processes payments connected to your Razorpay Sandbox). Datasets remain completely isolated.
            </p>

            <div className="bg-slate-950 p-4 rounded-xl border border-slate-850 mt-6 flex items-center justify-between">
              <div>
                <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block">Active Mode</span>
                <span className={`text-sm font-extrabold uppercase ${merchant?.mode === 'real' ? 'text-emerald-400' : 'text-amber-400'}`}>
                  {merchant?.mode === 'real' ? 'Real Test Mode' : 'Demo Mode'}
                </span>
              </div>
              <div className="flex space-x-2">
                <button
                  onClick={() => handleModeToggle('demo')}
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                    merchant?.mode === 'demo'
                      ? 'bg-amber-500/20 border border-amber-500/30 text-amber-400'
                      : 'bg-slate-900 hover:bg-slate-800 text-slate-500 border border-slate-800'
                  }`}
                >
                  Demo Mode
                </button>
                <button
                  onClick={() => handleModeToggle('real')}
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                    merchant?.mode === 'real'
                      ? 'bg-emerald-500/20 border border-emerald-500/30 text-emerald-400'
                      : 'bg-slate-900 hover:bg-slate-800 text-slate-500 border border-slate-800'
                  }`}
                >
                  Live Test Mode
                </button>
              </div>
            </div>
          </div>
          
          <div className="text-xs text-slate-500 font-medium leading-relaxed bg-slate-950/20 p-4 rounded-xl border border-slate-900/60 mt-4">
            {merchant?.mode === 'real' ? (
              <span className="text-emerald-400/90">
                ✓ Currently rendering actual synced transactions. Automated recovery decisions will generate real payment link interventions.
              </span>
            ) : (
              <span className="text-amber-400/90">
                ⚠ Displaying mock transactional data. Use the Trigger panels to test state machine transitions safely.
              </span>
            )}
          </div>
        </div>

        {/* Razorpay Integration Settings */}
        <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl space-y-6 shadow-lg flex flex-col justify-between">
          <div>
            <div className="flex items-center space-x-2 border-b border-slate-800/80 pb-3">
              <ShieldCheck className="w-5 h-5 text-blue-400" />
              <h3 className="text-base font-bold text-white">Razorpay API Integration</h3>
            </div>

            <div className="space-y-4 mt-6">
              <div className="flex justify-between items-center text-xs">
                <span className="text-slate-400 font-bold">API ENVIRONMENT</span>
                <span className="px-2 py-0.5 rounded bg-slate-950 text-[10px] text-cyan-400 font-bold border border-slate-850">
                  SANDBOX / TEST MODE
                </span>
              </div>
              <div className="flex justify-between items-center text-xs">
                <span className="text-slate-400 font-bold">KEY ID</span>
                <code className="text-slate-300 bg-slate-950 px-2 py-0.5 rounded border border-slate-850">
                  {rzpStatus.key_id_masked || 'rzp_test_••••••••'}
                </code>
              </div>
              <div className="flex justify-between items-center text-xs">
                <span className="text-slate-400 font-bold">KEY SECRET</span>
                <code className="text-slate-350 bg-slate-950 px-2 py-0.5 rounded border border-slate-850 font-sans tracking-wide">
                  ••••••••••••••••
                </code>
              </div>
              <div className="flex justify-between items-center text-xs border-t border-slate-850 pt-3">
                <span className="text-slate-400 font-bold">CONNECTION STATUS</span>
                <span className="flex items-center space-x-1.5">
                  <span className={`w-2.5 h-2.5 rounded-full ${rzpStatus.connected ? 'bg-emerald-400 shadow-md shadow-emerald-400/20' : 'bg-rose-500 animate-pulse'}`}></span>
                  <span className={`font-extrabold uppercase ${rzpStatus.connected ? 'text-emerald-400' : 'text-rose-500'}`}>
                    {rzpStatus.connected ? 'Connected' : 'Not Connected'}
                  </span>
                </span>
              </div>
            </div>
          </div>

          <div className="flex space-x-3 mt-6">
            <button
              onClick={handleVerifyConnection}
              disabled={checkingRzp}
              className="flex-1 py-2 px-3 bg-slate-950 border border-slate-800 hover:bg-slate-800 text-slate-300 font-bold text-xs rounded-xl flex items-center justify-center space-x-1.5 transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${checkingRzp ? 'animate-spin' : ''}`} />
              <span>{checkingRzp ? 'Verifying...' : 'Verify Connection'}</span>
            </button>

            <button
              onClick={handleSyncData}
              disabled={syncing || !rzpStatus.connected}
              className="flex-1 py-2 px-3 bg-gradient-to-r from-cyan-500 to-blue-600 text-white font-bold text-xs rounded-xl flex items-center justify-center space-x-1.5 hover:shadow-lg hover:shadow-cyan-500/10 transition-all disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${syncing ? 'animate-spin' : ''}`} />
              <span>{syncing ? 'Syncing...' : 'Sync Test Data'}</span>
            </button>
          </div>
        </div>

        {/* Gemini AI Integration Settings */}
        <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl space-y-6 shadow-lg flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
              <div className="flex items-center space-x-2">
                <Sparkles className="w-5 h-5 text-purple-400 font-bold" />
                <h3 className="text-base font-bold text-white">Gemini AI Engine</h3>
              </div>
              <span className="px-2 py-0.5 rounded bg-slate-950 text-[9px] text-slate-400 font-mono border border-slate-850">
                SDK: {geminiStatus.sdk || 'google-genai'}
              </span>
            </div>

            <div className="space-y-4 mt-6">
              <div className="flex justify-between items-center text-xs">
                <span className="text-slate-400 font-bold">API MODEL</span>
                <span className="px-2 py-0.5 rounded bg-slate-950 text-[10px] text-purple-400 font-bold border border-slate-850">
                  {geminiStatus.active_model || 'None'}
                </span>
              </div>
              
              <div className="flex justify-between items-center text-xs border-t border-slate-850 pt-3">
                <span className="text-slate-400 font-bold">INTEGRATION STATUS</span>
                <span className="flex items-center space-x-1.5">
                  <span className={`w-2.5 h-2.5 rounded-full ${geminiStatus.connected ? 'bg-emerald-400 shadow-md shadow-emerald-400/20' : 'bg-rose-500 animate-pulse'}`}></span>
                  <span className={`font-extrabold uppercase ${geminiStatus.connected ? 'text-emerald-400' : 'text-rose-500'}`}>
                    {geminiStatus.connected ? 'Connected' : 'Not Connected'}
                  </span>
                </span>
              </div>

              {geminiStatus.error && (
                <div className="text-[10px] text-rose-400 font-mono bg-slate-950/80 p-2.5 rounded-lg border border-slate-850/60 leading-relaxed break-all max-h-24 overflow-y-auto">
                  {geminiStatus.error}
                </div>
              )}

              {/* Model Selector Dropdown */}
              <div className="flex flex-col space-y-1.5 text-xs border-t border-slate-850 pt-3">
                <span className="text-slate-400 font-bold">SELECT ACTIVE MODEL</span>
                <div className="flex gap-2">
                  <select
                    value={selectedModel}
                    onChange={(e) => setSelectedModel(e.target.value)}
                    className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-2 text-xs text-slate-300 focus:outline-none focus:border-purple-500"
                  >
                    <option value="">No model selected</option>
                    {modelsList.map((m) => (
                      <option key={m.name} value={m.name}>
                        {m.name} {m.verified ? ' (Verified ✓)' : ''}
                      </option>
                    ))}
                  </select>
                  <button
                    onClick={handleSelectModel}
                    disabled={!selectedModel || selectedModel === geminiStatus.active_model}
                    className="px-3 py-2 bg-purple-600 hover:bg-purple-700 text-white font-bold text-xs rounded-lg transition-colors disabled:opacity-50"
                  >
                    Select
                  </button>
                </div>
              </div>

              {/* Inline action to verify selected model if not active */}
              {selectedModel && selectedModel !== geminiStatus.active_model && (
                <div className="flex justify-between items-center text-xs bg-slate-950/40 p-2 rounded-lg border border-slate-850/50">
                  <span className="text-slate-500">Selected model not verified?</span>
                  <button
                    onClick={() => handleVerifySpecificModel(selectedModel)}
                    disabled={verifyingModelName === selectedModel}
                    className="text-purple-400 hover:text-purple-300 font-bold transition-colors disabled:opacity-50"
                  >
                    {verifyingModelName === selectedModel ? 'Testing...' : 'Test Model'}
                  </button>
                </div>
              )}
            </div>
          </div>

          <div className="flex space-x-3 mt-6 pt-3 border-t border-slate-850/60">
            <button
              onClick={handleRefreshModels}
              disabled={loadingModels}
              className="flex-1 py-2 px-3 bg-slate-950 border border-slate-800 hover:bg-slate-800 text-slate-300 font-bold text-xs rounded-xl flex items-center justify-center space-x-1.5 transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loadingModels ? 'animate-spin' : ''}`} />
              <span>{loadingModels ? 'Refreshing...' : 'Refresh Models'}</span>
            </button>

            <button
              onClick={handleVerifyGemini}
              disabled={checkingGemini}
              className="flex-1 py-2 px-3 bg-purple-600/10 border border-purple-500/20 hover:bg-purple-600/20 text-purple-300 font-bold text-xs rounded-xl flex items-center justify-center space-x-1.5 transition-all disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${checkingGemini ? 'animate-spin' : ''}`} />
              <span>{checkingGemini ? 'Testing...' : 'Verify Active'}</span>
            </button>
          </div>
        </div>

      </div>

      {/* Sync statistics Display Panel */}
      {syncStats && (
        <div className="bg-slate-900 border border-slate-800 p-5 rounded-2xl flex items-start space-x-4 animate-fadeIn">
          <CheckCircle className="w-8 h-8 text-emerald-400 shrink-0 mt-0.5" />
          <div className="text-xs space-y-1">
            <span className="font-bold text-white block">Synchronization Successful</span>
            <span className="text-slate-400 block font-medium">Last synchronized at {syncStats.timestamp}</span>
            <div className="flex items-center space-x-4 mt-2 font-mono text-[11px] text-slate-300 bg-slate-950 p-2.5 rounded-lg border border-slate-850">
              <span>Fetched: {syncStats.fetched}</span>
              <span>Imported: {syncStats.created}</span>
              <span>Updated: {syncStats.updated}</span>
              <span>Duplicates: {syncStats.duplicates}</span>
            </div>
          </div>
        </div>
      )}

      {syncError && (
        <div className="bg-slate-900 border border-slate-800 p-5 rounded-2xl flex items-start space-x-4 animate-fadeIn">
          <AlertTriangle className="w-8 h-8 text-rose-500 shrink-0 mt-0.5" />
          <div className="text-xs space-y-1">
            <span className="font-bold text-white block">Synchronization Failed</span>
            <p className="text-rose-400 font-medium">{syncError}</p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        
        {/* Left Side: Rule Engine Policy Config Editor */}
        <form onSubmit={handleSave} className="bg-slate-900 border border-slate-800 p-6 rounded-2xl space-y-6 shadow-lg">
          <div className="flex items-center space-x-2 border-b border-slate-800 pb-3">
            <Sliders className="w-5 h-5 text-cyan-400" />
            <h3 className="text-base font-bold text-white">Compliance Policy Guardrails</h3>
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
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2 text-sm text-slate-200 focus:outline-none focus:border-cyan-500"
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
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2 text-sm text-slate-200 focus:outline-none focus:border-cyan-500"
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
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2 text-sm text-slate-200 focus:outline-none focus:border-cyan-500"
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
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2 text-sm text-slate-200 focus:outline-none focus:border-cyan-500"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={saving}
            className="w-full bg-cyan-500 hover:bg-cyan-600 text-white font-bold py-2.5 rounded-xl text-sm flex items-center justify-center space-x-2 transition-all shadow-lg shadow-cyan-500/15"
          >
            <Save className="w-4 h-4" />
            <span>{saving ? 'Saving...' : 'Save Rules Config'}</span>
          </button>

          {saveSuccess && (
            <div className="text-xs text-emerald-400 font-bold text-center mt-2 animate-pulse">
              Configurations saved and applied to live policy check engine!
            </div>
          )}
        </form>

        {/* Right Side: Demo Trigger Panel (Only visible in Demo Mode) */}
        <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl space-y-6 shadow-lg">
          <div className="flex items-center space-x-2 border-b border-slate-800 pb-3">
            <Sparkles className="w-5 h-5 text-amber-400" />
            <h3 className="text-base font-bold text-white">Trigger Demo Failure Scenarios</h3>
          </div>

          {merchant?.mode === 'real' ? (
            <div className="text-xs text-slate-500 leading-relaxed bg-slate-950 p-4 rounded-xl border border-slate-905 flex items-center space-x-3 text-left">
              <AlertTriangle className="w-6 h-6 text-amber-500 shrink-0" />
              <span>Demo Scenario triggers are disabled in Live Test Mode. Switch back to Demo Mode to execute failure webhooks.</span>
            </div>
          ) : (
            <>
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
                    className="p-2 rounded bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-400 font-bold flex items-center space-x-1.5 transition-colors"
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
                    className="p-2 rounded bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-400 font-bold flex items-center space-x-1.5 transition-colors"
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
                    className="p-2 rounded bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-400 font-bold flex items-center space-x-1.5 transition-colors"
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
                    className="p-2 rounded bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-400 font-bold flex items-center space-x-1.5 transition-colors"
                  >
                    <Send className="w-3.5 h-3.5" />
                    <span>Trigger</span>
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};
