import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ShieldCheck, User, Building, Mail, Lock, AlertTriangle, ArrowRight } from 'lucide-react';
import { api } from '../services/api';

export const Signup: React.FC = () => {
  const navigate = useNavigate();
  const [businessName, setBusinessName] = useState('');
  const [ownerName, setOwnerName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!businessName || !ownerName || !email || !password) {
      setError('Please fill in all fields');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const res = await api.signup({
        business_name: businessName,
        owner_name: ownerName,
        email: email,
        password: password,
      });
      api.setToken(res.access_token);
      navigate('/app');
    } catch (err: any) {
      setError(err.message || 'Failed to create merchant account');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-6 selection:bg-cyan-500 selection:text-slate-950">
      <div className="max-w-md w-full">
        {/* Brand Logo */}
        <div className="flex flex-col items-center mb-8">
          <div 
            onClick={() => navigate('/')}
            className="w-12 h-12 rounded-xl bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20 mb-3 cursor-pointer hover:scale-105 transition-all"
          >
            <ShieldCheck className="w-7 h-7 text-white" />
          </div>
          <h2 className="text-2xl font-extrabold text-white tracking-tight">Create your account</h2>
          <p className="text-sm text-slate-400 mt-1">Get started with RecoverAI revenue recovery</p>
        </div>

        {/* Card Body */}
        <div className="bg-slate-900/45 border border-slate-900 rounded-2xl p-8 backdrop-blur-xl shadow-2xl">
          <form onSubmit={handleSubmit} className="space-y-5">
            
            {error && (
              <div className="flex items-start space-x-3 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs">
                <AlertTriangle className="w-5 h-5 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
                Business Name
              </label>
              <div className="relative">
                <Building className="absolute left-4 top-3 text-slate-500 w-5 h-5" />
                <input 
                  type="text" 
                  value={businessName}
                  onChange={(e) => setBusinessName(e.target.value)}
                  placeholder="Acme Corp" 
                  className="w-full bg-slate-950 border border-slate-800 focus:border-cyan-500 rounded-xl py-3 pl-12 pr-4 text-sm text-white placeholder-slate-600 focus:outline-none transition-colors"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
                Owner / Operator Name
              </label>
              <div className="relative">
                <User className="absolute left-4 top-3 text-slate-500 w-5 h-5" />
                <input 
                  type="text" 
                  value={ownerName}
                  onChange={(e) => setOwnerName(e.target.value)}
                  placeholder="John Doe" 
                  className="w-full bg-slate-950 border border-slate-800 focus:border-cyan-500 rounded-xl py-3 pl-12 pr-4 text-sm text-white placeholder-slate-600 focus:outline-none transition-colors"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
                Email Address
              </label>
              <div className="relative">
                <Mail className="absolute left-4 top-3 text-slate-500 w-5 h-5" />
                <input 
                  type="email" 
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="john@acme.com" 
                  className="w-full bg-slate-950 border border-slate-800 focus:border-cyan-500 rounded-xl py-3 pl-12 pr-4 text-sm text-white placeholder-slate-600 focus:outline-none transition-colors"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
                Password
              </label>
              <div className="relative">
                <Lock className="absolute left-4 top-3 text-slate-500 w-5 h-5" />
                <input 
                  type="password" 
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••" 
                  className="w-full bg-slate-950 border border-slate-800 focus:border-cyan-500 rounded-xl py-3 pl-12 pr-4 text-sm text-white placeholder-slate-600 focus:outline-none transition-colors"
                />
              </div>
            </div>

            <button 
              type="submit" 
              disabled={loading}
              className="w-full flex items-center justify-center space-x-2 py-3.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:shadow-lg hover:shadow-cyan-500/15 text-sm font-bold text-white transition-all disabled:opacity-50"
            >
              <span>{loading ? 'Creating Account...' : 'Get Started'}</span>
              {!loading && <ArrowRight className="w-4 h-4" />}
            </button>
          </form>

          <div className="mt-8 text-center border-t border-slate-800/60 pt-6">
            <span className="text-xs text-slate-500">Already have an account? </span>
            <button 
              onClick={() => navigate('/login')}
              className="text-xs text-cyan-400 hover:underline font-semibold"
            >
              Sign In
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
