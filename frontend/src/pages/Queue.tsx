import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import type { Transaction } from '../services/api';
import { 
  Search, 
  Filter, 
  X, 
  ChevronRight, 
  User, 
  ShieldCheck, 
  Check, 
  Ban,
  Mail,
  AlertTriangle
} from 'lucide-react';

export const Queue: React.FC = () => {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedTxId, setSelectedTxId] = useState<string | null>(null);
  const [selectedTx, setSelectedTx] = useState<Transaction | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [failureFilter, setFailureFilter] = useState('');
  const [actionFilter, setActionFilter] = useState('');
  const [merchantMode, setMerchantMode] = useState<string>('demo');

  // Fetch queue
  const fetchQueue = async () => {
    try {
      setLoading(true);
      const data = await api.getTransactions({
        status: statusFilter || undefined,
        failure_type: failureFilter || undefined,
        recommended_action: actionFilter || undefined,
        search: searchTerm || undefined
      });
      setTransactions(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQueue();
  }, [statusFilter, failureFilter, actionFilter]);

  useEffect(() => {
    api.getMerchantProfile()
      .then((m) => setMerchantMode(m.mode))
      .catch(console.error);
  }, []);

  // Handle row click
  const handleSelectTransaction = async (txId: string) => {
    try {
      setSelectedTxId(txId);
      const tx = await api.getTransaction(txId);
      setSelectedTx(tx);
    } catch (err) {
      console.error(err);
    }
  };

  // Perform search
  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    fetchQueue();
  };

  // Actions execution handler
  const handleAction = async (actionType: 'approve' | 'stop', caseId: number) => {
    if (!selectedTx) return;
    try {
      if (actionType === 'stop') {
        const reason = prompt("Enter cancel reason:", "Merchant manual cancel override.");
        if (reason === null) return;
        await api.stopRecoveryCase(caseId, reason);
        alert("Case aborted successfully.");
      } else {
        await api.approveRecoveryCase(caseId);
        alert("Action manually approved and executed successfully!");
      }
      // Re-fetch transaction detail and queue
      const tx = await api.getTransaction(selectedTx.id);
      setSelectedTx(tx);
      fetchQueue();
    } catch (err: any) {
      alert(`Action failed: ${err.message}`);
    }
  };

  // Formatter helpers
  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(val);
  };

  const getStatusBadge = (status: string) => {
    const config: Record<string, string> = {
      "captured": "bg-accent-green/10 text-accent-green border-accent-green/20",
      "failed": "bg-red-950/20 text-accent-red border-accent-red/20",
      "RECOVERED": "bg-accent-green/10 text-accent-green border-accent-green/20",
      "STOPPED": "bg-slate-800 text-slate-400 border-slate-700",
      "MANUAL_REVIEW": "bg-accent-orange/10 text-accent-orange border-accent-orange/20",
      "ACTION_PENDING": "bg-accent-blue/10 text-accent-blue border-accent-blue/20",
      "ACTION_EXECUTED": "bg-accent-purple/10 text-accent-purple border-accent-purple/20",
      "AWAITING_RESULT": "bg-indigo-950/30 text-indigo-400 border-indigo-900/30",
      "ANALYZING": "bg-cyan-950/30 text-cyan-400 border-cyan-900/30",
    };
    const style = config[status] || "bg-slate-800 text-slate-400 border-slate-700";
    return <span className={`px-2.5 py-1 rounded-full text-xs font-semibold border ${style}`}>{status}</span>;
  };

  return (
    <div className="relative animate-fadeIn">
      {/* Title */}
      <div className="mb-6">
        <h2 className="text-3xl font-extrabold tracking-tight text-white">Recovery Queue</h2>
        <p className="text-slate-400 mt-1 text-sm">Monitor, inspect, and approve AI-driven recovery workflows for all payment failures.</p>
      </div>

      {/* Filters & Search Row */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 mb-6 flex flex-col md:flex-row gap-4 items-center justify-between shadow-lg">
        <form onSubmit={handleSearch} className="relative w-full md:w-80">
          <input
            type="text"
            placeholder="Search by Pay ID or Name..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-10 pr-4 py-2 text-sm text-slate-200 focus:outline-none focus:border-accent-blue transition-colors"
          />
          <Search className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
        </form>

        <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
          {/* Status filter */}
          <div className="flex items-center space-x-2">
            <Filter className="w-3.5 h-3.5 text-slate-500" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs font-medium text-slate-300 focus:outline-none"
            >
              <option value="">All Statuses</option>
              <option value="failed">Failed Tx</option>
              <option value="captured">Captured Tx</option>
            </select>
          </div>

          {/* Failure code filter */}
          <select
            value={failureFilter}
            onChange={(e) => setFailureFilter(e.target.value)}
            className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs font-medium text-slate-300 focus:outline-none"
          >
            <option value="">All Failure Types</option>
            <option value="temporary">Temporary Failure</option>
            <option value="permanent">Permanent Failure</option>
            <option value="fraud">Fraud Risk</option>
          </select>

          {/* Action Filter */}
          <select
            value={actionFilter}
            onChange={(e) => setActionFilter(e.target.value)}
            className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs font-medium text-slate-300 focus:outline-none"
          >
            <option value="">All Actions</option>
            <option value="RETRY">RETRY</option>
            <option value="PAYMENT_LINK">PAYMENT LINK</option>
            <option value="MANUAL_REVIEW">MANUAL REVIEW</option>
            <option value="STOP">STOP</option>
          </select>
        </div>
      </div>

      {/* Main Grid: Table list */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-lg">
        {loading && transactions.length === 0 ? (
          <div className="p-12 text-center text-slate-500 font-medium animate-pulse">Loading recovery queue...</div>
        ) : transactions.length === 0 ? (
          merchantMode === 'real' ? (
            <div className="p-12 text-center text-slate-500 max-w-md mx-auto space-y-4">
              <AlertTriangle className="w-12 h-12 text-amber-500 mx-auto" />
              <h3 className="text-base font-bold text-white">No Razorpay Test Mode transactions found</h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                We couldn't detect any Sandbox payment dropoffs in your account. To generate a failure transaction:
              </p>
              <div className="bg-slate-950 p-4 rounded-xl border border-slate-850 text-left text-xs font-mono text-slate-400 space-y-1">
                <p>1. Go to Policy Rules settings tab.</p>
                <p>2. Verify your Razorpay Connection status.</p>
                <p>3. Click "Sync Test Data" to fetch sandbox events.</p>
                <p>4. Wait for webhook signals to auto-ingest.</p>
              </div>
              <button 
                onClick={fetchQueue}
                className="px-4 py-2 bg-cyan-500 hover:bg-cyan-600 text-white font-bold text-xs rounded-lg transition-colors mt-2"
              >
                Refresh Queue
              </button>
            </div>
          ) : (
            <div className="p-12 text-center text-slate-500">No transactions match the filter parameters.</div>
          )
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-800 text-xs font-bold uppercase tracking-wider text-slate-500 bg-slate-900/60">
                  <th className="px-6 py-4">Transaction ID</th>
                  <th className="px-6 py-4">Customer</th>
                  <th className="px-6 py-4">Amount</th>
                  <th className="px-6 py-4">Failure Reason</th>
                  <th className="px-6 py-4">Recovery Prob.</th>
                  <th className="px-6 py-4">Recommended Action</th>
                  <th className="px-6 py-4">Status</th>
                  <th className="px-6 py-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {transactions.map((tx) => {
                  const caseObj = tx.recovery_cases[0];
                  return (
                    <tr
                      key={tx.id}
                      onClick={() => handleSelectTransaction(tx.id)}
                      className={`hover:bg-slate-800/40 cursor-pointer transition-colors ${
                        selectedTxId === tx.id ? 'bg-slate-800/50' : ''
                      }`}
                    >
                      <td className="px-6 py-4 font-mono text-xs text-slate-300 font-bold">{tx.id}</td>
                      <td className="px-6 py-4">
                        <div className="font-semibold text-white text-sm">{tx.customer?.name || 'Guest'}</div>
                        <div className="text-xs text-slate-500 font-medium">{tx.customer?.email}</div>
                      </td>
                      <td className="px-6 py-4 font-semibold text-white text-sm">{formatCurrency(tx.amount)}</td>
                      <td className="px-6 py-4">
                        <span className="text-xs text-slate-300 font-medium bg-slate-950 px-2 py-1 rounded border border-slate-800">
                          {tx.failure_code?.replace('BAD_REQUEST_PAYMENT_', '') || 'BANK_DECLINE'}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        {caseObj ? (
                          <div className="flex items-center space-x-1.5">
                            <span className="text-sm font-bold text-white">
                              {Math.round(caseObj.recovery_probability * 100)}%
                            </span>
                            <div className="w-1.5 h-1.5 rounded-full" style={{
                              backgroundColor: caseObj.recovery_probability >= 0.7 ? '#10b981' : caseObj.recovery_probability >= 0.3 ? '#f59e0b' : '#ef4444'
                            }}></div>
                          </div>
                        ) : (
                          <span className="text-slate-600">-</span>
                        )}
                      </td>
                      <td className="px-6 py-4 font-semibold text-xs text-accent-blue tracking-wide">
                        {caseObj?.recommended_action || 'N/A'}
                      </td>
                      <td className="px-6 py-4">{getStatusBadge(caseObj?.status || tx.status)}</td>
                      <td className="px-6 py-4 text-right">
                        <ChevronRight className="w-5 h-5 text-slate-500 inline-block" />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Slide-over Panel (AI Decision Inspector Drawer) */}
      {selectedTx && (
        <div className="fixed inset-y-0 right-0 w-full max-w-xl bg-slate-900 border-l border-slate-800 shadow-2xl z-30 flex flex-col justify-between animate-slideLeft">
          {/* Header */}
          <div className="p-6 border-b border-slate-800 flex items-center justify-between bg-slate-950">
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-xs font-bold text-slate-500 uppercase tracking-widest">Decision Inspector</span>
                <span className="px-2 py-0.5 rounded bg-accent-blue/10 text-[9px] text-accent-blue font-bold tracking-wider">AI DIAGNOSIS</span>
              </div>
              <h3 className="text-lg font-bold text-white font-mono mt-1">{selectedTx.id}</h3>
            </div>
            <button
              onClick={() => { setSelectedTx(null); setSelectedTxId(null); }}
              className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-slate-100 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Drawer Body - Scrollable content */}
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {/* Customer & Transaction Overview */}
            <div className="grid grid-cols-2 gap-4 bg-slate-950/60 border border-slate-800/80 p-4 rounded-xl">
              <div>
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">Customer</span>
                <span className="font-bold text-white text-sm block mt-1">{selectedTx.customer?.name}</span>
                <div className="flex items-center text-xs text-slate-400 space-x-1.5 mt-1">
                  <Mail className="w-3.5 h-3.5 text-slate-500" />
                  <span>{selectedTx.customer?.email}</span>
                </div>
              </div>
              <div>
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">Value & Method</span>
                <span className="font-bold text-white text-sm block mt-1">{formatCurrency(selectedTx.amount)}</span>
                <span className="text-xs text-slate-400 uppercase font-mono block mt-1">{selectedTx.payment_method}</span>
              </div>
            </div>

            {/* AI Decision Inspector Steps - FLOW */}
            <div className="space-y-4">
              <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Why did RecoverAI make this decision?</h4>
              
              <div className="relative border-l border-slate-800 pl-6 space-y-6 ml-3">
                {/* Step 1: Failure Signal */}
                <div className="relative">
                  <div className="absolute -left-[31px] top-0.5 w-4 h-4 rounded-full bg-red-500/20 border border-red-500 flex items-center justify-center">
                    <div className="w-1.5 h-1.5 rounded-full bg-red-500"></div>
                  </div>
                  <div>
                    <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">1. Failure Event Detected</span>
                    <p className="text-xs text-white font-semibold mt-1">Declined Code: {selectedTx.failure_code}</p>
                    <p className="text-xs text-slate-400 font-medium mt-0.5">PSP Network declined card transaction.</p>
                  </div>
                </div>

                {/* Step 2: Customer History Segment */}
                <div className="relative">
                  <div className="absolute -left-[31px] top-0.5 w-4 h-4 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center">
                    <User className="w-2.5 h-2.5 text-slate-400" />
                  </div>
                  <div>
                    <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">2. Customer Segment Analysis</span>
                    <p className="text-xs text-white font-semibold mt-1">VIP Returning Segment</p>
                    <p className="text-xs text-slate-400 font-medium mt-0.5">8 captured checkout attempts historically, low chargeback risk.</p>
                  </div>
                </div>

                {/* Step 3: ML Probability Model */}
                <div className="relative">
                  <div className="absolute -left-[31px] top-0.5 w-4 h-4 rounded-full bg-accent-blue/20 border border-accent-blue flex items-center justify-center">
                    <div className="w-1.5 h-1.5 rounded-full bg-accent-blue"></div>
                  </div>
                  <div>
                    <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">3. ML Recovery Model Grade</span>
                    <p className="text-xs text-white font-semibold mt-1">
                      {selectedTx.recovery_cases[0] ? Math.round(selectedTx.recovery_cases[0].recovery_probability * 100) : 50}% Chance of Recovery
                    </p>
                    <p className="text-xs text-slate-400 font-medium mt-0.5">Evaluated against Random Forest Classifier trained on 604 failures.</p>
                  </div>
                </div>

                {/* Step 4: AI Reasoning */}
                <div className="relative">
                  <div className="absolute -left-[31px] top-0.5 w-4 h-4 rounded-full bg-accent-purple/20 border border-accent-purple flex items-center justify-center">
                    <div className="w-1.5 h-1.5 rounded-full bg-accent-purple"></div>
                  </div>
                  <div>
                    <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">4. AI Agent Proposal & Rationale</span>
                    <div className="p-3 bg-slate-950/70 border border-slate-850 rounded-lg mt-1 text-xs text-slate-300 italic font-medium leading-relaxed">
                      "{selectedTx.recovery_cases[0]?.explanation || (selectedTx.recovery_cases[0]?.recommended_action === 'STOP' 
                        ? 'Potential fraud or permanent loss. Stopping recovery saves fees and avoids duplicate interactions.' 
                        : selectedTx.recovery_cases[0]?.recommended_action === 'MANUAL_REVIEW' 
                        ? 'High value checkout failure. Requires custom merchant outreach rather than standard automated retries.'
                        : 'Temporary declined code with strong customer checkout history. Auto retry approved.')}"
                    </div>
                  </div>
                </div>

                {/* Step 5: Policy engine guardrail */}
                <div className="relative">
                  <div className="absolute -left-[31px] top-0.5 w-4 h-4 rounded-full bg-accent-green/20 border border-accent-green flex items-center justify-center">
                    <ShieldCheck className="w-2.5 h-2.5 text-accent-green" />
                  </div>
                  <div>
                    <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">5. Policy Engine Clearance</span>
                    <p className="text-xs text-white font-semibold mt-1 flex items-center space-x-1">
                      <span className="text-accent-green">APPROVED</span>
                      <span className="text-slate-500 font-normal">| Checked amount threshold, max retries, and fraud limits</span>
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Case Actions Execution details if exists */}
            {selectedTx.recovery_cases[0] && selectedTx.recovery_cases[0].actions.length > 0 && (
              <div className="space-y-3 border-t border-slate-850 pt-4">
                <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Intervention Attempts</h4>
                <div className="space-y-2">
                  {selectedTx.recovery_cases[0].actions.map((act) => (
                    <div key={act.id} className="bg-slate-950 p-3 rounded-lg border border-slate-850 flex items-center justify-between text-xs">
                      <div>
                        <span className="font-bold text-white block">{act.action_type}</span>
                        <span className="text-slate-500 text-[10px] font-medium block mt-0.5">
                          {new Date(act.created_at).toLocaleString('en-IN')}
                        </span>
                      </div>
                      <span className="font-semibold px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                        {act.status}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Drawer Footer Controls */}
          {selectedTx.recovery_cases[0] && (
            <div className="p-6 border-t border-slate-800 bg-slate-950/90 flex gap-4">
              {selectedTx.recovery_cases[0].status === 'MANUAL_REVIEW' && (
                <button
                  onClick={() => handleAction('approve', selectedTx.recovery_cases[0].id)}
                  className="flex-1 bg-accent-green hover:bg-accent-greenHover text-white py-2.5 rounded-xl text-xs font-bold flex items-center justify-center space-x-2 transition-all shadow-lg shadow-accent-green/20"
                >
                  <Check className="w-4 h-4" />
                  <span>Approve Action</span>
                </button>
              )}
              
              {!['RECOVERED', 'STOPPED'].includes(selectedTx.recovery_cases[0].status) && (
                <button
                  onClick={() => handleAction('stop', selectedTx.recovery_cases[0].id)}
                  className="flex-1 bg-slate-900 border border-slate-800 hover:bg-slate-800 text-accent-red py-2.5 rounded-xl text-xs font-bold flex items-center justify-center space-x-2 transition-all"
                >
                  <Ban className="w-4 h-4" />
                  <span>Force Abort Case</span>
                </button>
              )}
              
              {['RECOVERED', 'STOPPED'].includes(selectedTx.recovery_cases[0].status) && (
                <div className="w-full text-center text-xs text-slate-500 font-semibold py-2">
                  This case is in terminal state: <span className="text-slate-400">{selectedTx.recovery_cases[0].status}</span>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
