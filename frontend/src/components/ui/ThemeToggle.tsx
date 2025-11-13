/**
 * ThemeToggle Component - Dark/Light mode switcher
 * 
 * Beautiful animated toggle for theme switching
 */

import React, { useEffect } from 'react';
import { Moon, Sun } from 'lucide-react';
import { motion } from 'framer-motion';
import { useTheme } from '../../hooks/useTheme';

export const ThemeToggle: React.FC = () => {
  const { theme, toggleTheme } = useTheme();

  useEffect(() => {
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [theme]);

  return (
    <motion.button
      onClick={toggleTheme}
      className="relative flex h-10 w-10 items-center justify-center rounded-xl border border-gray-300 bg-white text-gray-700 transition-colors hover:bg-gray-100 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.95 }}
      aria-label="Toggle theme"
    >
      <motion.div
        initial={false}
        animate={{
          rotate: theme === 'dark' ? 180 : 0,
          scale: theme === 'dark' ? 1 : 0,
        }}
        transition={{ duration: 0.3 }}
        className="absolute"
      >
        <Moon className="h-5 w-5" />
      </motion.div>
      <motion.div
        initial={false}
        animate={{
          rotate: theme === 'light' ? 0 : -180,
          scale: theme === 'light' ? 1 : 0,
        }}
        transition={{ duration: 0.3 }}
        className="absolute"
      >
        <Sun className="h-5 w-5" />
      </motion.div>
    </motion.button>
  );
};

