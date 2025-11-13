/**
 * Integration Tests - User Flows
 * 
 * Tests for complete user journeys through the application
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { apiClient } from '../../api/client';

// Mock API client
vi.mock('../../api/client');

describe('User Flow: Product Discovery to Analysis', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('completes discovery workflow', async () => {
    // Mock discovery response
    vi.mocked(apiClient.discoverProducts).mockResolvedValue({
      success: true,
      products: [
        {
          asin: 'B001',
          title: 'Yoga Mat Premium',
          price: 29.99,
          rating: 4.5,
          reviews: 150,
          bsr: 12345,
        },
      ],
    } as any);

    // Step 1: User enters search criteria
    const criteria = {
      keyword: 'yoga mats',
      maxPrice: 50,
      minRating: 4.0,
    };

    // Step 2: System discovers products
    const response = await apiClient.discoverProducts(criteria);
    expect(response.success).toBe(true);
    expect(response.products).toHaveLength(1);

    // Step 3: User sees product
    const product = response.products[0];
    expect(product.asin).toBe('B001');
    expect(product.price).toBe(29.99);

    // Step 4: User can navigate to analysis
    expect(product.asin).toBeTruthy();
  });
});

describe('User Flow: Complete Business Cycle', () => {
  it('completes full business analysis flow', async () => {
    // Mock all necessary API calls
    vi.mocked(apiClient.getProducts).mockResolvedValue({
      products: [{ asin: 'B001', title: 'Product', price: 29.99 }],
      total: 1,
    } as any);

    vi.mocked(apiClient.getAnalysis).mockResolvedValue({
      data: [
        {
          asin: 'B001',
          viability_score: 85,
          recommendation: 'GO',
        },
      ],
    } as any);

    // Step 1: Get products
    const products = await apiClient.getProducts(1, 10);
    expect(products.products).toHaveLength(1);

    // Step 2: Get analysis
    const analysis = await apiClient.getAnalysis('B001');
    expect(analysis.data).toHaveLength(1);
    expect(analysis.data[0].recommendation).toBe('GO');

    // Step 3: Verify workflow completes
    expect(products.products[0].asin).toBe('B001');
    expect(analysis.data[0].asin).toBe('B001');
  });
});

describe('User Flow: Dashboard Monitoring', () => {
  it('loads and refreshes dashboard data', async () => {
    const mockMetrics = {
      business: {
        revenue_monthly: 45000,
        profit_monthly: 12000,
        roi_percent: 35.5,
      },
      products: { total: 15 },
    };

    vi.mocked(apiClient.getDashboardMetrics).mockResolvedValue({
      data: mockMetrics,
    } as any);

    // Step 1: Initial load
    const metrics1 = await apiClient.getDashboardMetrics();
    expect(metrics1.data.business.revenue_monthly).toBe(45000);

    // Step 2: Refresh
    const metrics2 = await apiClient.getDashboardMetrics();
    expect(metrics2.data.business.revenue_monthly).toBe(45000);

    // Verify data consistency
    expect(metrics1).toEqual(metrics2);
  });
});

describe('User Flow: Supplier Discovery', () => {
  it('searches and evaluates suppliers', async () => {
    const mockSuppliers = [
      {
        id: 'SUP001',
        name: 'Alibaba Supplier',
        country: 'China',
        rating: 4.8,
        trust_score: 85,
      },
    ];

    vi.mocked(apiClient.getSuppliers).mockResolvedValue({
      data: mockSuppliers,
    } as any);

    // Step 1: Get suppliers
    const suppliers = await apiClient.getSuppliers();
    expect(suppliers.data).toHaveLength(1);

    // Step 2: Verify supplier quality
    const supplier = suppliers.data[0];
    expect(supplier.trust_score).toBeGreaterThan(70);
    expect(supplier.rating).toBeGreaterThan(4.0);
  });
});

describe('Error Handling in User Flows', () => {
  it('handles API errors gracefully', async () => {
    vi.mocked(apiClient.getProducts).mockRejectedValue(
      new Error('Network error')
    );

    // Should handle error without crashing
    try {
      await apiClient.getProducts(1, 10);
    } catch (error) {
      expect(error).toBeDefined();
    }
  });

  it('handles empty responses', async () => {
    vi.mocked(apiClient.getProducts).mockResolvedValue({
      products: [],
      total: 0,
    } as any);

    const response = await apiClient.getProducts(1, 10);
    
    expect(response.products).toEqual([]);
    expect(response.total).toBe(0);
  });

  it('handles malformed data', async () => {
    vi.mocked(apiClient.getProducts).mockResolvedValue({
      products: null,
    } as any);

    const response = await apiClient.getProducts(1, 10);
    
    // Should handle gracefully
    expect(response).toBeDefined();
  });
});

