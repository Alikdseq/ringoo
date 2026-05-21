import type { Metadata } from 'next';
import Link from 'next/link';
import { LegalDocLayout } from '@/components/legal/LegalDocLayout';
import { LEGAL_DOC_LINKS, LEGAL_ORG } from '@/lib/legal/constants';
import { buildPageMetadata } from '@/lib/seo';

export const metadata: Metadata = buildPageMetadata({
  title: 'Политика cookie и веб-аналитики',
  description: 'Использование cookie и Яндекс.Метрики на сайте Ringoo.',
  path: LEGAL_DOC_LINKS.cookies,
});

export default function CookiesPage() {
  return (
    <LegalDocLayout
      title="Политика использования cookie и веб-аналитики"
      description="Какие файлы cookie используются на сайте и как управлять аналитикой."
    >
      <section>
        <h2 className="mb-2 text-lg font-semibold text-foreground">1. Что такое cookie</h2>
        <p className="text-foreground-muted">
          Cookie — небольшие файлы, которые сайт сохраняет в браузере для работы сервисов,
          запоминания настроек и (при вашем согласии) аналитики посещений.
        </p>
      </section>

      <section>
        <h2 className="mb-2 text-lg font-semibold text-foreground">2. Необходимые cookie</h2>
        <p className="text-foreground-muted">
          Используются без отдельного согласия, так как нужны для работы сайта:
        </p>
        <ul className="mt-2 list-inside list-disc space-y-1 text-foreground-muted">
          <li>сессия корзины и гостевой корзины (Django session);</li>
          <li>авторизация (JWT в httpOnly-куках при входе в аккаунт);</li>
          <li>защита от CSRF (csrftoken);</li>
          <li>режим интерфейса (ringoo_ui_mode), запись о выборе cookie/аналитики (ringoo_analytics_consent).</li>
        </ul>
      </section>

      <section>
        <h2 className="mb-2 text-lg font-semibold text-foreground">3. Яндекс.Метрика</h2>
        <p className="text-foreground-muted">
          При нажатии «Принять» в баннере на сайте подключается счётчик{' '}
          <strong>Яндекс.Метрика</strong> (ООО «Яндекс», РФ). Метрика может собирать: IP-адрес,
          тип устройства и браузера, страницы просмотра, источник перехода, действия на сайте
          (обезличенная статистика). Цель — улучшение сайта и оценка эффективности рекламы.
          Подробности — в политике конфиденциальности Яндекса. Отказ от аналитики: кнопка «Только
          необходимые» в баннере или очистка cookie в браузере.
        </p>
      </section>

      <section>
        <h2 className="mb-2 text-lg font-semibold text-foreground">4. Управление cookie</h2>
        <p className="text-foreground-muted">
          Вы можете изменить выбор в баннере при следующем визите (удалив cookie
          ringoo_analytics_consent) или в настройках браузера. Отключение необходимых cookie может
          нарушить работу корзины и входа в аккаунт.
        </p>
      </section>

      <section>
        <p className="text-foreground-muted">
          Обработка персональных данных в целом регулируется{' '}
          <Link href={LEGAL_DOC_LINKS.privacy} className="underline">
            Политикой конфиденциальности
          </Link>{' '}
          {LEGAL_ORG.legalName}. Вопросы: {LEGAL_ORG.privacyEmail}.
        </p>
      </section>
    </LegalDocLayout>
  );
}
