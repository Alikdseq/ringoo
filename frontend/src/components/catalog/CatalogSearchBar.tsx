'use client';

import Image from 'next/image';
import Link from 'next/link';
import { useEffect, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Search } from 'lucide-react';
import { getProductAutocomplete } from '@/lib/api/services/products.service';
import { CURRENCY_SYMBOL } from '@/lib/constants';
import { getMediaUrl } from '@/lib/image-url';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/theme/utils';

const DEBOUNCE_MS = 250;
const MIN_LENGTH = 2;

export interface CatalogSearchBarProps {
  value: string;
  onChange: (value: string) => void;
  onApply: (query: string) => void;
  onPickSuggestion: (title: string) => void;
}

export function CatalogSearchBar({
  value,
  onChange,
  onApply,
  onPickSuggestion,
}: CatalogSearchBarProps) {
  const [debounced, setDebounced] = useState('');
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const t = window.setTimeout(() => setDebounced(value.trim()), DEBOUNCE_MS);
    return () => window.clearTimeout(t);
  }, [value]);

  const { data: results = [], isLoading } = useQuery({
    queryKey: ['products', 'catalog-autocomplete', debounced],
    queryFn: () => getProductAutocomplete(debounced),
    enabled: debounced.length >= MIN_LENGTH,
    staleTime: 60_000,
  });

  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (!rootRef.current?.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', onDocClick);
    return () => document.removeEventListener('mousedown', onDocClick);
  }, []);

  const showDropdown = open && debounced.length >= MIN_LENGTH;

  const handleApply = () => {
    setOpen(false);
    onApply(value.trim());
  };

  return (
    <div ref={rootRef} className="relative w-full min-w-0">
      <div className="flex w-full min-w-0 flex-col gap-2 sm:flex-row sm:items-stretch">
        <div className="relative min-h-[44px] min-w-0 flex-1 rounded-xl border border-border bg-white focus-within:border-brand focus-within:ring-2 focus-within:ring-brand focus-within:ring-offset-1 sm:min-h-[42px]">
          <Search
            className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-foreground-muted"
            aria-hidden
          />
          <input
            type="search"
            value={value}
            onChange={e => {
              onChange(e.target.value);
              setOpen(true);
            }}
            onFocus={() => setOpen(true)}
            onKeyDown={e => {
              if (e.key === 'Enter') {
                e.preventDefault();
                handleApply();
              }
              if (e.key === 'Escape') setOpen(false);
            }}
            placeholder="Поиск по каталогу: айфон, самсунг, redmi…"
            className="h-full w-full min-w-0 rounded-xl bg-transparent py-2.5 pl-10 pr-3 text-base text-foreground outline-none placeholder:text-foreground-muted sm:text-sm"
            aria-label="Поиск по каталогу"
            aria-autocomplete="list"
            aria-expanded={showDropdown}
          />
        </div>
        <Button
          type="button"
          onClick={handleApply}
          variant="secondary"
          className="h-[44px] w-full shrink-0 sm:w-auto sm:min-w-[7.5rem]"
        >
          <Search className="mr-1.5 h-4 w-4" aria-hidden />
          Найти
        </Button>
      </div>

      {showDropdown && (
        <div className="absolute left-0 right-0 z-30 mt-2 w-full min-w-0 rounded-2xl border border-border bg-white p-2 shadow-lg">
          {isLoading ? (
            <p className="px-3 py-4 text-sm text-foreground-muted">Поиск…</p>
          ) : results.length === 0 ? (
            <p className="px-3 py-4 text-sm text-foreground-muted">Ничего не найдено</p>
          ) : (
            <ul className="grid gap-2 sm:grid-cols-2">
              {results.map(item => (
                <li key={item.id}>
                  <button
                    type="button"
                    className={cn(
                      'flex w-full min-w-0 items-center gap-3 rounded-xl border border-border bg-zinc-50/80 p-2.5 text-left',
                      'transition-colors hover:border-brand/40 hover:bg-brand/5 active:bg-brand/10'
                    )}
                    onClick={() => {
                      onPickSuggestion(item.title);
                      setOpen(false);
                    }}
                  >
                    {item.image ? (
                      <span className="relative h-12 w-12 shrink-0 overflow-hidden rounded-lg bg-white">
                        <Image
                          src={getMediaUrl(item.image)!}
                          alt=""
                          fill
                          sizes="48px"
                          className="object-contain p-0.5"
                        />
                      </span>
                    ) : (
                      <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-white text-foreground-muted">
                        <Search className="h-5 w-5" />
                      </span>
                    )}
                    <span className="min-w-0 flex-1">
                      <span className="line-clamp-2 text-sm font-medium text-foreground">
                        {item.title}
                      </span>
                      {item.price != null && (
                        <span className="mt-0.5 block text-xs text-foreground-muted">
                          {Math.round(Number(item.price)).toLocaleString('ru-RU')} {CURRENCY_SYMBOL}
                        </span>
                      )}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
          <div className="mt-2 border-t border-border/80 px-2 pt-2">
            <button
              type="button"
              className="w-full rounded-lg py-2 text-center text-sm font-medium text-brand hover:bg-brand/5"
              onClick={handleApply}
            >
              Показать все результаты
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
