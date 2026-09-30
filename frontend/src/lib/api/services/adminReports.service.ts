import { apiClient } from '@/lib/api/client';

export interface RevenueRow {
  date: string;
  total_revenue: string;
  orders_count: number;
}

export interface RevenueReportResponse {
  date_from: string;
  date_to: string;
  rows: RevenueRow[];
}

export interface RevenueReportParams {
  date_from?: string;
  date_to?: string;
}

export interface OrdersReportBucket {
  status?: string;
  payment_type?: string;
  delivery_type?: string;
  count: number;
}

export interface OrdersReportResponse {
  date_from: string;
  date_to: string;
  by_status: OrdersReportBucket[];
  by_payment_type: OrdersReportBucket[];
  by_delivery_type: OrdersReportBucket[];
}

export interface OrdersReportParams {
  date_from?: string;
  date_to?: string;
}

export interface TopProductRow {
  product_title: string;
  product_sku: string;
  quantity_sold: number;
  revenue: string;
}

export interface TopProductsReportResponse {
  date_from: string;
  date_to: string;
  rows: TopProductRow[];
}

export interface TopProductsReportParams {
  date_from?: string;
  date_to?: string;
  limit?: number;
}

export async function getRevenueReport(
  params: RevenueReportParams = {}
): Promise<RevenueReportResponse> {
  const { data } = await apiClient.get<RevenueReportResponse>('/admin/reports/revenue/', {
    params,
  });
  return data;
}

export async function getOrdersReport(
  params: OrdersReportParams = {}
): Promise<OrdersReportResponse> {
  const { data } = await apiClient.get<OrdersReportResponse>('/admin/reports/orders/', {
    params,
  });
  return data;
}

export async function getTopProductsReport(
  params: TopProductsReportParams = {}
): Promise<TopProductsReportResponse> {
  const { data } = await apiClient.get<TopProductsReportResponse>('/admin/reports/top-products/', {
    params,
  });
  return data;
}
