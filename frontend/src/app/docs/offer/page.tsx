import Link from 'next/link';

export const metadata = {
  title: 'Публичная оферта (пользовательское соглашение) | Ringoo',
  description: 'Условия продажи, оплаты и доставки в интернет-магазине Ringoo. Публичная оферта.',
};

export default function OfferPage() {
  return (
    <div className="mx-auto w-full max-w-4xl px-4 py-8 sm:px-6">
      <h1 className="mb-2 text-2xl font-semibold text-foreground sm:text-3xl">
        Публичная оферта (пользовательское соглашение)
      </h1>
      <p className="mb-8 text-sm text-foreground-muted">
        Последнее обновление: {new Date().toLocaleDateString('ru-RU')}
      </p>

      <div className="prose prose-zinc max-w-none space-y-8 text-sm dark:prose-invert">
        <section>
          <h2 className="mb-2 text-lg font-semibold text-foreground">1. Общие положения</h2>
          <p className="text-foreground-muted">
            Настоящий документ является публичной офертой продавца (далее — «Продавец») заключить
            договор купли-продажи товаров на условиях, изложенных ниже. Оформление заказа на сайте
            означает принятие покупателем (далее — «Покупатель») условий настоящей оферты. Договор
            считается заключённым с момента подтверждения заказа Продавцом (SMS, email или иным
            способом).
          </p>
        </section>

        <section>
          <h2 className="mb-2 text-lg font-semibold text-foreground">
            2. Порядок оформления заказа
          </h2>
          <p className="text-foreground-muted">
            Покупатель формирует заказ в корзине на сайте, указывает контактные данные, способ
            доставки и оплаты. Продавец оставляет за собой право отказать в приёме заказа при
            отсутствии товара, указании некорректных данных или по иным объективным причинам.
            Стоимость товара фиксируется в момент подтверждения заказа, если иное не оговорено.
          </p>
        </section>

        <section>
          <h2 className="mb-2 text-lg font-semibold text-foreground">3. Оплата и возврат</h2>
          <p className="text-foreground-muted">
            Оплата возможна способами, указанными на сайте при оформлении (наличными при получении,
            картой при получении, банковский перевод, онлайн-оплата). Возврат и обмен товара
            надлежащего качества осуществляются в соответствии с законодательством РФ и правилами,
            опубликованными на сайте (раздел «Доставка и оплата»). Для товаров ненадлежащего
            качества применяются гарантийные обязательства производителя и законные права
            потребителя.
          </p>
        </section>

        <section>
          <h2 className="mb-2 text-lg font-semibold text-foreground">4. Доставка</h2>
          <p className="text-foreground-muted">
            Способы, сроки и стоимость доставки указаны на сайте и в карточке заказа. Риск случайной
            гибели или повреждения товара переходит к Покупателю с момента передачи товара (при
            курьерской доставке — при подписании документов; при самовывозе — при получении в пункте
            выдачи).
          </p>
        </section>

        <section>
          <h2 className="mb-2 text-lg font-semibold text-foreground">5. Реквизиты и контакты</h2>
          <p className="text-foreground-muted">
            Реквизиты организации, юридический адрес и контактные данные указаны в разделе{' '}
            <Link href="/docs/requisites" className="text-[var(--color-brand)] underline">
              Реквизиты организации
            </Link>
            .
          </p>
        </section>
      </div>

      <p className="mt-8 text-xs text-foreground-muted">
        Оформляя заказ, вы подтверждаете, что ознакомились с офертой и согласны с её условиями.
      </p>
    </div>
  );
}
