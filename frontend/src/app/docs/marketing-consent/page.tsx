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
      description="Отдельное необязательное согласие на рекламу и информирование (38-ФЗ «О рекламе», ст. 15 152-ФЗ). Не смешивается с согласием на обработку ПДн для заказа и с принятием оферты."
    >
      <section>
        <p className="text-foreground-muted">
          Настоящим я даю согласие {LEGAL_ORG.legalName} на направление мне информационных и
          рекламных сообщений о товарах, акциях, скидках и услугах интернет-магазина Ringoo по
          каналам связи, которые я указал(а): SMS, электронная почта, мессенджеры и звонки (если
          номер телефона предоставлен).
        </p>
      </section>

      <section>
        <h2 className="mb-2 text-lg font-semibold text-foreground">Данные для рассылки</h2>
        <p className="text-foreground-muted">
          Номер телефона, адрес электронной почты, имя (если указаны в профиле или форме), сведения о
          предпочтениях в объёме, необходимом для персонализации сообщений.
        </p>
      </section>

      <section>
        <h2 className="mb-2 text-lg font-semibold text-foreground">Срок и отзыв</h2>
        <p className="text-foreground-muted">
          Согласие действует до его отзыва. Отозвать можно в любой момент: в личном кабинете
          (настройка рассылки, если доступна), письмом на {LEGAL_ORG.privacyEmail}, ответом «Стоп»
          / «Отписаться» в сообщении (если такой способ указан). Обработка персональных данных для
          целей продвижения товаров и услуг прекращается по вашему требованию без промедления (ст. 15
          152-ФЗ). Исполнение уже оформленных заказов и иные законные основания обработки при этом не
          прекращаются.
        </p>
      </section>

      <section>
        <p className="text-foreground-muted">
          Общие условия обработки персональных данных — в{' '}
          <Link href={LEGAL_DOC_LINKS.privacy} className="underline">
            Политике конфиденциальности
          </Link>
          . Текст согласия на обработку ПДн для заказа и кабинета —{' '}
          <Link href={LEGAL_DOC_LINKS.consent} className="underline">
            отдельно
          </Link>
          .
        </p>
      </section>
    </LegalDocLayout>
  );
}
