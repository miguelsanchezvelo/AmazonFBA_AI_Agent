/**
 * Type definitions for Amazon FBA AI Agent Frontend
 * 
 * Defines all TypeScript types and interfaces used across the application
 */

// Product types
export interface Product {
  id: string;
  asin: string;
  title: string;
  price: number;
  rating: number;
  reviews: number;
  bsr: number; // Best Seller Rank
  category: string;
  imageUrl?: string;
  url?: string;
  createdAt: string;
  updatedAt: string;
}

// Analysis types
export interface Analysis {
  id: string;
  productId: string;
  analysisType: 'market' | 'profitability' | 'competition' | 'demand' | 'profit';
  data: Record<string, any>;
  confidenceScore: number;
  score?: number;
  metrics?: Record<string, any>;
  insights?: string[];
  recommendations?: string[];
  createdAt: string;
}

export interface MarketAnalysis {
  trend: 'rising' | 'stable' | 'declining';
  searchVolume: number;
  competition: 'low' | 'medium' | 'high';
  seasonality: number[];
  estimatedRevenue: number;
}

export interface ProfitabilityAnalysis {
  cost: number;
  sellingPrice: number;
  estimatedProfit: number;
  roi: number;
  breakEvenUnits: number;
  marginPercentage: number;
}

// Supplier types
export interface Supplier {
  id: string;
  name: string;
  email: string;
  rating: number;
  country: string;
  products: string[]; // Product IDs
  communicationHistory: Communication[];
  lastContact: string;
  status: 'active' | 'pending' | 'inactive';
}

export interface Communication {
  id: string;
  date: string;
  type: 'email' | 'call' | 'message';
  subject: string;
  content: string;
  status: 'sent' | 'received' | 'pending';
}

// Inventory types
export interface Inventory {
  id: string;
  productId: string;
  quantity: number;
  location: string;
  lastOrderDate: string;
  nextRestockDate: string;
  minStock: number;
  maxStock: number;
  status: 'ok' | 'low' | 'critical' | 'overstock';
}

export interface InventoryAlert {
  id: string;
  type: 'restock' | 'overstock' | 'expiring';
  severity: 'info' | 'warning' | 'critical';
  message: string;
  productId: string;
  createdAt: string;
}

// Event types (for WebSocket)
export interface BaseEvent {
  id: string;
  type: string;
  timestamp: string;
  data: Record<string, any>;
}

export interface ProductDiscoveredEvent extends BaseEvent {
  type: 'product_discovered';
  data: {
    product: Product;
  };
}

export interface AnalysisCompleteEvent extends BaseEvent {
  type: 'analysis_complete';
  data: {
    analysis: Analysis;
  };
}

export interface SupplierFoundEvent extends BaseEvent {
  type: 'supplier_found';
  data: {
    supplier: Supplier;
  };
}

export interface InventoryAlertEvent extends BaseEvent {
  type: 'inventory_alert';
  data: {
    alert: InventoryAlert;
  };
}

export type WebSocketEvent =
  | ProductDiscoveredEvent
  | AnalysisCompleteEvent
  | SupplierFoundEvent
  | InventoryAlertEvent;

// Dashboard types
export interface DashboardMetrics {
  totalProducts: number;
  activeAnalyses: number;
  totalSuppliers: number;
  inventoryAlerts: number;
  avgROI: number;
  totalRevenue: number;
  profitMargin: number;
}

export interface AgentStatus {
  name: string;
  status: 'active' | 'idle' | 'error';
  lastActivity: string;
  eventsProcessed: number;
}

// API Response types
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  products?: T[]; // Alias for compatibility
  total: number;
  page: number;
  pageSize: number;
  hasMore: boolean;
}

// Filter and search types
export interface ProductFilters {
  category?: string;
  minPrice?: number;
  maxPrice?: number;
  minRating?: number;
  minReviews?: number;
  maxBSR?: number;
  searchQuery?: string;
}

export interface AnalysisFilters {
  analysisType?: Analysis['analysisType'];
  minConfidence?: number;
  dateFrom?: string;
  dateTo?: string;
}

// User preferences
export interface UserPreferences {
  theme: 'light' | 'dark' | 'system';
  defaultCurrency: string;
  notifications: {
    email: boolean;
    push: boolean;
    inventoryAlerts: boolean;
    supplierUpdates: boolean;
  };
  dashboard: {
    defaultView: 'overview' | 'products' | 'analysis' | 'suppliers' | 'inventory';
    refreshInterval: number;
  };
}

