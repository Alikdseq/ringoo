/**
 * Глобальный default для <Link prefetch>:
 *   - prod / dev на localhost: undefined → Next решает сам (обычно `true` для viewport).
 *   - ngrok-demo (бесплатный план): false — иначе массовый RSC-prefetch
 *     забивает rate-limit туннеля и часть запросов получают 503/404.
 *
 * Активируется при наличии `NEXT_PUBLIC_DISABLE_LINK_PREFETCH=1` или `RINGOO_NGROK_DEMO=1`.
 */
export const LINK_PREFETCH_DEFAULT: boolean | undefined =
  process.env.NEXT_PUBLIC_DISABLE_LINK_PREFETCH === '1' ||
  process.env.NEXT_PUBLIC_RINGOO_NGROK_DEMO === '1' ||
  process.env.RINGOO_NGROK_DEMO === '1'
    ? false
    : undefined;
