/**
 * Real Data Service Tests
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { realDataService } from '../../services/real-data.service';
import { apiClient } from '../../api/client';

// Mock apiClient
vi.mock('../../api/client', () => ({
  apiClient: {
    getOpportunities: vi.fn(),
    getReplenishment: vi.fn(),
    getCompetitorChanges: vi.fn(),
    getDashboardMetrics: vi.fn(),
    getAgentStatus: vi.fn(),
    getProducts: vi.fn(),
    getAnalysis: vi.fn(),
    getSuppliers: vi.fn(),
  },
}));

describe('RealDataService', () => {
  beforeEach(() => {
    // Clear cache before each test
    realDataService.clearCache();
    vi.clearAllMocks();
  });

  describe('getOpportunities', () => {
    it('fetches opportunities from API', async () => {
      const mockData = [
        { type: 'price_increase', potential: 500 },
        { type: 'supplier_change', potential: 300 },
      ];

      vi.mocked(apiClient.getOpportunities).mockResolvedValue({
        data: mockData,
        success: true,
      } as any);

      const result = await realDataService.getOpportunities();

      expect(apiClient.getOpportunities).toHaveBeenCalledOnce();
      expect(result).toEqual(mockData);
    });

    it('returns empty array on error', async () => {
      vi.mocked(apiClient.getOpportunities).mockRejectedValue(
        new Error('API Error')
      );

      const result = await realDataService.getOpportunities();

      expect(result).toEqual([]);
    });

    it('uses cache when available', async () => {
      const mockData = [{ type: 'test', potential: 100 }];
      vi.mocked(apiClient.getOpportunities).mockResolvedValue({
        data: mockData,
      } as any);

      // First call
      await realDataService.getOpportunities();
      // Second call (should use cache)
      await realDataService.getOpportunities();

      // Should only call API once
      expect(apiClient.getOpportunities).toHaveBeenCalledOnce();
    });

    it('forces refresh when requested', async () => {
      const mockData = [{ type: 'test', potential: 100 }];
      vi.mocked(apiClient.getOpportunities).mockResolvedValue({
        data: mockData,
      } as any);

      // First call
      await realDataService.getOpportunities();
      // Second call with force refresh
      await realDataService.getOpportunities({ forceRefresh: true });

      // Should call API twice
      expect(apiClient.getOpportunities).toHaveBeenCalledTimes(2);
    });
  });

  describe('getBusinessMetrics', () => {
    it('fetches business metrics from API', async () => {
      const mockMetrics = {
        revenue: 45000,
        profit: 12000,
        roi: 35.5,
      };

      vi.mocked(apiClient.getDashboardMetrics).mockResolvedValue({
        data: mockMetrics,
      } as any);

      const result = await realDataService.getBusinessMetrics();

      expect(apiClient.getDashboardMetrics).toHaveBeenCalledOnce();
      expect(result).toEqual(mockMetrics);
    });

    it('returns empty object on error', async () => {
      vi.mocked(apiClient.getDashboardMetrics).mockRejectedValue(
        new Error('Network error')
      );

      const result = await realDataService.getBusinessMetrics();

      expect(result).toEqual({});
    });
  });

  describe('getProducts', () => {
    it('fetches products with pagination', async () => {
      const mockProducts = [
        { asin: 'B001', title: 'Product 1', price: 29.99 },
        { asin: 'B002', title: 'Product 2', price: 39.99 },
      ];

      vi.mocked(apiClient.getProducts).mockResolvedValue({
        products: mockProducts,
        total: 2,
      } as any);

      const result = await realDataService.getProducts(1, 50);

      expect(apiClient.getProducts).toHaveBeenCalledWith(1, 50);
      expect(result).toEqual(mockProducts);
    });
  });

  describe('Cache Management', () => {
    it('clears specific cache key', async () => {
      const mockData = [{ test: 'data' }];
      vi.mocked(apiClient.getOpportunities).mockResolvedValue({
        data: mockData,
      } as any);

      // Load cache
      await realDataService.getOpportunities();
      
      // Clear specific key
      realDataService.clearCache('opportunities');
      
      // Next call should hit API again
      await realDataService.getOpportunities();

      expect(apiClient.getOpportunities).toHaveBeenCalledTimes(2);
    });

    it('clears all cache', async () => {
      const mockData = [{ test: 'data' }];
      vi.mocked(apiClient.getOpportunities).mockResolvedValue({
        data: mockData,
      } as any);
      vi.mocked(apiClient.getDashboardMetrics).mockResolvedValue({
        data: { revenue: 1000 },
      } as any);

      // Load multiple caches
      await realDataService.getOpportunities();
      await realDataService.getBusinessMetrics();
      
      // Clear all
      realDataService.clearCache();
      
      // Next calls should hit API
      await realDataService.getOpportunities();
      await realDataService.getBusinessMetrics();

      expect(apiClient.getOpportunities).toHaveBeenCalledTimes(2);
      expect(apiClient.getDashboardMetrics).toHaveBeenCalledTimes(2);
    });

    it('detects when real data is available', () => {
      // Initially no data
      expect(realDataService.hasRealData()).toBe(false);
    });
  });

  describe('Error Handling', () => {
    it('handles network errors gracefully', async () => {
      vi.mocked(apiClient.getOpportunities).mockRejectedValue(
        new Error('Network timeout')
      );

      const result = await realDataService.getOpportunities();

      expect(result).toEqual([]);
      // Should not throw
    });

    it('handles malformed API responses', async () => {
      vi.mocked(apiClient.getOpportunities).mockResolvedValue({
        data: null,
      } as any);

      const result = await realDataService.getOpportunities();

      expect(result).toEqual([]);
    });
  });
});

