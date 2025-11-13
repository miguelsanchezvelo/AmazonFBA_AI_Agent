/**
 * DashboardPage Tests
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { DashboardPage } from '../../pages/DashboardPage';
import { realDataService } from '../../services/real-data.service';

// Mock the real data service
vi.mock('../../services/real-data.service', () => ({
  realDataService: {
    getBusinessMetrics: vi.fn(),
    getAgentStatus: vi.fn(),
    clearCache: vi.fn(),
  },
}));

// Mock Zustand store
vi.mock('../../state/store', () => ({
  useDashboardStore: () => ({
    metrics: {
      totalProducts: 15,
      totalRevenue: 45000,
      avgROI: 35.5,
      avgMargin: 26.7,
      totalSales: 1250,
      inventory: 18750,
    },
    agentStatuses: {
      agents: {
        discovery: { status: 'running' },
        analysis: { status: 'running' },
      },
    },
    setMetrics: vi.fn(),
    setAgentStatuses: vi.fn(),
    setLoading: vi.fn(),
  }),
}));

describe('DashboardPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    
    // Mock successful API responses
    vi.mocked(realDataService.getBusinessMetrics).mockResolvedValue({
      business: {
        revenue_monthly: 45000,
        profit_monthly: 12000,
        margin_percent: 26.7,
        roi_percent: 35.5,
      },
      products: {
        total: 15,
        active: 15,
      },
      inventory: {
        total_units: 1250,
        total_value_usd: 18750,
      },
    });

    vi.mocked(realDataService.getAgentStatus).mockResolvedValue({
      agents: {
        discovery: { status: 'running' },
        analysis: { status: 'running' },
      },
    });
  });

  it('renders dashboard title', () => {
    render(<DashboardPage />);
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
  });

  it('displays metrics when data is available', async () => {
    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText('Total Products')).toBeInTheDocument();
      expect(screen.getByText('Total Revenue')).toBeInTheDocument();
      expect(screen.getByText('Average ROI')).toBeInTheDocument();
    });
  });

  it('fetches data on mount', async () => {
    render(<DashboardPage />);

    await waitFor(() => {
      expect(realDataService.getBusinessMetrics).toHaveBeenCalled();
      expect(realDataService.getAgentStatus).toHaveBeenCalled();
    });
  });

  it('does not show disclaimer when real data exists', async () => {
    render(<DashboardPage />);

    await waitFor(() => {
      // Should not show development disclaimer when metrics > 0
      const disclaimer = screen.queryByText(/en desarrollo/i);
      expect(disclaimer).not.toBeInTheDocument();
    });
  });

  it('handles API errors gracefully', async () => {
    vi.mocked(realDataService.getBusinessMetrics).mockRejectedValue(
      new Error('API Error')
    );

    // Should not throw
    expect(() => render(<DashboardPage />)).not.toThrow();
  });
});

