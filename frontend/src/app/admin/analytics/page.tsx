'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { RefreshCw } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Loading } from '@/components/ui/Loading';
import {
  getRevenueReport,
  getOrdersReport,
  getTopProductsReport,
  type RevenueReportParams,
  type OrdersReportParams,
  type TopProductsReportParams,
  type OrdersReportBucket,
} from '@/lib/api/services/adminReports.service';
import { CURRENCY_SYMBOL } from '@/lib/constants';

type TabKey = 'revenue' | 'orders' | 'top';

export default function AdminAnalyticsPage() {
  const [tab, setTab] = useState<TabKey>('revenue');

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-2xl font-semibold text-zinc-900">Аналитика и отчёты</h1>
      </div>

      <div className="flex gap-2 border-b border-zinc-200">
        <TabButton
          active={tab === 'revenue'}
          onClick={() => setTab('revenue')}
          label="Выручка по периодам"
        />
        <TabButton
          active={tab === 'orders'}
          onClick={() => setTab('orders')}
          label="Отчёт по заказам"
        />
        <TabButton active={tab === 'top'} onClick={() => setTab('top')} label="Топ товаров" />
      </div>

      {tab === 'revenue' && <RevenueTab />}
      {tab === 'orders' && <OrdersReportTab />}
      {tab === 'top' && <TopProductsTab />}
    </div>
  );
}

interface TabButtonProps {
  active: boolean;
  label: string;
  onClick: () => void;
}

function TabButton({ active, label, onClick }: TabButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`border-b-2 px-3 py-2 text-sm font-medium ${
        active
          ? 'border-[var(--color-brand)] text-zinc-900'
          : 'border-transparent text-zinc-500 hover:text-zinc-800'
      }`}
    >
      {label}
    </button>
  );
}

function RevenueTab() {
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  const params: RevenueReportParams = {
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
  };

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['admin', 'reports', 'revenue', params],
    queryFn: () => getRevenueReport(params),
  });

  const totalRevenue = data?.rows.reduce((sum, row) => sum + Number(row.total_revenue || 0), 0);
  const totalOrders = data?.rows.reduce((sum, row) => sum + row.orders_count, 0);

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div className="space-y-2">
          <h2 className="text-sm font-semibold text-zinc-900">Выручка за период</h2>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-1">
              <label className="block text-xs font-medium text-zinc-500">Дата от</label>
              <input
                type="date"
                value={dateFrom}
                onChange={e => setDateFrom(e.target.value)}
                className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
              />
            </div>
            <div className="space-y-1">
              <label className="block text-xs font-medium text-zinc-500">Дата до</label>
              <input
                type="date"
                value={dateTo}
                onChange={e => setDateTo(e.target.value)}
                className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
              />
            </div>
          </div>
        </div>
        <div className="flex gap-2">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => {
              setDateFrom('');
              setDateTo('');
            }}
          >
            Сбросить
          </Button>
          <Button type="button" variant="outline" size="sm" onClick={() => refetch()}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Обновить
          </Button>
        </div>
      </div>

      <Card className="overflow-hidden">
        {isLoading ? (
          <div className="flex min-h-[200px] items-center justify-center">
            <Loading />
          </div>
        ) : isError || !data ? (
          <div className="p-4 text-sm text-red-600">Не удалось загрузить отчёт по выручке.</div>
        ) : data.rows.length === 0 ? (
          <div className="p-4 text-sm text-zinc-500">Нет данных за выбранный период.</div>
        ) : (
          <>
            <div className="grid gap-4 border-b border-zinc-200 bg-zinc-50 px-6 py-4 text-sm text-zinc-800 sm:grid-cols-3">
              <div>
                <p className="text-xs uppercase tracking-wide text-zinc-500">Период</p>
                <p className="mt-1">
                  {data.date_from} — {data.date_to}
                </p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-wide text-zinc-500">Выручка всего</p>
                <p className="mt-1 font-semibold">
                  {totalRevenue?.toFixed(2)} {CURRENCY_SYMBOL}
                </p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-wide text-zinc-500">Заказов всего</p>
                <p className="mt-1 font-semibold">{totalOrders}</p>
              </div>
            </div>
            <div className="-mx-4 overflow-x-auto px-4 sm:mx-0 sm:px-0">
              <table className="w-full min-w-[600px] text-sm">
                <thead>
                  <tr className="border-b border-zinc-200 bg-zinc-50 text-xs uppercase text-zinc-500">
                    <th className="px-4 py-2 text-left">Дата</th>
                    <th className="px-4 py-2 text-right">Выручка</th>
                    <th className="px-4 py-2 text-right">Заказов</th>
                  </tr>
                </thead>
                <tbody>
                  {data.rows.map(row => (
                    <tr key={row.date} className="border-b border-zinc-100 last:border-0">
                      <td className="px-4 py-2 text-sm text-zinc-900">{row.date}</td>
                      <td className="px-4 py-2 text-right text-sm text-zinc-900">
                        {row.total_revenue} {CURRENCY_SYMBOL}
                      </td>
                      <td className="px-4 py-2 text-right text-sm text-zinc-900">
                        {row.orders_count}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </Card>
    </div>
  );
}

function OrdersReportTab() {
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  const params: OrdersReportParams = {
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
  };

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['admin', 'reports', 'orders', params],
    queryFn: () => getOrdersReport(params),
  });

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div className="space-y-2">
          <h2 className="text-sm font-semibold text-zinc-900">Отчёт по заказам</h2>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-1">
              <label className="block text-xs font-medium text-zinc-500">Дата от</label>
              <input
                type="date"
                value={dateFrom}
                onChange={e => setDateFrom(e.target.value)}
                className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
              />
            </div>
            <div className="space-y-1">
              <label className="block text-xs font-medium text-zinc-500">Дата до</label>
              <input
                type="date"
                value={dateTo}
                onChange={e => setDateTo(e.target.value)}
                className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
              />
            </div>
          </div>
        </div>
        <div className="flex gap-2">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => {
              setDateFrom('');
              setDateTo('');
            }}
          >
            Сбросить
          </Button>
          <Button type="button" variant="outline" size="sm" onClick={() => refetch()}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Обновить
          </Button>
        </div>
      </div>

      <Card className="space-y-4 p-4">
        {isLoading ? (
          <div className="flex min-h-[160px] items-center justify-center">
            <Loading />
          </div>
        ) : isError || !data ? (
          <div className="text-sm text-red-600">Не удалось загрузить отчёт по заказам.</div>
        ) : (
          <div className="grid gap-4 md:grid-cols-3">
            <OrdersBucketTable title="По статусам" rows={data.by_status} labelKey="status" />
            <OrdersBucketTable
              title="По способам оплаты"
              rows={data.by_payment_type}
              labelKey="payment_type"
            />
            <OrdersBucketTable
              title="По типам доставки"
              rows={data.by_delivery_type}
              labelKey="delivery_type"
            />
          </div>
        )}
      </Card>
    </div>
  );
}

interface OrdersBucketTableProps {
  title: string;
  rows: OrdersReportBucket[];
  labelKey: keyof OrdersReportBucket;
}

function OrdersBucketTable({ title, rows, labelKey }: OrdersBucketTableProps) {
  const total = rows.reduce((sum, row) => sum + Number(row.count || 0), 0);

  return (
    <div className="space-y-2">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-zinc-500">{title}</h3>
      {rows.length === 0 ? (
        <p className="text-xs text-zinc-500">Нет данных.</p>
      ) : (
        <table className="w-full text-xs">
          <tbody>
            {rows.map((row, idx) => (
              <tr key={idx} className="border-b border-zinc-100 last:border-0">
                <td className="px-2 py-1 text-zinc-700">{String(row[labelKey] || '—')}</td>
                <td className="px-2 py-1 text-right font-medium text-zinc-900">{row.count}</td>
              </tr>
            ))}
            <tr className="border-t border-zinc-200">
              <td className="px-2 py-1 text-xs font-semibold text-zinc-700">Всего</td>
              <td className="px-2 py-1 text-right text-xs font-semibold text-zinc-900">{total}</td>
            </tr>
          </tbody>
        </table>
      )}
    </div>
  );
}

function TopProductsTab() {
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [limit, setLimit] = useState(10);

  const params: TopProductsReportParams = {
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
    limit,
  };

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['admin', 'reports', 'top-products', params],
    queryFn: () => getTopProductsReport(params),
  });

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div className="space-y-2">
          <h2 className="text-sm font-semibold text-zinc-900">Топ товаров</h2>
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="space-y-1">
              <label className="block text-xs font-medium text-zinc-500">Дата от</label>
              <input
                type="date"
                value={dateFrom}
                onChange={e => setDateFrom(e.target.value)}
                className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
              />
            </div>
            <div className="space-y-1">
              <label className="block text-xs font-medium text-zinc-500">Дата до</label>
              <input
                type="date"
                value={dateTo}
                onChange={e => setDateTo(e.target.value)}
                className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
              />
            </div>
            <div className="space-y-1">
              <label className="block text-xs font-medium text-zinc-500">Количество товаров</label>
              <input
                type="number"
                min={1}
                max={100}
                value={limit}
                onChange={e => {
                  const v = Number(e.target.value);
                  if (Number.isFinite(v) && v > 0 && v <= 100) {
                    setLimit(v);
                  }
                }}
                className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
              />
            </div>
          </div>
        </div>
        <div className="flex gap-2">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => {
              setDateFrom('');
              setDateTo('');
            }}
          >
            Сбросить
          </Button>
          <Button type="button" variant="outline" size="sm" onClick={() => refetch()}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Обновить
          </Button>
        </div>
      </div>

      <Card className="overflow-hidden">
        {isLoading ? (
          <div className="flex min-h-[200px] items-center justify-center">
            <Loading />
          </div>
        ) : isError || !data ? (
          <div className="p-4 text-sm text-red-600">Не удалось загрузить топ товаров.</div>
        ) : data.rows.length === 0 ? (
          <div className="p-4 text-sm text-zinc-500">Нет данных за выбранный период.</div>
        ) : (
          <div className="-mx-4 overflow-x-auto px-4 sm:mx-0 sm:px-0">
            <table className="w-full min-w-[600px] text-sm">
              <thead>
                <tr className="border-b border-zinc-200 bg-zinc-50 text-xs uppercase text-zinc-500">
                  <th className="px-4 py-2 text-left">Товар</th>
                  <th className="px-4 py-2 text-left">Артикул</th>
                  <th className="px-4 py-2 text-right">Продано, шт</th>
                  <th className="px-4 py-2 text-right">Выручка</th>
                </tr>
              </thead>
              <tbody>
                {data.rows.map((row, idx) => (
                  <tr
                    key={`${row.product_sku}-${idx}`}
                    className="border-b border-zinc-100 last:border-0"
                  >
                    <td className="px-4 py-2 text-sm text-zinc-900">{row.product_title || '—'}</td>
                    <td className="px-4 py-2 text-xs text-zinc-600">{row.product_sku || '—'}</td>
                    <td className="px-4 py-2 text-right text-sm text-zinc-900">
                      {row.quantity_sold}
                    </td>
                    <td className="px-4 py-2 text-right text-sm text-zinc-900">
                      {row.revenue} {CURRENCY_SYMBOL}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
