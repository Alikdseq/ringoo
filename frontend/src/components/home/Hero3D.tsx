'use client';

/**
 * Встроенный 3D-просмотрщик Sketchfab (Apple iPhone 17 Pro Max).
 * Интерфейс Sketchfab скрыт по максимуму; при необходимости верх/низ обрезаются.
 */
const EMBED_SRC =
  'https://sketchfab.com/models/43570bd2d48f48b6aafb8adbb04e346d/embed?autospin=1&autostart=1&transparent=1&ui_controls=0&ui_infos=0&ui_watermark=0&ui_watermark_link=0&ui_help=0&ui_settings=0&ui_annotations=0&ui_inspector=0&ui_stop=0&ui_fullscreen=0';

export function Hero3D() {
  return (
    <div className="absolute inset-0 flex items-center justify-center overflow-hidden" aria-hidden>
      {/* Баланс: модель видна целиком на mobile/desktop, UI Sketchfab максимально скрыт параметрами embed */}
      <div className="relative h-full w-full max-w-4xl overflow-hidden rounded-none sm:rounded-xl">
        <iframe
          title="Apple iPhone 17 Pro Max"
          frameBorder="0"
          allow="autoplay; fullscreen; xr-spatial-tracking; accelerometer; gyroscope"
          className="absolute left-1/2 top-1/2 h-[126%] w-[114%] min-w-[114%] -translate-x-1/2 -translate-y-1/2 scale-[0.71] sm:h-[130%] sm:w-[116%] sm:min-w-[116%] sm:scale-[0.74] lg:h-[134%] lg:w-[120%] lg:min-w-[120%] lg:scale-[0.76] xl:h-[132%] xl:w-[118%] xl:min-w-[118%] xl:scale-[0.74]"
          style={{
            pointerEvents: 'none',
            // Скрываем служебный UI слева, но не режем низ модели.
            clipPath: 'inset(0 0 0 7%)',
            WebkitClipPath: 'inset(0 0 0 7%)',
          }}
          src={EMBED_SRC}
        />
        {/* Локальная маска для служебной иконки в нижнем левом углу iframe.
            Находится внутри 3D-зоны и не влияет на карточки категорий ниже. */}
        <div className="pointer-events-none absolute bottom-2 left-2 z-10 h-10 w-10 rounded-full bg-background sm:h-11 sm:w-11" />
      </div>
    </div>
  );
}
