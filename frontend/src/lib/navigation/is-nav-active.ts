/** Соответствие текущего URL пункту меню (вложенные маршруты считаются активными). */
export function isNavActive(pathname: string | null, href: string): boolean {
  if (!pathname || href.startsWith('/#')) return false;
  const path = href.split('#')[0];
  if (!path) return false;
  if (path === '/') return pathname === '/';
  if (pathname === path) return true;
  return pathname.startsWith(`${path}/`);
}
