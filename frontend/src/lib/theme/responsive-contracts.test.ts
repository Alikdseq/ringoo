/**
 * B8-019 / FIX-PACK L — контракты адаптивной вёрстки (без Playwright).
 * Проверяют наличие критичных utility-классов, а не «страница открылась».
 */
import { describe, expect, it } from 'vitest';
import {
  ADMIN_TABLE_SCROLL_CLASS,
  HEADER_ACTIONS_CLUSTER_CLASS,
  HEADER_CATALOG_BUTTON_CLASS,
  HEADER_ICON_BUTTON_CLASS,
  HEADER_LOGO_BOX_CLASS,
  HEADER_PILL_INNER_CLASS,
  PRODUCT_CARD_GRID_CLASS,
  TOUCH_TARGET_MOBILE_CLASS,
} from '@/lib/theme/spacing';

describe('responsive layout contracts (B8-019)', () => {
  it('header pill clips overflow on narrow mobile and restores on md+', () => {
    expect(HEADER_PILL_INNER_CLASS).toContain('overflow-hidden');
    expect(HEADER_PILL_INNER_CLASS).toContain('md:overflow-visible');
    expect(HEADER_PILL_INNER_CLASS).toContain('min-w-0');
  });

  it('header logo and catalog shrink below 380px to keep menu in viewport', () => {
    expect(HEADER_LOGO_BOX_CLASS).toMatch(/max-\[379px\]/);
    expect(HEADER_CATALOG_BUTTON_CLASS).toContain('max-[379px]:[&>span]:sr-only');
    expect(HEADER_ACTIONS_CLUSTER_CLASS).toContain('shrink-0');
  });

  it('header icon buttons keep touch targets on mobile', () => {
    expect(HEADER_ICON_BUTTON_CLASS).toContain('touch-manipulation');
    expect(HEADER_ICON_BUTTON_CLASS).toMatch(/min-h-9|min-h-10/);
  });

  it('product grid is 1→2→3 columns', () => {
    expect(PRODUCT_CARD_GRID_CLASS).toContain('grid-cols-1');
    expect(PRODUCT_CARD_GRID_CLASS).toContain('md:grid-cols-2');
    expect(PRODUCT_CARD_GRID_CLASS).toContain('lg:grid-cols-3');
  });

  it('admin tables scroll horizontally on narrow screens', () => {
    expect(ADMIN_TABLE_SCROLL_CLASS).toContain('overflow-x-auto');
  });

  it('shared touch target class expands below lg', () => {
    expect(TOUCH_TARGET_MOBILE_CLASS).toContain('min-h-[44px]');
    expect(TOUCH_TARGET_MOBILE_CLASS).toContain('lg:min-h-0');
  });
});
