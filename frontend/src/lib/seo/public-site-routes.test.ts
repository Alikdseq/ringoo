import { describe, expect, it } from 'vitest';

import {
  isNonIndexablePath,
  NON_INDEXABLE_PATH_PREFIXES,
  PUBLIC_INDEXABLE_STATIC_ROUTES,
} from './public-site-routes';

describe('public-site-routes (B8-016)', () => {
  it('does not put private paths into indexable static list', () => {
    const paths = PUBLIC_INDEXABLE_STATIC_ROUTES.map(r => r.path);
    for (const privatePath of [
      '/cart',
      '/checkout',
      '/login',
      '/register',
      '/profile',
      '/orders',
      '/admin',
      '/wishlist',
    ]) {
      expect(paths).not.toContain(privatePath);
    }
  });

  it('includes blog/news hubs and legal docs for HTML/XML sync', () => {
    const paths = PUBLIC_INDEXABLE_STATIC_ROUTES.map(r => r.path);
    expect(paths).toEqual(
      expect.arrayContaining([
        '/',
        '/catalog',
        '/blog',
        '/news',
        '/about',
        '/installment',
        '/site-map',
        '/docs/privacy',
      ])
    );
  });

  it('marks auth/cart/admin prefixes as non-indexable', () => {
    expect(isNonIndexablePath('/cart')).toBe(true);
    expect(isNonIndexablePath('/checkout')).toBe(true);
    expect(isNonIndexablePath('/orders/abc/payment/return')).toBe(true);
    expect(isNonIndexablePath('/admin/products')).toBe(true);
    expect(isNonIndexablePath('/forgot-password')).toBe(true);
    expect(isNonIndexablePath('/catalog')).toBe(false);
    expect(isNonIndexablePath('/products/phone')).toBe(false);
  });

  it('keeps NON_INDEXABLE list non-empty for robots alignment', () => {
    expect(NON_INDEXABLE_PATH_PREFIXES.length).toBeGreaterThan(5);
  });
});
