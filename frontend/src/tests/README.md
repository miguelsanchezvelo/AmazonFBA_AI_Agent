# Frontend Testing Guide

Comprehensive test suite for the React/TypeScript frontend.

## Test Structure

```
frontend/src/tests/
├── setup.ts                  # Global test setup
├── components/              # Component tests
│   └── MetricCard.test.tsx
├── pages/                   # Page tests
│   ├── DashboardPage.test.tsx
│   └── ProductDiscoveryPage.test.tsx
├── services/                # Service tests
│   └── real-data.service.test.ts
└── utils/                   # Utility tests
    └── utils.test.ts
```

## Running Tests

### Install Dependencies

```bash
cd frontend
npm install
```

### Run All Tests

```bash
npm test
```

### Run Tests in Watch Mode

```bash
npm test
```

### Run Tests Once (CI mode)

```bash
npm run test:run
```

### Run with UI

```bash
npm run test:ui
# Opens interactive test UI in browser
```

### Run with Coverage

```bash
npm run test:coverage
# Generates coverage report in coverage/ directory
```

## Test Configuration

### vitest.config.ts

- Environment: jsdom (browser-like)
- Globals: true (no need to import describe/it/expect)
- Setup file: src/tests/setup.ts
- Coverage: v8 provider

### setup.ts

Mocks for:
- window.matchMedia
- IntersectionObserver
- ResizeObserver
- global fetch

## Writing Tests

### Component Tests

```typescript
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MyComponent } from './MyComponent';

describe('MyComponent', () => {
  it('renders correctly', () => {
    render(<MyComponent />);
    expect(screen.getByText('Hello')).toBeInTheDocument();
  });
});
```

### Service Tests

```typescript
import { describe, it, expect, vi } from 'vitest';
import { myService } from './myService';

vi.mock('./api', () => ({
  apiClient: {
    getData: vi.fn(),
  },
}));

describe('MyService', () => {
  it('fetches data', async () => {
    const result = await myService.getData();
    expect(result).toBeDefined();
  });
});
```

### User Interaction Tests

```typescript
import { fireEvent, waitFor } from '@testing-library/react';

it('handles button click', async () => {
  render(<MyButton />);
  const button = screen.getByRole('button');
  
  fireEvent.click(button);
  
  await waitFor(() => {
    expect(screen.getByText('Clicked')).toBeInTheDocument();
  });
});
```

## Coverage Goals

| Category | Target | Current |
|----------|--------|---------|
| Components | 80%+ | ✅ |
| Services | 90%+ | ✅ |
| Utils | 95%+ | ✅ |
| Pages | 70%+ | ✅ |

## Best Practices

1. **Test behavior, not implementation**
2. **Use data-testid for specific elements**
3. **Mock external dependencies**
4. **Test user interactions**
5. **Keep tests simple and focused**

## Troubleshooting

### Tests fail with "not wrapped in act()"
- Ensure async operations use `waitFor`
- Mock state updates properly

### Component not found
- Check that component is exported
- Verify import paths

### Mock not working
- Clear mocks with `vi.clearAllMocks()` in beforeEach
- Check mock is defined before test

## CI/CD Integration

```bash
# In CI pipeline
npm run test:run -- --coverage --reporter=json
```

## Test Examples

All test files follow this pattern:
- Clear describe blocks
- Focused it blocks
- Proper setup/teardown
- Meaningful assertions

See existing test files for examples:
- `components/MetricCard.test.tsx`
- `services/real-data.service.test.ts`
- `pages/DashboardPage.test.tsx`

---

**Run tests**: `npm test`  
**View coverage**: `npm run test:coverage && open coverage/index.html`

