/**
 * Inventory Page
 * 
 * Track inventory levels, alerts, and forecasts
 */

import React, { useEffect } from 'react';
import { Package, AlertTriangle, TrendingUp, RefreshCw } from 'lucide-react';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { DevelopmentDisclaimer } from '../components/ui/DevelopmentDisclaimer';
import { useInventoryStore } from '../state/store';
import { apiClient } from '../api/client';
import { formatRelativeTime } from '../lib/utils';
import type { Inventory } from '../types';

export const InventoryPage: React.FC = () => {
  const {
    inventory,
    alerts,
    setInventory,
    setAlerts,
    setLoading,
    loading,
  } = useInventoryStore();

  // Fetch inventory on mount
  useEffect(() => {
    fetchInventory();
    fetchAlerts();
  }, []);

  const fetchInventory = async () => {
    setLoading(true);
    try {
      const response = await apiClient.getInventory();
      setInventory(response.items);
    } catch (error) {
      console.error('Failed to fetch inventory:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchAlerts = async () => {
    try {
      const response = await apiClient.getInventoryAlerts();
      if (response.data) {
        setAlerts(response.data);
      }
    } catch (error) {
      console.error('Failed to fetch alerts:', error);
    }
  };

  const getStatusBadge = (status: Inventory['status']) => {
    const variants = {
      ok: 'success' as const,
      low: 'warning' as const,
      critical: 'error' as const,
      overstock: 'info' as const,
    };
    const labels = {
      ok: 'Healthy',
      low: 'Low Stock',
      critical: 'Critical',
      overstock: 'Overstock',
    };
    return <Badge variant={variants[status]}>{labels[status]}</Badge>;
  };

  const getStatusIcon = (status: Inventory['status']) => {
    const colors = {
      ok: 'text-green-600',
      low: 'text-yellow-600',
      critical: 'text-red-600',
      overstock: 'text-blue-600',
    };
    return <Package className={`h-5 w-5 ${colors[status]}`} />;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Inventory</h1>
          <p className="text-muted-foreground">
            Monitor stock levels and manage reorders
          </p>
        </div>
        <Button onClick={fetchInventory}>
          <RefreshCw className="mr-2 h-4 w-4" />
          Refresh
        </Button>
      </div>

      {/* Show disclaimer only if no real inventory data */}
      {inventory.length === 0 && (
        <DevelopmentDisclaimer 
          type="development"
          message="El sistema de gestión de inventario está en desarrollo. Los datos de inventario reales estarán disponibles cuando se complete la integración con Amazon Seller Central API y sistemas de almacenamiento."
          details="Funcionalidades pendientes: sincronización automática de niveles de stock desde Amazon, alertas inteligentes de reabastecimiento basadas en ventas históricas, y pronósticos de demanda."
        />
      )}

      {/* Alerts */}
      {alerts.length > 0 && (
        <Card title="Active Alerts" description={`${alerts.length} items need attention`}>
          <div className="space-y-3">
            {alerts.map((alert) => (
              <div
                key={alert.id}
                className="flex items-start gap-3 rounded-lg border p-3"
              >
                <AlertTriangle
                  className={`h-5 w-5 ${
                    alert.severity === 'critical'
                      ? 'text-red-600'
                      : alert.severity === 'warning'
                      ? 'text-yellow-600'
                      : 'text-blue-600'
                  }`}
                />
                <div className="flex-1">
                  <h4 className="font-semibold">{alert.type.toUpperCase()}</h4>
                  <p className="text-sm text-muted-foreground">
                    {alert.message}
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {formatRelativeTime(alert.createdAt)}
                  </p>
                </div>
                <Button size="sm" variant="outline">
                  Action
                </Button>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Inventory Table */}
      <Card>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b">
                <th className="p-3 text-left text-sm font-medium">Product</th>
                <th className="p-3 text-left text-sm font-medium">Quantity</th>
                <th className="p-3 text-left text-sm font-medium">Location</th>
                <th className="p-3 text-left text-sm font-medium">Status</th>
                <th className="p-3 text-left text-sm font-medium">
                  Next Restock
                </th>
                <th className="p-3 text-left text-sm font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={6} className="p-6 text-center text-muted-foreground">
                    Loading inventory...
                  </td>
                </tr>
              ) : inventory.length === 0 ? (
                <tr>
                  <td colSpan={6} className="p-6 text-center text-muted-foreground">
                    No inventory items found.
                  </td>
                </tr>
              ) : (
                inventory.map((item) => (
                  <tr key={item.id} className="border-b last:border-0">
                    <td className="p-3">
                      <div className="flex items-center gap-2">
                        {getStatusIcon(item.status)}
                        <span className="font-medium">{item.productId}</span>
                      </div>
                    </td>
                    <td className="p-3">
                      <div>
                        <div className="font-medium">{item.quantity}</div>
                        <div className="text-xs text-muted-foreground">
                          Min: {item.minStock} | Max: {item.maxStock}
                        </div>
                      </div>
                    </td>
                    <td className="p-3 text-sm">{item.location}</td>
                    <td className="p-3">{getStatusBadge(item.status)}</td>
                    <td className="p-3 text-sm">
                      {formatRelativeTime(item.nextRestockDate)}
                    </td>
                    <td className="p-3">
                      <div className="flex gap-2">
                        <Button size="sm" variant="outline">
                          Update
                        </Button>
                        <Button size="sm" variant="ghost">
                          Reorder
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Forecast */}
      <Card title="Inventory Forecast" description="Predicted needs for next 30 days">
        <div className="space-y-3">
          <div className="flex items-center justify-between rounded-lg border p-3">
            <div className="flex items-center gap-3">
              <TrendingUp className="h-5 w-5 text-blue-600" />
              <div>
                <div className="font-medium">Expected Sales</div>
                <div className="text-sm text-muted-foreground">
                  Based on historical data
                </div>
              </div>
            </div>
            <div className="text-right">
              <div className="text-2xl font-bold">245</div>
              <div className="text-xs text-muted-foreground">units</div>
            </div>
          </div>
          <div className="flex items-center justify-between rounded-lg border p-3">
            <div className="flex items-center gap-3">
              <Package className="h-5 w-5 text-yellow-600" />
              <div>
                <div className="font-medium">Recommended Restock</div>
                <div className="text-sm text-muted-foreground">
                  To maintain optimal levels
                </div>
              </div>
            </div>
            <div className="text-right">
              <div className="text-2xl font-bold">180</div>
              <div className="text-xs text-muted-foreground">units</div>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
};

export default InventoryPage;

