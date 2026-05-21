'use client';

import { useMemo, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { createMissingProductRequest } from '@/lib/api/services/crm.service';
import { ConsentCheckboxes } from '@/components/legal/ConsentCheckboxes';
import Link from 'next/link';
import { ArrowRight, Instagram } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { useCategories } from '@/lib/hooks/useProducts';
import type { Category } from '@/types';

const FOOTER_INFO = [
  { label: 'О нас', href: '/about' },
  { label: 'Доставка и оплата', href: '/#delivery-payment' },
  { label: 'Проверить заказ', href: '/order-status' },
  { label: 'Гарантийные обязательства и возврат', href: '/#delivery-payment' },
  { label: 'Адрес и контакты', href: '/#delivery-payment' },
];

const FOOTER_CATALOG_FALLBACK = [
  { label: 'iPhone', href: '/catalog/category/iphone' },
  { label: 'iPad', href: '/catalog/category/ipad' },
  { label: 'Mac', href: '/catalog/category/mac' },
  { label: 'Watch', href: '/catalog/category/watch' },
  { label: 'AirPods', href: '/catalog/category/airpods' },
  { label: 'Android-смартфоны', href: '/catalog/category/android' },
];

const FOOTER_DOCS = [
  { label: 'Реквизиты организации', href: '/docs/requisites' },
  { label: 'Оферта', href: '/docs/offer' },
  { label: 'Политика конфиденциальности', href: '/docs/privacy' },
  { label: 'Согласие на обработку ПДн', href: '/docs/consent' },
  { label: 'Cookie и аналитика', href: '/docs/cookies' },
  { label: 'Карта сайта', href: '/site-map' },
];

const FOOTER_SUBSCRIBE_PRODUCT = 'Подписка на новости (футер)';

function buildFooterCatalogLinks(categories: Category[]) {
  const roots = categories.filter(c => !c.parent);
  const list = roots.length > 0 ? roots : categories;
  if (list.length === 0) return FOOTER_CATALOG_FALLBACK;
  return [...list]
    .sort((a, b) => a.title.localeCompare(b.title, 'ru'))
    .map(c => ({
      label: c.title,
      href: `/catalog/category/${c.slug}`,
    }));
}

interface FooterProps {
  initialCategories?: Category[];
}

export function Footer({ initialCategories }: FooterProps) {
  const [phone, setPhone] = useState('');
  const [consentPersonal, setConsentPersonal] = useState(false);
  const [consentMarketing, setConsentMarketing] = useState(false);
  const [footerMessage, setFooterMessage] = useState<string | null>(null);
  const subscribeMutation = useMutation({
    mutationFn: createMissingProductRequest,
    onSuccess: () => {
      setPhone('');
      setConsentPersonal(false);
      setConsentMarketing(false);
      setFooterMessage('Заявка принята. Мы свяжемся с вами.');
    },
    onError: () => {
      setFooterMessage('Не удалось отправить заявку. Попробуйте позже.');
    },
  });
  const { data: categories = initialCategories ?? [] } = useCategories({
    initialData: initialCategories,
  });
  const catalogLinks = useMemo(
    () => buildFooterCatalogLinks(categories),
    [categories]
  );

  return (
    <footer className="mt-auto border-t border-border bg-zinc-800 text-white">
      <div className="mx-auto max-w-6xl px-4 py-12 sm:px-6 lg:px-8">
        <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
          {/* Колонка 1: ИНФОРМАЦИЯ */}
          <div>
            <h3 className="mb-4 text-xs font-semibold uppercase tracking-wider text-zinc-400">
              Информация
            </h3>
            <ul className="space-y-2">
              {FOOTER_INFO.map(item => (
                <li key={item.label}>
                  <Link
                    href={item.href}
                    className="text-sm text-zinc-300 transition-colors hover:text-white"
                  >
                    {item.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Колонка 2: КАТАЛОГ */}
          <div>
            <h3 className="mb-4 text-xs font-semibold uppercase tracking-wider text-zinc-400">
              Каталог
            </h3>
            <ul className="space-y-2">
              {catalogLinks.map(item => (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    className="text-sm text-zinc-300 transition-colors hover:text-white"
                  >
                    {item.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Колонка 3: ДОКУМЕНТЫ */}
          <div>
            <h3 className="mb-4 text-xs font-semibold uppercase tracking-wider text-zinc-400">
              Документы
            </h3>
            <ul className="space-y-2">
              {FOOTER_DOCS.map(item => (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    className="text-sm text-zinc-300 transition-colors hover:text-white"
                  >
                    {item.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Колонка 4: ПРЕДЛОЖЕНИЯ ДЛЯ СОТРУДНИЧЕСТВА */}
          <div>
            <h3 className="mb-4 text-xs font-semibold uppercase tracking-wider text-zinc-400">
              Предложения для сотрудничества
            </h3>
            <p className="mb-3 text-sm text-zinc-300">
              Оставьте ваши контакты и мы вам перезвоним.
            </p>
            <div className="flex gap-2">
              <Input
                type="tel"
                placeholder="Ваш телефон"
                value={phone}
                onChange={e => setPhone(e.target.value)}
                className="flex-1 border-zinc-600 bg-zinc-700 text-white placeholder:text-zinc-400"
              />
              <Button
                type="button"
                size="sm"
                className="h-11 min-h-[44px] w-11 shrink-0 rounded-lg bg-zinc-600 px-0 hover:bg-zinc-500 touch-manipulation"
                aria-label="Отправить"
                disabled={
                  subscribeMutation.isPending || !phone.trim() || !consentPersonal
                }
                onClick={() => {
                  setFooterMessage(null);
                  const trimmed = phone.trim();
                  if (!trimmed || !consentPersonal) return;
                  subscribeMutation.mutate({
                    product_name: FOOTER_SUBSCRIBE_PRODUCT,
                    contact_phone: trimmed,
                    consent_personal_data: true,
                    consent_marketing: consentMarketing,
                  });
                }}
              >
                <ArrowRight className="h-4 w-4" />
              </Button>
            </div>
            <ConsentCheckboxes
              className="mt-3"
              variant="dark"
              consentPersonal={consentPersonal}
              onConsentPersonalChange={setConsentPersonal}
              consentMarketing={consentMarketing}
              onConsentMarketingChange={setConsentMarketing}
            />
            {footerMessage ? (
              <p className="mt-2 text-xs text-zinc-300">{footerMessage}</p>
            ) : null}
            <div className="mt-4 flex gap-3">
              <a
                href="https://instagram.com"
                target="_blank"
                rel="noopener noreferrer"
                className="text-zinc-400 transition-colors hover:text-white"
                aria-label="Instagram"
              >
                <Instagram className="h-5 w-5" />
              </a>
              <a
                href="https://t.me"
                target="_blank"
                rel="noopener noreferrer"
                className="text-zinc-400 transition-colors hover:text-white"
                aria-label="Telegram"
              >
                <svg className="h-5 w-5" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z" />
                </svg>
              </a>
              <a
                href="https://wa.me/79184157788"
                target="_blank"
                rel="noopener noreferrer"
                className="text-zinc-400 transition-colors hover:text-white"
                aria-label="WhatsApp"
              >
                <svg className="h-5 w-5" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z" />
                </svg>
              </a>
            </div>
          </div>
        </div>

        <div className="mt-10 border-t border-zinc-600 pt-6 text-center text-xs text-zinc-500">
          <p>© {new Date().getFullYear()} | Ringoo</p>
          <p className="mt-1">
            Сайт носит информационный характер и не является публичной офертой.
          </p>
        </div>
      </div>
    </footer>
  );
}
