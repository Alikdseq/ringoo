'use client';

import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { Download, RefreshCw } from 'lucide-react';
import type { Order } from '@/types';
import {
  getOrders,
  type OrderListParams,
  updateOrderStatus,
  exportOrdersCsv,
} from '@/lib/api/services/orders.service';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Loading } from '@/components/ui/Loading';
import { CURRENCY_SYMBOL } from '@/lib/constants';
import { getOrder } from '@/lib/api/services/orders.service';

const STATUS_LABELS: Record<string, string> = {
  new: 'Новый',
  confirmed: 'Подтверждён',
  in_progress: 'В работе',
  completed: 'Выполнен',
  cancelled: 'Отменён',
};

const DELIVERY_LABELS: Record<string, string> = {
  pickup: 'Самовывоз',
  delivery: 'Доставка',
};

const PAYMENT_LABELS: Record<string, string> = {
  cash: 'Наличными',
  card_on_delivery: 'Картой при получении',
  bank_transfer: 'Банковский перевод',
  online: 'Онлайн',
};

export default function AdminOrdersPage() {
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState('');
  const [deliveryType, setDeliveryType] = useState('');
  const [paymentType, setPaymentType] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [search, setSearch] = useState('');
  const [selectedOrderId, setSelectedOrderId] = useState<string | null>(null);

  const params: OrderListParams = {
    page,
    status: status || undefined,
    delivery_type: deliveryType || undefined,
    payment_type: paymentType || undefined,
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
    search: search || undefined,
  };

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['admin', 'orders', params],
    queryFn: () => getOrders(params),
  });

  const statusMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) => updateOrderStatus(id, status),
    onSuccess: () => {
      void refetch();
    },
  });

  const handleExport = async () => {
    try {
      const blob = await exportOrdersCsv(params);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'orders.csv';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {
      // можно добавить уведомление об ошибке, если будет общий toast
    }
  };

  const orders: Order[] = data?.results ?? [];
  const total = data?.count ?? 0;
  const pageSize = orders.length > 0 ? orders.length : 20;
  const totalPages = pageSize > 0 ? Math.ceil(total / pageSize) : 1;

  const {
    data: selectedOrder,
    isLoading: selectedLoading,
    isError: selectedError,
  } = useQuery({
    queryKey: ['admin', 'order', selectedOrderId],
    queryFn: () => getOrder(selectedOrderId as string),
    enabled: !!selectedOrderId,
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-2xl font-semibold text-zinc-900">Заказы</h1>
        <div className="flex gap-2">
          <Button type="button" variant="outline" size="sm" onClick={() => refetch()}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Обновить
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handleExport}
            disabled={orders.length === 0}
          >
            <Download className="mr-2 h-4 w-4" />
            Экспорт CSV
          </Button>
        </div>
      </div>

      {/* Фильтры */}
      <Card className="p-4">
        <div className="grid gap-3 md:grid-cols-5">
          <div className="space-y-1">
            <label className="block text-xs font-medium text-zinc-500">Статус</label>
            <select
              value={status}
              onChange={e => {
                setStatus(e.target.value);
                setPage(1);
              }}
              className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm"
            >
              <option value="">Все</option>
              {Object.entries(STATUS_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-1">
            <label className="block text-xs font-medium text-zinc-500">Тип доставки</label>
            <select
              value={deliveryType}
              onChange={e => {
                setDeliveryType(e.target.value);
                setPage(1);
              }}
              className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm"
            >
              <option value="">Все</option>
              {Object.entries(DELIVERY_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-1">
            <label className="block text-xs font-medium text-zinc-500">Способ оплаты</label>
            <select
              value={paymentType}
              onChange={e => {
                setPaymentType(e.target.value);
                setPage(1);
              }}
              className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm"
            >
              <option value="">Все</option>
              {Object.entries(PAYMENT_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-1">
            <label className="block text-xs font-medium text-zinc-500">Дата от</label>
            <input
              type="date"
              value={dateFrom}
              onChange={e => {
                setDateFrom(e.target.value);
                setPage(1);
              }}
              className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm"
            />
          </div>

          <div className="space-y-1">
            <label className="block text-xs font-medium text-zinc-500">Дата до</label>
            <input
              type="date"
              value={dateTo}
              onChange={e => {
                setDateTo(e.target.value);
                setPage(1);
              }}
              className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm"
            />
          </div>
        </div>

        <div className="mt-3 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <input
            type="text"
            placeholder="Поиск по номеру, телефону или ФИО"
            value={search}
            onChange={e => {
              setSearch(e.target.value);
              setPage(1);
            }}
            className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm md:max-w-md"
          />
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => {
              setStatus('');
              setDeliveryType('');
              setPaymentType('');
              setDateFrom('');
              setDateTo('');
              setSearch('');
              setPage(1);
            }}
          >
            Сбросить фильтры
          </Button>
        </div>
      </Card>

      {/* Список заказов */}
      {isLoading ? (
        <div className="flex min-h-[300px] items-center justify-center">
          <Loading />
        </div>
      ) : isError ? (
        <Card className="p-6">
          <p className="mb-3 text-sm text-red-600">Не удалось загрузить заказы.</p>
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            Повторить
          </Button>
        </Card>
      ) : orders.length === 0 ? (
        <Card className="p-6">
          <p className="text-sm text-zinc-500">Заказы не найдены.</p>
        </Card>
      ) : (
        <Card className="overflow-hidden">
          <div className="-mx-4 overflow-x-auto px-4 sm:mx-0 sm:px-0">
            <table className="w-full min-w-[800px] text-sm">
              <thead>
                <tr className="border-b border-zinc-200 bg-zinc-50 text-xs uppercase text-zinc-500">
                  <th className="px-3 py-2 text-left">Номер</th>
                  <th className="px-3 py-2 text-left">ФИО</th>
                  <th className="px-3 py-2 text-left">Телефон</th>
                  <th className="px-3 py-2 text-left">Сумма</th>
                  <th className="px-3 py-2 text-left">Статус</th>
                  <th className="px-3 py-2 text-left">Доставка</th>
                  <th className="px-3 py-2 text-left">Оплата</th>
                  <th className="px-3 py-2 text-left">Дата</th>
                </tr>
              </thead>
              <tbody>
                {orders.map(order => (
                  <tr
                    key={order.id}
                    className="cursor-pointer border-b border-zinc-100 last:border-0 hover:bg-zinc-50"
                    onClick={() => setSelectedOrderId(order.id)}
                  >
                    <td className="px-3 py-2 font-medium text-zinc-900">{order.order_number}</td>
                    <td className="px-3 py-2 text-zinc-800">{order.full_name}</td>
                    <td className="px-3 py-2 text-zinc-700">{order.phone}</td>
                    <td className="px-3 py-2 text-zinc-900">
                      {order.total_amount} {CURRENCY_SYMBOL}
                    </td>
                    <td
                      className="px-3 py-2"
                      onClick={e => {
                        // чтобы клик по select не открывал модалку
                        e.stopPropagation();
                      }}
                    >
                      <select
                        value={order.status}
                        onChange={e =>
                          statusMutation.mutate({
                            id: order.id,
                            status: e.target.value,
                          })
                        }
                        className="rounded-full border border-zinc-200 bg-white px-2 py-1 text-xs"
                      >
                        {Object.entries(STATUS_LABELS).map(([value, label]) => (
                          <option key={value} value={value}>
                            {label}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="px-3 py-2 text-zinc-700">
                      {DELIVERY_LABELS[order.delivery_type] ?? order.delivery_type}
                    </td>
                    <td className="px-3 py-2 text-zinc-700">
                      {PAYMENT_LABELS[order.payment_type] ?? order.payment_type}
                    </td>
                    <td className="px-3 py-2 text-zinc-700">
                      {new Date(order.created_at).toLocaleString('ru-RU')}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Пагинация */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between border-t border-zinc-200 px-4 py-3 text-xs text-zinc-500">
              <span>
                Страница {page} из {totalPages} (всего {total} заказов)
              </span>
              <div className="flex gap-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  disabled={page <= 1}
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                >
                  Назад
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  disabled={page >= totalPages}
                  onClick={() => setPage(p => (p < totalPages ? p + 1 : p))}
                >
                  Вперёд
                </Button>
              </div>
            </div>
          )}
        </Card>
      )}
      {/* Модалка с деталями заказа */}
      {selectedOrderId && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/40">
          <div className="max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-2xl bg-white p-6 shadow-2xl">
            <div className="mb-4 flex items-center justify-between gap-2">
              <div>
                <h2 className="text-lg font-semibold text-zinc-900">Детали заказа</h2>
                {selectedOrder && (
                  <p className="text-sm text-zinc-500">
                    №{selectedOrder.order_number} от{' '}
                    {new Date(selectedOrder.created_at).toLocaleString('ru-RU')}
                  </p>
                )}
              </div>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => setSelectedOrderId(null)}
              >
                Закрыть
              </Button>
            </div>

            {selectedLoading ? (
              <div className="flex min-h-[200px] items-center justify-center">
                <Loading />
              </div>
            ) : selectedError || !selectedOrder ? (
              <p className="text-sm text-red-600">Не удалось загрузить детали заказа.</p>
            ) : (
              <div className="space-y-6">
                <div className="grid gap-4 md:grid-cols-2">
                  <Card>
                    <div className="mb-2 text-sm font-semibold text-zinc-900">Сводка</div>
                    <dl className="space-y-1 text-sm text-zinc-700">
                      <div className="flex justify-between">
                        <dt>Сумма заказа</dt>
                        <dd>
                          {selectedOrder.total_amount} {CURRENCY_SYMBOL}
                        </dd>
                      </div>
                      <div className="flex justify-between">
                        <dt>Доставка</dt>
                        <dd>
                          {selectedOrder.delivery_cost} {CURRENCY_SYMBOL}
                        </dd>
                      </div>
                    </dl>
                  </Card>

                  <Card>
                    <div className="mb-2 text-sm font-semibold text-zinc-900">Получатель</div>
                    <div className="space-y-1 text-sm text-zinc-700">
                      <p>{selectedOrder.full_name}</p>
                      <p>{selectedOrder.phone}</p>
                      {selectedOrder.email && <p>{selectedOrder.email}</p>}
                      {selectedOrder.comment && (
                        <p className="mt-2 text-xs text-zinc-500">
                          Комментарий: {selectedOrder.comment}
                        </p>
                      )}
                    </div>
                  </Card>
                </div>

                <Card>
                  <div className="mb-2 text-sm font-semibold text-zinc-900">Доставка и оплата</div>
                  <div className="space-y-1 text-sm text-zinc-700">
                    <p>
                      Тип доставки:{' '}
                      {DELIVERY_LABELS[selectedOrder.delivery_type] ?? selectedOrder.delivery_type}
                    </p>
                    <p>
                      Способ оплаты:{' '}
                      {PAYMENT_LABELS[selectedOrder.payment_type] ?? selectedOrder.payment_type}
                    </p>
                    <p>Адрес: {JSON.stringify(selectedOrder.delivery_address)}</p>
                  </div>
                </Card>

                <Card>
                  <div className="mb-2 text-sm font-semibold text-zinc-900">Товары</div>
                  <ul className="divide-y divide-zinc-200 text-sm">
                    {selectedOrder.items.map(item => (
                      <li
                        key={item.id}
                        className="flex flex-wrap items-center justify-between gap-2 py-2"
                      >
                        <div>
                          <p className="font-medium text-zinc-900">{item.product_title}</p>
                          <p className="text-xs text-zinc-500">
                            {item.quantity} × {item.price} {CURRENCY_SYMBOL}
                          </p>
                        </div>
                        <p className="text-sm font-semibold text-zinc-900">
                          {item.item_total} {CURRENCY_SYMBOL}
                        </p>
                      </li>
                    ))}
                  </ul>
                </Card>

                <div className="flex items-center justify-between">
                  <div className="text-sm text-zinc-600">
                    Статус:{' '}
                    <select
                      value={selectedOrder.status}
                      onChange={e =>
                        statusMutation.mutate({
                          id: selectedOrder.id,
                          status: e.target.value,
                        })
                      }
                      className="ml-2 rounded-full border border-zinc-200 bg-white px-2 py-1 text-xs"
                    >
                      {Object.entries(STATUS_LABELS).map(([value, label]) => (
                        <option key={value} value={value}>
                          {label}
                        </option>
                      ))}
                    </select>
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => setSelectedOrderId(null)}
                  >
                    Закрыть
                  </Button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
