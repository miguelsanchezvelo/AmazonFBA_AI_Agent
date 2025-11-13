/**
 * Agent Status Card Component
 * 
 * Displays status of a single agent
 */

import React from 'react';
import { Activity, Clock, CheckCircle, XCircle } from 'lucide-react';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { formatRelativeTime } from '../../lib/utils';
import type { AgentStatus } from '../../types';

interface AgentStatusCardProps {
  agent: AgentStatus;
}

export const AgentStatusCard: React.FC<AgentStatusCardProps> = ({ agent }) => {
  const getStatusIcon = () => {
    switch (agent.status) {
      case 'active':
        return <CheckCircle className="h-5 w-5 text-green-600" />;
      case 'idle':
        return <Clock className="h-5 w-5 text-yellow-600" />;
      case 'error':
        return <XCircle className="h-5 w-5 text-red-600" />;
      default:
        return <Activity className="h-5 w-5" />;
    }
  };

  const getStatusBadge = () => {
    const variants = {
      active: 'success' as const,
      idle: 'warning' as const,
      error: 'error' as const,
    };
    return <Badge variant={variants[agent.status]}>{agent.status}</Badge>;
  };

  return (
    <Card className="hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          {getStatusIcon()}
          <div>
            <h3 className="font-semibold">{agent.name}</h3>
            <p className="text-sm text-muted-foreground">
              Last active {formatRelativeTime(agent.lastActivity)}
            </p>
          </div>
        </div>
        <div className="flex flex-col items-end space-y-2">
          {getStatusBadge()}
          <span className="text-xs text-muted-foreground">
            {agent.eventsProcessed} events
          </span>
        </div>
      </div>
    </Card>
  );
};

