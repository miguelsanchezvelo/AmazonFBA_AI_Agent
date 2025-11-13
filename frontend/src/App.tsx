/**
 * Main App Component
 * 
 * Root component with routing and layout
 */

import React, { Suspense, useEffect } from 'react';
import { Layout } from './components/layout/Layout';
import { wsClient } from './api/websocket';
import { useProductStore, useInventoryStore, useUIStore } from './state/store';
// import type { WebSocketEvent } from './types';

const DashboardPage = React.lazy(() => import('./pages/DashboardPage'));
const ProductDiscoveryPage = React.lazy(() => import('./pages/ProductDiscoveryPage'));
const MarketAnalysisPage = React.lazy(() => import('./pages/MarketAnalysisPage'));
const SuppliersPage = React.lazy(() => import('./pages/SuppliersPage'));
const InventoryPage = React.lazy(() => import('./pages/InventoryPage'));
const BusinessPage = React.lazy(() => import('./pages/BusinessPage'));

function App() {
  const { addProduct } = useProductStore();
  const { addAlert } = useInventoryStore();
  const { addNotification } = useUIStore();

  // Simple client-side routing (for demo purposes)
  // In production, use React Router or similar
  const [currentPage, setCurrentPage] = React.useState('/');

  // Setup WebSocket event handlers
  useEffect(() => {
    // Product discovered event
    const unsubProductDiscovered = wsClient.on('product_discovered', (event) => {
      if ('product' in event.data) {
        const product = event.data.product;
        addProduct(product);
        addNotification({
          type: 'success',
          title: 'Product Discovered',
          message: `New product found: ${product.title}`,
          timestamp: new Date().toISOString(),
        });
      }
    });

    // Analysis complete event
    const unsubAnalysisComplete = wsClient.on('analysis_complete', () => {
      addNotification({
        type: 'info',
        title: 'Analysis Complete',
        message: 'Market analysis has been completed',
        timestamp: new Date().toISOString(),
      });
    });

    // Inventory alert event
    const unsubInventoryAlert = wsClient.on('inventory_alert', (event) => {
      if ('alert' in event.data) {
        const alert = event.data.alert;
        addAlert(alert);
        addNotification({
          type: 'warning',
          title: 'Inventory Alert',
          message: alert.message,
          timestamp: new Date().toISOString(),
        });
      }
    });

    // Connection status
    const unsubConnect = wsClient.onConnect(() => {
      console.log('WebSocket connected');
    });

    const unsubDisconnect = wsClient.onDisconnect(() => {
      console.log('WebSocket disconnected');
    });

    // Cleanup
    return () => {
      unsubProductDiscovered();
      unsubAnalysisComplete();
      unsubInventoryAlert();
      unsubConnect();
      unsubDisconnect();
    };
  }, []);

  // Simple routing logic
  useEffect(() => {
    // Listen to sidebar clicks
    const handleClick = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      const link = target.closest('a[href]');
      if (link) {
        e.preventDefault();
        const href = link.getAttribute('href');
        if (href) {
          // Update URL with query params if present
          const url = new URL(href, window.location.origin);
          window.history.pushState({}, '', url.pathname + url.search);
          setCurrentPage(url.pathname + url.search);
        }
      }
    };

    document.addEventListener('click', handleClick);
    return () => document.removeEventListener('click', handleClick);
  }, []);

  // Render current page
  const renderPage = () => {
    // Extract pathname without query params for routing
    const pathname = currentPage.split('?')[0];
    
    switch (pathname) {
      case '/':
        return <DashboardPage />;
      case '/discovery':
        return <ProductDiscoveryPage />;
      case '/analysis':
        return <MarketAnalysisPage />;
      case '/suppliers':
        return <SuppliersPage />;
      case '/inventory':
        return <InventoryPage />;
      case '/business':
        return <BusinessPage />;
      default:
        return <DashboardPage />;
    }
  };

  return (
    <Layout>
      <Suspense fallback={<div className="p-6 text-sm text-slate-500">Loading module…</div>}>
        {renderPage()}
      </Suspense>
    </Layout>
  );
}

export default App;
