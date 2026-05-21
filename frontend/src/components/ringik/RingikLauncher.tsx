'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { MessageCircle, Phone, ExternalLink } from 'lucide-react';
import { Ringik } from '@/components/ringik/Ringik';
import { useUiMode } from '@/lib/providers/UiModeProvider';
import { cn } from '@/lib/theme/utils';
import { RINGIK_ENABLED } from '@/lib/ringik/featureFlags';

function RingikLauncherInner() {
  const { mode } = useUiMode();
  const [open, setOpen] = useState(false);
  const [showHello, setShowHello] = useState(false);

  const copy = useMemo(
    () =>
      mode === 'svoi'
        ? {
            hello: 'Здравствуй, родной! Мы — Зина и Бола. Подскажем, что выбрать.',
            panelTitle: 'Чем помочь?',
            panelLead: 'Напиши или набери — ответим по-человечески.',
            catalog: 'Заглянуть в каталог',
          }
        : {
            hello: 'Привет! Я Рингик. Помогу выбрать.',
            panelTitle: 'Чем помочь?',
            panelLead: 'Напиши нам или позвони — ответим быстро.',
            catalog: 'Найти товар в каталоге',
          },
    [mode]
  );

  useEffect(() => {
    const t1 = window.setTimeout(() => setShowHello(true), 1000);
    const t2 = window.setTimeout(() => setShowHello(false), 5000);
    return () => {
      window.clearTimeout(t1);
      window.clearTimeout(t2);
    };
  }, []);

  return (
    <>
      <Ringik
        pose="neutral"
        placement="fixed-bottom-right"
        visible
        clickable
        onClick={() => setOpen(v => !v)}
        message={copy.hello}
        showMessage={showHello}
      />

      {open && (
        <div
          className={cn(
            'fixed bottom-24 right-5 z-[95] w-[280px]',
            'rounded-[24px] border border-border bg-white p-4 shadow-lg'
          )}
        >
          <p className="text-sm font-semibold text-foreground">{copy.panelTitle}</p>
          <p className="mt-1 text-sm text-foreground-muted">{copy.panelLead}</p>

          <div className="mt-3 grid gap-2">
            <a
              href="https://wa.me/79184157788"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 rounded-xl border border-border px-3 py-2 text-sm font-medium text-foreground hover:bg-zinc-50"
            >
              <MessageCircle className="h-4 w-4 text-brand" />
              WhatsApp
              <ExternalLink className="ml-auto h-4 w-4 text-foreground-muted" />
            </a>
            <a
              href="tel:+79184157788"
              className="flex items-center gap-2 rounded-xl border border-border px-3 py-2 text-sm font-medium text-foreground hover:bg-zinc-50"
            >
              <Phone className="h-4 w-4 text-brand" />
              Позвонить
            </a>
            <Link
              href="/catalog"
              className="flex items-center gap-2 rounded-xl border border-border px-3 py-2 text-sm font-medium text-foreground hover:bg-zinc-50"
              onClick={() => setOpen(false)}
            >
              {copy.catalog}
            </Link>
          </div>
        </div>
      )}
    </>
  );
}

export function RingikLauncher() {
  if (!RINGIK_ENABLED) return null;
  return <RingikLauncherInner />;
}
