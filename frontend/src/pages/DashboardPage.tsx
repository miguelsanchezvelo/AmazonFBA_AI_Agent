/**
 * Dashboard Page
 * 
 * Main dashboard with metrics, charts, and agent status
 */

import React, { useEffect } from 'react';
import {
  Package,
  TrendingUp,
  Users,
  AlertCircle,
  DollarSign,
  Percent,
} from 'lucide-react';
import { Card } from '../components/ui/Card';
import { MetricCard } from '../components/Dashboard/MetricCard';
import { AgentStatusCard } from '../components/Dashboard/AgentStatusCard';
import { DevelopmentDisclaimer } from '../components/ui/DevelopmentDisclaimer';
import { useDashboardStore } from '../state/store';
import { apiClient } from '../api/client';
import { realDataService } from '../services/real-data.service';
import { formatCurrency, formatPercentage } from '../lib/utils';

export const DashboardPage: React.FC = () => {
  const { metrics, agentStatuses, setMetrics, setAgentStatuses, setLoading } =
    useDashboardStore();

  // Fetch REAL dashboard data on mount
  useEffect(() => {
    const fetchDashboardData = async () => {
      setLoading(true);
      try {
        // Fetch REAL data from backend
        const [businessMetrics, agentStatus] = await Promise.all([
          realDataService.getBusinessMetrics({ forceRefresh: true }),
          realDataService.getAgentStatus({ forceRefresh: true }),
        ]);

        // Set REAL metrics
        if (businessMetrics && Object.keys(businessMetrics).length > 0) {
          // Transform backend metrics to match our store format
          const transformedMetrics = {
            totalProducts: businessMetrics.products?.total || 0,
            totalRevenue: businessMetrics.business?.revenue_monthly || 0,
            avgROI: businessMetrics.business?.roi_percent || 0,
            avgMargin: businessMetrics.business?.margin_percent || 0,
            totalSales: businessMetrics.products?.total || 0,
            inventory: businessMetrics.inventory?.total_value_usd || 0,
          };
          setMetrics(transformedMetrics);
        }

        // Set REAL agent statuses
        if (agentStatus && Object.keys(agentStatus).length > 0) {
          setAgentStatuses(agentStatus);
        }
      } catch (error) {
        console.error('Failed to fetch real dashboard data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();

    // Refresh every 30 seconds for REAL-TIME updates
    const interval = setInterval(fetchDashboardData, 30000);
    return () => clearInterval(interval);
  }, [setMetrics, setAgentStatuses, setLoading]);

  // Check if we have real data from the backend
  const hasRealMetrics = metrics && (metrics.totalProducts > 0 || metrics.totalRevenue > 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">
          Overview of your Amazon FBA business
        </p>
      </div>

      {/* Show disclaimer only if no real data yet */}
      {!hasRealMetrics && (
        <DevelopmentDisclaimer 
          type="development"
          message="El dashboard está en desarrollo. Las métricas mostradas se actualizarán cuando haya datos reales disponibles de productos descubiertos y análisis completados."
          details="Los datos mostrados reflejan el estado actual del sistema. A medida que descubras productos y ejecutes análisis, las métricas se actualizarán automáticamente."
        />
      )}

      {/* Metrics Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <MetricCard
          title="Total Products"
          value={metrics?.totalProducts || 0}
          change={12.5}
          icon={<Package className="h-6 w-6" />}
          description="Active products in inventory"
        />
        <MetricCard
          title="Total Revenue"
          value={formatCurrency(metrics?.totalRevenue || 0)}
          change={8.2}
          icon={<DollarSign className="h-6 w-6" />}
          description="Last 30 days"
        />
        <MetricCard
          title="Average ROI"
          value={formatPercentage((metrics?.avgROI || 0) / 100)}
          change={3.1}
          icon={<TrendingUp className="h-6 w-6" />}
          description="Return on investment"
        />
        <MetricCard
          title="Active Suppliers"
          value={metrics?.totalSuppliers || 0}
          icon={<Users className="h-6 w-6" />}
          description="Verified suppliers"
        />
        <MetricCard
          title="Profit Margin"
          value={formatPercentage((metrics?.profitMargin || 0) / 100)}
          change={-2.4}
          icon={<Percent className="h-6 w-6" />}
          description="Average margin"
        />
        <MetricCard
          title="Inventory Alerts"
          value={metrics?.inventoryAlerts || 0}
          icon={<AlertCircle className="h-6 w-6" />}
          description="Requires attention"
        />
      </div>

      {/* Charts - Will show when historical data is available */}
      <Card title="Analytics" description="Charts will appear when you have transaction history">
        <div className="flex h-64 items-center justify-center text-gray-500 dark:text-gray-400">
          <div className="text-center">
            <TrendingUp className="mx-auto h-12 w-12 opacity-50" />
            <p className="mt-4">No historical data yet</p>
            <p className="mt-2 text-sm">Start discovering products to see analytics</p>
          </div>
        </div>
      </Card>

      {/* Agent Status */}
      <div>
        <h2 className="mb-4 text-2xl font-bold">Agent Status</h2>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {agentStatuses.map((agent) => (
            <AgentStatusCard key={agent.name} agent={agent} />
          ))}
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;

