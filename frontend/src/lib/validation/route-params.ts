/** UUID заказа (как в Django UUIDField), без обращения к API при заведомо невалидном id. */
const ORDER_UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export function isOrderIdParam(id: string | undefined): boolean {
  if (!id || typeof id !== 'string') return false;
  return ORDER_UUID_RE.test(id.trim());
}
