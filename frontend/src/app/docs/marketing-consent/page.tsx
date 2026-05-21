import type { Metadata } from 'next';
import Link from 'next/link';
import { LegalDocLayout } from '@/components/legal/LegalDocLayout';
import { LEGAL_DOC_LINKS, LEGAL_ORG } from '@/lib/legal/constants';
import { buildPageMetadata } from '@/lib/seo';

export const metadata: Metadata = buildPageMetadata({
  title: 'Согласие на маркетинговые сообщения',
  description: 'Согласие на получение рекламных и информационных рассылок Ringoo.',
  path: LEGAL_DOC_LINKS.marketing,
});

export default function MarketingConsentPage() {
  return (
    <LegalDocLayout
      title="Согласие на получение маркетинговых сообщений"
      description="Отдельное согласие на рассылку. Оформляется только при добровольной отметке соответствующей галочки."
    >
      <section>
        <p className="text-foreground-muted">
          Настоящим я даю согласие {LEGAL_ORG.legalName} на направление мне информационных и
          рекламных сообщений о товарах, акциях и услугах Ringoo по каналам: SMS, email,
          мессенджеры (при указании контактов).
        </p>
      </section>

      <section>
        <h2 className="mb-2 text-lg font-semibold text-foreground">Данные для рассылки</h2>
        <p className="text-foreground-muted">Телефон, email, имя (если указаны в профиле или форме).</p>
      </section>

      <section>
        <h2 className="mb-2 text-lg font-semibold text-foreground">Отзыв согласия</h2>
        <p className="text-foreground-muted">
          Согласие может быть отозвано в любой момент: в личном кабинете (настройка рассылки), по
          email {LEGAL_ORG.privacyEmail} или ответом «Стоп» в SMS, если такая опция предусмотрена
          сообщением. Обработка данных для исполнения заказов не прекращается.
        </p>
      </section>

      <section>
        <p className="text-foreground-muted">
          Общие условия обработки персональных данных — в{' '}
          <Link href={LEGAL_DOC_LINKS.privacy} className="underline">
            Политике конфиденциальности
          </Link>
          .
        </p>
      </section>
    </LegalDocLayout>
  );
}
