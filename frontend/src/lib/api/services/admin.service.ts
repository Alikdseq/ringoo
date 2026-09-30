import { apiClient } from '@/lib/api/client';

export interface DashboardStats {
  orders_today: number;
  orders_week: number;
  orders_month: number;
  revenue_week: string;
  revenue_month: string;
  avg_check_week: number;
  avg_check_month: number;
  top_products: Array<{
    product_title: string;
    product_sku: string;
    quantity_sold: number;
  }>;
}

export async function getDashboardStats(): Promise<DashboardStats> {
  const { data } = await apiClient.get<DashboardStats>('/admin/dashboard/stats/');
  return data;
}
