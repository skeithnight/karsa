import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useDebounce } from '../useDebounce';

describe('useDebounce', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('debounces multiple fast updates', () => {
    const { result, rerender } = renderHook(({ value, delay }) => useDebounce(value, delay), {
      initialProps: { value: 'a', delay: 300 },
    });

    // Should return initial value immediately
    expect(result.current).toBe('a');

    // Type "ab"
    rerender({ value: 'ab', delay: 300 });
    // Should still be 'a' immediately after
    expect(result.current).toBe('a');

    // Type "abc"
    rerender({ value: 'abc', delay: 300 });
    expect(result.current).toBe('a');

    // Fast forward time by 200ms (not enough to trigger)
    act(() => {
      vi.advanceTimersByTime(200);
    });
    expect(result.current).toBe('a');

    // Fast forward by another 100ms (total 300ms)
    act(() => {
      vi.advanceTimersByTime(100);
    });

    // Should now be "abc" and exactly ONE update occurred
    expect(result.current).toBe('abc');
  });
});
