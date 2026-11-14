/**
 * B8-001: куда вести после cash / card_on_delivery checkout.
 * Гость — публичная страница без auth-only getOrder; auth — детальный success по id.
 * Токен в URL не передаём.
 */
export function resolveCashCheckoutSuccessPath(options: {
  isAuthenticated: boolean;
  orderId: string;
  orderNumber: string;
}): string {
  const orderNumber = (options.orderNumber || '').trim();
  if (!options.isAuthenticated) {
    if (!orderNumber) {
      return '/orders/success';
    }
    return `/orders/success?order_number=${encodeURIComponent(orderNumber)}`;
  }
  return `/orders/${options.orderId}/success`;
}
