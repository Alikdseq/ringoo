import { apiClient } from '@/lib/api/client';

export type ColorMappingRow = {
  id: string;
  product_id: string;
  product_title: string;
  product_onec_code: string;
  label: string;
  slug: string;
  hex: string;
  sku: string;
  barcode: string;
  onec_code: string;
  onec_characteristic_ref: string;
  mapping_status: string;
};

export async function getColorMappings(params?: {
  q?: string;
  mapping_status?: string;
}): Promise<ColorMappingRow[]> {
  const { data } = await apiClient.get<ColorMappingRow[]>('/admin/products/color-mappings/', {
    params,
  });
  return Array.isArray(data) ? data : [];
}

export async function updateColorMapping(
  id: string,
  payload: Partial<
    Pick<ColorMappingRow, 'sku' | 'barcode' | 'onec_code' | 'onec_characteristic_ref' | 'mapping_status'>
  >
): Promise<Partial<ColorMappingRow>> {
  const { data } = await apiClient.patch(`/admin/products/color-mappings/${id}/`, payload);
  return data as Partial<ColorMappingRow>;
}
