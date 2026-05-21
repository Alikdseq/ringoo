import type { Metadata } from 'next';
import { OrderStatusContent } from '@/app/order-status/OrderStatusContent';

export const metadata: Metadata = {
  title: 'Проверить статус заказа Ringoo — отслеживание заказа по номеру',
  description:
    'Введите номер заказа и телефон — узнайте, на каком этапе ваш заказ. Статус, состав, доставка, оплата. Удобное отслеживание.',
  openGraph: {
    title: 'Проверить статус заказа Ringoo',
    description:
      'Введите номер заказа и телефон, чтобы посмотреть статус и детали заказа: товары, доставка, сумма.',
    url: '/order-status',
    type: 'website',
  },
  robots: {
    index: true,
    follow: true,
  },
};

export default function OrderStatusPage() {
  return <OrderStatusContent />;
}

