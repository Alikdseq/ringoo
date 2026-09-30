import type { ProductDetail, ProductSpec } from '@/types';

/**
 * Возвращает все значения характеристик с заданным именем (без учёта регистра).
 * Например: getSpecValues(product, "Материал") → ["Кожа Horween", "Кожа"]
 *           getSpecValues(product, "Цвет") → ["Чёрный"]
 */
export function getSpecValues(product: Pick<ProductDetail, 'specs'>, specName: string): string[] {
  const specs: ProductSpec[] = product.specs ?? [];
  const nameLower = specName.trim().toLowerCase();
  if (!nameLower) return [];

  const values: string[] = [];
  for (const spec of specs) {
    if ((spec.name ?? '').trim().toLowerCase() === nameLower && spec.value?.trim()) {
      const v = spec.value.trim();
      if (v.includes(',')) {
        values.push(
          ...v
            .split(',')
            .map(s => s.trim())
            .filter(Boolean)
        );
      } else {
        values.push(v);
      }
    }
  }
  return [...new Set(values)];
}

/**
 * Первое значение характеристики по имени или null.
 */
export function getSpecValue(
  product: Pick<ProductDetail, 'specs'>,
  specName: string
): string | null {
  const arr = getSpecValues(product, specName);
  return arr.length > 0 ? arr[0] : null;
}
