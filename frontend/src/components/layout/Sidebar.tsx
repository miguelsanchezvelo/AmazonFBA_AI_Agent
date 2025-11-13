/**
 * Sidebar Component - Modern Navigation
 * 
 * Beautiful animated sidebar with smooth transitions
 */

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  LayoutDashboard,
  Search,
  TrendingUp,
  Users,
  Package,
  BarChart3,
  Settings,
  Sparkles,
  Activity,
} from 'lucide-react';
import { useUIStore } from '../../state/store';
import { cn } from '../../lib/utils';

interface NavItem {
  title: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: string;
  badgeColor?: string;
}

const navItems: NavItem[] = [
  {
    title: 'Dashboard',
    href: '/',
    icon: LayoutDashboard,
  },
  {
    title: 'Product Discovery',
    href: '/discovery',
    icon: Search,
  },
  {
    title: 'Market Analysis',
    href: '/analysis',
    icon: TrendingUp,
  },
  {
    title: 'Suppliers',
    href: '/suppliers',
    icon: Users,
  },
  {
    title: 'Inventory',
    href: '/inventory',
    icon: Package,
  },
  {
    title: 'Business Intelligence',
    href: '/business',
    icon: Sparkles,
  },
  {
    title: 'Reports',
    href: '/reports',
    icon: BarChart3,
  },
  {
    title: 'Settings',
    href: '/settings',
    icon: Settings,
  },
];

export const Sidebar: React.FC = () => {
  const { sidebarOpen, toggleSidebar } = useUIStore();
  const [activeItem, setActiveItem] = React.useState('/business');

  const sidebarVariants = {
    open: {
      x: 0,
      transition: {
        type: 'spring' as const,
        stiffness: 300,
        damping: 30,
      },
    },
    closed: {
      x: -300,
      transition: {
        type: 'spring' as const,
        stiffness: 300,
        damping: 30,
      },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, x: -20 },
    visible: (i: number) => ({
      opacity: 1,
      x: 0,
      transition: {
        delay: i * 0.05,
        duration: 0.3,
      },
    }),
  };

  return (
    <>
      {/* Sidebar */}
      <motion.aside
        variants={sidebarVariants}
        initial="closed"
        animate={sidebarOpen ? 'open' : 'closed'}
        className="fixed left-0 top-16 z-40 h-[calc(100vh-4rem)] w-64 border-r border-gray-200 bg-white/80 backdrop-blur-xl transition-colors dark:border-gray-800 dark:bg-gray-900/80"
      >
        <div className="flex h-full flex-col">
          {/* Navigation */}
          <div className="flex-1 overflow-y-auto p-4">
            <nav className="space-y-1">
              {navItems.map((item, index) => {
                const Icon = item.icon;
                const isActive = activeItem === item.href;

                return (
                  <motion.a
                    key={item.href}
                    href={item.href}
                    onClick={(e) => {
                      e.preventDefault();
                      setActiveItem(item.href);
                    }}
                    custom={index}
                    variants={itemVariants}
                    initial="hidden"
                    animate="visible"
                    whileHover={{ x: 4, transition: { duration: 0.2 } }}
                    whileTap={{ scale: 0.98 }}
                    className={cn(
                      'group relative flex items-center justify-between rounded-xl px-3 py-2.5 text-sm font-medium transition-all',
                      isActive
                        ? 'bg-gradient-to-r from-blue-600 to-purple-600 text-white shadow-lg shadow-blue-500/50 dark:shadow-blue-600/30'
                        : 'text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800'
                    )}
                  >
                    {/* Active indicator */}
                    {isActive && (
                      <motion.div
                        layoutId="activeIndicator"
                        className="absolute inset-0 rounded-xl bg-gradient-to-r from-blue-600 to-purple-600"
                        transition={{ type: 'spring', stiffness: 300, damping: 30 }}
                      />
                    )}

                    <div className="relative z-10 flex items-center space-x-3">
                      <Icon
                        className={cn(
                          'h-5 w-5 transition-transform',
                          isActive
                            ? 'text-white'
                            : 'text-gray-500 group-hover:text-gray-900 dark:text-gray-400 dark:group-hover:text-gray-200'
                        )}
                      />
                      <span className="relative">{item.title}</span>
                    </div>

                    {item.badge && (
                      <motion.span
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        transition={{ type: 'spring', stiffness: 500, damping: 15 }}
                        className={cn(
                          'relative z-10 flex h-5 w-5 items-center justify-center rounded-full text-xs font-bold text-white',
                          item.badgeColor || 'bg-red-500',
                          isActive && 'bg-white/20'
                        )}
                      >
                        {item.badge}
                      </motion.span>
                    )}
                  </motion.a>
                );
              })}
            </nav>
          </div>

          {/* Agent Status */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5 }}
            className="border-t border-gray-200 p-4 dark:border-gray-800"
          >
            <div className="rounded-xl bg-gradient-to-br from-green-50 to-emerald-50 p-3 dark:from-green-950/20 dark:to-emerald-950/20">
              <div className="flex items-center space-x-2">
                <div className="relative flex h-2 w-2">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-500 opacity-75"></span>
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-green-600"></span>
                </div>
                <div className="flex-1">
                  <p className="text-xs font-semibold text-gray-900 dark:text-white">
                    All Agents Active
                  </p>
                  <p className="text-xs text-gray-600 dark:text-gray-400">System operational</p>
                </div>
                <Activity className="h-4 w-4 text-green-600 dark:text-green-500" />
              </div>
            </div>
          </motion.div>
        </div>
      </motion.aside>

      {/* Overlay for mobile */}
      <AnimatePresence>
        {sidebarOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 z-30 bg-black/60 backdrop-blur-sm lg:hidden"
            onClick={toggleSidebar}
          />
        )}
      </AnimatePresence>
    </>
  );
};
