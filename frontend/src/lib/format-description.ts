/**
 * Текст описаний из ERP/бэкенда часто приходит с HTML (<p>, <br>).
 * Для UI отдаём чистый текст без тегов.
 */
export function stripDescriptionHtml(html: string | null | undefined): string {
  if (!html?.trim()) return '';
  return html
    .replace(/<\/?p[^>]*>/gi, '\n')
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/<\/li>/gi, '\n')
    .replace(/<[^>]+>/g, '')
    .replace(/&nbsp;/gi, ' ')
    .replace(/&amp;/gi, '&')
    .replace(/&lt;/gi, '<')
    .replace(/&gt;/gi, '>')
    .replace(/&quot;/gi, '"')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}
