/**
 * MetricCard Component Tests
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MetricCard } from '../../components/Dashboard/MetricCard';
import { Package } from 'lucide-react';

describe('MetricCard Component', () => {
  it('renders with basic props', () => {
    render(
      <MetricCard
        title="Total Products"
        value={100}
        icon={<Package data-testid="package-icon" />}
      />
    );

    expect(screen.getByText('Total Products')).toBeInTheDocument();
    expect(screen.getByText('100')).toBeInTheDocument();
    expect(screen.getByTestId('package-icon')).toBeInTheDocument();
  });

  it('displays positive change correctly', () => {
    render(
      <MetricCard
        title="Revenue"
        value="$1000"
        change={15.5}
        icon={<Package />}
      />
    );

    expect(screen.getByText('Revenue')).toBeInTheDocument();
    expect(screen.getByText('$1000')).toBeInTheDocument();
    // Change indicator should be visible
    const changeText = screen.getByText(/15\.5/);
    expect(changeText).toBeInTheDocument();
  });

  it('displays negative change correctly', () => {
    render(
      <MetricCard
        title="Orders"
        value={50}
        change={-5.2}
        icon={<Package />}
      />
    );

    expect(screen.getByText('Orders')).toBeInTheDocument();
    // Should show negative change
    const changeText = screen.getByText(/-5\.2/);
    expect(changeText).toBeInTheDocument();
  });

  it('renders description when provided', () => {
    render(
      <MetricCard
        title="Active Products"
        value={25}
        description="Currently in inventory"
        icon={<Package />}
      />
    );

    expect(screen.getByText('Currently in inventory')).toBeInTheDocument();
  });

  it('handles string values', () => {
    render(
      <MetricCard
        title="Status"
        value="Active"
        icon={<Package />}
      />
    );

    expect(screen.getByText('Active')).toBeInTheDocument();
  });

  it('handles numeric values', () => {
    render(
      <MetricCard
        title="Count"
        value={42}
        icon={<Package />}
      />
    );

    expect(screen.getByText('42')).toBeInTheDocument();
  });
});

