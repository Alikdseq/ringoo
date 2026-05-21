import { redirect } from 'next/navigation';

/** Дашборд отключён — вход в ERP ведёт в заказы. */
export default function AdminDashboardPage() {
  redirect('/admin/orders');
}
