/**
 * Metric Card Component
 * 
 * Displays a single metric with icon and trend
 */

import React from 'react';
import { TrendingUp, TrendingDown } from 'lucide-react';
import { Card } from '../ui/Card';
import { Tooltip } from '../ui/Tooltip';
import { cn } from '../../lib/utils';

interface MetricCardProps {
  title: string;
  value: string | number;
  change?: number;
  icon: React.ReactNode;
  description?: string;
  tooltip?: string;
  format?: 'number' | 'currency' | 'percentage';
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  change,
  icon,
  description,
  tooltip,
}) => {
  const isPositive = change && change > 0;
  const isNegative = change && change < 0;

  return (
    <Card className="hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <p className="text-sm font-medium text-muted-foreground">{title}</p>
            {tooltip && <Tooltip content={tooltip} />}
          </div>
          <div className="flex items-baseline gap-2">
            <h2 className="text-3xl font-bold tracking-tight">{value}</h2>
            {change !== undefined && (
              <div
                className={cn(
                  'flex items-center text-sm font-medium',
                  isPositive && 'text-green-600',
                  isNegative && 'text-red-600'
                )}
              >
                {isPositive ? (
                  <TrendingUp className="mr-1 h-4 w-4" />
                ) : (
                  <TrendingDown className="mr-1 h-4 w-4" />
                )}
                {Math.abs(change)}%
              </div>
            )}
          </div>
          {description && (
            <p className="mt-1 text-xs text-muted-foreground">{description}</p>
          )}
        </div>
        <div className="rounded-lg bg-primary/10 p-3 text-primary">
          {icon}
        </div>
      </div>
    </Card>
  );
};

