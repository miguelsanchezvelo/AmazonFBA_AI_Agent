/**
 * Product Analysis Modal
 * 
 * Displays detailed analysis for a product
 */

import React, { useEffect, useState } from 'react';
import { X, TrendingUp, DollarSign, Package, AlertCircle, BarChart3, Target } from 'lucide-react';
import { Card } from './ui/Card';
import { Button } from './ui/Button';
import { Badge } from './ui/Badge';
import { apiClient } from '../api/client';
import type { Analysis } from '../types';

interface ProductAnalysisModalProps {
  asin: string;
  productTitle: string;
  onClose: () => void;
}

export const ProductAnalysisModal: React.FC<ProductAnalysisModalProps> = ({
  asin,
  productTitle,
  onClose,
}) => {
  const [analyses, setAnalyses] = useState<Analysis[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchAnalysis();
  }, [asin]);

  const fetchAnalysis = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.getAnalysis(asin);
      setAnalyses(response.data || []);
    } catch (err) {
      console.error('Failed to fetch analysis:', err);
      setError('Failed to load analysis data. Please try again later.');
    } finally {
      setLoading(false);
    }
  };

  const getAnalysisIcon = (type: Analysis['analysisType']) => {
    switch (type) {
      case 'market':
        return <BarChart3 className="h-5 w-5" />;
      case 'competition':
        return <Target className="h-5 w-5" />;
      case 'profit':
        return <DollarSign className="h-5 w-5" />;
      default:
        return <TrendingUp className="h-5 w-5" />;
    }
  };

  const getAnalysisTitle = (type: Analysis['analysisType']) => {
    switch (type) {
      case 'market':
        return 'Market Analysis';
      case 'competition':
        return 'Competition Analysis';
      case 'profit':
        return 'Profit Analysis';
      default:
        return 'General Analysis';
    }
  };

  const formatMetric = (key: string, value: any): string => {
    if (typeof value === 'number') {
      if (key.toLowerCase().includes('price') || key.toLowerCase().includes('revenue')) {
        return `$${value.toFixed(2)}`;
      }
      if (key.toLowerCase().includes('margin') || key.toLowerCase().includes('rate')) {
        return `${value.toFixed(2)}%`;
      }
      return value.toLocaleString();
    }
    return String(value);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <Card className="max-h-[90vh] w-full max-w-4xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between border-b p-6">
          <div>
            <h2 className="text-2xl font-bold">Product Analysis</h2>
            <p className="mt-1 text-sm text-muted-foreground line-clamp-1">
              {productTitle}
            </p>
            <p className="text-xs text-muted-foreground">ASIN: {asin}</p>
          </div>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="h-5 w-5" />
          </Button>
        </div>

        {/* Content */}
        <div className="overflow-y-auto p-6" style={{ maxHeight: 'calc(90vh - 180px)' }}>
          {loading && (
            <div className="flex items-center justify-center py-12">
              <div className="text-center">
                <div className="mx-auto mb-4 h-12 w-12 animate-spin rounded-full border-4 border-primary border-t-transparent" />
                <p className="text-sm text-muted-foreground">Loading analysis...</p>
              </div>
            </div>
          )}

          {error && (
            <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4">
              <div className="flex items-start gap-3">
                <AlertCircle className="h-5 w-5 text-destructive" />
                <div>
                  <h3 className="font-semibold text-destructive">Error</h3>
                  <p className="mt-1 text-sm text-destructive/90">{error}</p>
                </div>
              </div>
            </div>
          )}

          {!loading && !error && analyses.length === 0 && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-6 dark:border-amber-800 dark:bg-amber-950/20">
              <div className="flex items-start gap-3">
                <Package className="h-6 w-6 text-amber-600 dark:text-amber-400" />
                <div>
                  <h3 className="text-lg font-semibold text-amber-800 dark:text-amber-100">
                    No Analysis Available
                  </h3>
                  <p className="mt-1 text-sm text-amber-700 dark:text-amber-200">
                    No analysis data is currently available for this product. Analysis may still be in progress
                    or hasn't been initiated yet.
                  </p>
                </div>
              </div>
            </div>
          )}

          {!loading && !error && analyses.length > 0 && (
            <div className="space-y-6">
              {analyses.map((analysis, index) => (
                <Card key={analysis.id || index} className="p-6">
                  <div className="mb-4 flex items-center gap-3">
                    <div className="rounded-lg bg-primary/10 p-2 text-primary">
                      {getAnalysisIcon(analysis.analysisType)}
                    </div>
                    <div>
                      <h3 className="font-semibold">{getAnalysisTitle(analysis.analysisType)}</h3>
                      <p className="text-xs text-muted-foreground">
                        {new Date(analysis.createdAt).toLocaleDateString()}
                      </p>
                    </div>
                    <Badge variant="default" className="ml-auto">
                      Score: {analysis.score ? `${analysis.score}/100` : 'N/A'}
                    </Badge>
                  </div>

                  {/* Metrics */}
                  {analysis.metrics && Object.keys(analysis.metrics).length > 0 && (
                    <div className="mb-4 grid gap-4 sm:grid-cols-2">
                      {Object.entries(analysis.metrics).map(([key, value]) => (
                        <div key={key} className="rounded-lg border p-3">
                          <p className="text-xs font-medium text-muted-foreground">
                            {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                          </p>
                          <p className="mt-1 text-lg font-semibold">
                            {formatMetric(key, value)}
                          </p>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Insights */}
                  {analysis.insights && analysis.insights.length > 0 && (
                    <div className="space-y-2">
                      <h4 className="text-sm font-semibold">Key Insights:</h4>
                      <ul className="space-y-1 text-sm">
                        {analysis.insights.map((insight, i) => (
                          <li key={i} className="flex items-start gap-2">
                            <span className="mt-1 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-primary" />
                            <span className="text-muted-foreground">{insight}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Recommendations */}
                  {analysis.recommendations && analysis.recommendations.length > 0 && (
                    <div className="mt-4 space-y-2">
                      <h4 className="text-sm font-semibold">Recommendations:</h4>
                      <ul className="space-y-1 text-sm">
                        {analysis.recommendations.map((rec, i) => (
                          <li key={i} className="flex items-start gap-2">
                            <TrendingUp className="mt-0.5 h-4 w-4 flex-shrink-0 text-primary" />
                            <span className="text-muted-foreground">{rec}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </Card>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="border-t p-6">
          <Button onClick={onClose} className="w-full">
            Close
          </Button>
        </div>
      </Card>
    </div>
  );
};

export default ProductAnalysisModal;

