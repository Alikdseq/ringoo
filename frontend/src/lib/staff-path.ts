/** SEO-friendly URL профиля менеджера. */
export function staffProfilePath(slug: string): string {
  return `/staff/${encodeURIComponent(slug)}`;
}
