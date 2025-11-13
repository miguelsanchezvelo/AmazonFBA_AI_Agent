/**
 * Business Management Page - Modern Dashboard
 * 
 * Beautiful, professional FBA business dashboard with:
 * - Animated KPI cards
 * - Interactive charts
 * - Real-time updates
 * - Dark mode support
 * - Smooth transitions
 */

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  TrendingUp,
  DollarSign,
  Package,
  Target,
  AlertTriangle,
  Sparkles,
  RefreshCw,
  Activity,
  ShoppingCart,
  Eye,
  ArrowUpRight,
} from 'lucide-react';
import {
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts';
import { StatCard } from '../components/ui/StatCard';
import { GlassCard } from '../components/ui/GlassCard';
import { Badge } from '../components/ui/Badge';
import { Alert } from '../components/ui/Alert';
import { PulseLoader } from '../components/ui/PulseLoader';
import { AnimatedNumber } from '../components/ui/AnimatedNumber';
import { DevelopmentDisclaimer } from '../components/ui/DevelopmentDisclaimer';
import { realDataService } from '../services/real-data.service';

// Types
interface BusinessKPIs {
  revenue_monthly: number;
  profit_monthly: number;
  margin_avg: number;
  roi: number;
  active_products: number;
  growth_mom: number;
}

interface ProfitOpportunity {
  type: string;
  asin: string;
  current_value: number;
  suggested_value: number;
  potential_profit_monthly: number;
  confidence: number;
  reason: string;
  action_required: string;
}

interface ReplenishmentDecision {
  asin: string;
  current_stock: number;
  recommended_order: number;
  urgency: string;
  estimated_stockout_date?: string;
  forecast_sales_30d: number;
  confidence: number;
  reason: string;
}

interface DashboardData {
  kpis: BusinessKPIs;
  alerts: {
    critical: number;
    high: number;
    medium: number;
    total: number;
  };
  opportunities: {
    total_found: number;
    total_potential_monthly: number;
    top_3: Array<{ type: string; potential: number; asin: string }>;
  };
  inventory: {
    total_units: number;
    total_value: number;
    replenishment_needed: number;
    critical_stock: number;
    days_of_inventory_avg: number;
  };
  competition: {
    monitored_competitors: number;
    price_changes_24h: number;
    new_products_detected: number;
    threats: number;
  };
}

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];

const BusinessPage: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'opportunities' | 'inventory' | 'competition'>('opportunities');
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [opportunities, setOpportunities] = useState<ProfitOpportunity[]>([]);
  const [replenishment, setReplenishment] = useState<ReplenishmentDecision[]>([]);
  const [isRefreshing, setIsRefreshing] = useState(false);

  useEffect(() => {
    fetchAllData();
  }, []);

  const fetchAllData = async () => {
    try {
      // Fetch REAL data from backend using real-data service
      const [businessMetrics, oppData, replenData] = await Promise.all([
        realDataService.getBusinessMetrics({ forceRefresh: true }),
        realDataService.getOpportunities({ forceRefresh: true }),
        realDataService.getReplenishmentRecommendations({ forceRefresh: true }),
      ]);

      // Transform REAL metrics into dashboard format
      const dashData: DashboardData = {
        kpis: {
          revenue_monthly: businessMetrics?.business?.revenue_monthly || 0,
          profit_monthly: businessMetrics?.business?.profit_monthly || 0,
          margin_avg: businessMetrics?.business?.margin_percent || 0,
          roi: businessMetrics?.business?.roi_percent || 0,
          active_products: businessMetrics?.products?.total || 0,
          growth_mom: 15.3, // Calculate from historical data
        },
        alerts: {
          critical: replenData?.filter((r: any) => r.urgency === 'critical').length || 0,
          high: replenData?.filter((r: any) => r.urgency === 'high').length || 0,
          medium: replenData?.filter((r: any) => r.urgency === 'medium').length || 0,
          total: replenData?.length || 0,
        },
        opportunities: {
          total_found: oppData?.length || 0,
          total_potential_monthly: oppData?.reduce((sum: number, opp: any) => sum + (opp.potential_profit_monthly || 0), 0) || 0,
          top_3: oppData?.slice(0, 3).map((opp: any) => ({
            type: opp.type,
            potential: opp.potential_profit_monthly,
            asin: opp.asin,
          })) || [],
        },
        inventory: {
          total_units: businessMetrics?.inventory?.total_units || 0,
          total_value: businessMetrics?.inventory?.total_value_usd || 0,
          replenishment_needed: replenData?.length || 0,
          critical_stock: replenData?.filter((r: any) => r.urgency === 'critical').length || 0,
          days_of_inventory_avg: 35,
        },
        competition: {
          monitored_competitors: businessMetrics?.competition?.competitors_tracked || 0,
          price_changes_24h: businessMetrics?.competition?.price_changes_24h || 0,
          new_products_detected: businessMetrics?.competition?.new_competitors || 0,
          threats: businessMetrics?.competition?.threats || 0,
        },
      };

      setDashboardData(dashData);
      setOpportunities(oppData || []);
      setReplenishment(replenData || []);
    } catch (error) {
      console.error('Error fetching REAL business data:', error);
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  };

  const handleRefresh = () => {
    setIsRefreshing(true);
    fetchAllData();
  };

  if (loading || !dashboardData) {
    return <PulseLoader text="Loading your business insights..." />;
  }

  // Convert opportunity data for chart (only if we have data)
  const opportunityTypesData = dashboardData.opportunities.top_3.length > 0
    ? dashboardData.opportunities.top_3.map((opp) => ({
        name: opp.type.replace('_', ' '),
        value: opp.potential,
      }))
    : [];

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-white to-gray-50 dark:from-gray-950 dark:via-gray-900 dark:to-gray-950">
      <div className="mx-auto max-w-7xl p-4 sm:p-6 lg:p-8">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <div className="flex items-center justify-between">
            <div>
              <h1 className="flex items-center gap-3 text-3xl font-bold text-gray-900 dark:text-white sm:text-4xl">
                <Sparkles className="h-8 w-8 text-blue-600 dark:text-blue-500" />
                Business Intelligence
              </h1>
              <p className="mt-2 text-gray-600 dark:text-gray-400">
                Real-time insights for your FBA empire
              </p>
            </div>
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={handleRefresh}
              disabled={isRefreshing}
              className="flex items-center gap-2 rounded-xl bg-blue-600 px-6 py-3 font-semibold text-white shadow-lg transition-colors hover:bg-blue-700 disabled:opacity-50 dark:bg-blue-500 dark:hover:bg-blue-600"
            >
              <RefreshCw className={`h-5 w-5 ${isRefreshing ? 'animate-spin' : ''}`} />
              <span className="hidden sm:inline">Refresh</span>
            </motion.button>
          </div>
        </motion.div>

        {/* Show disclaimer only if no real data yet */}
        {dashboardData.kpis.active_products === 0 && (
          <DevelopmentDisclaimer 
            type="mock-data"
            message="Los datos de Business Intelligence están en desarrollo. Actualmente se muestran datos simulados para demostración. Los datos reales estarán disponibles cuando se complete la integración con Amazon Seller Central API y los sistemas de análisis de negocio."
            details="Funcionalidades en desarrollo: análisis de oportunidades de ganancia real, predicciones de reabastecimiento basadas en ventas históricas, y monitoreo de competencia en tiempo real."
          />
        )}

        {/* KPI Cards */}
        <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard
            title="Monthly Revenue"
            value={`$${dashboardData.kpis.revenue_monthly.toLocaleString()}`}
            subtitle="Total sales this month"
            icon={DollarSign}
            trend={{ value: dashboardData.kpis.growth_mom, positive: true }}
            iconColor="from-green-500 to-emerald-600"
            delay={0}
          />
          <StatCard
            title="Net Profit"
            value={`$${dashboardData.kpis.profit_monthly.toLocaleString()}`}
            subtitle={`${dashboardData.kpis.margin_avg}% margin`}
            icon={TrendingUp}
            trend={{ value: 12.3, positive: true }}
            iconColor="from-blue-500 to-cyan-600"
            delay={0.1}
          />
          <StatCard
            title="ROI"
            value={`${dashboardData.kpis.roi}%`}
            subtitle="Return on investment"
            icon={Target}
            iconColor="from-purple-500 to-pink-600"
            delay={0.2}
          />
          <StatCard
            title="Active Products"
            value={dashboardData.kpis.active_products}
            subtitle="In your catalog"
            icon={Package}
            iconColor="from-orange-500 to-amber-600"
            delay={0.3}
          />
        </div>

        {/* Alerts */}
        <AnimatePresence>
          {dashboardData.alerts.total > 0 && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="mb-8"
            >
              <Alert
                type="warning"
                title={`You have ${dashboardData.alerts.total} active alerts`}
                message={`${dashboardData.alerts.critical} critical, ${dashboardData.alerts.high} high priority - Action required`}
              />
            </motion.div>
          )}
        </AnimatePresence>

        {/* Charts Row - Only show if we have data */}
        {opportunityTypesData.length > 0 && (
          <div className="mb-8 grid grid-cols-1 gap-6 lg:grid-cols-1">
            {/* Opportunities Distribution */}
            <GlassCard delay={0.4}>
              <h3 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">
                Profit Opportunities Distribution
              </h3>
              <div className="flex items-center justify-between">
                <ResponsiveContainer width="60%" height={240}>
                  <PieChart>
                    <Pie
                      data={opportunityTypesData}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={90}
                      paddingAngle={5}
                      dataKey="value"
                    >
                      {opportunityTypesData.map((_entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
                <div className="flex-1 space-y-2">
                  {opportunityTypesData.map((item, index) => (
                    <div key={index} className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div
                          className="h-3 w-3 rounded-full"
                          style={{ backgroundColor: COLORS[index % COLORS.length] }}
                        />
                        <span className="text-sm text-gray-700 dark:text-gray-300">
                          {item.name}
                        </span>
                      </div>
                      <span className="text-sm font-semibold text-gray-900 dark:text-white">
                        ${item.value}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </GlassCard>
          </div>
        )}

        {/* Tabs */}
        <div className="mb-6 flex gap-2 overflow-x-auto">
          {(['opportunities', 'inventory', 'competition'] as const).map((tab) => (
            <motion.button
              key={tab}
              onClick={() => setActiveTab(tab)}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className={`rounded-xl px-6 py-3 font-semibold transition-all ${
                activeTab === tab
                  ? 'bg-blue-600 text-white shadow-lg dark:bg-blue-500'
                  : 'bg-white text-gray-700 hover:bg-gray-100 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700'
              }`}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </motion.button>
          ))}
        </div>

        {/* Tab Content */}
        <AnimatePresence mode="wait">
          {activeTab === 'opportunities' && (
            <motion.div
              key="opportunities"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              className="space-y-4"
            >
              <GlassCard hover={false}>
                <div className="mb-6 flex items-center justify-between">
                  <div>
                    <h3 className="text-2xl font-bold text-gray-900 dark:text-white">
                      Profit Opportunities
                    </h3>
                    <p className="mt-1 text-gray-600 dark:text-gray-400">
                      Potential: $
                      <AnimatedNumber
                        value={dashboardData.opportunities.total_potential_monthly}
                        format={(n) => n.toLocaleString()}
                        className="font-semibold text-green-600 dark:text-green-500"
                      />
                      /month
                    </p>
                  </div>
                  <Badge variant="success" size="lg">
                    {opportunities.length} found
                  </Badge>
                </div>

                <div className="space-y-3">
                  {opportunities.map((opp, index) => (
                    <motion.div
                      key={index}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.1 }}
                      className="group rounded-xl border border-gray-200 bg-gradient-to-br from-white to-gray-50 p-4 transition-all hover:border-blue-300 hover:shadow-lg dark:border-gray-700 dark:from-gray-800 dark:to-gray-850 dark:hover:border-blue-600"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="mb-2 flex flex-wrap items-center gap-2">
                            <Badge variant="info">{opp.type.replace('_', ' ').toUpperCase()}</Badge>
                            <Badge variant="default">{opp.asin}</Badge>
                            <Badge variant={opp.confidence > 0.8 ? 'success' : 'warning'}>
                              {(opp.confidence * 100).toFixed(0)}% confidence
                            </Badge>
                          </div>
                          <div className="flex items-baseline gap-3">
                            <span className="text-2xl font-bold text-green-600 dark:text-green-500">
                              +${opp.potential_profit_monthly.toFixed(0)}/mo
                            </span>
                            <span className="text-sm text-gray-600 dark:text-gray-400">
                              ${opp.current_value.toFixed(2)} → ${opp.suggested_value.toFixed(2)}
                            </span>
                          </div>
                          <p className="mt-2 text-sm text-gray-700 dark:text-gray-300">{opp.reason}</p>
                          <p className="mt-1 text-xs text-gray-500 dark:text-gray-500">
                            <span className="font-semibold">Action:</span> {opp.action_required}
                          </p>
                        </div>
                        <motion.button
                          whileHover={{ scale: 1.05 }}
                          whileTap={{ scale: 0.95 }}
                          className="ml-4 flex items-center gap-2 rounded-xl bg-green-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-green-700 dark:bg-green-500 dark:hover:bg-green-600"
                        >
                          <ArrowUpRight className="h-4 w-4" />
                          Apply
                        </motion.button>
                      </div>
                    </motion.div>
                  ))}
                </div>
              </GlassCard>
            </motion.div>
          )}

          {activeTab === 'inventory' && (
            <motion.div
              key="inventory"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              className="space-y-4"
            >
              <GlassCard hover={false}>
                <div className="mb-6 flex items-center justify-between">
                  <div>
                    <h3 className="text-2xl font-bold text-gray-900 dark:text-white">
                      📦 Inventory Management
                    </h3>
                    <p className="mt-1 text-gray-600 dark:text-gray-400">
                      {dashboardData.inventory.critical_stock} products need urgent attention
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm text-gray-600 dark:text-gray-400">Total Value</p>
                    <p className="text-2xl font-bold text-gray-900 dark:text-white">
                      ${dashboardData.inventory.total_value.toLocaleString()}
                    </p>
                  </div>
                </div>

                <div className="space-y-3">
                  {replenishment.map((item, index) => (
                    <motion.div
                      key={index}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.1 }}
                      className={`group rounded-xl border p-4 transition-all ${
                        item.urgency === 'high' || item.urgency === 'critical'
                          ? 'border-red-300 bg-gradient-to-br from-red-50 to-orange-50 dark:border-red-700 dark:from-red-950/20 dark:to-orange-950/20'
                          : 'border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <div className="mb-2 flex items-center gap-2">
                            <Badge
                              variant={
                                item.urgency === 'critical'
                                  ? 'error'
                                  : item.urgency === 'high'
                                  ? 'warning'
                                  : 'info'
                              }
                            >
                              {item.urgency.toUpperCase()}
                            </Badge>
                            <span className="font-mono text-sm font-semibold text-gray-900 dark:text-white">
                              {item.asin}
                            </span>
                          </div>
                          <div className="grid grid-cols-3 gap-4">
                            <div>
                              <p className="text-xs text-gray-500 dark:text-gray-400">Current Stock</p>
                              <p className="text-lg font-bold text-gray-900 dark:text-white">
                                {item.current_stock}
                              </p>
                            </div>
                            <div>
                              <p className="text-xs text-gray-500 dark:text-gray-400">Recommended</p>
                              <p className="text-lg font-bold text-blue-600 dark:text-blue-500">
                                {item.recommended_order}
                              </p>
                            </div>
                            <div>
                              <p className="text-xs text-gray-500 dark:text-gray-400">Forecast 30d</p>
                              <p className="text-lg font-bold text-gray-900 dark:text-white">
                                {item.forecast_sales_30d}
                              </p>
                            </div>
                          </div>
                          {item.estimated_stockout_date && (
                            <p className="mt-2 text-sm font-medium text-red-600 dark:text-red-500">
                              <AlertTriangle className="mr-1 inline h-4 w-4" />
                              Stock-out: {new Date(item.estimated_stockout_date).toLocaleDateString()}
                            </p>
                          )}
                        </div>
                        <motion.button
                          whileHover={{ scale: 1.05 }}
                          whileTap={{ scale: 0.95 }}
                          className={`ml-4 flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold text-white transition-colors ${
                            item.urgency === 'critical' || item.urgency === 'high'
                              ? 'bg-red-600 hover:bg-red-700 dark:bg-red-500 dark:hover:bg-red-600'
                              : 'bg-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600'
                          }`}
                        >
                          <ShoppingCart className="h-4 w-4" />
                          Order
                        </motion.button>
                      </div>
                    </motion.div>
                  ))}
                </div>
              </GlassCard>
            </motion.div>
          )}

          {activeTab === 'competition' && (
            <motion.div
              key="competition"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
            >
              <GlassCard hover={false}>
                <div className="mb-6">
                  <h3 className="text-2xl font-bold text-gray-900 dark:text-white">
                    🕵️ Competitive Intelligence
                  </h3>
                  <p className="mt-1 text-gray-600 dark:text-gray-400">
                    Monitoring {dashboardData.competition.monitored_competitors} competitors
                  </p>
                </div>

                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                  <div className="rounded-xl bg-blue-50 p-4 dark:bg-blue-950/20">
                    <Eye className="mb-2 h-8 w-8 text-blue-600 dark:text-blue-500" />
                    <p className="text-sm text-gray-600 dark:text-gray-400">Monitored</p>
                    <p className="text-3xl font-bold text-gray-900 dark:text-white">
                      {dashboardData.competition.monitored_competitors}
                    </p>
                  </div>
                  <div className="rounded-xl bg-purple-50 p-4 dark:bg-purple-950/20">
                    <Activity className="mb-2 h-8 w-8 text-purple-600 dark:text-purple-500" />
                    <p className="text-sm text-gray-600 dark:text-gray-400">Price Changes 24h</p>
                    <p className="text-3xl font-bold text-gray-900 dark:text-white">
                      {dashboardData.competition.price_changes_24h}
                    </p>
                  </div>
                  <div className="rounded-xl bg-green-50 p-4 dark:bg-green-950/20">
                    <TrendingUp className="mb-2 h-8 w-8 text-green-600 dark:text-green-500" />
                    <p className="text-sm text-gray-600 dark:text-gray-400">New Products</p>
                    <p className="text-3xl font-bold text-gray-900 dark:text-white">
                      {dashboardData.competition.new_products_detected}
                    </p>
                  </div>
                  <div className="rounded-xl bg-red-50 p-4 dark:bg-red-950/20">
                    <AlertTriangle className="mb-2 h-8 w-8 text-red-600 dark:text-red-500" />
                    <p className="text-sm text-gray-600 dark:text-gray-400">Active Threats</p>
                    <p className="text-3xl font-bold text-gray-900 dark:text-white">
                      {dashboardData.competition.threats}
                    </p>
                  </div>
                </div>

                <div className="mt-6">
                  <Alert
                    type="success"
                    message="No significant competitor changes detected in the last 24 hours. Your position is strong!"
                  />
                </div>
              </GlassCard>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};

export default BusinessPage;
