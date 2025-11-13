/**
 * Real Data Service
 *
 * Centralized service for accessing real business data from backend.
 * Replaces all mock data with real API calls.
 *
 * Features:
 * - Automatic caching with TTL
 * - Error handling and fallbacks
 * - Type-safe responses
 * - Real-time updates
 */

import { apiClient } from '../api/client';

export interface RealDataOptions {
  useCache?: boolean;
  cacheTTL?: number;
  forceRefresh?: boolean;
}

class RealDataService {
  private cache: Map<string, { data: any; timestamp: number }> = new Map();
  private readonly DEFAULT_CACHE_TTL = 5 * 60 * 1000; // 5 minutes

  /**
   * Get all business opportunities with real data
   */
  async getOpportunities(options?: RealDataOptions) {
    const cacheKey = 'opportunities';
    
    if (!options?.forceRefresh && this.isCached(cacheKey, options?.cacheTTL)) {
      return this.cache.get(cacheKey)?.data;
    }

    try {
      const response = await apiClient.getOpportunities();
      const data = response.data || [];
      this.setCache(cacheKey, data, options?.cacheTTL);
      return data;
    } catch (error) {
      console.error('Failed to fetch opportunities:', error);
      return [];
    }
  }

  /**
   * Get replenishment recommendations with real data
   */
  async getReplenishmentRecommendations(options?: RealDataOptions) {
    const cacheKey = 'replenishment';
    
    if (!options?.forceRefresh && this.isCached(cacheKey, options?.cacheTTL)) {
      return this.cache.get(cacheKey)?.data;
    }

    try {
      const response = await apiClient.getReplenishment();
      const data = response.data || [];
      this.setCache(cacheKey, data, options?.cacheTTL);
      return data;
    } catch (error) {
      console.error('Failed to fetch replenishment:', error);
      return [];
    }
  }

  /**
   * Get competitor changes with real data
   */
  async getCompetitorChanges(options?: RealDataOptions) {
    const cacheKey = 'competitor-changes';
    
    if (!options?.forceRefresh && this.isCached(cacheKey, options?.cacheTTL)) {
      return this.cache.get(cacheKey)?.data;
    }

    try {
      const response = await apiClient.getCompetitorChanges();
      const data = response.data || [];
      this.setCache(cacheKey, data, options?.cacheTTL);
      return data;
    } catch (error) {
      console.error('Failed to fetch competitor changes:', error);
      return [];
    }
  }

  /**
   * Get real business metrics
   */
  async getBusinessMetrics(options?: RealDataOptions) {
    const cacheKey = 'business-metrics';
    
    if (!options?.forceRefresh && this.isCached(cacheKey, options?.cacheTTL)) {
      return this.cache.get(cacheKey)?.data;
    }

    try {
      const response = await apiClient.getDashboardMetrics();
      const data = response.data || {};
      this.setCache(cacheKey, data, options?.cacheTTL);
      return data;
    } catch (error) {
      console.error('Failed to fetch business metrics:', error);
      return {};
    }
  }

  /**
   * Get real agent status
   */
  async getAgentStatus(options?: RealDataOptions) {
    const cacheKey = 'agent-status';
    
    if (!options?.forceRefresh && this.isCached(cacheKey, options?.cacheTTL)) {
      return this.cache.get(cacheKey)?.data;
    }

    try {
      const response = await apiClient.getAgentStatus();
      const data = response.data || {};
      this.setCache(cacheKey, data, options?.cacheTTL);
      return data;
    } catch (error) {
      console.error('Failed to fetch agent status:', error);
      return {};
    }
  }

  /**
   * Get real products with data
   */
  async getProducts(page: number = 1, limit: number = 100) {
    try {
      const response = await apiClient.getProducts(page, limit);
      return response.products || [];
    } catch (error) {
      console.error('Failed to fetch products:', error);
      return [];
    }
  }

  /**
   * Get real analysis for product
   */
  async getProductAnalysis(asin: string) {
    try {
      const response = await apiClient.getAnalysis(asin);
      return response.data || [];
    } catch (error) {
      console.error('Failed to fetch analysis:', error);
      return [];
    }
  }

  /**
   * Get real suppliers
   */
  async getSuppliers() {
    try {
      const response = await apiClient.getSuppliers();
      return response.data || [];
    } catch (error) {
      console.error('Failed to fetch suppliers:', error);
      return [];
    }
  }

  /**
   * Clear cache
   */
  clearCache(key?: string) {
    if (key) {
      this.cache.delete(key);
    } else {
      this.cache.clear();
    }
  }

  /**
   * Check if data is cached and fresh
   */
  private isCached(key: string, ttl?: number): boolean {
    const cached = this.cache.get(key);
    if (!cached) return false;

    const age = Date.now() - cached.timestamp;
    const maxAge = ttl || this.DEFAULT_CACHE_TTL;
    
    return age < maxAge;
  }

  /**
   * Set cache with TTL
   */
  private setCache(key: string, data: any, ttl?: number) {
    this.cache.set(key, {
      data,
      timestamp: Date.now()
    });

    // Auto-expire after TTL
    const maxAge = ttl || this.DEFAULT_CACHE_TTL;
    setTimeout(() => {
      this.cache.delete(key);
    }, maxAge);
  }

  /**
   * Check if we have any real data
   */
  hasRealData(): boolean {
    return this.cache.size > 0;
  }
}

// Export singleton instance
export const realDataService = new RealDataService();

