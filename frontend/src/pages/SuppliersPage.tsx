/**
 * Suppliers Page
 * 
 * Manage supplier relationships and communications
 */

import React, { useEffect, useState } from 'react';
import { Mail, MapPin, Star, MessageSquare, AlertCircle } from 'lucide-react';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { DevelopmentDisclaimer } from '../components/ui/DevelopmentDisclaimer';
import { useSupplierStore } from '../state/store';
import { apiClient } from '../api/client';
import { formatRelativeTime } from '../lib/utils';
import type { Supplier } from '../types';

export const SuppliersPage: React.FC = () => {
  const {
    suppliers,
    setSuppliers,
    selectSupplier,
    selectedSupplier,
    setLoading,
    loading,
    error,
    setError,
  } = useSupplierStore();
  const [showContactModal, setShowContactModal] = useState(false);
  const [message, setMessage] = useState('');

  // Fetch suppliers on mount
  useEffect(() => {
    fetchSuppliers();
  }, []);

  const fetchSuppliers = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.getSuppliers();
      setSuppliers(response.items);
    } catch (error) {
      console.error('Failed to fetch suppliers:', error);
      setError('Unable to load supplier data. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleContact = async (supplier: Supplier) => {
    selectSupplier(supplier);
    setShowContactModal(true);
  };

  const handleSendMessage = async () => {
    if (!selectedSupplier || !message) return;

    try {
      await apiClient.contactSupplier(selectedSupplier.id, message);
      setMessage('');
      setShowContactModal(false);
      // Refresh supplier data
      fetchSuppliers();
    } catch (error) {
      console.error('Failed to send message:', error);
    }
  };

  const getStatusBadge = (status: Supplier['status']) => {
    const variants = {
      active: 'success' as const,
      pending: 'warning' as const,
      inactive: 'info' as const,
    };
    return <Badge variant={variants[status]}>{status}</Badge>;
  };

  return (
    <div className="space-y-6">
      {/* Error banner */}
      {error && (
        <Card className="border-red-200 bg-red-50 p-4 text-red-700">
          <div className="flex items-start gap-3">
            <AlertCircle className="mt-0.5 h-5 w-5" />
            <div>
              <p className="text-sm font-semibold">Supplier data unavailable</p>
              <p className="text-sm">{error}</p>
            </div>
          </div>
        </Card>
      )}

      {/* Development Disclaimer */}
      {suppliers.length === 0 && !loading && (
        <DevelopmentDisclaimer 
          type="mock-data"
          message="El sistema de proveedores busca proveedores reales usando SerpAPI. Si no hay proveedores disponibles, se mostrarán datos de ejemplo para demostración. Los proveedores reales se obtienen automáticamente cuando descubres productos."
          details="Los proveedores se buscan en sitios como Alibaba, Made-in-China y Global Sources. Si no hay productos descubiertos, no habrá proveedores disponibles."
        />
      )}

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Suppliers</h1>
          <p className="text-muted-foreground">
            Manage your supplier relationships
          </p>
        </div>
        <Button>
          <Mail className="mr-2 h-4 w-4" />
          Contact All
        </Button>
      </div>

      {/* Suppliers Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {loading ? (
          <div className="col-span-full text-center text-muted-foreground">
            Loading suppliers...
          </div>
        ) : suppliers.length === 0 ? (
          <div className="col-span-full text-center text-muted-foreground">
            No suppliers found. Start by discovering products.
          </div>
        ) : (
          suppliers.map((supplier) => (
            <Card
              key={supplier.id}
              className="hover:shadow-lg transition-shadow"
            >
              <div className="space-y-4">
                {/* Header */}
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-semibold">{supplier.name}</h3>
                    <div className="mt-1 flex items-center gap-1 text-sm text-muted-foreground">
                      <MapPin className="h-3 w-3" />
                      {supplier.country}
                    </div>
                  </div>
                  {getStatusBadge(supplier.status)}
                </div>

                {/* Rating */}
                <div className="flex items-center gap-2">
                  <div className="flex items-center">
                    {[...Array(5)].map((_, i) => (
                      <Star
                        key={i}
                        className={`h-4 w-4 ${
                          i < supplier.rating
                            ? 'fill-yellow-400 text-yellow-400'
                            : 'text-gray-300'
                        }`}
                      />
                    ))}
                  </div>
                  <span className="text-sm font-medium">{supplier.rating}/5</span>
                </div>

                {/* Contact Info */}
                <div className="space-y-2 text-sm">
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <Mail className="h-4 w-4" />
                    {supplier.email}
                  </div>
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <MessageSquare className="h-4 w-4" />
                    {supplier.communicationHistory.length} communications
                  </div>
                </div>

                {/* Products */}
                <div>
                  <div className="text-sm font-medium">Products</div>
                  <div className="mt-1 text-sm text-muted-foreground">
                    {supplier.products.length} active products
                  </div>
                </div>

                {/* Last Contact */}
                <div className="text-xs text-muted-foreground">
                  Last contact: {formatRelativeTime(supplier.lastContact)}
                </div>

                {/* Actions */}
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    className="flex-1"
                    onClick={() => handleContact(supplier)}
                  >
                    <Mail className="mr-2 h-4 w-4" />
                    Contact
                  </Button>
                  <Button variant="ghost" className="flex-1">
                    View Details
                  </Button>
                </div>
              </div>
            </Card>
          ))
        )}
      </div>

      {/* Contact Modal (simplified) */}
      {showContactModal && selectedSupplier && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <Card className="w-full max-w-md">
            <h2 className="mb-4 text-xl font-bold">
              Contact {selectedSupplier.name}
            </h2>
            <div className="space-y-4">
              <div>
                <label className="mb-2 block text-sm font-medium">Message</label>
                <textarea
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  className="w-full rounded-md border bg-background px-3 py-2"
                  rows={6}
                  placeholder="Enter your message..."
                />
              </div>
              <div className="flex gap-2">
                <Button onClick={handleSendMessage} className="flex-1">
                  Send Message
                </Button>
                <Button
                  variant="outline"
                  onClick={() => setShowContactModal(false)}
                  className="flex-1"
                >
                  Cancel
                </Button>
              </div>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
};

export default SuppliersPage;

