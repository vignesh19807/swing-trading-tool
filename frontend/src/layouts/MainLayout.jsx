import React, { useState } from 'react';
import Sidebar from '../components/Sidebar';
import TopBar from '../components/TopBar';

const MainLayout = ({ children, theme, toggleTheme }) => {
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);

  return (
    <div className="flex h-screen bg-bg text-tx-primary font-sans overflow-hidden transition-colors">
      <Sidebar 
        isOpen={isMobileSidebarOpen} 
        onClose={() => setIsMobileSidebarOpen(false)} 
        theme={theme}
        toggleTheme={toggleTheme}
      />
      
      <div className="flex-1 flex flex-col h-full overflow-hidden w-full relative">
        <TopBar 
          onMenuClick={() => setIsMobileSidebarOpen(true)} 
          theme={theme} 
          toggleTheme={toggleTheme} 
        />
        <main className="flex-1 overflow-y-auto">
          {children}
        </main>
      </div>
    </div>
  );
};

export default MainLayout;
