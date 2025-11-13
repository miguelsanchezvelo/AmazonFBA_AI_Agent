/**
 * Layout Component
 * 
 * Main layout wrapper for the application
 */

import React, { useEffect } from 'react';
import { Navbar } from './Navbar';
import { Sidebar } from './Sidebar';
import { useUIStore } from '../../state/store';
import { cn } from '../../lib/utils';

interface LayoutProps {
  children: React.ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({ children }) => {
  const { sidebarOpen, theme, setTheme } = useUIStore();

  // Initialize theme on mount
  useEffect(() => {
    setTheme(theme);
  }, []);

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <Sidebar />
      
      {/* Main Content */}
      <main
        className={cn(
          'min-h-[calc(100vh-4rem)] transition-all duration-200',
          sidebarOpen ? 'lg:pl-64' : 'lg:pl-0'
        )}
      >
        <div className="container mx-auto p-6">{children}</div>
      </main>
    </div>
  );
};

