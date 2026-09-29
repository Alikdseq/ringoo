'use client';

import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useRef,
  useState,
} from 'react';
import Image from 'next/image';
import { useRouter } from 'next/navigation';
import { Search, X } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { getProductAutocomplete } from '@/lib/api/services/products.service';
import { CURRENCY_SYMBOL } from '@/lib/constants';
import { getMediaUrl } from '@/lib/image-url';
import { HEADER_ICON_BUTTON_CLASS } from '@/lib/theme/spacing';
import { cn } from '@/lib/theme/utils';

const DEBOUNCE_MS = 300;
const MIN_LENGTH = 2;

export type HeaderSearchHandle = {
  openMobilePanel: () => void;
};

export const HeaderSearch = forwardRef<HeaderSearchHandle, object>(function HeaderSearch(
  _props,
  ref
) {
  const router = useRouter();
  const [query, setQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useImperativeHandle(ref, () => ({
    openMobilePanel: () => setMobileOpen(true),
  }));

  useEffect(() => {
    const t = setTimeout(() => setDebouncedQuery(query.trim()), DEBOUNCE_MS);
    return () => clearTimeout(t);
  }, [query]);

  const { data: results = [], isLoading } = useQuery({
    queryKey: ['products', 'autocomplete', debouncedQuery],
    queryFn: () => getProductAutocomplete(debouncedQuery),
    enabled: debouncedQuery.length >= MIN_LENGTH,
    staleTime: 60 * 1000,
  });

  const showDropdown = debouncedQuery.length >= MIN_LENGTH && (isOpen || results.length > 0);
  const closeDropdown = useCallback(() => {
    setIsOpen(false);
    setMobileOpen(false);
  }, []);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(e.target as Node) &&
        !(e.target as HTMLElement).closest?.('[data-header-search-input]')
      ) {
        closeDropdown();
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [closeDropdown]);

  const handleSelect = useCallback(
    (slug: string) => {
      closeDropdown();
      setQuery('');
      setDebouncedQuery('');
      router.push(`/products/${slug}`);
      setMobileOpen(false);
    },
    [closeDropdown, router]
  );

  return (
    <>
      {/* Десктоп: поле поиска в шапке */}
      <div
        className="relative hidden w-44 shrink-0 lg:block xl:w-52"
        ref={dropdownRef}
      >
        <div className="relative">
          <Search className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-foreground-muted" />
          <input
            ref={inputRef}
            data-header-search-input
            type="search"
            role="combobox"
            placeholder="Поиск товаров..."
            value={query}
            onChange={e => setQuery(e.target.value)}
            onFocus={() => setIsOpen(true)}
            className="w-full rounded-full border border-border bg-zinc-50 py-2.5 pl-10 pr-4 text-base text-foreground placeholder:text-foreground-muted focus:border-brand focus:outline-none focus:ring-1 focus:ring-brand"
            aria-label="Поиск по каталогу"
            aria-autocomplete="list"
            aria-expanded={showDropdown}
            aria-controls="header-search-listbox"
            id="header-search-input"
          />
        </div>
        {showDropdown && (
          <div
            id="header-search-listbox"
            role="listbox"
            className="absolute left-0 top-full z-50 mt-1 max-h-[70vh] w-full min-w-[280px] overflow-auto rounded-xl border border-border bg-white py-1 shadow-lg"
          >
            {isLoading ? (
              <div className="px-3 py-4 text-center text-sm text-foreground-muted">Поиск...</div>
            ) : results.length === 0 ? (
              <div className="px-3 py-4 text-center text-sm text-foreground-muted">
                Ничего не найдено
              </div>
            ) : (
              <ul className="py-1">
                {results.map(item => (
                  <li key={item.id} role="option" aria-selected={false}>
                    <button
                      type="button"
                      className="flex w-full items-center gap-3 px-3 py-2 text-left text-sm hover:bg-zinc-50 focus:bg-zinc-50 focus:outline-none"
                      onClick={() => handleSelect(item.slug)}
                    >
                      {item.image ? (
                        <span className="relative h-10 w-10 shrink-0 overflow-hidden rounded bg-zinc-100">
                          <Image
                            src={getMediaUrl(item.image)}
                            alt=""
                            fill
                            sizes="40px"
                            className="object-cover"
                          />
                        </span>
                      ) : (
                        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded bg-zinc-100 text-xs text-foreground-muted">
                          —
                        </span>
                      )}
                      <span className="min-w-0 flex-1 truncate font-medium text-foreground">
                        {item.title}
                      </span>
                      <span className="shrink-0 text-foreground-muted">
                        {item.price ? `${Math.round(Number(item.price))} ${CURRENCY_SYMBOL}` : '—'}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>

      {/* Мобильный: иконка поиска */}
      <div className="lg:hidden">
        <button
          type="button"
          onClick={() => setMobileOpen(true)}
          className={HEADER_ICON_BUTTON_CLASS}
          aria-label="Открыть поиск"
        >
          <Search className="text-foreground" />
        </button>
      </div>

      {/* Мобильная панель поиска (полноэкранная модалка) */}
      {mobileOpen && (
        <div className="fixed inset-0 z-[100] bg-white lg:hidden">
          <div className="flex flex-col h-full">
            <div className="flex items-center gap-2 border-b border-border px-3 py-3">
              <div className="relative flex-1" ref={dropdownRef}>
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-foreground-muted" />
                <input
                  data-header-search-input
                  type="search"
                  placeholder="Поиск по названию или артикулу..."
                  value={query}
                  onChange={e => setQuery(e.target.value)}
                  className="w-full rounded-full border border-border bg-zinc-50 py-3 pl-10 pr-4 text-base text-foreground placeholder:text-foreground-muted focus:border-brand focus:outline-none focus:ring-1 focus:ring-brand"
                  autoFocus
                  aria-label="Поиск по каталогу"
                />
              </div>
              <button
                type="button"
                onClick={() => setMobileOpen(false)}
                className="shrink-0 rounded-full p-2 hover:bg-zinc-100"
                aria-label="Закрыть поиск"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="flex-1 overflow-auto">
              {debouncedQuery.length >= MIN_LENGTH && (
                <>
                  {isLoading ? (
                    <div className="px-4 py-8 text-center text-foreground-muted">Поиск...</div>
                  ) : results.length === 0 ? (
                    <div className="px-4 py-8 text-center text-foreground-muted">
                      Ничего не найдено по запросу «{debouncedQuery}»
                    </div>
                  ) : (
                    <ul className="divide-y divide-border">
                      {results.map(item => (
                        <li key={item.id}>
                          <button
                            type="button"
                            className="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-zinc-50 active:bg-zinc-100"
                            onClick={() => handleSelect(item.slug)}
                          >
                            {item.image ? (
                              <span className="relative h-14 w-14 shrink-0 overflow-hidden rounded-lg bg-zinc-100">
                                <Image
                                  src={getMediaUrl(item.image)}
                                  alt=""
                                  fill
                                  sizes="56px"
                                  className="object-cover"
                                />
                              </span>
                            ) : (
                              <span className="flex h-14 w-14 shrink-0 items-center justify-center rounded-lg bg-zinc-100 text-foreground-muted">
                                —
                              </span>
                            )}
                            <div className="min-w-0 flex-1">
                              <p className="truncate font-medium text-foreground">{item.title}</p>
                              <p className="text-sm text-foreground-muted">
                                {item.price
                                  ? `${Math.round(Number(item.price))} ${CURRENCY_SYMBOL}`
                                  : '—'}
                              </p>
                            </div>
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                </>
              )}
              {debouncedQuery.length > 0 && debouncedQuery.length < MIN_LENGTH && (
                <div className="px-4 py-8 text-center text-sm text-foreground-muted">
                  Введите минимум {MIN_LENGTH} символа
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
});

HeaderSearch.displayName = 'HeaderSearch';
