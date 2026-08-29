import React, { useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Landing } from './pages/Landing';
import { Login } from './pages/Login';
import { Signup } from './pages/Signup';
import { Sidebar } from './components/Sidebar';
import { Overview } from './pages/Overview';
import { Queue } from './pages/Queue';
import { Simulator } from './pages/Simulator';
import { WhatIf } from './pages/WhatIf';
import { AuditTrail } from './pages/AuditTrail';
import { Settings } from './pages/Settings';
import { api } from './services/api';

const ProtectedLayout: React.FC = () => {
  const [currentTab, setCurrentTab] = useState<string>('overview');
  
  if (!api.getToken()) {
    return <Navigate to="/login" replace />;
  }

  const renderContent = () => {
    switch (currentTab) {
      case 'overview':
        return <Overview />;
      case 'queue':
        return <Queue />;
      case 'simulator':
        return <Simulator />;
      case 'whatif':
        return <WhatIf />;
      case 'audit':
        return <AuditTrail />;
      case 'settings':
        return <Settings />;
      default:
        return <Overview />;
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex w-full">
      {/* Navigation Sidebar (fixed width 64) */}
      <Sidebar currentTab={currentTab} setCurrentTab={setCurrentTab} />
      
      {/* Main Content Pane */}
      <main className="flex-1 min-h-screen pl-64 bg-slate-950 text-slate-100">
        <div className="max-w-6xl mx-auto p-8 lg:p-12">
          {renderContent()}
        </div>
      </main>
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />
        <Route path="/app" element={<ProtectedLayout />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
};

export default App;
