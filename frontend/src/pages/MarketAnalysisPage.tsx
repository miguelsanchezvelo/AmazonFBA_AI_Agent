/**
 * Market Analysis Page
 * 
 * Analyze market trends and competition
 */

import React, { useState, useEffect } from 'react';
import { TrendingUp, Target, Users, DollarSign, Info, ChevronDown, ChevronUp, AlertCircle } from 'lucide-react';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { MetricCard } from '../components/Dashboard/MetricCard';
import { apiClient } from '../api/client';
import type { Product, Analysis } from '../types';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

export const MarketAnalysisPage: React.FC = () => {
  const [selectedProduct, setSelectedProduct] = useState<string | null>(null);
  const [showInfo, setShowInfo] = useState(false);
  const [loading, setLoading] = useState(false);
  const [analyses, setAnalyses] = useState<Analysis[]>([]);
  const [availableProducts, setAvailableProducts] = useState<Product[]>([]);

  // Fetch products on mount and check for URL parameter
  useEffect(() => {
    fetchAvailableProducts();
    
    // Check if there's an ASIN in the URL query parameters
    const urlParams = new URLSearchParams(window.location.search);
    const asinFromUrl = urlParams.get('asin');
    if (asinFromUrl) {
      setSelectedProduct(asinFromUrl);
    }
  }, []);

  // Fetch analyses when a product is selected
  useEffect(() => {
    if (selectedProduct) {
      fetchAnalyses();
    }
  }, [selectedProduct]);

  const fetchAvailableProducts = async () => {
    try {
      const response = await apiClient.getProducts(1, 100);
      setAvailableProducts(response.products || []);
    } catch (error) {
      console.error('Failed to fetch products:', error);
    }
  };

  const fetchAnalyses = async () => {
    if (!selectedProduct) return;
    
    setLoading(true);
    try {
      const response = await apiClient.getAnalysis(selectedProduct);
      setAnalyses(response.data || []);
    } catch (error) {
      console.error('Failed to fetch analyses:', error);
      setAnalyses([]);
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyzeMarket = async () => {
    if (!selectedProduct) {
      alert('Please select a product first');
      return;
    }

    setLoading(true);
    try {
      // Run market analysis for the selected product
      await apiClient.runAnalysis(selectedProduct, 'market');
      // Refresh analyses after running
      await fetchAnalyses();
    } catch (error) {
      console.error('Failed to run analysis:', error);
      alert('Failed to run market analysis. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const hasRealData = analyses.length > 0;

  // Process analysis data for charts
  const processAnalysisData = () => {
    if (!hasRealData) return null;

    // Extract metrics from the most recent analysis
    const latestAnalysis = analyses[0];
    const data = latestAnalysis.data || {};

    return {
      trendData: data.trend_data || [],
      competitionData: data.competition_data || [],
      seasonalityData: data.seasonality_data || [],
      metrics: latestAnalysis.metrics || {},
    };
  };

  const processedData = processAnalysisData();

  // Mock data for charts (fallback when no real data)
  const trendData = (processedData && processedData.trendData.length > 0)
    ? processedData.trendData 
    : [
    { month: 'Jan', searches: 4000, sales: 2400, competition: 2100 },
    { month: 'Feb', searches: 3000, sales: 1398, competition: 2210 },
    { month: 'Mar', searches: 2000, sales: 9800, competition: 2290 },
    { month: 'Apr', searches: 2780, sales: 3908, competition: 2000 },
    { month: 'May', searches: 1890, sales: 4800, competition: 2181 },
    { month: 'Jun', searches: 2390, sales: 3800, competition: 2500 },
  ];

  const competitionData = (processedData && processedData.competitionData.length > 0)
    ? processedData.competitionData
    : [
      { name: 'Low Competition', value: 35, color: '#10b981' },
      { name: 'Medium Competition', value: 45, color: '#f59e0b' },
      { name: 'High Competition', value: 20, color: '#ef4444' },
    ];

  const seasonalityData = (processedData && processedData.seasonalityData.length > 0)
    ? processedData.seasonalityData
    : [
    { month: 'Jan', demand: 65 },
    { month: 'Feb', demand: 59 },
    { month: 'Mar', demand: 80 },
    { month: 'Apr', demand: 81 },
    { month: 'May', demand: 56 },
    { month: 'Jun', demand: 55 },
    { month: 'Jul', demand: 40 },
    { month: 'Aug', demand: 95 },
    { month: 'Sep', demand: 88 },
    { month: 'Oct', demand: 100 },
    { month: 'Nov', demand: 98 },
    { month: 'Dec', demand: 85 },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Market Analysis</h1>
        <p className="text-muted-foreground">
          Analyze trends, competition, and market opportunities
        </p>
      </div>

      {/* Demo Mode Alert */}
      {!hasRealData && (
        <DevelopmentDisclaimer 
          type="mock-data"
          message="Esta página muestra datos de análisis de mercado simulados para demostración. Selecciona un producto de los descubiertos y haz clic en 'Analyze Market' para ver datos de análisis reales."
          details="Los datos reales incluyen métricas de búsqueda, análisis de competencia, tendencias de precios y análisis de estacionalidad basados en datos reales de Amazon y Google Trends."
        />
      )}

      {/* Info Banner */}
      <div className="rounded-lg border border-blue-200 bg-blue-50 p-4 dark:border-blue-800 dark:bg-blue-950/20">
        <button
          onClick={() => setShowInfo(!showInfo)}
          className="flex w-full items-center justify-between text-left"
        >
          <div className="flex items-center gap-2">
            <Info className="h-5 w-5 text-blue-600 dark:text-blue-400" />
            <span className="font-semibold text-blue-900 dark:text-blue-100">
              Understanding Market Analysis Metrics
            </span>
          </div>
          {showInfo ? (
            <ChevronUp className="h-5 w-5 text-blue-600 dark:text-blue-400" />
          ) : (
            <ChevronDown className="h-5 w-5 text-blue-600 dark:text-blue-400" />
          )}
        </button>

        {showInfo && (
          <div className="mt-4 space-y-3 border-t border-blue-200 pt-4 dark:border-blue-800">
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <h4 className="mb-2 font-semibold text-blue-900 dark:text-blue-100">
                  What We Analyze
                </h4>
                <ul className="space-y-1 text-sm text-blue-800 dark:text-blue-200">
                  <li>• <strong>Search Volume:</strong> How many people search for this product monthly</li>
                  <li>• <strong>Competition:</strong> Number of active sellers in the niche</li>
                  <li>• <strong>Seasonality:</strong> Demand patterns throughout the year</li>
                  <li>• <strong>Price Trends:</strong> Historical pricing data and market movements</li>
                </ul>
              </div>
              <div>
                <h4 className="mb-2 font-semibold text-blue-900 dark:text-blue-100">
                  Business Insights
                </h4>
                <ul className="space-y-1 text-sm text-blue-800 dark:text-blue-200">
                  <li>• <strong>Demand:</strong> High search volume = Strong market interest</li>
                  <li>• <strong>Supply:</strong> Low competition = Easier market entry</li>
                  <li>• <strong>Pricing:</strong> Stable prices = Predictable margins</li>
                  <li>• <strong>ROI:</strong> Balance of demand, competition & pricing</li>
                </ul>
              </div>
            </div>
            <div className="rounded-lg bg-white p-3 dark:bg-blue-900/20">
              <p className="text-xs text-blue-700 dark:text-blue-300">
                <strong>Note:</strong> Currently showing demo data. Real-time analysis will be available after
                connecting to live data sources. Use this to understand how market metrics influence product selection.
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Product Selection */}
      <Card>
        <div className="flex items-center gap-4">
          <div className="flex-1">
            <label className="mb-2 block text-sm font-medium">
              Select Product to Analyze
            </label>
            <select
              value={selectedProduct || ''}
              onChange={(e) => setSelectedProduct(e.target.value)}
              className="w-full rounded-md border bg-background px-3 py-2"
              disabled={loading || availableProducts.length === 0}
            >
              <option value="">
                {availableProducts.length === 0 
                  ? 'No products available - Run Product Discovery first' 
                  : 'Select a product...'}
              </option>
              {availableProducts.map((product) => (
                <option key={product.asin} value={product.asin}>
                  {product.title} (${product.price})
                </option>
              ))}
            </select>
          </div>
          <div className="flex items-end">
            <Button 
              onClick={handleAnalyzeMarket}
              disabled={!selectedProduct || loading}
            >
              {loading ? 'Analyzing...' : 'Analyze Market'}
            </Button>
          </div>
        </div>
      </Card>

      {/* Real Analysis Data */}
      {hasRealData && (
        <div className="space-y-6">
          <div className="rounded-lg border border-green-200 bg-green-50 p-4 dark:border-green-800 dark:bg-green-950/20">
            <div className="flex items-start gap-3">
              <TrendingUp className="h-5 w-5 text-green-600 dark:text-green-400" />
              <div className="flex-1">
                <h4 className="font-semibold text-green-900 dark:text-green-100">
                  Analysis Complete
                </h4>
                <p className="mt-1 text-sm text-green-800 dark:text-green-200">
                  Showing real analysis data for the selected product. Found {analyses.length} analysis report(s).
                </p>
              </div>
            </div>
          </div>

          {analyses.map((analysis, index) => (
            <Card key={analysis.id || index} className="p-6">
              <div className="mb-4 flex items-center justify-between">
                <div>
                  <h3 className="text-xl font-semibold">
                    {analysis.analysisType.charAt(0).toUpperCase() + analysis.analysisType.slice(1)} Analysis
                  </h3>
                  <p className="text-sm text-muted-foreground">
                    Generated on {new Date(analysis.createdAt).toLocaleString()}
                  </p>
                </div>
                {analysis.score && (
                  <div className="text-right">
                    <div className="text-3xl font-bold text-primary">{analysis.score}</div>
                    <div className="text-xs text-muted-foreground">Score / 100</div>
                  </div>
                )}
              </div>

              {/* Metrics */}
              {analysis.metrics && Object.keys(analysis.metrics).length > 0 && (
                <div className="mb-6">
                  <h4 className="mb-3 font-semibold">Key Metrics</h4>
                  <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                    {Object.entries(analysis.metrics).map(([key, value]) => (
                      <div key={key} className="rounded-lg border p-4">
                        <p className="text-xs font-medium text-muted-foreground">
                          {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                        </p>
                        <p className="mt-2 text-2xl font-bold">
                          {typeof value === 'number' 
                            ? key.toLowerCase().includes('price') || key.toLowerCase().includes('revenue')
                              ? `$${value.toFixed(2)}`
                              : key.toLowerCase().includes('margin') || key.toLowerCase().includes('rate')
                              ? `${value.toFixed(2)}%`
                              : value.toLocaleString()
                            : String(value)}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Insights */}
              {analysis.insights && analysis.insights.length > 0 && (
                <div className="mb-6">
                  <h4 className="mb-3 font-semibold">Insights</h4>
                  <div className="space-y-2">
                    {analysis.insights.map((insight, i) => (
                      <div key={i} className="flex items-start gap-3 rounded-lg border p-3">
                        <div className="mt-1 h-2 w-2 flex-shrink-0 rounded-full bg-primary" />
                        <p className="text-sm text-muted-foreground">{insight}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Recommendations */}
              {analysis.recommendations && analysis.recommendations.length > 0 && (
                <div>
                  <h4 className="mb-3 font-semibold">Recommendations</h4>
                  <div className="space-y-2">
                    {analysis.recommendations.map((rec, i) => (
                      <div key={i} className="flex items-start gap-3 rounded-lg border border-primary/20 bg-primary/5 p-3">
                        <TrendingUp className="mt-0.5 h-4 w-4 flex-shrink-0 text-primary" />
                        <p className="text-sm">{rec}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </Card>
          ))}
        </div>
      )}

      {/* Key Metrics - Demo Data */}
      {!hasRealData && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          title="Search Volume"
          value="45.2K"
          change={12.5}
          icon={<TrendingUp className="h-6 w-6" />}
          description="Monthly searches"
          tooltip="Number of monthly Amazon searches for this product/category. Higher volume indicates stronger demand and market interest."
        />
        <MetricCard
          title="Competition Level"
          value="Medium"
          icon={<Target className="h-6 w-6" />}
          description="Market saturation"
          tooltip="Difficulty of entering this market. Low = easier entry, High = more established sellers. Medium competition often offers the best balance."
        />
        <MetricCard
          title="Active Sellers"
          value="127"
          change={-5.2}
          icon={<Users className="h-6 w-6" />}
          description="Direct competitors"
          tooltip="Number of sellers currently offering similar products. Fewer sellers means less price competition and better profit margins."
        />
        <MetricCard
          title="Estimated Revenue"
          value="$12.5K"
          change={8.3}
          icon={<DollarSign className="h-6 w-6" />}
          description="Per month"
          tooltip="Projected monthly revenue based on search volume, pricing, and conversion rates. This is an estimate to gauge market size."
        />
        </div>
      )}

      {/* Charts - Demo Data */}
      {!hasRealData && (
        <>
        <div className="grid gap-4 md:grid-cols-2">
          {/* Trend Analysis */}
          <Card title="Market Trends" description="Last 6 months">
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={trendData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" />
              <YAxis />
              <RechartsTooltip />
              <Legend />
              <Line
                type="monotone"
                dataKey="searches"
                stroke="#3b82f6"
                strokeWidth={2}
              />
              <Line
                type="monotone"
                dataKey="sales"
                stroke="#10b981"
                strokeWidth={2}
              />
              <Line
                type="monotone"
                dataKey="competition"
                stroke="#f59e0b"
                strokeWidth={2}
              />
            </LineChart>
          </ResponsiveContainer>
        </Card>

        {/* Competition Distribution */}
        <Card title="Competition Level" description="Market distribution">
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={competitionData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) =>
                  `${name}: ${((percent as number) * 100).toFixed(0)}%`
                }
                outerRadius={80}
                fill="#8884d8"
                dataKey="value"
              >
                {competitionData.map((entry: any, index: number) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <RechartsTooltip />
            </PieChart>
          </ResponsiveContainer>
        </Card>

        {/* Seasonality */}
        <Card title="Seasonal Demand" description="12-month pattern" className="md:col-span-2">
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={seasonalityData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" />
              <YAxis />
              <RechartsTooltip />
              <Area
                type="monotone"
                dataKey="demand"
                stroke="#3b82f6"
                fill="#3b82f6"
                fillOpacity={0.3}
              />
            </AreaChart>
          </ResponsiveContainer>
        </Card>
      </div>

      {/* Insights */}
      <Card title="Market Insights" description="AI-generated recommendations">
        <div className="space-y-4">
          <div className="flex items-start gap-3 rounded-lg border p-4">
            <Badge variant="success">Opportunity</Badge>
            <div className="flex-1">
              <h4 className="font-semibold">Growing Demand Detected</h4>
              <p className="text-sm text-muted-foreground">
                Search volume has increased by 25% in the last 3 months. Consider
                increasing inventory.
              </p>
            </div>
          </div>
          <div className="flex items-start gap-3 rounded-lg border p-4">
            <Badge variant="warning">Warning</Badge>
            <div className="flex-1">
              <h4 className="font-semibold">High Competition Ahead</h4>
              <p className="text-sm text-muted-foreground">
                15 new sellers entered this category last month. Monitor pricing
                closely.
              </p>
            </div>
          </div>
          <div className="flex items-start gap-3 rounded-lg border p-4">
            <Badge variant="default">Info</Badge>
            <div className="flex-1">
              <h4 className="font-semibold">Peak Season Approaching</h4>
              <p className="text-sm text-muted-foreground">
                Historical data shows 45% increase in demand during Q4. Plan inventory
                accordingly.
              </p>
            </div>
          </div>
        </div>
      </Card>
        </>
      )}
    </div>
  );
};

export default MarketAnalysisPage;

