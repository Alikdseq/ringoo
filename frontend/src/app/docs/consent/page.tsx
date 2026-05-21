import type { Metadata } from 'next';
import Link from 'next/link';
import { LegalDocLayout } from '@/components/legal/LegalDocLayout';
import { LEGAL_DOC_LINKS, LEGAL_ORG } from '@/lib/legal/constants';
import { buildPageMetadata } from '@/lib/seo';

export const metadata: Metadata = buildPageMetadata({
  title: 'Согласие на обработку персональных данных',
  description: 'Текст согласия субъекта на обработку персональных данных Ringoo.',
  path: LEGAL_DOC_LINKS.consent,
});

export default function ConsentPage() {
  return (
    <LegalDocLayout
      title="Согласие на обработку персональных данных"
      description="Текст, на который вы даёте согласие отдельной отмеченной галочкой при регистрации, оформлении заказа и в иных формах сайта."
    >
      <section>
        <p className="text-foreground-muted">
          Настоящим я, действуя свободно, своей волей и в своём интересе, даю согласие{' '}
          {LEGAL_ORG.legalName} (Оператор, сайт {LEGAL_ORG.url}) на обработку моих персональных
          данных на условиях{' '}
          <Link href={LEGAL_DOC_LINKS.privacy} className="underline">
            Политики обработки персональных данных
          </Link>
          .
        </p>
      </section>

      <section>
        <h2 className="mb-2 text-lg font-semibold text-foreground">Перечень данных</h2>
        <p className="text-foreground-muted">
          ФИО, контактный телефон, адрес электронной почты, адрес доставки, сведения о заказе,
          иные данные, которые я указываю в формах сайта.
        </p>
      </section>

      <section>
        <h2 className="mb-2 text-lg font-semibold text-foreground">Цели обработки</h2>
        <ul className="list-inside list-disc space-y-1 text-foreground-muted">
          <li>Регистрация и ведение личного кабинета;</li>
          <li>Оформление, оплата и доставка заказов, связь по заказу;</li>
          <li>Обработка заявок (в том числе «Не нашли товар»);</li>
          <li>Исполнение требований законодательства РФ.</li>
        </ul>
      </section>

      <section>
        <h2 className="mb-2 text-lg font-semibold text-foreground">Действия с данными</h2>
        <p className="text-foreground-muted">
          Сбор, запись, систематизация, накопление, хранение, уточнение, использование, передача
          (предоставление) курьерским и иным партнёрам в объёме, необходимом для доставки,
          обезличивание, блокирование, удаление.
        </p>
      </section>

      <section>
        <h2 className="mb-2 text-lg font-semibold text-foreground">Срок действия согласия</h2>
        <p className="text-foreground-muted">
          До достижения целей обработки или до отзыва согласия. Отзыв направляется на{' '}
          {LEGAL_ORG.privacyEmail} или через функции личного кабинета (удаление аккаунта, отзыв
          маркетинга).
        </p>
      </section>

      <section>
        <h2 className="mb-2 text-lg font-semibold text-foreground">Маркетинг</h2>
        <p className="text-foreground-muted">
          Рассылка новостей и акций — только при отдельном согласии по тексту{' '}
          <Link href={LEGAL_DOC_LINKS.marketing} className="underline">
            Согласия на получение маркетинговых сообщений
          </Link>
          .
        </p>
      </section>
    </LegalDocLayout>
  );
}
