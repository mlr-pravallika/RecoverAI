import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import type { AuditLog } from '../services/api';
import { Clock, RefreshCw, Cpu, ShieldCheck, ShieldAlert } from 'lucide-react';

export const AuditTrail: React.FC = () => {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchLogs = async () => {
    try {
      setLoading(true);
      const data = await api.getAuditLogs();
      setLogs(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, []);

  const getActorBadge = (actor: string) => {
    const config: Record<string, { bg: string, text: string, icon: any }> = {
      "SYSTEM": { bg: "bg-slate-800 text-slate-300", text: "SYSTEM", icon: Clock },
      "AI": { bg: "bg-accent-purple/10 text-accent-purple", text: "AI AGENT", icon: Cpu },
      "POLICY": { bg: "bg-accent-green/10 text-accent-green", text: "POLICY", icon: ShieldCheck },
      "ADMIN": { bg: "bg-accent-blue/10 text-accent-blue", text: "MERCHANT", icon: ShieldAlert },
    };
    const style = config[actor] || { bg: "bg-slate-800 text-slate-300", text: actor, icon: Clock };
    const Icon = style.icon;
    return (
      <span className={`px-2 py-0.5 rounded-md text-[10px] font-bold border border-current/10 flex items-center space-x-1 w-fit ${style.bg}`}>
        <Icon className="w-3 h-3" />
        <span>{style.text}</span>
      </span>
    );
  };

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Title */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-3xl font-extrabold tracking-tight text-white">Security Audit Trail</h2>
          <p className="text-slate-400 mt-1 text-sm">Every payment failure analysis, ML prediction, and policy clearance is securely logged for compliance auditing.</p>
        </div>
        <button
          onClick={fetchLogs}
          className="p-2 rounded-xl bg-slate-900 border border-slate-800 text-slate-400 hover:text-white transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {/* Timeline List */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-lg">
        {loading && logs.length === 0 ? (
          <div className="p-12 text-center text-slate-500 font-medium">Loading audit logs...</div>
        ) : logs.length === 0 ? (
          <div className="p-12 text-center text-slate-500">No audit logs recorded in database.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-800 text-xs font-bold uppercase tracking-wider text-slate-500 bg-slate-900/60">
                  <th className="px-6 py-4">Timestamp</th>
                  <th className="px-6 py-4">Transaction ID</th>
                  <th className="px-6 py-4">Actor</th>
                  <th className="px-6 py-4">Action</th>
                  <th className="px-6 py-4">Reason / Description</th>
                  <th className="px-6 py-4">Transitions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-xs font-medium">
                {logs.map((log) => (
                  <tr key={log.id} className="hover:bg-slate-800/20">
                    <td className="px-6 py-4 text-slate-500 font-mono">
                      {new Date(log.timestamp).toLocaleString('en-IN')}
                    </td>
                    <td className="px-6 py-4 font-mono text-slate-300 font-bold">
                      {log.transaction_id || '-'}
                    </td>
                    <td className="px-6 py-4">{getActorBadge(log.actor)}</td>
                    <td className="px-6 py-4 text-slate-400 uppercase font-bold tracking-wide">
                      {log.action.replace('_', ' ')}
                    </td>
                    <td className="px-6 py-4 text-slate-300 leading-relaxed max-w-sm break-words">
                      {log.reason}
                    </td>
                    <td className="px-6 py-4">
                      {log.previous_state && log.new_state ? (
                        <div className="flex items-center space-x-1.5 font-semibold">
                          <span className="text-slate-500">{log.previous_state}</span>
                          <span className="text-slate-600">→</span>
                          <span className="text-accent-blue">{log.new_state}</span>
                        </div>
                      ) : (
                        <span className="text-slate-600">-</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
