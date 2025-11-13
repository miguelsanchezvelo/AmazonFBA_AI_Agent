/**
 * Zustand Global State Store
 * 
 * Central state management for the application
 */

import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import type {
  Product,
  Analysis,
  Supplier,
  Inventory,
  DashboardMetrics,
  AgentStatus,
  UserPreferences,
  InventoryAlert,
} from '../types';

// ============ Store Interfaces ============

interface ProductState {
  products: Product[];
  selectedProduct: Product | null;
  loading: boolean;
  error: string | null;
  setProducts: (products: Product[]) => void;
  addProduct: (product: Product) => void;
  updateProduct: (asin: string, product: Partial<Product>) => void;
  removeProduct: (asin: string) => void;
  selectProduct: (product: Product | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}

interface AnalysisState {
  analyses: Analysis[];
  loading: boolean;
  error: string | null;
  setAnalyses: (analyses: Analysis[]) => void;
  addAnalysis: (analysis: Analysis) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}

interface SupplierState {
  suppliers: Supplier[];
  selectedSupplier: Supplier | null;
  loading: boolean;
  error: string | null;
  setSuppliers: (suppliers: Supplier[]) => void;
  addSupplier: (supplier: Supplier) => void;
  updateSupplier: (id: string, supplier: Partial<Supplier>) => void;
  selectSupplier: (supplier: Supplier | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}

interface InventoryState {
  inventory: Inventory[];
  alerts: InventoryAlert[];
  loading: boolean;
  error: string | null;
  setInventory: (inventory: Inventory[]) => void;
  updateInventoryItem: (productId: string, item: Partial<Inventory>) => void;
  setAlerts: (alerts: InventoryAlert[]) => void;
  addAlert: (alert: InventoryAlert) => void;
  removeAlert: (id: string) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}

interface DashboardState {
  metrics: DashboardMetrics | null;
  agentStatuses: AgentStatus[];
  loading: boolean;
  error: string | null;
  setMetrics: (metrics: DashboardMetrics) => void;
  setAgentStatuses: (statuses: AgentStatus[]) => void;
  updateAgentStatus: (name: string, status: Partial<AgentStatus>) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}

interface UIState {
  theme: 'light' | 'dark' | 'system';
  sidebarOpen: boolean;
  notifications: Notification[];
  setTheme: (theme: 'light' | 'dark' | 'system') => void;
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  addNotification: (notification: Omit<Notification, 'id'>) => void;
  removeNotification: (id: string) => void;
}

interface Notification {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message: string;
  timestamp: string;
}

interface UserState {
  preferences: UserPreferences;
  updatePreferences: (preferences: Partial<UserPreferences>) => void;
}

// ============ Store Implementations ============

/**
 * Product Store
 */
export const useProductStore = create<ProductState>()(
  devtools(
    (set) => ({
      products: [],
      selectedProduct: null,
      loading: false,
      error: null,
      setProducts: (products) => set({ products }),
      addProduct: (product) =>
        set((state) => ({ products: [...state.products, product] })),
      updateProduct: (asin, updates) =>
        set((state) => ({
          products: state.products.map((p) =>
            p.asin === asin ? { ...p, ...updates } : p
          ),
        })),
      removeProduct: (asin) =>
        set((state) => ({
          products: state.products.filter((p) => p.asin !== asin),
        })),
      selectProduct: (product) => set({ selectedProduct: product }),
      setLoading: (loading) => set({ loading }),
      setError: (error) => set({ error }),
    }),
    { name: 'ProductStore' }
  )
);

/**
 * Analysis Store
 */
export const useAnalysisStore = create<AnalysisState>()(
  devtools(
    (set) => ({
      analyses: [],
      loading: false,
      error: null,
      setAnalyses: (analyses) => set({ analyses }),
      addAnalysis: (analysis) =>
        set((state) => ({ analyses: [...state.analyses, analysis] })),
      setLoading: (loading) => set({ loading }),
      setError: (error) => set({ error }),
    }),
    { name: 'AnalysisStore' }
  )
);

/**
 * Supplier Store
 */
export const useSupplierStore = create<SupplierState>()(
  devtools(
    (set) => ({
      suppliers: [],
      selectedSupplier: null,
      loading: false,
      error: null,
      setSuppliers: (suppliers) => set({ suppliers }),
      addSupplier: (supplier) =>
        set((state) => ({ suppliers: [...state.suppliers, supplier] })),
      updateSupplier: (id, updates) =>
        set((state) => ({
          suppliers: state.suppliers.map((s) =>
            s.id === id ? { ...s, ...updates } : s
          ),
        })),
      selectSupplier: (supplier) => set({ selectedSupplier: supplier }),
      setLoading: (loading) => set({ loading }),
      setError: (error) => set({ error }),
    }),
    { name: 'SupplierStore' }
  )
);

/**
 * Inventory Store
 */
export const useInventoryStore = create<InventoryState>()(
  devtools(
    (set) => ({
      inventory: [],
      alerts: [],
      loading: false,
      error: null,
      setInventory: (inventory) => set({ inventory }),
      updateInventoryItem: (productId, updates) =>
        set((state) => ({
          inventory: state.inventory.map((item) =>
            item.productId === productId ? { ...item, ...updates } : item
          ),
        })),
      setAlerts: (alerts) => set({ alerts }),
      addAlert: (alert) =>
        set((state) => ({ alerts: [...state.alerts, alert] })),
      removeAlert: (id) =>
        set((state) => ({
          alerts: state.alerts.filter((a) => a.id !== id),
        })),
      setLoading: (loading) => set({ loading }),
      setError: (error) => set({ error }),
    }),
    { name: 'InventoryStore' }
  )
);

/**
 * Dashboard Store
 */
export const useDashboardStore = create<DashboardState>()(
  devtools(
    (set) => ({
      metrics: null,
      agentStatuses: [],
      loading: false,
      error: null,
      setMetrics: (metrics) => set({ metrics }),
      setAgentStatuses: (agentStatuses) => set({ agentStatuses }),
      updateAgentStatus: (name, updates) =>
        set((state) => ({
          agentStatuses: state.agentStatuses.map((agent) =>
            agent.name === name ? { ...agent, ...updates } : agent
          ),
        })),
      setLoading: (loading) => set({ loading }),
      setError: (error) => set({ error }),
    }),
    { name: 'DashboardStore' }
  )
);

/**
 * UI Store
 * Persisted to localStorage for theme and layout preferences
 */
export const useUIStore = create<UIState>()(
  persist(
    devtools(
      (set) => ({
        theme: 'system',
        sidebarOpen: true,
        notifications: [],
        setTheme: (theme) => {
          set({ theme });
          // Apply theme to document
          const root = window.document.documentElement;
          root.classList.remove('light', 'dark');

          if (theme === 'system') {
            const systemTheme = window.matchMedia('(prefers-color-scheme: dark)')
              .matches
              ? 'dark'
              : 'light';
            root.classList.add(systemTheme);
          } else {
            root.classList.add(theme);
          }
        },
        toggleSidebar: () =>
          set((state) => ({ sidebarOpen: !state.sidebarOpen })),
        setSidebarOpen: (open) => set({ sidebarOpen: open }),
        addNotification: (notification) =>
          set((state) => ({
            notifications: [
              ...state.notifications,
              {
                ...notification,
                id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
                timestamp: new Date().toISOString(),
              },
            ],
          })),
        removeNotification: (id) =>
          set((state) => ({
            notifications: state.notifications.filter((n) => n.id !== id),
          })),
      }),
      { name: 'UIStore' }
    ),
    {
      name: 'fba-ui-storage',
      partialize: (state) => ({
        theme: state.theme,
        sidebarOpen: state.sidebarOpen,
      }),
    }
  )
);

/**
 * User Store
 * Persisted to localStorage for user preferences
 */
export const useUserStore = create<UserState>()(
  persist(
    devtools(
      (set) => ({
        preferences: {
          theme: 'system',
          defaultCurrency: 'USD',
          notifications: {
            email: true,
            push: true,
            inventoryAlerts: true,
            supplierUpdates: true,
          },
          dashboard: {
            defaultView: 'overview',
            refreshInterval: 30000, // 30 seconds
          },
        },
        updatePreferences: (updates) =>
          set((state) => ({
            preferences: { ...state.preferences, ...updates },
          })),
      }),
      { name: 'UserStore' }
    ),
    {
      name: 'fba-user-storage',
    }
  )
);

