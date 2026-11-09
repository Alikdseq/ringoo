/** Сопоставление пунктов меню админки с группами ringoo_*. */
export const ADMIN_GROUP = {
  orders: 'ringoo_orders',
  catalog: 'ringoo_catalog',
  content: 'ringoo_content',
  crm: 'ringoo_crm',
  reports: 'ringoo_reports',
  users: 'ringoo_users',
  stores: 'ringoo_stores',
} as const;

export type AdminGroupName = (typeof ADMIN_GROUP)[keyof typeof ADMIN_GROUP];

export interface StaffAccessInfo {
  staff: boolean;
  is_superuser: boolean;
  groups: string[];
}

/** Какие группы нужны для href (достаточно одной). Superuser видит всё. */
export const ADMIN_NAV_REQUIRED_GROUPS: Record<string, AdminGroupName[]> = {
  '/admin/orders': [ADMIN_GROUP.orders],
  '/admin/products': [ADMIN_GROUP.catalog],
  '/admin/products/import': [ADMIN_GROUP.catalog],
  '/admin/categories': [ADMIN_GROUP.catalog],
  '/admin/sync': [ADMIN_GROUP.catalog],
  '/admin/color-mappings': [ADMIN_GROUP.catalog],
  '/admin/stock': [ADMIN_GROUP.stores],
  '/admin/users': [ADMIN_GROUP.users],
  '/admin/content': [ADMIN_GROUP.content],
  '/admin/stores': [ADMIN_GROUP.stores],
  '/admin/managers': [ADMIN_GROUP.stores],
  '/admin/promotions': [ADMIN_GROUP.catalog],
  '/admin/crm': [ADMIN_GROUP.crm],
  '/admin/analytics': [ADMIN_GROUP.reports],
  '/admin/returns': [ADMIN_GROUP.orders],
  // Только суперпользователь (canAccessAdminNav → is_superuser)
  '/admin/backup': [],
};

/** Разделы только для суперпользователя (даже при пустых required groups). */
export const ADMIN_SUPERUSER_ONLY_NAV = new Set<string>(['/admin/backup']);

export function canAccessAdminNav(
  href: string,
  access: StaffAccessInfo | null | undefined
): boolean {
  if (!access?.staff) return false;
  if (ADMIN_SUPERUSER_ONLY_NAV.has(href)) {
    return Boolean(access.is_superuser);
  }
  if (access.is_superuser) return true;
  const required = ADMIN_NAV_REQUIRED_GROUPS[href];
  if (!required || required.length === 0) return true;
  const set = new Set(access.groups ?? []);
  // Staff без групп — не показываем разделы (избегаем ложных 403 в меню).
  if (set.size === 0) return false;
  return required.some(g => set.has(g));
}

/** Допустимые переходы статуса заказа (зеркало BE FSM). */
export {
  ORDER_STATUS_TRANSITIONS,
  allowedOrderStatusOptions,
} from '@/lib/orders/status-labels';
