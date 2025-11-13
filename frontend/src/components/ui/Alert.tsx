/**
 * Alert Component - Beautiful alert messages
 * 
 * Modern alert with icons and animations
 */

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { AlertTriangle, CheckCircle, Info, XCircle, X } from 'lucide-react';
import { cn } from '../../lib/utils';

interface AlertProps {
  type: 'success' | 'error' | 'warning' | 'info';
  title?: string;
  message: string;
  dismissible?: boolean;
  onDismiss?: () => void;
  className?: string;
}

const alertConfig = {
  success: {
    icon: CheckCircle,
    bgClass: 'bg-green-50 dark:bg-green-950/20 border-green-200 dark:border-green-900',
    iconClass: 'text-green-600 dark:text-green-500',
    textClass: 'text-green-900 dark:text-green-100',
  },
  error: {
    icon: XCircle,
    bgClass: 'bg-red-50 dark:bg-red-950/20 border-red-200 dark:border-red-900',
    iconClass: 'text-red-600 dark:text-red-500',
    textClass: 'text-red-900 dark:text-red-100',
  },
  warning: {
    icon: AlertTriangle,
    bgClass: 'bg-yellow-50 dark:bg-yellow-950/20 border-yellow-200 dark:border-yellow-900',
    iconClass: 'text-yellow-600 dark:text-yellow-500',
    textClass: 'text-yellow-900 dark:text-yellow-100',
  },
  info: {
    icon: Info,
    bgClass: 'bg-blue-50 dark:bg-blue-950/20 border-blue-200 dark:border-blue-900',
    iconClass: 'text-blue-600 dark:text-blue-500',
    textClass: 'text-blue-900 dark:text-blue-100',
  },
};

export const Alert: React.FC<AlertProps> = ({
  type,
  title,
  message,
  dismissible = false,
  onDismiss,
  className,
}) => {
  const config = alertConfig[type];
  const Icon = config.icon;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -10 }}
        className={cn(
          'relative rounded-xl border p-4',
          config.bgClass,
          className
        )}
      >
        <div className="flex items-start">
          <Icon className={cn('h-5 w-5 flex-shrink-0', config.iconClass)} />
          <div className="ml-3 flex-1">
            {title && (
              <h3 className={cn('text-sm font-semibold', config.textClass)}>
                {title}
              </h3>
            )}
            <p className={cn('text-sm', title ? 'mt-1' : '', config.textClass)}>
              {message}
            </p>
          </div>
          {dismissible && onDismiss && (
            <button
              onClick={onDismiss}
              className={cn(
                'ml-3 flex-shrink-0 rounded-lg p-1 transition-colors hover:bg-black/5 dark:hover:bg-white/5',
                config.iconClass
              )}
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>
      </motion.div>
    </AnimatePresence>
  );
};

