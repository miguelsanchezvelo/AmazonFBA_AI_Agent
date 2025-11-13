/**
 * Tooltip Component
 * 
 * Displays helpful information on hover
 */

import React, { useState } from 'react';
import { HelpCircle } from 'lucide-react';

interface TooltipProps {
  content: string;
  children?: React.ReactNode;
}

export const Tooltip: React.FC<TooltipProps> = ({ content, children }) => {
  const [show, setShow] = useState(false);

  return (
    <div className="relative inline-block">
      <div
        onMouseEnter={() => setShow(true)}
        onMouseLeave={() => setShow(false)}
        className="cursor-help"
      >
        {children || <HelpCircle className="h-4 w-4 text-muted-foreground" />}
      </div>
      {show && (
        <div className="absolute bottom-full left-1/2 z-50 mb-2 w-64 -translate-x-1/2 rounded-lg border bg-popover p-3 text-sm text-popover-foreground shadow-lg">
          <div className="relative">
            {content}
            <div className="absolute -bottom-1 left-1/2 h-2 w-2 -translate-x-1/2 rotate-45 border-b border-r bg-popover" />
          </div>
        </div>
      )}
    </div>
  );
};

