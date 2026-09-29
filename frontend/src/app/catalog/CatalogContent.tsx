'use client';

import {
  Suspense,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from 'react';
import Link from 'next/link';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { useInView } from 'react-intersection-observer';
import {
  ChevronDown,
  ChevronRight,
  Filter,
  PackageSearch,
  Search,
  SlidersHorizontal,
  Star,
  X,
} from 'lucide-react';
import type { Category, PaginatedResponse, Product } from '@/types';
import type { ProductFilters } from '@/lib/api/services/products.service';
import { stripDescriptionHtml } from '@/lib/format-description';

import { CatalogSearchBar } from '@/components/catalog/CatalogSearchBar';
import { useProducts, useCategories, useBrands, useProductModels } from '@/lib/hooks/useProducts';
import type { ProductModelOption } from '@/lib/api/services/products.service';
import { ProductCard } from '@/components/features/products/ProductCard';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Loading } from '@/components/ui/Loading';
import { CatalogSkeleton } from '@/components/ui/CatalogSkeleton';
import { MissingProductForm } from '@/components/features/crm/MissingProductForm';
import { getFriendlyErrorMessage } from '@/lib/errors';
import { Chip, ChipList } from '@/components/ui/Chip';
import { FilterChoiceChips } from '@/components/ui/FilterChoiceChips';
import { CURRENCY_SYMBOL } from '@/lib/constants';
import { cn } from '@/lib/theme/utils';
import {
  readRecentlyViewedProducts,
  recentSnapshotToProduct,
  type RecentProductSnapshot,
} from '@/lib/recently-viewed-products';
import { dedupeById } from '@/lib/dedupe-by-id';
import { PageContainer } from '@/components/layout/PageContainer';
import { PRODUCT_CARD_GRID_CLASS } from '@/lib/theme/spacing';

type Ordering = NonNullable<ProductFilters['ordering']>;

const ORDER_LABELS: Record<Ordering, string> = {
  popular: 'По популярности',
  created_at: 'Сначала новинки',
  price_asc: 'Сначала дешевле',
  price_desc: 'Сначала дороже',
  rating_desc: 'По рейтингу',
};

function parseOrdering(raw: string | null): Ordering {
  if (
    raw === 'price_asc' ||
    raw === 'price_desc' ||
    raw === 'rating_desc' ||
    raw === 'created_at' ||
    raw === 'popular'
  ) {
    return raw;
  }
  return 'popular';
}

function categoryTrail(slug: string, categories: Category[]): Category[] {
  const byId = new Map(categories.map(c => [c.id, c]));
  const bySlug = new Map(categories.map(c => [c.slug, c]));
  const trail: Category[] = [];
  let current = bySlug.get(slug);
  let guard = 0;
  while (current && guard < 20) {
    trail.unshift(current);
    current = current.parent ? byId.get(current.parent) : undefined;
    guard += 1;
  }
  return trail;
}

function FilterAccordion({
  title,
  defaultOpen = false,
  children,
}: {
  title: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <details
      className="group border-b border-border py-1"
      open={open}
      onToggle={e => setOpen(e.currentTarget.open)}
    >
      <summary className="flex cursor-pointer list-none items-center justify-between gap-2 py-2 text-sm font-medium text-foreground marker:hidden">
        <span className="flex items-center gap-2">
          <ChevronRight
            className={cn(
              'h-4 w-4 shrink-0 text-emerald-700 transition-transform',
              open && 'rotate-90'
            )}
          />
          {title}
        </span>
      </summary>
      <div className="pb-3 pt-1">{children}</div>
    </details>
  );
}

interface FilterFieldsProps {
  categories: Category[];
  brands: string[];
  brandQuery: string;
  setBrandQuery: (v: string) => void;
  category: string;
  setCategorySlug: (slug: string) => void;
  brand: string;
  setBrand: (b: string) => void;
  minDraft: string;
  setMinDraft: (v: string) => void;
  maxDraft: string;
  setMaxDraft: (v: string) => void;
  inStock: boolean;
  setInStock: (v: boolean) => void;
  ratingMin: number | null;
  setRatingMin: (v: number | null) => void;
}

function FilterFields({
  categories,
  brands,
  brandQuery,
  setBrandQuery,
  category,
  setCategorySlug,
  brand,
  setBrand,
  minDraft,
  setMinDraft,
  maxDraft,
  setMaxDraft,
  inStock,
  setInStock,
  ratingMin,
  setRatingMin,
}: FilterFieldsProps) {
  const filteredBrands = useMemo(() => {
    const q = brandQuery.trim().toLowerCase();
    if (!q) return brands;
    return brands.filter(b => b.toLowerCase().includes(q));
  }, [brands, brandQuery]);

  const inStockId = 'filter-in-stock';

  const categoryOptions = useMemo(
    () => categories.map((c: Category) => ({ value: c.slug, label: c.title })),
    [categories]
  );

  const brandOptions = useMemo(
    () => filteredBrands.map(b => ({ value: b, label: b })),
    [filteredBrands]
  );

  return (
    <div className="space-y-1">
      <FilterAccordion title="Категория" defaultOpen={true}>
        <FilterChoiceChips
          options={categoryOptions}
          value={category}
          onChange={setCategorySlug}
          allLabel="Все категории"
        />
      </FilterAccordion>

      <FilterAccordion title="Бренд" defaultOpen={Boolean(brand)}>
        {brands.length > 8 && (
          <Input
            type="search"
            placeholder="Поиск бренда..."
            value={brandQuery}
            onChange={e => setBrandQuery(e.target.value)}
            className="mb-3 w-full"
          />
        )}
        {brandOptions.length === 0 ? (
          <p className="text-xs text-foreground-muted">Нет совпадений</p>
        ) : (
          <FilterChoiceChips
            options={brandOptions}
            value={brand}
            onChange={setBrand}
            allLabel="Все бренды"
          />
        )}
      </FilterAccordion>

      <FilterAccordion title={`Цена, ${CURRENCY_SYMBOL}`}>
        <div className="flex gap-2">
          <Input
            type="number"
            inputMode="numeric"
            placeholder="От"
            value={minDraft}
            onChange={e => setMinDraft(e.target.value)}
            min={0}
            className="w-full"
          />
          <Input
            type="number"
            inputMode="numeric"
            placeholder="До"
            value={maxDraft}
            onChange={e => setMaxDraft(e.target.value)}
            min={0}
            className="w-full"
          />
        </div>
      </FilterAccordion>

      <FilterAccordion title="Рейтинг">
        <p className="mb-2 text-xs text-foreground-muted">Минимум звёзд</p>
        <div className="flex gap-1">
          {[1, 2, 3, 4, 5].map(n => (
            <button
              key={n}
              type="button"
              onClick={() => setRatingMin(ratingMin === n ? null : n)}
              className="inline-flex min-h-[44px] min-w-[44px] touch-manipulation items-center justify-center rounded-md transition-colors hover:bg-amber-50 lg:min-h-0 lg:min-w-0"
              aria-label={`От ${n} звёзд`}
            >
              <Star
                className={cn(
                  'h-7 w-7 sm:h-8 sm:w-8',
                  ratingMin != null && n <= ratingMin
                    ? 'fill-amber-400 text-amber-400'
                    : 'text-zinc-300'
                )}
              />
            </button>
          ))}
        </div>
      </FilterAccordion>

      <FilterAccordion title="Наличие">
        <label className="flex cursor-pointer items-center gap-2 text-sm">
          <input
            type="checkbox"
            id={inStockId}
            checked={inStock}
            onChange={e => setInStock(e.target.checked)}
            className="h-4 w-4 rounded border-border text-emerald-700 focus:ring-emerald-600"
          />
          <span>Только в наличии</span>
        </label>
      </FilterAccordion>
    </div>
  );
}

function categoryPageHref(slug: string): string {
  return `/catalog/category/${encodeURIComponent(slug)}`;
}

export interface CatalogContentProps {
  /** Фиксированная категория из ЧПУ /catalog/category/{slug} */
  categorySlugFromPath?: string;
  /** SSR-первая страница товаров для категории */
  initialProductsPage?: PaginatedResponse<Product>;
  /** SSR-список категорий для фильтра (совпадает с HTML сервера, без hydration mismatch) */
  initialCategories?: Category[];
  /** SSR-список брендов для фильтра */
  initialBrands?: string[];
}

function CatalogInner({
  categorySlugFromPath,
  initialProductsPage,
  initialCategories,
  initialBrands,
}: CatalogContentProps) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const urlSearch = searchParams.get('search') ?? '';
  const category = categorySlugFromPath ?? searchParams.get('category') ?? '';
  const catalogBasePath = categorySlugFromPath
    ? categoryPageHref(categorySlugFromPath)
    : pathname;
  const brand = searchParams.get('brand') ?? '';
  const model = searchParams.get('model') ?? '';
  const minUrl = searchParams.get('min_price') ?? '';
  const maxUrl = searchParams.get('max_price') ?? '';
  const inStock = ['1', 'true', 'yes'].includes(
    (searchParams.get('in_stock') ?? '').toLowerCase()
  );
  const ordering = parseOrdering(searchParams.get('ordering'));
  const ratingMinUrl = searchParams.get('rating_min');
  const ratingMin =
    ratingMinUrl != null && ratingMinUrl !== '' && !Number.isNaN(Number(ratingMinUrl))
      ? Number(ratingMinUrl)
      : null;
  const storeSlug = searchParams.get('store') ?? '';

  const [searchInput, setSearchInput] = useState(urlSearch);
  const [minDraft, setMinDraft] = useState(minUrl);
  const [maxDraft, setMaxDraft] = useState(maxUrl);
  const [brandQuery, setBrandQuery] = useState('');
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [sortOpen, setSortOpen] = useState(false);
  const [seoOpen, setSeoOpen] = useState(false);

  const [recentSnapshots, setRecentSnapshots] = useState<RecentProductSnapshot[]>([]);

  useEffect(() => {
    setSearchInput(urlSearch);
  }, [urlSearch]);

  useEffect(() => {
    setMinDraft(minUrl);
    setMaxDraft(maxUrl);
  }, [minUrl, maxUrl]);

  useEffect(() => {
    setRecentSnapshots(readRecentlyViewedProducts());
    const onRecent = () => setRecentSnapshots(readRecentlyViewedProducts());
    window.addEventListener('ringoo-recent-products', onRecent);
    return () => window.removeEventListener('ringoo-recent-products', onRecent);
  }, []);

  const replaceQuery = useCallback(
    (mutate: (p: URLSearchParams) => void) => {
      const p = new URLSearchParams(searchParams.toString());
      mutate(p);
      if (categorySlugFromPath) p.delete('category');
      const qs = p.toString();
      router.replace(qs ? `${catalogBasePath}?${qs}` : catalogBasePath, { scroll: false });
    },
    [router, catalogBasePath, searchParams, categorySlugFromPath]
  );

  useEffect(() => {
    const h = setTimeout(() => {
      if (minDraft === minUrl && maxDraft === maxUrl) return;
      replaceQuery(p => {
        if (minDraft !== minUrl) {
          if (minDraft) p.set('min_price', minDraft);
          else p.delete('min_price');
        }
        if (maxDraft !== maxUrl) {
          if (maxDraft) p.set('max_price', maxDraft);
          else p.delete('max_price');
        }
      });
    }, 300);
    return () => clearTimeout(h);
  }, [minDraft, maxDraft, minUrl, maxUrl, replaceQuery]);

  const setCategorySlug = useCallback(
    (slug: string) => {
      if (categorySlugFromPath) {
        const p = new URLSearchParams(searchParams.toString());
        p.delete('category');
        p.delete('model');
        const qs = p.toString();
        if (!slug) {
          router.replace(qs ? `/catalog?${qs}` : '/catalog', { scroll: false });
          return;
        }
        router.replace(
          qs ? `${categoryPageHref(slug)}?${qs}` : categoryPageHref(slug),
          { scroll: false }
        );
        return;
      }
      replaceQuery(p => {
        if (slug) p.set('category', slug);
        else p.delete('category');
        p.delete('model');
      });
    },
    [categorySlugFromPath, replaceQuery, router, searchParams]
  );

  const setBrand = useCallback(
    (b: string) => {
      replaceQuery(p => {
        if (b) p.set('brand', b);
        else p.delete('brand');
        p.delete('model');
      });
    },
    [replaceQuery]
  );

  const setModel = useCallback(
    (key: string) => {
      replaceQuery(p => {
        if (key) p.set('model', key);
        else p.delete('model');
      });
    },
    [replaceQuery]
  );

  const setInStock = useCallback(
    (v: boolean) => {
      replaceQuery(p => {
        if (v) p.set('in_stock', '1');
        else p.delete('in_stock');
      });
    },
    [replaceQuery]
  );

  const setOrdering = useCallback(
    (o: Ordering) => {
      replaceQuery(p => {
        if (o === 'popular') p.delete('ordering');
        else p.set('ordering', o);
      });
    },
    [replaceQuery]
  );

  const setRatingMin = useCallback(
    (n: number | null) => {
      replaceQuery(p => {
        if (n != null) p.set('rating_min', String(n));
        else p.delete('rating_min');
      });
    },
    [replaceQuery]
  );

  const filters: ProductFilters = useMemo(
    () => ({
      search: urlSearch.trim() || undefined,
      category: category || undefined,
      brand: brand || undefined,
      min_price: minUrl ? Number(minUrl) : undefined,
      max_price: maxUrl ? Number(maxUrl) : undefined,
      in_stock: inStock || undefined,
      store: storeSlug.trim() || undefined,
      ordering,
      model: model || undefined,
      rating_min: ratingMin != null ? ratingMin : undefined,
    }),
    [urlSearch, category, brand, model, minUrl, maxUrl, inStock, storeSlug, ordering, ratingMin]
  );

  const modelFilterParams = useMemo(
    () => ({
      search: urlSearch.trim() || undefined,
      category: category || undefined,
      brand: brand || undefined,
      min_price: minUrl ? Number(minUrl) : undefined,
      max_price: maxUrl ? Number(maxUrl) : undefined,
      in_stock: inStock || undefined,
      store: storeSlug.trim() || undefined,
      rating_min: ratingMin != null ? ratingMin : undefined,
    }),
    [urlSearch, category, brand, minUrl, maxUrl, inStock, storeSlug, ratingMin]
  );

  const { data: productModels = [], isLoading: modelsLoading } = useProductModels(
    modelFilterParams
  );

  const hasExtraFilters =
    Boolean(
      brand || model || minUrl || maxUrl || urlSearch.trim() || inStock || storeSlug || ratingMin
    );

  const { data, fetchNextPage, hasNextPage, isFetchingNextPage, isLoading, isError, error } =
    useProducts(filters, {
      initialData:
        initialProductsPage &&
        !hasExtraFilters &&
        !urlSearch.trim() &&
        !category &&
        ordering === 'popular'
          ? { pages: [initialProductsPage], pageParams: [1] }
          : categorySlugFromPath &&
              initialProductsPage &&
              !hasExtraFilters &&
              ordering === 'popular'
            ? { pages: [initialProductsPage], pageParams: [1] }
            : undefined,
    });

  const { data: categories = initialCategories ?? [] } = useCategories({
    initialData: initialCategories,
  });
  const { data: brands = initialBrands ?? [] } = useBrands({
    initialData: initialBrands,
  });

  const { ref, inView } = useInView({ threshold: 0.1 });
  useEffect(() => {
    if (inView && hasNextPage && !isFetchingNextPage) fetchNextPage();
  }, [inView, hasNextPage, isFetchingNextPage, fetchNextPage]);

  const products = useMemo(
    () => dedupeById(data?.pages.flatMap(p => p.results) ?? []),
    [data]
  );
  const totalCount = data?.pages[0]?.count ?? 0;

  const trail = useMemo(
    () => (category ? categoryTrail(category, categories) : []),
    [category, categories]
  );

  const activeCategory = trail[trail.length - 1];
  const pageTitle = activeCategory?.title ?? 'Каталог товаров';
  const categorySeoDescription = stripDescriptionHtml(activeCategory?.description);

  const applySearch = useCallback(
    (query?: string) => {
      const trimmed = (query ?? searchInput).trim();
      replaceQuery(p => {
        if (trimmed) p.set('search', trimmed);
        else p.delete('search');
      });
    },
    [searchInput, replaceQuery]
  );

  const clearAllFilters = useCallback(() => {
    setBrandQuery('');
    setSearchInput('');
    setMinDraft('');
    setMaxDraft('');
    router.replace('/catalog', { scroll: false });
  }, [router]);

  const activeFilters = useMemo(() => {
    const list: { key: string; label: string; onClear: () => void }[] = [];
    if (urlSearch.trim()) {
      list.push({
        key: 'search',
        label: `Поиск: ${urlSearch.trim()}`,
        onClear: () =>
          replaceQuery(p => {
            p.delete('search');
          }),
      });
    }
    if (category && activeCategory) {
      list.push({
        key: 'category',
        label: activeCategory.title,
        onClear: () => setCategorySlug(''),
      });
    }
    if (storeSlug.trim()) {
      list.push({
        key: 'store',
        label: `Магазин: ${storeSlug}`,
        onClear: () =>
          replaceQuery(p => {
            p.delete('store');
          }),
      });
    }
    if (brand) {
      list.push({
        key: 'brand',
        label: `Бренд: ${brand}`,
        onClear: () =>
          replaceQuery(p => {
            p.delete('brand');
            p.delete('model');
          }),
      });
    }
    if (model) {
      const modelLabel = productModels.find(m => m.key === model)?.label ?? model;
      list.push({
        key: 'model',
        label: `Модель: ${modelLabel}`,
        onClear: () =>
          replaceQuery(p => {
            p.delete('model');
          }),
      });
    }
    if (minUrl) {
      list.push({
        key: 'min_price',
        label: `От ${minUrl} ${CURRENCY_SYMBOL}`,
        onClear: () => {
          setMinDraft('');
          replaceQuery(p => p.delete('min_price'));
        },
      });
    }
    if (maxUrl) {
      list.push({
        key: 'max_price',
        label: `До ${maxUrl} ${CURRENCY_SYMBOL}`,
        onClear: () => {
          setMaxDraft('');
          replaceQuery(p => p.delete('max_price'));
        },
      });
    }
    if (inStock) {
      list.push({
        key: 'in_stock',
        label: 'В наличии',
        onClear: () =>
          replaceQuery(p => {
            p.delete('in_stock');
          }),
      });
    }
    if (ratingMin != null) {
      list.push({
        key: 'rating_min',
        label: `Рейтинг от ${ratingMin}`,
        onClear: () =>
          replaceQuery(p => {
            p.delete('rating_min');
          }),
      });
    }
    if (ordering !== 'popular') {
      list.push({
        key: 'ordering',
        label: `Сортировка: ${ORDER_LABELS[ordering]}`,
        onClear: () =>
          replaceQuery(p => {
            p.delete('ordering');
          }),
      });
    }
    return list;
  }, [
    urlSearch,
    category,
    activeCategory,
    brand,
    model,
    productModels,
    minUrl,
    maxUrl,
    inStock,
    ratingMin,
    ordering,
    replaceQuery,
    setCategorySlug,
    storeSlug,
  ]);

  const sortControl = (
    <div className="relative">
      <button
        type="button"
        onClick={() => setSortOpen(v => !v)}
        className="flex min-h-[44px] w-full min-w-0 touch-manipulation items-center justify-between gap-2 rounded-lg border border-border bg-white px-3 py-2 text-sm text-foreground sm:min-w-[200px] sm:w-auto lg:min-h-0"
      >
        {ORDER_LABELS[ordering]}
        <ChevronDown className="h-4 w-4 shrink-0" />
      </button>
      {sortOpen && (
        <>
          <div className="fixed inset-0 z-10" aria-hidden onClick={() => setSortOpen(false)} />
          <ul className="absolute right-0 top-full z-20 mt-1 max-h-72 w-full min-w-[220px] overflow-auto rounded-lg border border-border bg-white py-1 shadow-lg sm:left-0 sm:right-auto">
            {(Object.keys(ORDER_LABELS) as Ordering[]).map(key => (
              <li key={key}>
                <button
                  type="button"
                  onClick={() => {
                    setOrdering(key);
                    setSortOpen(false);
                  }}
                  className={cn(
                    'min-h-[44px] w-full touch-manipulation px-3 py-2 text-left text-sm text-foreground lg:min-h-0',
                    ordering === key ? 'bg-zinc-100 font-medium' : 'hover:bg-zinc-50 active:bg-zinc-100'
                  )}
                >
                  {ORDER_LABELS[key]}
                </button>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );

  return (
    <div className="min-h-screen min-w-0 overflow-x-hidden bg-background">
      <PageContainer wide className="min-w-0 py-6">
        {/* Хлебные крошки — десктоп */}
        <nav
          className="mb-4 hidden flex-wrap items-center gap-2 text-sm text-foreground-muted sm:flex"
          aria-label="Хлебные крошки"
        >
          <Link href="/" className="hover:text-foreground">
            Главная
          </Link>
          <span aria-hidden>/</span>
          <Link href="/catalog" className="hover:text-foreground">
            Каталог
          </Link>
          {trail.map(c => (
            <span key={c.id} className="flex items-center gap-2">
              <span aria-hidden>/</span>
              <Link
                href={categoryPageHref(c.slug)}
                className="hover:text-foreground"
              >
                {c.title}
              </Link>
            </span>
          ))}
        </nav>

        {/* Мобильные крошки */}
        <details className="mb-4 sm:hidden">
          <summary className="cursor-pointer list-none rounded-lg border border-border bg-white px-3 py-2 text-sm font-medium text-foreground marker:hidden">
            <span className="flex items-center justify-between gap-2">
              Навигация: {pageTitle}
              <ChevronDown className="h-4 w-4" />
            </span>
          </summary>
          <div className="mt-2 space-y-1 rounded-lg border border-border bg-white p-3 text-sm">
            <Link href="/" className="block py-1 text-foreground-muted hover:text-foreground">
              Главная
            </Link>
            <Link href="/catalog" className="block py-1 text-foreground-muted hover:text-foreground">
              Каталог
            </Link>
            {trail.map(c => (
              <Link
                key={c.id}
                href={categoryPageHref(c.slug)}
                className="block py-1 pl-2 text-foreground-muted hover:text-foreground"
              >
                {c.title}
              </Link>
            ))}
          </div>
        </details>

        <div className="mb-6 flex items-start gap-3 rounded-lg border border-border bg-zinc-50 px-4 py-3 text-sm text-foreground-muted">
          <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-zinc-200 text-xs font-semibold text-foreground">
            i
          </span>
          <div>
            <p>Цены могут меняться в течение дня.</p>
            <p>Стоимость фиксируется только после внесения оплаты.</p>
          </div>
        </div>

        <header className="mb-6">
          <h1 className="text-2xl font-semibold text-foreground sm:text-3xl">{pageTitle}</h1>
          {category && categorySeoDescription && (
            <p className="mt-2 max-w-3xl text-sm text-foreground-muted line-clamp-3 sm:line-clamp-none">
              {categorySeoDescription.slice(0, 200)}
              {categorySeoDescription.length > 200 ? '…' : ''}
            </p>
          )}
        </header>

        <div className="mb-6 w-full min-w-0 space-y-3">
          <CatalogSearchBar
            value={searchInput}
            onChange={setSearchInput}
            onApply={q => {
              setSearchInput(q);
              applySearch(q);
            }}
            onPickSuggestion={title => {
              setSearchInput(title);
              applySearch(title);
            }}
          />
          <div className="flex min-w-0 w-full flex-col gap-2 sm:flex-row sm:items-center sm:justify-end">
            {sortControl}
            <Button
              variant="secondary"
              size="sm"
              className="lg:hidden"
              onClick={() => setFiltersOpen(true)}
            >
              <SlidersHorizontal className="h-4 w-4" />
              Фильтры
            </Button>
          </div>
        </div>

        {activeFilters.length > 0 && (
          <div className="mb-4 flex flex-wrap items-center gap-2">
            <div className="-mx-1 max-w-full overflow-x-auto px-1 pb-1">
              <ChipList className="flex-nowrap">
                {activeFilters.map(({ key, label, onClear }) => (
                  <Chip key={key} variant="removable" onRemove={onClear}>
                    {label}
                  </Chip>
                ))}
              </ChipList>
            </div>
            <button
              type="button"
              onClick={clearAllFilters}
              className="shrink-0 text-sm text-foreground-muted underline hover:text-foreground"
            >
              Сбросить все
            </button>
          </div>
        )}

        <div className="flex gap-6 lg:gap-8">
          <aside className="hidden w-[280px] shrink-0 lg:block">
            <div className="sticky top-4 rounded-xl border border-border bg-white p-4 shadow-sm">
              <h2 className="mb-2 flex items-center gap-2 text-base font-semibold">
                <Filter className="h-4 w-4 text-emerald-700" />
                Фильтры
              </h2>
              <FilterFields
                categories={categories}
                brands={brands}
                brandQuery={brandQuery}
                setBrandQuery={setBrandQuery}
                category={category}
                setCategorySlug={setCategorySlug}
                brand={brand}
                setBrand={setBrand}
                minDraft={minDraft}
                setMinDraft={setMinDraft}
                maxDraft={maxDraft}
                setMaxDraft={setMaxDraft}
                inStock={inStock}
                setInStock={setInStock}
                ratingMin={ratingMin}
                setRatingMin={setRatingMin}
              />
              <Button
                type="button"
                variant="outline"
                className="mt-4 w-full"
                onClick={clearAllFilters}
              >
                Сбросить все фильтры
              </Button>
            </div>
          </aside>

          <main className="min-w-0 flex-1">
            <p className="mb-4 text-sm text-foreground-muted">Найдено: {totalCount}</p>

            {(category || brand) && (
              <div className="mb-4 min-w-0 max-w-full">
                <p className="mb-2 text-sm font-semibold text-foreground">Модель</p>
                {modelsLoading ? (
                  <p className="text-xs text-foreground-muted">Загрузка моделей…</p>
                ) : productModels.length === 0 ? (
                  <p className="text-xs text-foreground-muted">
                    Нет линеек для текущей выборки. Смените категорию или бренд.
                  </p>
                ) : (
                  <div className="-mx-1 max-w-full overflow-x-auto overscroll-x-contain px-1 pb-1">
                    <FilterChoiceChips
                      className="min-w-max flex-nowrap"
                      options={productModels.map(m => ({
                        value: m.key,
                        label: `${m.label} (${m.count})`,
                      }))}
                      value={model}
                      onChange={setModel}
                      allLabel="Все модели"
                    />
                  </div>
                )}
              </div>
            )}

            {isLoading ? (
              <CatalogSkeleton />
            ) : isError ? (
              <div className="rounded-lg border border-danger/30 bg-danger/5 p-4 text-danger">
                {getFriendlyErrorMessage(error)}
              </div>
            ) : products.length === 0 ? (
              <div className="flex flex-col items-center rounded-xl border border-border bg-white px-6 py-12 text-center shadow-sm">
                <div
                  className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-zinc-100 text-zinc-500"
                  aria-hidden
                >
                  <PackageSearch className="h-8 w-8" />
                </div>
                <p className="max-w-md text-foreground-muted">
                  По вашему запросу ничего не найдено. Попробуйте изменить фильтры или поиск.
                </p>
                <Button type="button" className="mt-6" onClick={clearAllFilters}>
                  Сбросить фильтры
                </Button>
                <Link
                  href="/catalog"
                  className="mt-3 text-sm font-medium text-emerald-700 hover:underline"
                >
                  Открыть весь каталог
                </Link>
              </div>
            ) : (
              <>
                <div className={PRODUCT_CARD_GRID_CLASS}>
                  {products.map((product, i) => (
                    <ProductCard
                      key={product.id}
                      product={product}
                      priority={i < 4}
                      className="h-full"
                    />
                  ))}
                </div>
                <div ref={ref} className="h-10 w-full" aria-hidden />
                {isFetchingNextPage && (
                  <div className="flex justify-center py-6">
                    <Loading />
                  </div>
                )}
                {hasNextPage && !isFetchingNextPage && (
                  <div className="flex justify-center py-4">
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => fetchNextPage()}
                    >
                      Загрузить ещё
                    </Button>
                  </div>
                )}
              </>
            )}
          </main>
        </div>

        {recentSnapshots.length > 0 && (
          <section className="mt-12 border-t border-border pt-10">
            <h2 className="mb-4 text-lg font-semibold text-foreground">Вы смотрели ранее</h2>
            <div className={PRODUCT_CARD_GRID_CLASS}>
              {recentSnapshots.map((s, i) => (
                <ProductCard
                  key={s.id}
                  product={recentSnapshotToProduct(s)}
                  priority={i === 0}
                  className="h-full"
                />
              ))}
            </div>
          </section>
        )}

        <div className="mt-12 space-y-6 border-t border-border pt-10">
          <MissingProductForm />
          <div className="rounded-xl border border-border bg-white p-4 shadow-sm">
            <h2 className="mb-3 hidden text-base font-semibold text-foreground sm:block">
              О каталоге Ringoo
            </h2>
            <details
              className="sm:hidden"
              open={seoOpen}
              onToggle={e => setSeoOpen((e.target as HTMLDetailsElement).open)}
            >
              <summary className="cursor-pointer list-none text-base font-semibold text-foreground marker:hidden">
                <span className="flex items-center justify-between gap-2">
                  О каталоге Ringoo
                  <ChevronDown className="h-4 w-4" />
                </span>
              </summary>
              <div className="mt-3 text-sm leading-relaxed text-foreground-muted">
                <p>
                  Каталог Ringoo — смартфоны, планшеты, наушники, ноутбуки и аксессуары с доставкой
                  и самовывозом. Удобные фильтры по цене, бренду и рейтингу помогут быстро выбрать
                  технику. Рассрочка 0%, актуальные цены и отзывы покупателей — всё для уверенной
                  покупки онлайн и в магазинах сети.
                </p>
                {categorySeoDescription && (
                  <p className="mt-3 border-t border-border pt-3">{categorySeoDescription}</p>
                )}
              </div>
            </details>
            <div className="hidden text-sm leading-relaxed text-foreground-muted sm:block">
              <p>
                Каталог Ringoo — смартфоны, планшеты, наушники, ноутбуки и аксессуары с доставкой и
                самовывозом. Удобные фильтры по цене, бренду и рейтингу помогут быстро выбрать
                технику. Рассрочка 0%, актуальные цены и отзывы покупателей — всё для уверенной
                покупки онлайн и в магазинах сети.
              </p>
              {categorySeoDescription && (
                <p className="mt-3 border-t border-border pt-3">{categorySeoDescription}</p>
              )}
            </div>
          </div>
        </div>
      </PageContainer>

      {filtersOpen && (
        <>
          <div
            className="fixed inset-0 z-40 bg-black/50 lg:hidden"
            aria-hidden
            onClick={() => setFiltersOpen(false)}
          />
          <div className="fixed inset-y-0 left-0 z-50 w-full max-w-[min(100vw,360px)] overflow-y-auto border-r border-border bg-white shadow-xl lg:hidden">
            <div className="sticky top-0 z-10 flex items-center justify-between border-b border-border bg-white px-4 py-3">
              <h2 className="text-base font-semibold">Фильтры</h2>
              <button
                type="button"
                onClick={() => setFiltersOpen(false)}
                className="inline-flex min-h-[44px] min-w-[44px] touch-manipulation items-center justify-center rounded-lg hover:bg-zinc-100"
                aria-label="Закрыть"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="p-4">
              <FilterFields
                categories={categories}
                brands={brands}
                brandQuery={brandQuery}
                setBrandQuery={setBrandQuery}
                category={category}
                setCategorySlug={setCategorySlug}
                brand={brand}
                setBrand={setBrand}
                minDraft={minDraft}
                setMinDraft={setMinDraft}
                maxDraft={maxDraft}
                setMaxDraft={setMaxDraft}
                inStock={inStock}
                setInStock={setInStock}
                ratingMin={ratingMin}
                setRatingMin={setRatingMin}
              />
              <div className="mt-6 flex flex-col gap-2">
                <Button className="w-full" onClick={() => setFiltersOpen(false)}>
                  Применить
                </Button>
                <Button type="button" variant="outline" className="w-full" onClick={clearAllFilters}>
                  Сбросить все
                </Button>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export function CatalogContent(props: CatalogContentProps = {}) {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-[50vh] items-center justify-center">
          <Loading />
        </div>
      }
    >
      <CatalogInner {...props} />
    </Suspense>
  );
}
