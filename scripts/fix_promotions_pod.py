from pathlib import Path

p = Path(Path(__file__).resolve().parents[1] / "frontend/src/app/promotions/page.tsx")
text = p.read_text(encoding="utf-8")
start = text.index("function ProductOfDayProductBlock")
end = text.index("\nfunction Faq()")
new_block = """function ProductOfDayProductBlock({ product }: { product: Product }) {
  const timeLeft = usePromotionCountdown(endOfTodayISO());
  const mainImageSrc = useMemo(() => productMainImageSrc(product), [product]);
  const old = product.old_price ? Number(product.old_price) : null;
  const cur = product.price ? Number(product.price) : null;
  const discount =
    product.discount_percent != null
      ? Math.round(Number(product.discount_percent))
      : old && cur && old > cur
        ? Math.round(((old - cur) / old) * 100)
        : null;

  return (
    <section className="bg-background px-2 py-10 sm:px-4 lg:px-6">
      <div className="mx-auto max-w-[92rem]">
        <motion.div className="mb-6 flex items-end justify-between gap-4">
          <motion.div>
            <h2 className="text-2xl font-semibold text-foreground sm:text-3xl">Товар дня</h2>
            <p className="mt-2 text-base text-foreground-muted sm:text-lg">
              Суперпредложение — успей забрать.
            </p>
          </motion.div>
        </motion.div>

        <Card className="overflow-hidden p-0">
          <motion.div className="flex flex-col lg:grid lg:grid-cols-[1.05fr_0.95fr] lg:items-start">
            {mainImageSrc ? (
              <motion.div className="order-1 bg-white p-4 lg:hidden">
                <motion.div className="relative mx-auto aspect-square w-full max-w-md">
                  <Image
                    src={mainImageSrc}
                    alt={product.title}
                    fill
                    sizes="100vw"
                    className="object-contain"
                    priority
                  />
                </motion.div>
              </motion.div>
            ) : null}

            <motion.div className="order-2 p-6 sm:p-8 lg:order-1">
              <PromoBadge kind="product_of_day" text="Товар дня" />
              <h3 className="mt-3 text-2xl font-semibold tracking-tight text-foreground">
                {product.title}
              </h3>

              <motion.div className="mt-3 flex flex-wrap items-end gap-3">
                <motion.div className="text-3xl font-semibold leading-none text-foreground">
                  {cur != null && Number.isFinite(cur) ? Math.round(cur).toLocaleString('ru-RU') : '—'}{' '}
                  {CURRENCY_SYMBOL}
                </motion.div>
                {old != null && cur != null && old > cur && (
                  <motion.div className="pb-0.5 text-base font-medium text-foreground-muted line-through">
                    {Math.round(old).toLocaleString('ru-RU')} {CURRENCY_SYMBOL}
                  </motion.div>
                )}
                {discount != null && discount > 0 && (
                  <span className="rounded-full bg-zinc-900 px-3 py-1 text-xs font-semibold text-white">
                    −{discount}%
                  </span>
                )}
              </motion.div>

              <motion.div className="mt-4 rounded-2xl border border-border bg-white px-4 py-3">
                <motion.div className="text-sm font-medium text-foreground-muted">До конца дня</motion.div>
                <motion.div className="mt-1 text-xl font-semibold text-foreground tabular-nums sm:text-2xl">
                  {timeLeft === 'Завершена' ? 'Завершена' : timeLeft}
                </motion.div>
              </motion.div>

              <Button asChild className="mt-5 w-full">
                <Link
                  href={`/products/${product.slug}?utm_source=promotions&utm_medium=product_of_day&utm_campaign=${product.id}`}
                >
                  Купить со скидкой
                </Link>
              </Button>
            </motion.div>

            <motion.div className="order-3 hidden min-h-0 bg-white p-4 sm:p-6 lg:block lg:order-2 lg:max-h-[min(520px,80vh)] lg:overflow-hidden">
              <ProductCard product={product} priority className="max-h-full" />
            </motion.div>
          </motion.div>
        </Card>
      </motion.div>
    </motion.div>
  );
}

"""
new_block = (
    new_block.replace("<motion.div", "<div")
    .replace("</motion.div>", "</div>")
)
p.write_text(text[:start] + new_block + text[end:], encoding="utf-8")
print("ok")
