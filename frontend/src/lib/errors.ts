/** Текст из тела ответа DRF (поля → списки строк или вложенные объекты). */
function formatDrfErrorBody(data: unknown): string | null {
  if (data == null || typeof data !== 'object') return null;
  const d = data as Record<string, unknown>;

  if (typeof d.detail === 'string' && d.detail.trim()) {
    return d.detail.trim();
  }
  if (Array.isArray(d.detail) && d.detail.length && typeof d.detail[0] === 'string') {
    return d.detail.join(' ');
  }

  const parts: string[] = [];
  for (const [key, value] of Object.entries(d)) {
    if (key === 'detail') continue;
    if (typeof value === 'string' && value.trim()) {
      parts.push(value.trim());
    } else if (Array.isArray(value)) {
      const first = value.find(v => typeof v === 'string') as string | undefined;
      if (first?.trim()) parts.push(first.trim());
    } else if (value && typeof value === 'object') {
      const nested = formatDrfErrorBody(value);
      if (nested) parts.push(nested);
    }
  }
  return parts.length ? parts.join(' ') : null;
}

/**
 * Преобразует ошибку API/сети в понятное пользователю сообщение.
 * Вместо "Ошибка 500" или сырого текста показываем дружелюбный текст.
 */
export function getFriendlyErrorMessage(error: unknown): string {
  if (error == null) return 'Произошла ошибка. Попробуйте ещё раз.';
  if (typeof error === 'string') return error;

  const err = error as {
    message?: string;
    status?: number;
    response?: { status?: number; data?: unknown };
  };
  const status = err?.response?.status ?? err?.status;
  const message = err?.message?.trim();
  const bodyText = formatDrfErrorBody(err?.response?.data);

  if (status === 400) {
    if (bodyText) return bodyText;
    if (message) return message;
    return 'Проверьте введённые данные и попробуйте снова.';
  }
  if (status === 401) return 'Войдите в аккаунт и попробуйте снова.';
  if (status === 429) {
    if (bodyText) return bodyText;
    return 'Слишком много запросов. Подождите немного и попробуйте снова.';
  }
  if (status === 403) return 'Недостаточно прав для этого действия.';
  if (status === 404) return 'Запрашиваемая страница или данные не найдены.';
  if (status === 409) return message || 'Конфликт данных. Обновите страницу и попробуйте снова.';
  if (status != null && status >= 500) {
    return 'Сервер временно недоступен. Попробуйте через несколько минут.';
  }
  if (message && !message.toLowerCase().includes('failed') && !message.startsWith('Network')) {
    return message;
  }
  return 'Не удалось выполнить действие. Проверьте подключение к интернету и попробуйте снова.';
}
