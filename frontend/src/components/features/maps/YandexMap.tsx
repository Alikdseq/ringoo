'use client';

import { useEffect, useRef, useState } from 'react';
import { cn } from '@/lib/theme/utils';

declare global {
  interface Window {
    ymaps?: any;
    __ringooYmapsLoading?: Promise<any> | null;
  }
}

export interface YandexMapMarker {
  id: string;
  coordinates: [number, number];
  title?: string;
  description?: string;
  selected?: boolean;
}

const VLADIKAVKAZ_CENTER: [number, number] = [43.0246, 44.6818];
const SCRIPT_ID = 'ringoo-ymaps-script';

interface YandexMapProps {
  markers: YandexMapMarker[];
  center?: [number, number];
  zoom?: number;
  className?: string;
  onMarkerClick?: (id: string) => void;
  /** Включить кластеризацию при ≥ 2 точках (по умолчанию true) */
  cluster?: boolean;
  /** Высота на mobile / desktop */
  heightClass?: string;
}

/** Грузит Я.Карты один раз на всё SPA (re-use между страницами). */
function ensureYmapsLoaded(apiKey?: string | null): Promise<any> {
  if (typeof window === 'undefined') return Promise.reject(new Error('SSR'));
  if (window.ymaps?.Map) return Promise.resolve(window.ymaps);
  if (window.__ringooYmapsLoading) return window.__ringooYmapsLoading;

  const params = new URLSearchParams({
    lang: 'ru_RU',
    load: 'package.full',
  });
  if (apiKey) params.set('apikey', apiKey);

  const src = `https://api-maps.yandex.ru/2.1/?${params.toString()}`;

  window.__ringooYmapsLoading = new Promise<any>((resolve, reject) => {
    let script = document.getElementById(SCRIPT_ID) as HTMLScriptElement | null;
    const start = () => {
      if (!window.ymaps?.ready) {
        reject(new Error('ymaps did not initialize'));
        return;
      }
      window.ymaps.ready(() => resolve(window.ymaps));
    };
    if (script) {
      script.addEventListener('load', start, { once: true });
      return;
    }
    script = document.createElement('script');
    script.id = SCRIPT_ID;
    script.src = src;
    script.async = true;
    script.defer = true;
    script.onload = start;
    script.onerror = () => reject(new Error('Failed to load Yandex Maps SDK'));
    document.head.appendChild(script);
  });

  return window.__ringooYmapsLoading;
}

export function YandexMap({
  markers,
  center,
  zoom = 11,
  className,
  onMarkerClick,
  cluster = true,
  heightClass = 'h-72 sm:h-80',
}: YandexMapProps) {
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const mapInstanceRef = useRef<any>(null);
  const objectsRef = useRef<any>(null);
  const [shouldLoad, setShouldLoad] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const node = mapContainerRef.current;
    if (!node) return;
    const observer = new IntersectionObserver(
      entries => {
        if (entries.some(e => e.isIntersecting)) {
          setShouldLoad(true);
          observer.disconnect();
        }
      },
      { rootMargin: '300px' }
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!shouldLoad) return;
    const apiKey = process.env.NEXT_PUBLIC_YANDEX_MAPS_API_KEY ?? null;
    let cancelled = false;

    ensureYmapsLoaded(apiKey)
      .then(ymaps => {
        if (cancelled || !mapContainerRef.current) return;

        const first = markers[0];
        const mapCenter: [number, number] = center ?? first?.coordinates ?? VLADIKAVKAZ_CENTER;

        if (!mapInstanceRef.current) {
          mapInstanceRef.current = new ymaps.Map(mapContainerRef.current, {
            center: mapCenter,
            zoom,
            controls: ['zoomControl', 'geolocationControl', 'fullscreenControl'],
          });
        }

        const map = mapInstanceRef.current;

        if (objectsRef.current) {
          map.geoObjects.remove(objectsRef.current);
          objectsRef.current = null;
        }

        const useCluster = cluster && markers.length >= 2 && ymaps.Clusterer;
        const container = useCluster
          ? new ymaps.Clusterer({
              preset: 'islands#greenClusterIcons',
              groupByCoordinates: false,
              clusterDisableClickZoom: false,
              clusterHideIconOnBalloonOpen: false,
              geoObjectHideIconOnBalloonOpen: false,
            })
          : null;

        const placemarks = markers.map(marker => {
          const placemark = new ymaps.Placemark(
            marker.coordinates,
            {
              balloonContentHeader: marker.title ?? '',
              balloonContentBody: marker.description ?? '',
              hintContent: marker.title ?? '',
            },
            {
              preset: marker.selected ? 'islands#redIcon' : 'islands#greenIcon',
            }
          );
          if (onMarkerClick) {
            placemark.events.add('click', () => onMarkerClick(marker.id));
          }
          return placemark;
        });

        if (container) {
          container.add(placemarks);
          map.geoObjects.add(container);
          objectsRef.current = container;
        } else {
          placemarks.forEach(p => map.geoObjects.add(p));
          objectsRef.current = { remove: () => placemarks.forEach(p => map.geoObjects.remove(p)) };
        }

        if (markers.length > 1) {
          const lats = markers.map(m => m.coordinates[0]);
          const lons = markers.map(m => m.coordinates[1]);
          const bounds: [[number, number], [number, number]] = [
            [Math.min(...lats), Math.min(...lons)],
            [Math.max(...lats), Math.max(...lons)],
          ];
          map.setBounds(bounds, { checkZoomRange: true, zoomMargin: 36 }).catch(() => {
            /* ignore zoom-range fail */
          });
        } else {
          map.setCenter(mapCenter, zoom);
        }
      })
      .catch(err => {
        if (!cancelled) setError(err?.message || 'Не удалось загрузить карту');
      });

    return () => {
      cancelled = true;
    };
  }, [shouldLoad, markers, center, zoom, onMarkerClick, cluster]);

  return (
    <div
      ref={mapContainerRef}
      data-testid="yandex-map-container"
      className={cn(
        'relative w-full overflow-hidden rounded-2xl border border-border bg-zinc-100 dark:border-zinc-800 dark:bg-zinc-900',
        heightClass,
        className
      )}
    >
      {error && (
        <div className="absolute inset-0 z-[1] flex items-center justify-center bg-white/85 p-4 text-center text-sm text-foreground-muted backdrop-blur dark:bg-zinc-900/85">
          <div>
            <p className="font-medium text-foreground">Карта временно недоступна</p>
            <p className="mt-1 text-xs">{error}. Откройте адреса в Яндекс.Картах вручную.</p>
          </div>
        </div>
      )}
    </div>
  );
}
