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
      description="Отдельный текст согласия (ч. 1 ст. 9 152-ФЗ). Оформляется отмеченной галочкой и не объединяется с принятием оферты или согласием на рекламу."
    >
      <section>
        <p className="text-foreground-muted">
          Настоящим я, действуя свободно, своей волей и в своём интересе, даю{' '}
          {LEGAL_ORG.legalName} (Оператор, сайт {LEGAL_ORG.url}) конкретное, информированное,
          сознательное и однозначное согласие на обработку моих персональных данных на условиях{' '}
          <Link href={LEGAL_DOC_LINKS.privacy} className="underline">
            Политики обработки персональных данных
          </Link>
          .
        </p>
      </section>

      <section>
        <h2 className="mb-2 text-lg font-semibold text-foreground">Перечень персональных данных</h2>
        <p className="text-foreground-muted">
          ФИО; контактный телефон; адрес электронной почты; адрес доставки; сведения о заказе и
          обращении; иные данные, которые я указываю в формах сайта. Технические сведения (IP-адрес,
          данные журналов), связанные с использованием сайта при заполнении форм и оформлении
          заказа, — в объёме, необходимом для безопасности и исполнения договора.
        </p>
      </section>

      <section>
        <h2 className="mb-2 text-lg font-semibold text-foreground">Цели обработки</h2>
        <ul className="list-inside list-disc space-y-1 text-foreground-muted">
          <li>регистрация и ведение личного кабинета;</li>
          <li>оформление, оплата, комплектация и доставка заказов, связь по заказу;</li>
          <li>обработка заявок (в том числе «Не нашли товар») и обращений;</li>
          <li>исполнение требований законодательства Российской Федерации.</li>
        </ul>
      </section>

      <section>
        <h2 className="mb-2 text-lg font-semibold text-foreground">Действия с данными</h2>
        <p className="text-foreground-muted">
          Сбор, запись, систематизация, накопление, хранение, уточнение, извлечение, использование,
          передача (предоставление) третьим лицам по поручению Оператора в объёме, необходимом для
          указанных целей (службы доставки, хостинг, платёжные сервисы при их подключении),
          обезличивание, блокирование, удаление (уничтожение). Обработка допускается с
          использованием средств автоматизации и без них. Первичная запись и хранение данных граждан
          РФ осуществляются с использованием баз данных на территории РФ.
        </p>
      </section>

      <section>
        <h2 className="mb-2 text-lg font-semibold text-foreground">Срок действия и отзыв</h2>
        <p className="text-foreground-muted">
          Согласие действует до достижения целей обработки либо до его отзыва. Отзыв направляется на{' '}
          {LEGAL_ORG.privacyEmail} или через функции личного кабинета (где предусмотрено). Отзыв не
          влияет на законность обработки, осуществлённой до отзыва. Если для продолжения оказания
          услуги необходимо согласие, Оператор вправе прекратить соответствующие услуги. Обработка,
          необходимая для исполнения договора и обязанностей по закону, может продолжаться на иных
          правовых основаниях.
        </p>
      </section>

      <section>
        <h2 className="mb-2 text-lg font-semibold text-foreground">Что не входит в это согласие</h2>
        <ul className="list-inside list-disc space-y-1 text-foreground-muted">
          <li>
            принятие{' '}
            <Link href={LEGAL_DOC_LINKS.offer} className="underline">
              публичной оферты
            </Link>{' '}
            — отдельная галочка;
          </li>
          <li>
            <Link href={LEGAL_DOC_LINKS.marketing} className="underline">
              маркетинговые / рекламные сообщения
            </Link>{' '}
            — отдельная необязательная галочка;
          </li>
          <li>
            аналитические cookie и Яндекс.Метрика — отдельный выбор в{' '}
            <Link href={LEGAL_DOC_LINKS.cookies} className="underline">
              баннере cookie
            </Link>
            .
          </li>
        </ul>
      </section>
    </LegalDocLayout>
  );
}
