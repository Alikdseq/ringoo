'use client';

import Link from 'next/link';
import { LegalDocLayout } from '@/components/legal/LegalDocLayout';
import { LEGAL_DOC_LINKS, LEGAL_ORG } from '@/lib/legal/constants';
import { requestAnalyticsConsentReset } from '@/lib/legal/analytics-consent';

export default function CookiesPage() {
  return (
    <LegalDocLayout
      title="Политика использования cookie и веб-аналитики"
      description="Какие файлы cookie используются на сайте, как подключается Яндекс.Метрика и как отозвать согласие на аналитику."
    >
      <section>
        <h2 className="mb-2 text-lg font-semibold text-foreground">1. Что такое cookie</h2>
        <p className="text-foreground-muted">
          Cookie и сходные технологии — небольшие данные, которые сайт или сторонний сервис сохраняет
          в браузере. Если по ним можно прямо или косвенно определить пользователя, такие сведения
          рассматриваются как персональные данные и обрабатываются по 152-ФЗ. Для аналитики
          необходимо отдельное активное согласие; одной фразы «продолжая пользоваться сайтом…»
          недостаточно.
        </p>
      </section>

      <section>
        <h2 className="mb-2 text-lg font-semibold text-foreground">2. Необходимые cookie</h2>
        <p className="text-foreground-muted">
          Используются для работы сайта и безопасности (без отдельного согласия на аналитику):
        </p>
        <ul className="mt-2 list-inside list-disc space-y-1 text-foreground-muted">
          <li>сессия корзины и гостевой корзины;</li>
          <li>авторизация (JWT в httpOnly-куках при входе в аккаунт);</li>
          <li>защита от CSRF (csrftoken);</li>
          <li>
            режим интерфейса (ringoo_ui_mode) и запись выбора по аналитике
            (ringoo_analytics_consent) — чтобы не показывать баннер повторно без необходимости.
          </li>
        </ul>
      </section>

      <section>
        <h2 className="mb-2 text-lg font-semibold text-foreground">3. Яндекс.Метрика</h2>
        <p className="text-foreground-muted">
          Только после нажатия «Принять» в баннере подключается счётчик <strong>Яндекс.Метрика</strong>.
          Оператор сайта — {LEGAL_ORG.legalName}. ООО «ЯНДЕКС» (РФ) обрабатывает данные посетителей
          по поручению Оператора (ч. 3 ст. 6 152-ФЗ; условия использования Яндекс.Метрики). До согласия
          скрипт Метрики не загружается.
        </p>
        <p className="mt-2 text-foreground-muted">Могут обрабатываться, в частности:</p>
        <ul className="mt-2 list-inside list-disc space-y-1 text-foreground-muted">
          <li>cookie и идентификаторы браузера/устройства;</li>
          <li>IP-адрес, данные о браузере и ОС, разрешение экрана;</li>
          <li>адреса просматриваемых страниц, источник перехода, действия на сайте;</li>
          <li>иные технические сведения, предусмотренные документацией Яндекса.</li>
        </ul>
        <p className="mt-2 text-foreground-muted">
          Цели: статистика посещаемости, улучшение сайта, оценка эффективности рекламы. Подробности —
          в политике конфиденциальности и условиях Яндекса. Вы также можете запретить сбор данных
          расширением «Блокировщик Яндекс.Метрики» (обязанность информирования предусмотрена
          условиями сервиса Метрики).
        </p>
      </section>

      <section>
        <h2 className="mb-2 text-lg font-semibold text-foreground">4. Управление и отзыв</h2>
        <p className="text-foreground-muted">
          В баннере доступны кнопки «Принять» и «Только необходимые». Отказ сохраняется: счётчик не
          подключается на последующих страницах, пока вы не измените выбор.
        </p>
        <p className="mt-3">
          <button
            type="button"
            onClick={() => requestAnalyticsConsentReset()}
            className="rounded-md border border-border bg-background-alt px-3 py-2 text-sm font-medium text-foreground hover:bg-background"
          >
            Изменить настройки cookie / аналитики
          </button>
        </p>
        <p className="mt-2 text-foreground-muted">
          Также можно удалить cookie ringoo_analytics_consent в браузере. Отключение необходимых
          cookie может нарушить работу корзины и входа.
        </p>
      </section>

      <section>
        <p className="text-foreground-muted">
          Общие правила обработки персональных данных — в{' '}
          <Link href={LEGAL_DOC_LINKS.privacy} className="underline">
            Политике конфиденциальности
          </Link>{' '}
          {LEGAL_ORG.legalName}. Вопросы: {LEGAL_ORG.privacyEmail}.
        </p>
      </section>
    </LegalDocLayout>
  );
}
