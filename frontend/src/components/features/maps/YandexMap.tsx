'use client';

import { useEffect, useRef, useState } from 'react';
import Script from 'next/script';
import { cn } from '@/lib/theme/utils';

declare global {
  interface Window {
    ymaps?: any;
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

interface YandexMapProps {
  markers: YandexMapMarker[];
  center?: [number, number];
  zoom?: number;
  className?: string;
  onMarkerClick?: (id: string) => void;
}

export function YandexMap({
  markers,
  center,
  zoom = 11,
  className,
  onMarkerClick,
}: YandexMapProps) {
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const [shouldLoadScript, setShouldLoadScript] = useState(false);

  useEffect(() => {
    const node = mapContainerRef.current;
    if (!node) return;
    const observer = new IntersectionObserver(
      entries => {
        if (entries.some(e => e.isIntersecting)) {
          setShouldLoadScript(true);
          observer.disconnect();
        }
      },
      { rootMargin: '200px' }
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!shouldLoadScript || !window.ymaps || !mapContainerRef.current) {
      return;
    }

    let mapInstance: any;

    window.ymaps.ready(() => {
      const first = markers[0];
      const mapCenter: [number, number] = center ?? first?.coordinates ?? VLADIKAVKAZ_CENTER;

      mapInstance =
        (mapContainerRef.current as any)._ymap ??
        new window.ymaps.Map(mapContainerRef.current, {
          center: mapCenter,
          zoom,
          controls: ['zoomControl'],
        });

      (mapContainerRef.current as any)._ymap = mapInstance;

      mapInstance.geoObjects.removeAll();

      markers.forEach(marker => {
        const placemark = new window.ymaps.Placemark(
          marker.coordinates,
          {
            balloonContentHeader: marker.title,
            balloonContentBody: marker.description,
          },
          {
            preset: marker.selected ? 'islands#redIcon' : 'islands#blueIcon',
          }
        );

        if (onMarkerClick) {
          placemark.events.add('click', () => onMarkerClick(marker.id));
        }

        mapInstance.geoObjects.add(placemark);
      });

      if (markers.length > 1) {
        const lats = markers.map(m => m.coordinates[0]);
        const lons = markers.map(m => m.coordinates[1]);
        const bounds: [[number, number], [number, number]] = [
          [Math.min(...lats), Math.min(...lons)],
          [Math.max(...lats), Math.max(...lons)],
        ];
        mapInstance.setBounds(bounds, { checkZoomRange: true, zoomMargin: 30 });
      } else {
        mapInstance.setCenter(mapCenter, zoom);
      }
    });

    return () => {
      /* карту не уничтожаем, чтобы не мигала при ре-рендерах */
    };
  }, [markers, center, zoom, onMarkerClick, shouldLoadScript]);

  const apiKey = process.env.NEXT_PUBLIC_YANDEX_MAPS_API_KEY;

  return (
    <>
      {apiKey && shouldLoadScript && (
        <Script
          src={`https://api-maps.yandex.ru/2.1/?lang=ru_RU&apikey=${apiKey}`}
          strategy="lazyOnload"
        />
      )}
      <div
        ref={mapContainerRef}
        data-testid="yandex-map-container"
        className={cn(
          'h-72 w-full overflow-hidden rounded-2xl border border-zinc-200 dark:border-zinc-800',
          className
        )}
      />
    </>
  );
}
