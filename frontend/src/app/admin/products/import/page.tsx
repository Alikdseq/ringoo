'use client';

import { useCallback, useState } from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import {
  bulkImportProducts,
  downloadProductImportTemplate,
} from '@/lib/api/services/adminProducts.service';
import { getFriendlyErrorMessage } from '@/lib/errors';

export default function AdminProductImportPage() {
  const [xlsx, setXlsx] = useState<File | null>(null);
  const [zip, setZip] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleDownloadTemplate = useCallback(async () => {
    setDownloading(true);
    setError(null);
    try {
      const blob = await downloadProductImportTemplate();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'ringoo_products_import_template.xlsx';
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(getFriendlyErrorMessage(e));
    } finally {
      setDownloading(false);
    }
  }, []);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!xlsx) {
        setError('Выберите файл XLSX.');
        return;
      }
      setLoading(true);
      setError(null);
      setResult(null);
      try {
        const data = await bulkImportProducts(xlsx, zip);
        const lines = [
          data.ok ? 'Импорт выполнен.' : 'Импорт завершён с ошибками.',
          `Создано: ${data.created}, обновлено: ${data.updated}, фото: ${data.images}`,
        ];
        if (data.errors?.length) {
          lines.push('Ошибки:', ...data.errors.slice(0, 30));
          if (data.errors.length > 30) {
            lines.push(`… ещё ${data.errors.length - 30}`);
          }
        }
        setResult(lines.join('\n'));
      } catch (err) {
        setError(getFriendlyErrorMessage(err));
      } finally {
        setLoading(false);
      }
    },
    [xlsx, zip]
  );

  return (
    <div className="mx-auto w-full max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-zinc-900">Импорт товаров</h1>
        <p className="mt-1 text-sm text-zinc-600">
          Загрузите таблицу Excel и при необходимости архив с фотографиями. Товары появятся в
          каталоге после успешного импорта.
        </p>
      </div>

      <Card className="space-y-4 p-6">
        <h2 className="text-lg font-semibold text-zinc-900">Как заполнить таблицу</h2>
        <ol className="list-decimal space-y-2 pl-5 text-sm text-zinc-700">
          <li>
            Нажмите «Скачать шаблон» — в файле два листа: <strong>Товары</strong> и{' '}
            <strong>Инструкция</strong>.
          </li>
          <li>
            <strong>Одна строка = один цвет.</strong> Если у товара три цвета — три строки с
            одинаковым артикулом (SKU).
          </li>
          <li>
            Обязательно: артикул, название, категория (
            <code className="rounded bg-zinc-100 px-1">iphone</code> или{' '}
            <code className="rounded bg-zinc-100 px-1">samsung</code>), цена товара.
          </li>
          <li>
            Для каждого цвета укажите код цвета (латиницей, например{' '}
            <code className="rounded bg-zinc-100 px-1">black-titanium</code>), название цвета и при
            желании HEX (<code className="rounded bg-zinc-100 px-1">#1C1C1E</code>).
          </li>
          <li>
            Если у цвета своя цена — заполните колонки «Цена цвета» и «Старая цена цвета». Иначе
            на сайте будет цена товара.
          </li>
        </ol>

        <h2 className="text-lg font-semibold text-zinc-900">Как упаковать фото (ZIP)</h2>
        <ul className="list-disc space-y-2 pl-5 text-sm text-zinc-700">
          <li>
            Фото конкретного цвета:{' '}
            <code className="rounded bg-zinc-100 px-1">Артикул/код_цвета/файл.jpg</code>
            <br />
            Пример:{' '}
            <code className="rounded bg-zinc-100 px-1">SAM-S24U-256/titanium-gray/1.jpg</code>
          </li>
          <li>
            Общие фото (коробка, комплект):{' '}
            <code className="rounded bg-zinc-100 px-1">Артикул/файл.jpg</code>
          </li>
          <li>
            Форматы: JPG, PNG, WebP. На сайте они автоматически приводятся к виду на белом фоне.
          </li>
          <li>Имена папок цвета должны совпадать с «Код цвета» в таблице.</li>
        </ul>
      </Card>

      <Card className="p-6">
        <div className="mb-4 flex flex-wrap gap-2">
          <Button type="button" variant="secondary" onClick={handleDownloadTemplate} disabled={downloading}>
            {downloading ? 'Скачивание…' : 'Скачать шаблон XLSX'}
          </Button>
          <Button asChild variant="secondary">
            <Link href="/admin/products">К списку товаров</Link>
          </Button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-zinc-800" htmlFor="xlsx">
              Таблица (.xlsx) <span className="text-red-600">*</span>
            </label>
            <input
              id="xlsx"
              name="xlsx"
              type="file"
              accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
              className="block w-full text-sm text-zinc-700"
              onChange={ev => setXlsx(ev.target.files?.[0] ?? null)}
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-zinc-800" htmlFor="zip">
              Архив фото (.zip, по желанию)
            </label>
            <input
              id="zip"
              name="zip"
              type="file"
              accept=".zip,application/zip"
              className="block w-full text-sm text-zinc-700"
              onChange={ev => setZip(ev.target.files?.[0] ?? null)}
            />
          </div>
          {error && (
            <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800 whitespace-pre-wrap">
              {error}
            </p>
          )}
          {result && (
            <pre className="max-h-64 overflow-auto rounded-lg border border-zinc-200 bg-zinc-50 p-3 text-xs text-zinc-800 whitespace-pre-wrap">
              {result}
            </pre>
          )}
          <Button type="submit" disabled={loading}>
            {loading ? 'Импорт…' : 'Загрузить'}
          </Button>
        </form>
      </Card>
    </div>
  );
}
