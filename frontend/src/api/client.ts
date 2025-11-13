/**
 * API Client for Amazon FBA Backend
 * 
 * Handles all HTTP requests to the FastAPI backend
 */

import axios, { type AxiosInstance, AxiosError } from 'axios';
import type {
  Product,
  Analysis,
  Supplier,
  Inventory,
  ApiResponse,
  PaginatedResponse,
  DashboardMetrics,
  ProductFilters,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Main API client instance
 */
class APIClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
        // Add authentication token if available
        const token = localStorage.getItem('auth_token');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        // Handle common errors
        if (error.response?.status === 401) {
          // Unauthorized - clear token and redirect to login
          localStorage.removeItem('auth_token');
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  // Health check
  async healthCheck(): Promise<ApiResponse<{ status: string }>> {
    const response = await this.client.get('/health');
    return response.data;
  }

  // ============ Product Endpoints ============

  async getProducts(
    page: number = 1,
    pageSize: number = 20,
    filters?: ProductFilters
  ): Promise<PaginatedResponse<Product>> {
    const response = await this.client.get('/api/v2/products/', {
      params: { page, pageSize, ...filters },
    });
    return response.data;
  }

  async getProduct(asin: string): Promise<ApiResponse<Product>> {
    const response = await this.client.get(`/api/v2/products/${asin}`);
    return response.data;
  }

  async discoverProducts(budget: number): Promise<ApiResponse<Product[]>> {
    const response = await this.client.post('/api/v2/products/discover', { budget });
    return response.data;
  }

  async deleteProduct(asin: string): Promise<ApiResponse<void>> {
    const response = await this.client.delete(`/api/v2/products/${asin}`);
    return response.data;
  }

  // ============ Analysis Endpoints ============

  async getAnalysis(asin: string): Promise<ApiResponse<Analysis[]>> {
    const response = await this.client.get(`/api/v2/analysis/${asin}`);
    return response.data;
  }

  async runAnalysis(
    asin: string,
    analysisType: Analysis['analysisType']
  ): Promise<ApiResponse<Analysis>> {
    const response = await this.client.post(`/api/v2/analysis/`, {
      asin,
      analysis_types: [analysisType],
      force_refresh: false,
    });
    return response.data;
  }

  async getAllAnalyses(
    page: number = 1,
    pageSize: number = 20
  ): Promise<PaginatedResponse<Analysis>> {
    const response = await this.client.get('/api/v2/analysis/', {
      params: { page, pageSize },
    });
    return response.data;
  }

  // ============ Supplier Endpoints ============

  async getSuppliers(
    page: number = 1,
    pageSize: number = 20
  ): Promise<PaginatedResponse<Supplier>> {
    const response = await this.client.get('/api/v2/suppliers/', {
      params: { page, pageSize },
    });
    return response.data;
  }

  async getSupplier(id: string): Promise<ApiResponse<Supplier>> {
    const response = await this.client.get(`/api/v2/suppliers/${id}`);
    return response.data;
  }

  async contactSupplier(
    supplierId: string,
    message: string
  ): Promise<ApiResponse<void>> {
    const response = await this.client.post('/api/v2/suppliers/contact', {
      supplierId,
      message,
    });
    return response.data;
  }

  async searchSuppliers(productId: string): Promise<ApiResponse<Supplier[]>> {
    const response = await this.client.post('/api/v2/suppliers/search', {
      productId,
    });
    return response.data;
  }

  // ============ Inventory Endpoints ============

  async getInventory(
    page: number = 1,
    pageSize: number = 20
  ): Promise<PaginatedResponse<Inventory>> {
    const response = await this.client.get('/api/v2/inventory/', {
      params: { page, pageSize },
    });
    return response.data;
  }

  async getInventoryByProduct(
    productId: string
  ): Promise<ApiResponse<Inventory>> {
    const response = await this.client.get(`/api/v2/inventory/${productId}`);
    return response.data;
  }

  async updateInventory(
    productId: string,
    quantity: number
  ): Promise<ApiResponse<Inventory>> {
    const response = await this.client.patch(`/api/v2/inventory/${productId}`, {
      quantity,
    });
    return response.data;
  }

  async getInventoryAlerts(): Promise<ApiResponse<any[]>> {
    const response = await this.client.get('/api/v2/inventory/alerts');
    return response.data;
  }

  // ============ Dashboard Endpoints ============

  async getDashboardMetrics(): Promise<ApiResponse<DashboardMetrics>> {
    const response = await this.client.get('/api/v2/dashboard/metrics');
    return response.data;
  }

  async getAgentStatus(): Promise<ApiResponse<any[]>> {
    const response = await this.client.get('/api/v2/dashboard/agents');
    return response.data;
  }
}

// Export singleton instance
export const apiClient = new APIClient();

// Export type for use in other files
export type { APIClient };

