'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { Input } from '@/components/ui/Input';
import { cn } from '@/lib/theme/utils';

const SUGGEST_URL = 'https://suggest-maps.yandex.ru/v1/suggest';
const GEOCODE_URL = 'https://geocode-maps.yandex.ru/1.x/';

/** Ключ Suggest API (можно тот же, что для карт, если подключён Suggest). */
function getSuggestApiKey(): string {
  return (
    process.env.NEXT_PUBLIC_YANDEX_SUGGEST_API_KEY ??
    process.env.NEXT_PUBLIC_YANDEX_MAPS_API_KEY ??
    ''
  );
}

interface SuggestResult {
  title?: { text?: string };
  subtitle?: { text?: string };
  address?: { formatted_address?: string };
}

interface SuggestResponse {
  results?: SuggestResult[];
}

interface GeocodeResponse {
  response?: {
    GeoObjectCollection?: {
      featureMember?: Array<{
        GeoObject?: {
          Point?: { pos?: string };
          metaDataProperty?: {
            GeocoderMetaData?: {
              text?: string;
            };
          };
        };
      }>;
    };
  };
}

export interface AddressSuggestion {
  address: string;
  coordinates?: { lat: number; lon: number };
}

export interface AddressAutocompleteProps {
  value: string;
  onChange: (value: string) => void;
  onSelect?: (suggestion: AddressSuggestion) => void;
  placeholder?: string;
  className?: string;
  /** Минимальная длина запроса для запроса подсказок */
  minLength?: number;
  /** Задержка перед запросом (мс) */
  debounceMs?: number;
  disabled?: boolean;
  id?: string;
  'aria-label'?: string;
}

function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);

  return debouncedValue;
}

async function fetchSuggest(query: string, apiKey: string): Promise<SuggestResult[]> {
  if (!apiKey || !query.trim()) return [];
  const params = new URLSearchParams({
    apikey: apiKey,
    lang: 'ru_RU',
    results: '8',
    text: query.trim(),
  });
  const res = await fetch(`${SUGGEST_URL}?${params.toString()}`);
  if (!res.ok) return [];
  const data: SuggestResponse = await res.json();
  return data.results ?? [];
}

async function fetchGeocode(
  address: string,
  apiKey: string
): Promise<{ lat: number; lon: number } | null> {
  if (!apiKey || !address.trim()) return null;
  const params = new URLSearchParams({
    apikey: apiKey,
    geocode: address.trim(),
    format: 'json',
  });
  const res = await fetch(`${GEOCODE_URL}?${params.toString()}`);
  if (!res.ok) return null;
  const data: GeocodeResponse = await res.json();
  const pos = data.response?.GeoObjectCollection?.featureMember?.[0]?.GeoObject?.Point?.pos;
  if (!pos) return null;
  const [lonStr, latStr] = pos.split(/\s+/);
  const lon = parseFloat(lonStr);
  const lat = parseFloat(latStr);
  if (Number.isNaN(lat) || Number.isNaN(lon)) return null;
  return { lat, lon };
}

function getSuggestionDisplayText(item: SuggestResult): string {
  const formatted = item.address?.formatted_address?.trim();
  if (formatted) return formatted;
  const title = item.title?.text?.trim() ?? '';
  const subtitle = item.subtitle?.text?.trim() ?? '';
  if (subtitle) return `${title}, ${subtitle}`;
  return title;
}

export function AddressAutocomplete({
  value,
  onChange,
  onSelect,
  placeholder = 'Улица, дом, квартира',
  className,
  minLength = 2,
  debounceMs = 300,
  disabled,
  id,
  'aria-label': ariaLabel,
}: AddressAutocompleteProps) {
  const [suggestPack, setSuggestPack] = useState<{ q: string; items: SuggestResult[] }>({
    q: '',
    items: [],
  });
  const [listOpen, setListOpen] = useState(false);
  const [resolvedQuery, setResolvedQuery] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const debouncedQuery = useDebounce(value, debounceMs);
  const apiKey = getSuggestApiKey();
  const shouldFetch = Boolean(apiKey && debouncedQuery.length >= minLength);
  const suggestions =
    shouldFetch && suggestPack.q === debouncedQuery ? suggestPack.items : [];
  const isLoadingSuggestions = shouldFetch && resolvedQuery !== debouncedQuery;

  useEffect(() => {
    if (!shouldFetch) return;

    let cancelled = false;
    fetchSuggest(debouncedQuery, apiKey)
      .then(results => {
        if (!cancelled) {
          setSuggestPack({ q: debouncedQuery, items: results });
          setListOpen(results.length > 0);
          setResolvedQuery(debouncedQuery);
        }
      })
      .catch(() => {
        if (!cancelled) setResolvedQuery(debouncedQuery);
      });

    return () => {
      cancelled = true;
    };
  }, [shouldFetch, debouncedQuery, apiKey]);

  const isOpen = shouldFetch && suggestions.length > 0 && listOpen;

  const handleSelect = useCallback(
    async (item: SuggestResult) => {
      const address = getSuggestionDisplayText(item);
      onChange(address);
      setSuggestPack({ q: '', items: [] });
      setListOpen(false);

      if (onSelect) {
        const coords = apiKey ? await fetchGeocode(address, apiKey) : null;
        onSelect({
          address,
          coordinates: coords ?? undefined,
        });
      }
    },
    [onChange, onSelect, apiKey]
  );

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setListOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div ref={containerRef} className={cn('relative', className)}>
      <Input
        id={id}
        type="text"
        autoComplete="off"
        role="combobox"
        aria-expanded={isOpen}
        aria-autocomplete="list"
        aria-controls={isOpen ? 'address-suggestions-list' : undefined}
        aria-label={ariaLabel}
        value={value}
        onChange={e => onChange(e.target.value)}
        onFocus={() => {
          if (shouldFetch && suggestions.length > 0) setListOpen(true);
        }}
        placeholder={placeholder}
        disabled={disabled}
      />
      {isOpen && suggestions.length > 0 && (
        <ul
          id="address-suggestions-list"
          role="listbox"
          className="absolute z-50 mt-1 max-h-60 w-full overflow-auto rounded-lg border border-zinc-200 bg-white py-1 shadow-lg dark:border-zinc-700 dark:bg-zinc-900"
        >
          {suggestions.map((item, index) => {
            const text = getSuggestionDisplayText(item);
            return (
              <li
                key={`${index}-${text}`}
                role="option"
                aria-selected={false}
                tabIndex={0}
                className="cursor-pointer px-3 py-2 text-sm text-zinc-900 hover:bg-zinc-100 dark:text-zinc-100 dark:hover:bg-zinc-800"
                onMouseDown={e => {
                  e.preventDefault();
                  handleSelect(item);
                }}
                onKeyDown={e => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    handleSelect(item);
                  }
                }}
              >
                {text}
              </li>
            );
          })}
        </ul>
      )}
      {isLoadingSuggestions && value.length >= minLength && (
        <span
          className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-zinc-400"
          aria-hidden
        >
          …
        </span>
      )}
    </div>
  );
}
