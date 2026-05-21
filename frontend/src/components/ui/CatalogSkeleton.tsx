import { Skeleton } from './Loading';

/** Скелетон списка товаров каталога при загрузке */
export function CatalogSkeleton() {
  return (
    <div className="grid grid-cols-2 gap-3 sm:gap-4 md:grid-cols-3 lg:grid-cols-3">
      {Array.from({ length: 8 }).map((_, i) => (
        <div
          key={i}
          className="flex flex-col overflow-hidden rounded-xl border border-border bg-white"
        >
          <Skeleton className="aspect-square w-full" />
          <div className="flex flex-1 flex-col gap-2 p-3">
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-4 w-1/2" />
            <Skeleton className="mt-auto h-6 w-20" />
          </div>
        </div>
      ))}
    </div>
  );
}
