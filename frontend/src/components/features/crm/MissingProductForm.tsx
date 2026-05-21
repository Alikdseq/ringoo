'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import type { ProductAutocompleteItem } from '@/lib/api/services/products.service';
import { getProductAutocomplete } from '@/lib/api/services/products.service';
import { createMissingProductRequest } from '@/lib/api/services/crm.service';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { cn } from '@/lib/theme/utils';
import { ConsentCheckboxes } from '@/components/legal/ConsentCheckboxes';

const AUTCOMPLETE_DEBOUNCE_MS = 300;

export function MissingProductForm() {
  const [contactName, setContactName] = useState('');
  const [contactPhone, setContactPhone] = useState('');
  const [productName, setProductName] = useState('');
  const [comment, setComment] = useState('');
  const [consentPersonal, setConsentPersonal] = useState(false);
  const [consentMarketing, setConsentMarketing] = useState(false);
  const [consentError, setConsentError] = useState<string | null>(null);
  const [suggestions, setSuggestions] = useState<ProductAutocompleteItem[]>([]);
  const [suggestionsOpen, setSuggestionsOpen] = useState(false);
  const [submitStatus, setSubmitStatus] = useState<'idle' | 'success' | 'error'>('idle');
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);

  const fetchSuggestions = useCallback((q: string) => {
    if (!q.trim()) {
      setSuggestions([]);
      return;
    }
    getProductAutocomplete(q).then(list => {
      setSuggestions(list);
      setSuggestionsOpen(true);
    });
  }, []);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      fetchSuggestions(productName);
      debounceRef.current = null;
    }, AUTCOMPLETE_DEBOUNCE_MS);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [productName, fetchSuggestions]);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setSuggestionsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const mutation = useMutation({
    mutationFn: createMissingProductRequest,
    onSuccess: () => {
      setSubmitStatus('success');
      setContactName('');
      setContactPhone('');
      setProductName('');
      setComment('');
      setConsentPersonal(false);
      setConsentMarketing(false);
      setConsentError(null);
      setSuggestionsOpen(false);
    },
    onError: () => {
      setSubmitStatus('error');
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitStatus('idle');
    if (!consentPersonal) {
      setConsentError('Подтвердите согласие на обработку персональных данных.');
      return;
    }
    setConsentError(null);
    mutation.mutate({
      contact_name: contactName.trim() || undefined,
      contact_phone: contactPhone.trim(),
      product_name: productName.trim(),
      comment: comment.trim() || undefined,
      consent_personal_data: true,
      consent_marketing: consentMarketing,
    });
  };

  const selectSuggestion = (item: ProductAutocompleteItem) => {
    setProductName(item.title);
    setSuggestionsOpen(false);
  };

  return (
    <div className="rounded-2xl border border-border bg-card p-5">
      <h2 className="mb-4 text-lg font-semibold text-foreground">Не нашли нужный товар?</h2>
      <p className="mb-4 text-sm text-foreground-muted">
        Оставьте заявку — мы подберём товар или сообщим о поступлении.
      </p>
      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        <div>
          <label htmlFor="missing-name" className="mb-1 block text-sm text-foreground-muted">
            Имя
          </label>
          <Input
            id="missing-name"
            type="text"
            value={contactName}
            onChange={e => setContactName(e.target.value)}
            placeholder="Ваше имя"
            maxLength={255}
            className="w-full"
          />
        </div>
        <div>
          <label htmlFor="missing-phone" className="mb-1 block text-sm text-foreground-muted">
            Телефон <span className="text-danger">*</span>
          </label>
          <Input
            id="missing-phone"
            type="tel"
            value={contactPhone}
            onChange={e => setContactPhone(e.target.value)}
            placeholder="+7 (999) 123-45-67"
            required
            className="w-full"
          />
        </div>
        <div ref={wrapperRef} className="relative">
          <label htmlFor="missing-product" className="mb-1 block text-sm text-foreground-muted">
            Название искомого товара <span className="text-danger">*</span>
          </label>
          <Input
            id="missing-product"
            type="text"
            value={productName}
            onChange={e => setProductName(e.target.value)}
            onFocus={() => suggestions.length > 0 && setSuggestionsOpen(true)}
            placeholder="Начните вводить название или артикул"
            required
            className="w-full"
            autoComplete="off"
          />
          {suggestionsOpen && suggestions.length > 0 && (
            <ul
              className="absolute top-full left-0 right-0 z-10 mt-1 max-h-48 overflow-y-auto rounded-lg border border-border bg-white py-1 shadow-lg dark:bg-zinc-900"
              role="listbox"
            >
              {suggestions.map(item => (
                <li
                  key={item.id}
                  role="option"
                  aria-selected={false}
                  className="cursor-pointer px-3 py-2 text-sm hover:bg-zinc-100 dark:hover:bg-zinc-800"
                  onClick={() => selectSuggestion(item)}
                >
                  {item.title}
                  {item.sku && <span className="ml-2 text-foreground-muted">({item.sku})</span>}
                </li>
              ))}
            </ul>
          )}
        </div>
        <div>
          <label htmlFor="missing-comment" className="mb-1 block text-sm text-foreground-muted">
            Комментарий (необязательно)
          </label>
          <textarea
            id="missing-comment"
            value={comment}
            onChange={e => setComment(e.target.value)}
            placeholder="Укажите пожелания или сроки"
            rows={2}
            className={cn(
              'w-full rounded-lg border border-border bg-white px-3 py-2 text-sm text-foreground',
              'placeholder:text-foreground-muted focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary'
            )}
          />
        </div>
        {submitStatus === 'success' && (
          <p className="text-sm text-green-600 dark:text-green-400">
            Заявка отправлена. Мы свяжемся с вами в ближайшее время.
          </p>
        )}
        {submitStatus === 'error' && (
          <p className="text-sm text-red-600 dark:text-red-400">
            Не удалось отправить заявку. Попробуйте позже или позвоните нам.
          </p>
        )}
        <ConsentCheckboxes
          consentPersonal={consentPersonal}
          onConsentPersonalChange={setConsentPersonal}
          consentMarketing={consentMarketing}
          onConsentMarketingChange={setConsentMarketing}
        />
        {consentError && <p className="text-sm text-red-600 dark:text-red-400">{consentError}</p>}
        <Button type="submit" disabled={mutation.isPending || !consentPersonal}>
          {mutation.isPending ? 'Отправка…' : 'Отправить заявку'}
        </Button>
      </form>
    </div>
  );
}
