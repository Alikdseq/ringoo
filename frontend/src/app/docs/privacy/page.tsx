import type { Metadata } from 'next';
import Link from 'next/link';
import { LegalDocLayout } from '@/components/legal/LegalDocLayout';
import { LEGAL_DOC_LINKS, LEGAL_ORG, formatLegalAddress } from '@/lib/legal/constants';
import { buildPageMetadata } from '@/lib/seo';

export const metadata: Metadata = buildPageMetadata({
  title: 'Политика обработки персональных данных',
  description: `Политика обработки персональных данных интернет-магазина ${LEGAL_ORG.name}.`,
  path: LEGAL_DOC_LINKS.privacy,
});

export default function PrivacyPage() {
  const inn = LEGAL_ORG.inn || 'указан в разделе «Реквизиты»';
  const ogrn = LEGAL_ORG.ogrn || 'указан в разделе «Реквизиты»';

  return (
    <LegalDocLayout
      title="Политика обработки персональных данных"
      description={`Настоящая политика определяет порядок обработки и защиты персональных данных в ${LEGAL_ORG.legalName} (далее — Оператор).`}
    >
      <section>
        <h2 className="mb-2 text-lg font-semibold text-foreground">1. Оператор персональных данных</h2>
        <ul className="list-inside list-disc space-y-1 text-foreground-muted">
          <li>Наименование: {LEGAL_ORG.legalName}</li>
          <li>Адрес: {formatLegalAddress()}</li>
          <li>ИНН: {inn}</li>
          <li>ОГРН: {ogrn}</li>
          <li>
            Email для обращений по ПДн:{' '}
            <a href={`mailto:${LEGAL_ORG.privacyEmail}`} className="text-[var(--color-brand)] underline">
              {LEGAL_ORG.privacyEmail}
            </a>
          </li>
          <li>
            Сайт:{' '}
            <Link href="/" className="text-[var(--color-brand)] underline">
              {LEGAL_ORG.url}
            </Link>
          </li>
        </ul>
      </section>

      <section>
        <h2 className="mb-2 text-lg font-semibold text-foreground">2. Категории субъектов и данных</h2>
        <p className="text-foreground-muted">
          Оператор обрабатывает персональные данные посетителей сайта, покупателей, пользователей
          личного кабинета, лиц, оставивших заявки через формы (в том числе «Не нашли товар»), а
          также данные сотрудников (ФИО, фото) при наличии отдельного согласия.
        </p>
        <p className="mt-2 text-foreground-muted">Могут обрабатываться: ФИО, телефон, email, адрес доставки, сведения о заказах, IP-адрес, данные cookie и технические журналы, иные данные, которые вы добровольно указываете в формах.</p>
      </section>

      <section>
        <h2 className="mb-2 text-lg font-semibold text-foreground">3. Цели и правовые основания</h2>
        <ul className="list-inside list-disc space-y-1 text-foreground-muted">
          <li>Оформление, исполнение и доставка заказов — исполнение договора, согласие субъекта.</li>
          <li>Регистрация и ведение личного кабинета — согласие субъекта.</li>
          <li>Обработка заявок и обратная связь — согласие субъекта.</li>
          <li>Маркетинговые рассылки — отдельное согласие (см.{' '}
            <Link href={LEGAL_DOC_LINKS.marketing} className="underline">
              согласие на маркетинг
            </Link>
            ).
          </li>
          <li>Веб-аналитика (Яндекс.Метрика) — согласие на cookie/аналитику (см.{' '}
            <Link href={LEGAL_DOC_LINKS.cookies} className="underline">
              политику cookie
            </Link>
            ).
          </li>
          <li>Исполнение требований законодательства РФ.</li>
        </ul>
      </section>

      <section>
        <h2 className="mb-2 text-lg font-semibold text-foreground">4. Сроки хранения</h2>
        <p className="text-foreground-muted">
          Данные заказов и учётной записи хранятся в сроки, необходимые для исполнения договора,
          бухгалтерского и налогового учёта, а также разрешения споров. После удаления аккаунта
          персональные данные в профиле анонимизируются; сведения о заказах могут храниться в
          обезличенном виде для статистики и учёта. Журналы согласий (дата, IP, версия документа)
          хранятся не менее срока, установленного внутренней политикой Оператора и требованиями
          закона.
        </p>
      </section>

      <section>
        <h2 className="mb-2 text-lg font-semibold text-foreground">5. Локализация и субподрядчики</h2>
        <p className="text-foreground-muted">
          Первичное хранение персональных данных пользователей из РФ осуществляется на территории
          Российской Федерации (152-ФЗ, 242-ФЗ). Оператор может привлекать обработчиков: хостинг,
          почтовые сервисы, службы доставки — при условии заключения договоров и соблюдения
          конфиденциальности. Яндекс.Метрика обрабатывает обезличенные технические данные в
          соответствии с политикой Яндекса; подключение счётчика — только после вашего согласия в
          баннере cookie.
        </p>
      </section>

      <section>
        <h2 className="mb-2 text-lg font-semibold text-foreground">6. Cookie и Яндекс.Метрика</h2>
        <p className="text-foreground-muted">
          Подробно — в{' '}
          <Link href={LEGAL_DOC_LINKS.cookies} className="underline">
            Политике использования cookie и аналитики
          </Link>
          . Технически необходимые cookie (сессия корзины, авторизация) используются для работы
          сайта. Аналитические cookie и счётчик Яндекс.Метрики — только после нажатия «Принять» в
          баннере на сайте.
        </p>
      </section>

      <section>
        <h2 className="mb-2 text-lg font-semibold text-foreground">7. Права субъекта персональных данных</h2>
        <p className="text-foreground-muted">
          Вы вправе запросить доступ, уточнение, блокирование или удаление данных, отозвать согласие
          на маркетинг в личном кабинете, экспортировать данные и удалить аккаунт. Обращения
          направляйте на {LEGAL_ORG.privacyEmail}. Оператор рассмотрит запрос в сроки, установленные
          152-ФЗ.
        </p>
      </section>

      <section>
        <h2 className="mb-2 text-lg font-semibold text-foreground">8. Меры защиты</h2>
        <p className="text-foreground-muted">
          Применяются организационные и технические меры: HTTPS, ограничение доступа к данным,
          журналирование действий администраторов, хеширование паролей, разграничение прав в
          админ-панели. Подробнее — в документации по информационной безопасности проекта (для
          внутреннего использования).
        </p>
      </section>

      <section>
        <h2 className="mb-2 text-lg font-semibold text-foreground">9. Изменение политики</h2>
        <p className="text-foreground-muted">
          Оператор вправе обновлять политику. Актуальная версия публикуется на этой странице с
          указанием даты версии. При существенных изменениях пользователи могут быть уведомлены
          через сайт или email.
        </p>
      </section>

      <section>
        <h2 className="mb-2 text-lg font-semibold text-foreground">10. Согласие</h2>
        <p className="text-foreground-muted">
          Текст согласия на обработку персональных данных для форм сайта размещён на странице{' '}
          <Link href={LEGAL_DOC_LINKS.consent} className="underline">
            Согласие на обработку ПДн
          </Link>
          . Согласие оформляется отдельной отмеченной галочкой в каждой форме сбора данных.
        </p>
      </section>
    </LegalDocLayout>
  );
}
