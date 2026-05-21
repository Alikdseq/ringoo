'use client';

import { motion } from 'framer-motion';
import Image from 'next/image';
import Link from 'next/link';
import { Minus, Plus, Trash2 } from 'lucide-react';
import type { CartItem as CartItemType } from '@/types';
import { Card } from '@/components/ui/Card';
import { getMediaUrl } from '@/lib/image-url';
import { CURRENCY_SYMBOL } from '@/lib/constants';

interface CartItemProps {
  item: CartItemType;
  onIncrease: () => void;
  onDecrease: () => void;
  onRemove: () => void;
}

export function CartItem({ item, onIncrease, onDecrease, onRemove }: CartItemProps) {
  const product = item.product;
  const mainImage = product.images?.[0];
  const imageSrc = mainImage ? getMediaUrl(mainImage.image) : null;

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8, scale: 0.98 }}
      transition={{ duration: 0.18 }}
    >
      <Card className="flex gap-4">
        <div className="relative h-24 w-24 shrink-0 overflow-hidden rounded-xl bg-zinc-100 dark:bg-zinc-900">
          {imageSrc ? (
            <Image
              src={imageSrc}
              alt={mainImage?.alt_text ?? product.title}
              fill
              sizes="96px"
              className="object-cover"
              loading="lazy"
            />
          ) : (
            <div className="flex h-full items-center justify-center text-xs text-zinc-400 dark:text-zinc-600">
              Нет фото
            </div>
          )}
        </div>
        <div className="flex flex-1 flex-col gap-2">
          <div className="flex items-start justify-between gap-2">
            <div>
              <Link
                href={`/products/${product.slug}`}
                className="text-sm font-medium text-zinc-900 hover:underline dark:text-zinc-50"
              >
                {product.title}
              </Link>
              {item.color?.label ? (
                <p className="mt-1 text-xs text-zinc-600 dark:text-zinc-300">Цвет: {item.color.label}</p>
              ) : null}
              <p className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">
                Цена за шт.: {item.price_at_add} {CURRENCY_SYMBOL}
              </p>
            </div>
            <button
              type="button"
              onClick={onRemove}
              className="rounded-full p-1 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-700 dark:text-zinc-500 dark:hover:bg-zinc-800 dark:hover:text-zinc-200"
              aria-label="Удалить из корзины"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          </div>
          <div className="mt-auto flex items-center justify-between gap-4">
            <div className="inline-flex items-center gap-2 rounded-full border border-zinc-200 bg-white px-2 py-1 dark:border-zinc-700 dark:bg-zinc-900">
              <button
                type="button"
                onClick={onDecrease}
                className="rounded-full p-1 text-zinc-500 hover:bg-zinc-100 dark:hover:bg-zinc-800"
                aria-label="Уменьшить количество"
              >
                <Minus className="h-3 w-3" />
              </button>
              <span className="w-8 text-center text-sm">{item.quantity}</span>
              <button
                type="button"
                onClick={onIncrease}
                className="rounded-full p-1 text-zinc-500 hover:bg-zinc-100 dark:hover:bg-zinc-800"
                aria-label="Увеличить количество"
              >
                <Plus className="h-3 w-3" />
              </button>
            </div>
            <div className="text-right">
              <p className="text-sm font-semibold text-zinc-900 dark:text-zinc-50">
                {item.item_total} {CURRENCY_SYMBOL}
              </p>
            </div>
          </div>
        </div>
      </Card>
    </motion.div>
  );
}
