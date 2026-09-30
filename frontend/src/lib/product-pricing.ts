import type { Product, ProductColor, ProductListColor } from '@/types';

type ColorLike = Pick<ProductColor, 'id' | 'price' | 'old_price'> | ProductListColor;

export type ProductDisplayPrice = {
  price: string;
  old_price: string | null;
  discount_percent: number;
};

function parseAmount(value: string | null | undefined): number | null {
  if (value == null || value === '') return null;
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

function calcDiscountPercent(price: number, oldPrice: number | null): number {
  if (oldPrice == null || oldPrice <= price || oldPrice <= 0) return 0;
  return Math.round(((oldPrice - price) / oldPrice) * 100);
}

function findColor(
  colors: ColorLike[] | undefined,
  colorId: string | null | undefined
): ColorLike | undefined {
  if (!colorId || !colors?.length) return undefined;
  return colors.find(c => c.id === colorId);
}

/** Цена для отображения с учётом выбранного цвета (если у цвета своя цена). */
export function resolveProductDisplayPrice(
  product: Pick<Product, 'price' | 'old_price' | 'discount_percent' | 'colors'>,
  colorId?: string | null
): ProductDisplayPrice {
  const color = findColor(product.colors, colorId);
  const basePrice = parseAmount(product.price) ?? 0;
  const baseOld = parseAmount(product.old_price);

  const colorPrice = color ? parseAmount(color.price ?? undefined) : null;
  const colorOld = color ? parseAmount(color.old_price ?? undefined) : null;

  const priceNum = colorPrice ?? basePrice;
  const oldNum = colorOld ?? (colorPrice != null ? null : baseOld);

  const discount =
    product.discount_percent != null && colorPrice == null
      ? Math.round(Number(product.discount_percent))
      : calcDiscountPercent(priceNum, oldNum);

  return {
    price: String(priceNum),
    old_price: oldNum != null && oldNum > priceNum ? String(oldNum) : null,
    discount_percent: discount > 0 ? discount : 0,
  };
}
