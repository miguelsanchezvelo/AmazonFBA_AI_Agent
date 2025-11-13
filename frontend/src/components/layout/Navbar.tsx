/**
 * Navbar Component
 * 
 * Top navigation bar with theme toggle and notifications
 */

import React from 'react';
import { Menu, Bell, Settings } from 'lucide-react';
import { useUIStore } from '../../state/store';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import { ThemeToggle } from '../ui/ThemeToggle';

export const Navbar: React.FC = () => {
  const { toggleSidebar, notifications } = useUIStore();

  return (
    <nav className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-16 items-center">
        {/* Menu Toggle */}
        <Button
          variant="ghost"
          size="icon"
          onClick={toggleSidebar}
          className="mr-2"
        >
          <Menu className="h-5 w-5" />
        </Button>

        {/* Logo */}
        <div className="flex items-center space-x-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <span className="text-sm font-bold">FBA</span>
          </div>
          <span className="hidden font-bold sm:inline-block">
            Amazon FBA AI Agent
          </span>
        </div>

        <div className="flex flex-1 items-center justify-end space-x-2">
          {/* Notifications */}
          <Button variant="ghost" size="icon" className="relative">
            <Bell className="h-5 w-5" />
            {notifications.length > 0 && (
              <Badge
                variant="error"
                className="absolute -right-1 -top-1 h-5 w-5 rounded-full p-0 text-xs"
              >
                {notifications.length}
              </Badge>
            )}
          </Button>

          {/* Theme Toggle */}
          <ThemeToggle />

          {/* Settings */}
          <Button variant="ghost" size="icon">
            <Settings className="h-5 w-5" />
          </Button>
        </div>
      </div>
    </nav>
  );
};

