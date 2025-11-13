# Amazon FBA AI Agent - Frontend

Modern React dashboard for Amazon FBA product analysis and management.

## 🚀 Tech Stack

- **React 18** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool
- **Tailwind CSS** - Styling
- **Zustand** - State management
- **React Query** - Data fetching
- **Recharts** - Charts and visualizations
- **Axios** - HTTP client
- **Lucide React** - Icons
- **WebSocket** - Real-time updates

## 📦 Features

### Core Features
- ✅ **Dashboard** - Real-time metrics and agent status
- ✅ **Product Discovery** - Find profitable products with filters
- ✅ **Market Analysis** - Trends, competition, and seasonality
- ✅ **Supplier Management** - Track and communicate with suppliers
- ✅ **Inventory** - Monitor stock levels and alerts
- ✅ **Dark Mode** - Light/Dark theme support
- ✅ **Real-time Updates** - WebSocket integration
- ✅ **Responsive Design** - Mobile-friendly interface

### Technical Features
- Type-safe TypeScript throughout
- Global state management with Zustand
- Persistent state (theme, preferences)
- Real-time data synchronization
- Clean and modular architecture
- Reusable UI components
- Error handling and loading states

## 🛠️ Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the frontend directory:

```env
# API Configuration
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws

# Environment
VITE_ENV=development
```

### Available Scripts

- `npm run dev` - Start development server (port 5173)
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint

## 📁 Project Structure

```
frontend/
├── src/
│   ├── api/              # API clients
│   │   ├── client.ts     # REST API client
│   │   └── websocket.ts  # WebSocket client
│   ├── components/       # React components
│   │   ├── Dashboard/    # Dashboard components
│   │   ├── layout/       # Layout components
│   │   └── ui/           # Reusable UI components
│   ├── pages/            # Page components
│   │   ├── DashboardPage.tsx
│   │   ├── ProductDiscoveryPage.tsx
│   │   ├── MarketAnalysisPage.tsx
│   │   ├── SuppliersPage.tsx
│   │   └── InventoryPage.tsx
│   ├── state/            # State management
│   │   └── store.ts      # Zustand stores
│   ├── types/            # TypeScript types
│   │   └── index.ts      # Type definitions
│   ├── lib/              # Utilities
│   │   └── utils.ts      # Helper functions
│   ├── App.tsx           # Main app component
│   ├── main.tsx          # Entry point
│   └── index.css         # Global styles
├── public/               # Static assets
├── package.json
├── tsconfig.json         # TypeScript config
├── tailwind.config.js    # Tailwind config
├── vite.config.ts        # Vite config
└── README.md
```

## 🎨 Styling

The project uses Tailwind CSS with a custom design system:

- **Colors**: Primary, Secondary, Destructive, Muted, Accent
- **Components**: Shadcn/ui inspired component library
- **Theme**: Light/Dark mode support
- **Responsive**: Mobile-first design

## 🔌 API Integration

### REST API

All API calls are handled through `src/api/client.ts`:

```typescript
import { apiClient } from './api/client';

// Get products
const products = await apiClient.getProducts();

// Discover products
const result = await apiClient.discoverProducts(5000);
```

### WebSocket

Real-time updates are handled through `src/api/websocket.ts`:

```typescript
import { wsClient } from './api/websocket';

// Subscribe to events
wsClient.on('product_discovered', (event) => {
  console.log('New product:', event.data.product);
});
```

## 🗂️ State Management

The app uses Zustand for state management with multiple stores:

- `useProductStore` - Products data
- `useAnalysisStore` - Analysis data
- `useSupplierStore` - Suppliers data
- `useInventoryStore` - Inventory data
- `useDashboardStore` - Dashboard metrics
- `useUIStore` - UI state (theme, sidebar, notifications)
- `useUserStore` - User preferences

## 🎯 Key Components

### MetricCard
Displays a single metric with icon and trend indicator.

### AgentStatusCard
Shows the status of backend agents.

### Card
Reusable card component for content containers.

### Button
Styled button with multiple variants and sizes.

### Badge
Small label component for status indicators.

## 🚀 Development

### Adding a New Page

1. Create page component in `src/pages/`
2. Import and add route in `App.tsx`
3. Add navigation link in `Sidebar.tsx`

### Adding a New Component

1. Create component in `src/components/`
2. Export from component file
3. Import where needed

### Adding New API Endpoint

1. Add method to `src/api/client.ts`
2. Add types to `src/types/index.ts`
3. Use in components with React Query or state

## 📊 Charts

Charts are built with Recharts:

- Line Charts - Trends over time
- Bar Charts - Category comparisons
- Pie Charts - Distribution
- Area Charts - Seasonal patterns

## 🔐 Authentication

Authentication is handled via JWT tokens stored in localStorage. The API client automatically includes the token in requests.

## 🐛 Troubleshooting

### WebSocket Connection Issues

If WebSocket fails to connect:
1. Check that backend is running
2. Verify `VITE_WS_URL` in `.env`
3. Check browser console for errors

### API Errors

If API calls fail:
1. Verify backend is running on correct port
2. Check `VITE_API_BASE_URL` in `.env`
3. Check network tab in browser DevTools

### Build Issues

If build fails:
1. Clear node_modules: `rm -rf node_modules`
2. Reinstall: `npm install`
3. Clear Vite cache: `npm run dev -- --force`

## 📝 License

Part of the Amazon FBA AI Agent project.

## 🤝 Contributing

1. Create a feature branch
2. Make your changes
3. Test thoroughly
4. Submit a pull request

## 📧 Support

For issues or questions, please open an issue in the repository.
