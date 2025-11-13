/**
 * PulseLoader Component - Beautiful loading animation
 * 
 * Animated pulsing loader for async content
 */

import React from 'react';
import { motion } from 'framer-motion';

export const PulseLoader: React.FC<{ text?: string }> = ({ text = 'Loading...' }) => {
  return (
    <div className="flex min-h-[400px] flex-col items-center justify-center">
      <div className="flex space-x-2">
        {[0, 1, 2].map((i) => (
          <motion.div
            key={i}
            className="h-4 w-4 rounded-full bg-blue-600 dark:bg-blue-500"
            animate={{
              scale: [1, 1.2, 1],
              opacity: [0.5, 1, 0.5],
            }}
            transition={{
              duration: 1.5,
              repeat: Infinity,
              delay: i * 0.2,
            }}
          />
        ))}
      </div>
      <p className="mt-4 text-sm text-gray-600 dark:text-gray-400">{text}</p>
    </div>
  );
};

