/**
 * StatCard Component - Beautiful stat display with animations
 * 
 * Modern card for showing KPIs with icon and trend
 */

import React from 'react';
import { motion } from 'framer-motion';
import type { LucideIcon } from 'lucide-react';
import { cn } from '../../lib/utils';

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
  trend?: {
    value: number;
    positive: boolean;
  };
  iconColor?: string;
  delay?: number;
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  subtitle,
  icon: Icon,
  trend,
  iconColor = 'text-blue-500',
  delay = 0,
}) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
      whileHover={{ scale: 1.02, transition: { duration: 0.2 } }}
      className="group relative overflow-hidden rounded-2xl border border-gray-200 bg-white p-6 shadow-sm transition-all hover:shadow-lg dark:border-gray-800 dark:bg-gray-900"
    >
      {/* Gradient overlay on hover */}
      <div className="absolute inset-0 bg-gradient-to-br from-transparent via-transparent to-blue-50/50 opacity-0 transition-opacity group-hover:opacity-100 dark:to-blue-950/20" />
      
      <div className="relative flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-600 dark:text-gray-400">
            {title}
          </p>
          <p className="mt-2 text-3xl font-bold text-gray-900 dark:text-white">
            {value}
          </p>
          
          {subtitle && (
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-500">
              {subtitle}
            </p>
          )}
          
          {trend && (
            <div className="mt-2 flex items-center">
              <span
                className={cn(
                  'text-sm font-medium',
                  trend.positive
                    ? 'text-green-600 dark:text-green-500'
                    : 'text-red-600 dark:text-red-500'
                )}
              >
                {trend.positive ? '+' : ''}{trend.value}%
              </span>
              <span className="ml-2 text-xs text-gray-500">vs last month</span>
            </div>
          )}
        </div>
        
        <div
          className={cn(
            'flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br transition-transform group-hover:scale-110',
            iconColor
          )}
        >
          <Icon className="h-6 w-6 text-white" />
        </div>
      </div>
    </motion.div>
  );
};

