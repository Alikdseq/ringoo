/** Клиентский preview slug (как django.utils.text.slugify без unicode). */
export function slugifyProductTitle(title: string): string {
  const s = title
    .trim()
    .toLowerCase()
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
  return s || 'product';
}
