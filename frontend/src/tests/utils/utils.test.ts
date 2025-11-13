/**
 * Utility Functions Tests
 */

import { describe, it, expect } from 'vitest';
import { formatCurrency, formatPercentage } from '../../lib/utils';

describe('Utility Functions', () => {
  describe('formatCurrency', () => {
    it('formats positive numbers correctly', () => {
      expect(formatCurrency(1000)).toBe('$1,000.00');
      expect(formatCurrency(1234.56)).toBe('$1,234.56');
      expect(formatCurrency(999999.99)).toBe('$999,999.99');
    });

    it('formats zero correctly', () => {
      expect(formatCurrency(0)).toBe('$0.00');
    });

    it('formats negative numbers correctly', () => {
      expect(formatCurrency(-100)).toBe('-$100.00');
      expect(formatCurrency(-1234.56)).toBe('-$1,234.56');
    });

    it('handles decimal precision', () => {
      expect(formatCurrency(10.5)).toBe('$10.50');
      expect(formatCurrency(10.123)).toBe('$10.12');
      expect(formatCurrency(10.999)).toBe('$11.00');
    });

    it('handles very large numbers', () => {
      expect(formatCurrency(1000000)).toBe('$1,000,000.00');
      expect(formatCurrency(1234567.89)).toBe('$1,234,567.89');
    });

    it('handles very small numbers', () => {
      expect(formatCurrency(0.01)).toBe('$0.01');
      expect(formatCurrency(0.99)).toBe('$0.99');
    });
  });

  describe('formatPercentage', () => {
    it('formats percentages correctly', () => {
      expect(formatPercentage(0.25)).toBe('25%');
      expect(formatPercentage(0.5)).toBe('50%');
      expect(formatPercentage(1.0)).toBe('100%');
    });

    it('formats decimal percentages', () => {
      expect(formatPercentage(0.255)).toBe('25.5%');
      expect(formatPercentage(0.3333)).toBe('33.33%');
    });

    it('handles zero', () => {
      expect(formatPercentage(0)).toBe('0%');
    });

    it('handles negative percentages', () => {
      expect(formatPercentage(-0.15)).toBe('-15%');
    });

    it('handles percentages over 100%', () => {
      expect(formatPercentage(1.5)).toBe('150%');
      expect(formatPercentage(2.0)).toBe('200%');
    });
  });
});

