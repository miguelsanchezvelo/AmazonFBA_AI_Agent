/**
 * GlassCard Component - Modern glass-morphism card
 * 
 * Beautiful card with blur effect and subtle shadows
 */

import React from 'react';
import { motion } from 'framer-motion';
import { cn } from '../../lib/utils';

interface GlassCardProps {
  children: React.ReactNode;
  className?: string;
  delay?: number;
  hover?: boolean;
}

export const GlassCard: React.FC<GlassCardProps> = ({
  children,
  className,
  delay = 0,
  hover = true,
}) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
      whileHover={hover ? { scale: 1.01, transition: { duration: 0.2 } } : undefined}
      className={cn(
        'rounded-2xl border border-gray-200/50 bg-white/80 p-6 shadow-xl backdrop-blur-sm transition-all',
        'dark:border-gray-700/50 dark:bg-gray-900/80',
        hover && 'hover:shadow-2xl',
        className
      )}
    >
      {children}
    </motion.div>
  );
};

