import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ShieldCheck, ArrowRight, Zap, Target, BarChart3, Lock } from 'lucide-react';

export const Landing: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-between selection:bg-cyan-500 selection:text-slate-950 font-sans">
      
      {/* Navigation Header */}
      <header className="max-w-6xl mx-auto w-full px-6 py-6 flex items-center justify-between border-b border-slate-900">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20">
            <ShieldCheck className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight text-white leading-none">RecoverAI</h1>
            <span className="text-[10px] text-cyan-400 font-bold uppercase tracking-wider">Revenue Recovery</span>
          </div>
        </div>
        <div className="flex items-center space-x-4">
          <button 
            onClick={() => navigate('/login')}
            className="text-sm font-medium text-slate-400 hover:text-white transition-colors"
          >
            Sign In
          </button>
          <button 
            onClick={() => navigate('/signup')}
            className="text-sm font-semibold px-4 py-2 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 text-white hover:opacity-90 transition-all shadow-md shadow-cyan-500/10"
          >
            Get Started
          </button>
        </div>
      </header>

      {/* Hero Section */}
      <main className="max-w-6xl mx-auto w-full px-6 py-12 md:py-20 flex-1 flex flex-col items-center text-center justify-center">
        <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-slate-900 border border-slate-800 text-slate-400 text-xs font-semibold mb-8 animate-fade-in">
          <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse"></span>
          <span>Razorpay AI Buildathon Submission</span>
        </div>
        
        <h2 className="text-4xl md:text-6xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-white via-slate-100 to-slate-400 tracking-tight max-w-3xl leading-tight mb-6">
          Turn Failed Payments Into Recoverable Revenue
        </h2>
        
        <p className="text-slate-400 text-lg md:text-xl max-w-2xl mb-10 leading-relaxed">
          RecoverAI detects payment dropoffs in real-time, runs multi-agent AI risk assessments, applies compliance policy guardrails, and automates bounding recovery interventions.
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16">
          <button 
            onClick={() => navigate('/signup')}
            className="w-full sm:w-auto flex items-center justify-center space-x-2 text-base font-bold px-8 py-4 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 text-white hover:shadow-lg hover:shadow-cyan-500/20 hover:scale-[1.02] active:scale-[0.98] transition-all"
          >
            <span>Create Merchant Account</span>
            <ArrowRight className="w-5 h-5" />
          </button>
          <button 
            onClick={() => navigate('/login')}
            className="w-full sm:w-auto text-base font-semibold px-8 py-4 rounded-xl bg-slate-900 hover:bg-slate-800 text-white border border-slate-800 hover:border-slate-700 transition-all"
          >
            Merchant Sign In
          </button>
        </div>

        {/* Feature Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 w-full text-left">
          
          <div className="p-6 rounded-2xl bg-slate-900/50 border border-slate-900 hover:border-slate-800 transition-all flex flex-col justify-between">
            <div className="w-12 h-12 rounded-xl bg-cyan-500/10 flex items-center justify-center mb-6">
              <Zap className="w-6 h-6 text-cyan-400" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-white mb-2">Real-Time Ingestion</h3>
              <p className="text-sm text-slate-400 leading-relaxed">
                Connects directly to Razorpay Test Mode webhooks to capture failed payments instantly, before checkouts are abandoned.
              </p>
            </div>
          </div>

          <div className="p-6 rounded-2xl bg-slate-900/50 border border-slate-900 hover:border-slate-800 transition-all flex flex-col justify-between">
            <div className="w-12 h-12 rounded-xl bg-blue-500/10 flex items-center justify-center mb-6">
              <Target className="w-6 h-6 text-blue-400" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-white mb-2">Multi-Agent AI Inspector</h3>
              <p className="text-sm text-slate-400 leading-relaxed">
                Uses Google Gemini models to classify root-causes, assess VIP customer values, and propose context-aware recovery workflows.
              </p>
            </div>
          </div>

          <div className="p-6 rounded-2xl bg-slate-900/50 border border-slate-900 hover:border-slate-800 transition-all flex flex-col justify-between">
            <div className="w-12 h-12 rounded-xl bg-purple-500/10 flex items-center justify-center mb-6">
              <BarChart3 className="w-6 h-6 text-purple-400" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-white mb-2">Compliance Guardrails</h3>
              <p className="text-sm text-slate-400 leading-relaxed">
                Enforces velocity filters and stops automatically on fraud suspects, preventing payment loops and keeping operations clean.
              </p>
            </div>
          </div>

        </div>
      </main>

      {/* Footer */}
      <footer className="max-w-6xl mx-auto w-full px-6 py-8 border-t border-slate-900 flex flex-col md:flex-row items-center justify-between text-xs text-slate-500 gap-4">
        <div className="flex items-center space-x-2">
          <Lock className="w-4 h-4 text-slate-600" />
          <span>Secured Sandbox Environment (Razorpay Test Mode Only)</span>
        </div>
        <div>
          <span>© 2026 RecoverAI. Prepared for Razorpay AI Buildathon Track 03.</span>
        </div>
      </footer>

    </div>
  );
};
