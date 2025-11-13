/**
 * Badge Component - Modern badge with variants
 * 
 * Updated with beautiful colors and animations
 */

import React from 'react';
import { motion } from 'framer-motion';
import { cn } from '../../lib/utils';

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'default' | 'success' | 'warning' | 'error' | 'info' | 'purple' | 'pink';
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  pulse?: boolean;
}

const variantClasses = {
  default: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200',
  success: 'bg-green-100 text-green-800 dark:bg-green-950/50 dark:text-green-300',
  warning: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-950/50 dark:text-yellow-300',
  error: 'bg-red-100 text-red-800 dark:bg-red-950/50 dark:text-red-300',
  info: 'bg-blue-100 text-blue-800 dark:bg-blue-950/50 dark:text-blue-300',
  purple: 'bg-purple-100 text-purple-800 dark:bg-purple-950/50 dark:text-purple-300',
  pink: 'bg-pink-100 text-pink-800 dark:bg-pink-950/50 dark:text-pink-300',
};

const sizeClasses = {
  sm: 'px-2 py-0.5 text-xs',
  md: 'px-2.5 py-1 text-sm',
  lg: 'px-3 py-1.5 text-base',
};

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'default',
  size = 'sm',
  className,
  pulse = false,
}) => {
  return (
    <motion.span
      initial={{ scale: 0.9, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      className={cn(
        'inline-flex items-center rounded-full font-medium',
        variantClasses[variant],
        sizeClasses[size],
        pulse && 'animate-pulse',
        className
      )}
    >
      {children}
    </motion.span>
  );
};
