import React, { useState } from 'react';
import { Sidebar } from './components/Sidebar';
import { Overview } from './pages/Overview';
import { Queue } from './pages/Queue';
import { Simulator } from './pages/Simulator';
import { WhatIf } from './pages/WhatIf';
import { AuditTrail } from './pages/AuditTrail';
import { Settings } from './pages/Settings';

export const App: React.FC = () => {
  const [currentTab, setCurrentTab] = useState<string>('overview');

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
    <div className="min-h-screen bg-slate-950 flex">
      {/* Navigation Sidebar (fixed width 64) */}
      <Sidebar currentTab={currentTab} setCurrentTab={setCurrentTab} />
      
      {/* Main Content Pane (shifted right by 64 to clear fixed sidebar) */}
      <main className="flex-1 min-h-screen pl-64 bg-slate-950 text-slate-100">
        <div className="max-w-6xl mx-auto p-8 lg:p-12">
          {renderContent()}
        </div>
      </main>
    </div>
  );
};

export default App;
