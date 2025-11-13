/**
 * ProductDiscoveryPage Tests
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ProductDiscoveryPage } from '../../pages/ProductDiscoveryPage';

// Mock API client
vi.mock('../../api/client', () => ({
  apiClient: {
    discoverProducts: vi.fn(),
    getProducts: vi.fn(),
  },
}));

// Mock Zustand store
vi.mock('../../state/store', () => ({
  useProductStore: () => ({
    products: [
      {
        asin: 'B001',
        title: 'Test Product 1',
        price: 29.99,
        rating: 4.5,
        reviews: 150,
        bsr: 12345,
        imageUrl: 'https://example.com/image.jpg',
      },
    ],
    setProducts: vi.fn(),
    setLoading: vi.fn(),
    loading: false,
  }),
}));

describe('ProductDiscoveryPage', () => {
  it('renders discovery page title', () => {
    render(<ProductDiscoveryPage />);
    expect(screen.getByText('Product Discovery')).toBeInTheDocument();
  });

  it('displays products when available', () => {
    render(<ProductDiscoveryPage />);
    
    expect(screen.getByText('Test Product 1')).toBeInTheDocument();
    expect(screen.getByText('$29.99')).toBeInTheDocument();
  });

  it('shows View Analysis button for each product', () => {
    render(<ProductDiscoveryPage />);
    
    const buttons = screen.getAllByText('View Analysis');
    expect(buttons.length).toBeGreaterThan(0);
  });

  it('displays product ratings', () => {
    render(<ProductDiscoveryPage />);
    
    // Should show rating and review count
    expect(screen.getByText(/4\.5/)).toBeInTheDocument();
    expect(screen.getByText(/150 reviews/)).toBeInTheDocument();
  });

  it('does not show disclaimer when products exist', () => {
    render(<ProductDiscoveryPage />);
    
    // Should not show "No products" disclaimer
    const emptyMessage = screen.queryByText(/No hay productos descubiertos/i);
    expect(emptyMessage).not.toBeInTheDocument();
  });
});

