/**
 * Product Discovery Page
 * 
 * Search and discover products with filters
 */

import React, { useState, useEffect } from 'react';
import { Search, RefreshCw, Download, ChevronDown, ChevronUp, Info, TrendingUp, Star, DollarSign } from 'lucide-react';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Tooltip } from '../components/ui/Tooltip';
import { DevelopmentDisclaimer } from '../components/ui/DevelopmentDisclaimer';
import { useProductStore } from '../state/store';
import { apiClient } from '../api/client';
import { formatCurrency, exportToCSV } from '../lib/utils';
import type { ProductFilters } from '../types';

export const ProductDiscoveryPage: React.FC = () => {
  const { products, setProducts, setLoading, loading } = useProductStore();
  const [filters, setFilters] = useState<ProductFilters>({});
  const [budget, setBudget] = useState<number>(5000);
  const [showHowItWorks, setShowHowItWorks] = useState(false);

  // Fetch products on mount
  useEffect(() => {
    fetchProducts();
  }, [filters]);

  const fetchProducts = async () => {
    setLoading(true);
    try {
      const response = await apiClient.getProducts(1, 20, filters);
      setProducts(response.products || []);
    } catch (error) {
      console.error('Failed to fetch products:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDiscover = async () => {
    setLoading(true);
    try {
      const response = await apiClient.discoverProducts(budget);
      console.log('Discovery started with task_id:', response.data);
      
      // After discovery completes (it's async), refresh the products list
      // Wait a bit for the async process to complete
      setTimeout(async () => {
        await fetchProducts();
      }, 15000); // Wait 15 seconds for discovery to complete
    } catch (error) {
      console.error('Failed to discover products:', error);
      setLoading(false);
    }
  };

  const handleExport = () => {
    exportToCSV(products, 'fba-products');
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Product Discovery</h1>
          <p className="text-muted-foreground">
            Find and analyze profitable products
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={fetchProducts}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Refresh
          </Button>
          <Button variant="outline" onClick={handleExport}>
            <Download className="mr-2 h-4 w-4" />
            Export
          </Button>
        </div>
      </div>

      {/* Discovery Controls */}
      <Card>
        <div className="space-y-4">
          <div className="flex gap-4">
            <div className="flex-1">
              <label className="mb-2 flex items-center gap-2 text-sm font-medium">
                Budget (USD)
                <Tooltip content="Your total investment budget. This helps prioritize products that fit your financial capacity and optimize inventory planning." />
              </label>
              <input
                type="number"
                value={budget}
                onChange={(e) => setBudget(Number(e.target.value))}
                className="w-full rounded-md border bg-background px-3 py-2"
                placeholder="Enter budget"
              />
            </div>
            <div className="flex items-end">
              <Button onClick={handleDiscover} disabled={loading}>
                <Search className="mr-2 h-4 w-4" />
                Discover Products
              </Button>
            </div>
          </div>

          {/* Filters */}
          <div className="grid gap-4 md:grid-cols-4">
            <div>
              <label className="mb-2 flex items-center gap-2 text-sm font-medium">
                Min Price
                <Tooltip content="Minimum product price. Lower prices typically mean better margins and faster turnover." />
              </label>
              <input
                type="number"
                value={filters.minPrice || ''}
                onChange={(e) =>
                  setFilters({ ...filters, minPrice: Number(e.target.value) })
                }
                className="w-full rounded-md border bg-background px-3 py-2"
                placeholder="$0"
              />
            </div>
            <div>
              <label className="mb-2 flex items-center gap-2 text-sm font-medium">
                Max Price
                <Tooltip content="Maximum product price. Products under $50 receive higher ranking scores for better ROI potential." />
              </label>
              <input
                type="number"
                value={filters.maxPrice || ''}
                onChange={(e) =>
                  setFilters({ ...filters, maxPrice: Number(e.target.value) })
                }
                className="w-full rounded-md border bg-background px-3 py-2"
                placeholder="$1000"
              />
            </div>
            <div>
              <label className="mb-2 flex items-center gap-2 text-sm font-medium">
                Min Rating
                <Tooltip content="Minimum customer rating (1-5 stars). Higher ratings indicate better product quality and customer satisfaction." />
              </label>
              <input
                type="number"
                step="0.1"
                max="5"
                value={filters.minRating || ''}
                onChange={(e) =>
                  setFilters({ ...filters, minRating: Number(e.target.value) })
                }
                className="w-full rounded-md border bg-background px-3 py-2"
                placeholder="4.0"
              />
            </div>
            <div>
              <label className="mb-2 flex items-center gap-2 text-sm font-medium">
                Category
                <Tooltip content="Target product category. Focuses the search on specific Amazon marketplace segments for better targeting." />
              </label>
              <select
                value={filters.category || ''}
                onChange={(e) =>
                  setFilters({ ...filters, category: e.target.value })
                }
                className="w-full rounded-md border bg-background px-3 py-2"
              >
                <option value="">All Categories</option>
                <option value="Electronics">Electronics</option>
                <option value="Home">Home & Kitchen</option>
                <option value="Toys">Toys & Games</option>
                <option value="Sports">Sports & Outdoors</option>
              </select>
            </div>
          </div>
        </div>
      </Card>

      {/* How It Works Section */}
      <Card>
        <button
          onClick={() => setShowHowItWorks(!showHowItWorks)}
          className="flex w-full items-center justify-between text-left"
        >
          <div className="flex items-center gap-2">
            <Info className="h-5 w-5 text-primary" />
            <h3 className="font-semibold">How Product Discovery Works</h3>
          </div>
          {showHowItWorks ? (
            <ChevronUp className="h-5 w-5" />
          ) : (
            <ChevronDown className="h-5 w-5" />
          )}
        </button>

        {showHowItWorks && (
          <div className="mt-4 space-y-4 border-t pt-4">
            {/* Process Overview */}
            <div className="rounded-lg bg-muted/50 p-4">
              <h4 className="mb-3 flex items-center gap-2 font-semibold">
                <Search className="h-4 w-4" />
                Discovery Process
              </h4>
              <ol className="space-y-2 text-sm text-muted-foreground">
                <li className="flex gap-2">
                  <span className="font-semibold text-primary">1.</span>
                  <span>
                    <strong>Search Amazon:</strong> Uses SerpAPI to find trending products based on your criteria
                  </span>
                </li>
                <li className="flex gap-2">
                  <span className="font-semibold text-primary">2.</span>
                  <span>
                    <strong>Quality Filter:</strong> Removes low-rated products (minimum 4.0★ rating required)
                  </span>
                </li>
                <li className="flex gap-2">
                  <span className="font-semibold text-primary">3.</span>
                  <span>
                    <strong>Demand Validation:</strong> Ensures products have proven demand (reviews ≥ 10 - validates sustained interest, not just initial sales)
                  </span>
                </li>
                <li className="flex gap-2">
                  <span className="font-semibold text-primary">4.</span>
                  <span>
                    <strong>Smart Ranking:</strong> Scores products by: Rating × log₁₀(Reviews) × Price Factor
                  </span>
                </li>
              </ol>
            </div>

            {/* Selection Criteria */}
            <div className="grid gap-4 md:grid-cols-3">
              <div className="rounded-lg border p-3">
                <div className="mb-2 flex items-center gap-2 text-sm font-semibold">
                  <Star className="h-4 w-4 text-yellow-500" />
                  Quality & Demand
                </div>
                <ul className="space-y-1 text-xs text-muted-foreground">
                  <li>• Rating: ≥ 4.0 stars</li>
                  <li>• Reviews: ≥ 10 (sustained demand)</li>
                  <li>• Valid ASIN required</li>
                </ul>
              </div>

              <div className="rounded-lg border p-3">
                <div className="mb-2 flex items-center gap-2 text-sm font-semibold">
                  <DollarSign className="h-4 w-4 text-green-500" />
                  Profit Potential
                </div>
                <ul className="space-y-1 text-xs text-muted-foreground">
                  <li>• Price Range: $0-$1000</li>
                  <li>• Prefers mid-range (&lt;$50)</li>
                  <li>• Better margins & turnover</li>
                </ul>
              </div>

              <div className="rounded-lg border p-3">
                <div className="mb-2 flex items-center gap-2 text-sm font-semibold">
                  <TrendingUp className="h-4 w-4 text-blue-500" />
                  Ranking Score
                </div>
                <ul className="space-y-1 text-xs text-muted-foreground">
                  <li>• High rating = Quality</li>
                  <li>• Many reviews = Demand</li>
                  <li>• Lower price = Higher margin</li>
                </ul>
              </div>
            </div>

            {/* Business Logic */}
            <div className="rounded-lg bg-blue-50 p-4 dark:bg-blue-950/20">
              <h4 className="mb-2 font-semibold text-blue-900 dark:text-blue-100">
                Business Logic
              </h4>
              <p className="text-sm text-blue-800 dark:text-blue-200">
                The algorithm prioritizes <strong>high-quality products</strong> (4+ stars) with{' '}
                <strong>sustained demand</strong> (10+ reviews - validates ongoing interest, not just initial purchases).
                Products under $50 receive higher scores due to better profit margins and faster inventory
                turnover. The 10-review threshold filters out products with potentially declining demand or recent launches
                without proven market traction.
              </p>
            </div>
          </div>
        )}
      </Card>

      {/* Products Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {loading ? (
          <div className="col-span-full text-center text-muted-foreground">
            Loading products...
          </div>
        ) : products.length === 0 ? (
          <>
            <div className="col-span-full">
              <DevelopmentDisclaimer 
                type="development"
                message="No hay productos descubiertos aún. Haz clic en 'Discover Products' para buscar productos reales en Amazon usando SerpAPI. Los productos mostrados son datos reales obtenidos de Amazon."
                details="El sistema busca productos reales basándose en tus criterios de búsqueda (presupuesto, precio, rating, categoría). Los productos se obtienen directamente de Amazon a través de SerpAPI."
              />
            </div>
            <div className="col-span-full text-center text-muted-foreground">
              No products found. Try discovering products with different criteria.
            </div>
          </>
        ) : (
          products.map((product) => (
            <Card key={product.asin} className="hover:shadow-lg transition-shadow">
              {product.imageUrl && (
                <img
                  src={product.imageUrl}
                  alt={product.title}
                  className="mb-4 h-48 w-full rounded-lg object-cover"
                />
              )}
              <div className="space-y-2">
                <h3 className="line-clamp-2 font-semibold">{product.title}</h3>
                <div className="flex items-center justify-between">
                  <span className="text-2xl font-bold">
                    {formatCurrency(product.price)}
                  </span>
                  <Badge variant="default">BSR: {product.bsr}</Badge>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">
                    ⭐ {product.rating} ({product.reviews} reviews)
                  </span>
                </div>
                <a href={`/analysis?asin=${product.asin}`} className="block w-full">
                  <Button 
                    className="w-full" 
                    variant="outline"
                  >
                    View Analysis
                  </Button>
                </a>
              </div>
            </Card>
          ))
        )}
      </div>
    </div>
  );
};

export default ProductDiscoveryPage;

