'use client';

import { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Check, ChevronLeft, ChevronRight } from 'lucide-react';
import Link from 'next/link';
import type { Store } from '@/types';
import { useCart } from '@/lib/hooks/useCart';
import { updateMarketingOptIn } from '@/lib/api/services/auth.service';
import { createOrder, type CreateOrderPayload } from '@/lib/api/services/orders.service';
import { getFriendlyErrorMessage } from '@/lib/errors';
import { getStores } from '@/lib/api/services/stores.service';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Loading } from '@/components/ui/Loading';
import { PlaceholderBlock } from '@/components/ui/PlaceholderBlock';
import { StoreSelector } from '@/components/features/stores/StoreSelector';
import { AddressAutocomplete } from '@/components/features/maps/AddressAutocomplete';
import { CURRENCY_SYMBOL } from '@/lib/constants';
import { useAuth } from '@/lib/hooks/useAuth';
import { getAddresses } from '@/lib/api/services/addresses.service';
import { mergeCheckoutFromUser } from '@/lib/user-profile-form';
import { ConsentCheckboxes } from '@/components/legal/ConsentCheckboxes';
import { PageContainer } from '@/components/layout/PageContainer';

type DeliveryType = 'pickup' | 'delivery';
type PaymentType = 'cash' | 'card_on_delivery' | 'bank_transfer' | 'online';

interface DeliveryFormState {
  fullName: string;
  phone: string;
  email: string;
  deliveryType: DeliveryType;
  storeId: string | null;
  city: string;
  addressLine: string;
  comment: string;
  /** Координаты выбранного адреса (из автодополнения). */
  deliveryCoordinates?: { lat: number; lon: number } | null;
}

interface PaymentFormState {
  paymentType: PaymentType | null;
}

interface DeliveryErrors {
  fullName?: string;
  phone?: string;
  storeId?: string;
  city?: string;
  addressLine?: string;
}

/**
 * Поля для API: после normalize на бэкенде должны остаться непустые city, street, house.
 * Город — из поля формы или из первой части адреса «Город, улица, дом, …», если город не ввели отдельно.
 */
function resolveDeliveryAddressForApi(d: DeliveryFormState): {
  city: string;
  street: string;
  house: string;
  apartment: string | null;
} {
  const line = d.addressLine.trim();
  const cityField = d.city.trim();
  const parts = line.split(',').map(s => s.trim()).filter(Boolean);

  if (cityField) {
    return {
      city: cityField,
      street: parts[0] || line,
      house: parts[1] || (line ? '—' : ''),
      apartment: parts.length >= 3 ? parts[2] : null,
    };
  }
  if (parts.length >= 3) {
    return {
      city: parts[0],
      street: parts[1],
      house: parts[2],
      apartment: parts.length >= 4 ? parts[3] : null,
    };
  }
  return {
    city: '',
    street: parts[0] || line,
    house: parts[1] || (line ? '—' : ''),
    apartment: parts.length >= 3 ? parts[2] : null,
  };
}

interface PaymentErrors {
  paymentType?: string;
}

const STEPS = ['Корзина', 'Доставка', 'Оплата', 'Подтверждение'] as const;

export default function CheckoutPage() {
  const [currentStep, setCurrentStep] = useState(0);

  const { data: cart, isLoading, isError } = useCart();

  const [delivery, setDelivery] = useState<DeliveryFormState>({
    fullName: '',
    phone: '',
    email: '',
    deliveryType: 'pickup',
    storeId: null,
    city: '',
    addressLine: '',
    comment: '',
    deliveryCoordinates: null,
  });

  const [payment, setPayment] = useState<PaymentFormState>({
    paymentType: null,
  });

  const [deliveryErrors, setDeliveryErrors] = useState<DeliveryErrors>({});
  const [paymentErrors, setPaymentErrors] = useState<PaymentErrors>({});
  const [consentPersonalData, setConsentPersonalData] = useState(false);
  /** Согласие на рассылку — отдельный чекбокс, по умолчанию не отмечен */
  const [consentNewsletter, setConsentNewsletter] = useState(false);
  const [consentError, setConsentError] = useState<string | null>(null);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const router = useRouter();
  const queryClient = useQueryClient();
  const { isAuthenticated, user } = useAuth();

  const { data: addressesData } = useQuery({
    queryKey: ['addresses'],
    queryFn: getAddresses,
    enabled: isAuthenticated,
    staleTime: 5 * 60 * 1000,
  });

  const defaultAddress = useMemo(() => {
    const list = Array.isArray(addressesData) ? addressesData : [];
    return list.find(a => a.is_default) ?? list[0];
  }, [addressesData]);

  useEffect(() => {
    if (!isAuthenticated || !user) return;
    setDelivery(prev => mergeCheckoutFromUser(prev, user, defaultAddress));
  }, [isAuthenticated, user, defaultAddress]);
  const createOrderMutation = useMutation({
    mutationFn: (payload: {
      data: CreateOrderPayload;
      idempotencyKey: string;
      consentNewsletter: boolean;
    }) => createOrder(payload.data, { idempotencyKey: payload.idempotencyKey }),
    onSuccess: async (order, variables) => {
      queryClient.invalidateQueries({ queryKey: ['cart'] });
      queryClient.invalidateQueries({ queryKey: ['orders'] });
      if (isAuthenticated && variables.consentNewsletter) {
        try {
          await updateMarketingOptIn(true);
        } catch {
          /* согласие не критично для завершения заказа */
        }
      }
      router.push('/orders');
    },
  });

  const items = useMemo(() => cart?.items ?? [], [cart]);
  /** Сумма с сервера; итог заказа на бэкенде пересчитывается из каталога — показываем ту же базу без демо-скидок. */
  const cartTotal = useMemo(() => (cart ? parseFloat(cart.total_amount) || 0 : 0), [cart]);

  const { data: storesData } = useQuery({
    queryKey: ['stores', 'active'],
    queryFn: () => getStores({ is_active: true }),
  });
  const stores: Store[] = storesData?.results ?? [];

  const validateDeliveryStep = (): boolean => {
    const errors: DeliveryErrors = {};
    if (!delivery.fullName.trim()) {
      errors.fullName = 'Укажите ФИО получателя';
    }
    if (!delivery.phone.trim()) {
      errors.phone = 'Укажите телефон';
    }
    if (delivery.deliveryType === 'pickup' && !delivery.storeId) {
      errors.storeId = 'Выберите магазин для самовывоза';
    }
    if (delivery.deliveryType === 'delivery') {
      if (!delivery.addressLine.trim()) {
        errors.addressLine = 'Укажите адрес доставки';
      } else {
        const addr = resolveDeliveryAddressForApi(delivery);
        if (!addr.city.trim()) {
          errors.city =
            'Укажите город или полный адрес через запятую: город, улица, дом';
        }
        if (!addr.street.trim() || !addr.house.trim()) {
          errors.addressLine = errors.addressLine ?? 'Укажите улицу и дом (можно через запятую)';
        }
      }
    }
    setDeliveryErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const validatePaymentStep = (): boolean => {
    const errors: PaymentErrors = {};
    if (!payment.paymentType) {
      errors.paymentType = 'Выберите способ оплаты';
    }
    setPaymentErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const canGoNext = (): boolean => {
    if (!cart || items.length === 0) return false;
    if (currentStep === 0) return true;
    if (currentStep === 1) return validateDeliveryStep();
    if (currentStep === 2) return validatePaymentStep();
    return true;
  };

  const handleNext = () => {
    if (!canGoNext()) return;
    setCurrentStep(prev => Math.min(prev + 1, STEPS.length - 1));
  };

  const handlePrev = () => {
    setCurrentStep(prev => Math.max(prev - 1, 0));
  };

  const handleSubmit = () => {
    setConsentError(null);
    if (!validateDeliveryStep() || !validatePaymentStep()) return;
    if (!consentPersonalData) {
      setConsentError('Необходимо согласие на обработку персональных данных');
      return;
    }
    const deliveryAddress =
      delivery.deliveryType === 'delivery'
        ? (() => {
            const a = resolveDeliveryAddressForApi(delivery);
            const out: Record<string, string | null> = {
              city: a.city,
              street: a.street,
              house: a.house,
            };
            if (a.apartment?.trim()) out.apartment = a.apartment.trim();
            return out;
          })()
        : {};
    // Позиции с клиента обязательны при from_cart: иначе на API пустая session-корзина → 400
    // (разные origin / cookie). Суммы и цены пересчитывает бэкенд из каталога.
    const payload = {
      from_cart: true,
      full_name: delivery.fullName.trim(),
      phone: delivery.phone.trim(),
      email: delivery.email.trim() || null,
      delivery_type: delivery.deliveryType,
      delivery_address: deliveryAddress,
      // Для доставки store не передаём (иначе 400: «Для доставки поле «магазин» не указывается»),
      // в т.ч. если пользователь переключился с самовывоза и storeId ещё в state.
      store:
        delivery.deliveryType === 'pickup' && delivery.storeId?.trim()
          ? delivery.storeId.trim()
          : null,
      payment_type: payment.paymentType!,
      items: items.map(item => ({
        product_id: item.product.id,
        quantity: item.quantity,
      })),
      total_amount: String(cartTotal.toFixed(2)),
      delivery_cost: '0',
      bonus_used: '0',
      comment: delivery.comment.trim() || null,
      consent_personal_data: true,
      consent_marketing: consentNewsletter,
    };
    const idempotencyKey =
      typeof crypto !== 'undefined' && crypto.randomUUID
        ? crypto.randomUUID()
        : `ck-${Date.now()}-${Math.random().toString(36).slice(2, 12)}`;
    createOrderMutation.mutate({
      data: payload,
      idempotencyKey,
      consentNewsletter,
    });
  };

  if (isLoading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <Loading />
      </div>
    );
  }

  if (isError || !cart || items.length === 0) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center px-4 text-center">
        <p className="mb-3 text-sm text-red-600 dark:text-red-400">
          Не удалось загрузить корзину для оформления заказа.
        </p>
        <Button asChild>
          <Link href="/cart">Вернуться в корзину</Link>
        </Button>
      </div>
    );
  }

  return (
    <PageContainer className="py-6">
      <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-50">
          Оформление заказа
        </h1>
        <p className="text-sm text-zinc-500 dark:text-zinc-400">
          Шаг {currentStep + 1} из {STEPS.length}
        </p>
      </div>

      {/* Вернуться к покупкам — корзина сохраняется */}
      <div className="mb-4">
        <Link
          href="/catalog"
          className="inline-flex items-center gap-1 text-sm text-[var(--color-brand)] hover:underline"
        >
          <ChevronLeft className="h-4 w-4" />
          Вернуться к покупкам
        </Link>
      </div>

      {/* Stepper */}
      <div className="mb-6 flex flex-wrap items-center gap-2 sm:gap-4">
        {STEPS.map((label, index) => {
          const isActive = index === currentStep;
          const isCompleted = index < currentStep;
          return (
            <div key={label} className="flex items-center gap-2">
              <div
                className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm font-medium ${
                  isCompleted
                    ? 'bg-[--color-brand] text-white'
                    : isActive
                      ? 'border-2 border-[--color-brand] bg-white text-[--color-brand]'
                      : 'border border-zinc-300 bg-white text-zinc-500'
                }`}
              >
                {isCompleted ? <Check className="h-4 w-4" /> : index + 1}
              </div>
              <span
                className={`text-sm ${
                  isActive
                    ? 'font-semibold text-zinc-900 dark:text-zinc-50'
                    : 'text-zinc-500 dark:text-zinc-400'
                }`}
              >
                {label}
              </span>
              {index < STEPS.length - 1 && (
                <div className="mx-1 h-px w-8 bg-zinc-200 dark:bg-zinc-800" />
              )}
            </div>
          );
        })}
      </div>

      <div className="flex flex-col gap-6 lg:flex-row">
        {/* Left: step content */}
        <div className="flex-1 space-y-4">
          {currentStep === 0 && (
            <Card className="space-y-3">
              <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">
                Шаг 1. Корзина
              </h2>
              <p className="text-sm text-zinc-600 dark:text-zinc-400">
                Проверьте состав заказа. Изменить количество или удалить товары можно на странице
                корзины.
              </p>
              <ul className="divide-y divide-zinc-200 text-sm dark:divide-zinc-800">
                {items.map(item => (
                  <li key={item.id} className="flex items-center justify-between gap-2 py-2">
                    <div>
                      <p className="font-medium text-zinc-900 dark:text-zinc-50">
                        {item.product.title}
                      </p>
                      <p className="text-xs text-zinc-500 dark:text-zinc-400">
                        {item.quantity} × {item.price_at_add} {CURRENCY_SYMBOL}
                      </p>
                    </div>
                    <p className="text-sm font-semibold text-zinc-900 dark:text-zinc-50">
                      {item.item_total} {CURRENCY_SYMBOL}
                    </p>
                  </li>
                ))}
              </ul>
              <div className="flex flex-wrap gap-2">
                <Button
                  asChild
                  variant="outline"
                  size="sm"
                  className="min-h-[44px] min-w-[44px] touch-manipulation sm:min-h-0 sm:min-w-0"
                >
                  <Link href="/cart">Перейти к корзине</Link>
                </Button>
                <Button
                  asChild
                  variant="ghost"
                  size="sm"
                  className="min-h-[44px] touch-manipulation sm:min-h-0"
                >
                  <Link href="/catalog">Вернуться к покупкам</Link>
                </Button>
              </div>
            </Card>
          )}

          {currentStep === 1 && (
            <Card className="space-y-4">
              <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">
                Шаг 2. Доставка
              </h2>

              {/* Контакты */}
              <div className="space-y-3">
                <div>
                  <label className="mb-1 block text-sm text-zinc-600 dark:text-zinc-400">
                    ФИО получателя
                  </label>
                  <Input
                    value={delivery.fullName}
                    onChange={e =>
                      setDelivery(prev => ({
                        ...prev,
                        fullName: e.target.value,
                      }))
                    }
                    placeholder="Иванов Иван Иванович"
                  />
                  {deliveryErrors.fullName && (
                    <p className="mt-1 text-xs text-red-600">{deliveryErrors.fullName}</p>
                  )}
                </div>
                <div className="flex flex-col gap-3 sm:flex-row">
                  <div className="flex-1">
                    <label className="mb-1 block text-sm text-zinc-600 dark:text-zinc-400">
                      Телефон
                    </label>
                    <Input
                      value={delivery.phone}
                      onChange={e =>
                        setDelivery(prev => ({
                          ...prev,
                          phone: e.target.value,
                        }))
                      }
                      placeholder="+7 777 123 45 67"
                    />
                    {deliveryErrors.phone && (
                      <p className="mt-1 text-xs text-red-600">{deliveryErrors.phone}</p>
                    )}
                  </div>
                  <div className="flex-1">
                    <label className="mb-1 block text-sm text-zinc-600 dark:text-zinc-400">
                      Email (необязательно)
                    </label>
                    <Input
                      value={delivery.email}
                      onChange={e =>
                        setDelivery(prev => ({
                          ...prev,
                          email: e.target.value,
                        }))
                      }
                      placeholder="you@example.com"
                    />
                  </div>
                </div>
              </div>

              {/* Тип доставки */}
              <div>
                <label className="mb-2 block text-sm text-zinc-600 dark:text-zinc-400">
                  Тип доставки
                </label>
                <div className="flex flex-wrap gap-2 text-sm">
                  <button
                    type="button"
                    className={`rounded-full border px-3 py-1 ${
                      delivery.deliveryType === 'pickup'
                        ? 'border-[--color-brand] bg-[--color-brand-soft] text-[--color-brand]'
                        : 'border-zinc-300 text-zinc-700 dark:border-zinc-700 dark:text-zinc-300'
                    }`}
                    onClick={() =>
                      setDelivery(prev => ({
                        ...prev,
                        deliveryType: 'pickup',
                      }))
                    }
                  >
                    Самовывоз
                  </button>
                  <button
                    type="button"
                    className={`rounded-full border px-3 py-1 ${
                      delivery.deliveryType === 'delivery'
                        ? 'border-[--color-brand] bg-[--color-brand-soft] text-[--color-brand]'
                        : 'border-zinc-300 text-zinc-700 dark:border-zinc-700 dark:text-zinc-300'
                    }`}
                    onClick={() =>
                      setDelivery(prev => ({
                        ...prev,
                        deliveryType: 'delivery',
                        storeId: null,
                      }))
                    }
                  >
                    Доставка
                  </button>
                </div>
              </div>

              {delivery.deliveryType === 'pickup' && (
                <StoreSelector
                  stores={stores}
                  selectedStoreId={delivery.storeId}
                  onSelectStore={storeId => setDelivery(prev => ({ ...prev, storeId }))}
                  error={deliveryErrors.storeId}
                />
              )}

              {delivery.deliveryType === 'delivery' && (
                <div className="space-y-3">
                  <div className="flex flex-col gap-3 sm:flex-row">
                    <div className="flex-1">
                      <label className="mb-1 block text-sm text-zinc-600 dark:text-zinc-400">
                        Город
                      </label>
                      <Input
                        value={delivery.city}
                        onChange={e =>
                          setDelivery(prev => ({
                            ...prev,
                            city: e.target.value,
                          }))
                        }
                        placeholder="Город"
                      />
                      {deliveryErrors.city && (
                        <p className="mt-1 text-xs text-red-600">{deliveryErrors.city}</p>
                      )}
                    </div>
                    <div className="flex-[2]">
                      <label className="mb-1 block text-sm text-zinc-600 dark:text-zinc-400">
                        Адрес доставки
                      </label>
                      <AddressAutocomplete
                        value={delivery.addressLine}
                        onChange={addressLine =>
                          setDelivery(prev => ({
                            ...prev,
                            addressLine,
                          }))
                        }
                        onSelect={({ address, coordinates }) =>
                          setDelivery(prev => ({
                            ...prev,
                            addressLine: address,
                            deliveryCoordinates: coordinates ?? null,
                          }))
                        }
                        placeholder="Улица, дом, квартира"
                        aria-label="Адрес доставки"
                      />
                      {deliveryErrors.addressLine && (
                        <p className="mt-1 text-xs text-red-600">{deliveryErrors.addressLine}</p>
                      )}
                    </div>
                  </div>
                </div>
              )}

              <div>
                <label className="mb-1 block text-sm text-zinc-600 dark:text-zinc-400">
                  Комментарий к заказу (необязательно)
                </label>
                <Input
                  value={delivery.comment}
                  onChange={e =>
                    setDelivery(prev => ({
                      ...prev,
                      comment: e.target.value,
                    }))
                  }
                  placeholder="Например: позвонить за час до доставки"
                />
              </div>
            </Card>
          )}

          {currentStep === 2 && (
            <Card className="space-y-4">
              <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">
                Шаг 3. Оплата
              </h2>
              <div className="space-y-3">
                <p className="text-sm text-zinc-600 dark:text-zinc-400">
                  Выберите удобный способ оплаты.
                </p>
                <div className="grid gap-2 text-sm sm:grid-cols-2">
                  {[
                    { value: 'cash', label: 'Наличными при получении' },
                    { value: 'card_on_delivery', label: 'Картой при получении' },
                    { value: 'bank_transfer', label: 'Банковский перевод' },
                    { value: 'online', label: 'Онлайн-оплата' },
                  ].map(opt => (
                    <button
                      key={opt.value}
                      type="button"
                      className={`rounded-xl border px-3 py-2 text-left ${
                        payment.paymentType === opt.value
                          ? 'border-[--color-brand] bg-[--color-brand-soft]'
                          : 'border-zinc-300 hover:bg-zinc-50 dark:border-zinc-700 dark:hover:bg-zinc-900'
                      }`}
                      onClick={() =>
                        setPayment({
                          paymentType: opt.value as PaymentType,
                        })
                      }
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
                {paymentErrors.paymentType && (
                  <p className="mt-1 text-xs text-red-600">{paymentErrors.paymentType}</p>
                )}
              </div>
            </Card>
          )}

          {currentStep === 3 && (
            <Card className="space-y-4">
              <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">
                Шаг 4. Подтверждение
              </h2>
              <div className="space-y-3 text-sm text-zinc-700 dark:text-zinc-300">
                <p>
                  Проверьте данные перед подтверждением. После нажатия кнопки заказ будет отправлен
                  в обработку.
                </p>
                <ul className="space-y-1">
                  <li>
                    <span className="font-medium">Получатель:</span> {delivery.fullName || '—'},{' '}
                    {delivery.phone || 'телефон не указан'}
                  </li>
                  <li>
                    <span className="font-medium">Доставка:</span>{' '}
                    {delivery.deliveryType === 'pickup' ? 'самовывоз' : 'доставка'}
                  </li>
                  <li>
                    <span className="font-medium">Адрес / магазин:</span>{' '}
                    {delivery.deliveryType === 'pickup'
                      ? (stores.find(s => s.id === delivery.storeId)?.name ?? 'не выбран')
                      : delivery.addressLine || 'не указан'}
                  </li>
                  <li>
                    <span className="font-medium">Оплата:</span>{' '}
                    {payment.paymentType ?? 'не выбрана'}
                  </li>
                </ul>
                <ConsentCheckboxes
                  className="mt-3 border-0 bg-transparent p-0"
                  consentPersonal={consentPersonalData}
                  onConsentPersonalChange={setConsentPersonalData}
                  consentMarketing={consentNewsletter}
                  onConsentMarketingChange={setConsentNewsletter}
                />
                {consentError && (
                  <p className="text-xs text-red-600 dark:text-red-400">{consentError}</p>
                )}
                {createOrderMutation.isError && (
                  <p className="text-xs text-red-600 dark:text-red-400">
                    {getFriendlyErrorMessage(createOrderMutation.error)}
                  </p>
                )}
              </div>
            </Card>
          )}
        </div>

        {/* Right: totals and promo */}
        <aside className="w-full space-y-4 lg:sticky lg:top-24 lg:w-80 lg:max-w-sm">
          <Card className="space-y-3">
            <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">
              Итоговая сумма
            </h2>
            <div className="space-y-2 text-sm">
              <div className="flex items-center justify-between">
                <span className="text-zinc-500 dark:text-zinc-400">Сумма товаров</span>
                <span className="font-medium text-zinc-900 dark:text-zinc-50">
                  {cartTotal.toFixed(2)} {CURRENCY_SYMBOL}
                </span>
              </div>
              <div className="mt-2 flex items-center justify-between border-t border-dashed border-zinc-200 pt-2 text-sm dark:border-zinc-800">
                <span className="font-medium text-zinc-900 dark:text-zinc-50">Итого к оплате</span>
                <span className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">
                  {cartTotal.toFixed(2)} {CURRENCY_SYMBOL}
                </span>
              </div>
            </div>
            <p className="pt-2 text-xs text-zinc-500 dark:text-zinc-400">
              Промокоды и скидки появятся здесь после подключения к API пересчёта — сумма заказа сейчас совпадает с
              корзиной и с тем, что сохранит сервер.
            </p>
          </Card>

          <div className="flex gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={currentStep === 0}
              onClick={handlePrev}
              className="flex-1"
            >
              <ChevronLeft className="mr-1 h-4 w-4" />
              Назад
            </Button>
            {currentStep < STEPS.length - 1 ? (
              <Button type="button" size="sm" onClick={handleNext} className="flex-1">
                Далее
                <ChevronRight className="ml-1 h-4 w-4" />
              </Button>
            ) : (
              <Button
                type="button"
                size="sm"
                onClick={handleSubmit}
                disabled={createOrderMutation.isPending}
                loading={createOrderMutation.isPending}
                className="flex-1"
              >
                Подтвердить заказ
              </Button>
            )}
          </div>

          <PlaceholderBlock
            title="Блок: Дополнительные условия checkout"
            note="Тут будут: рассрочка, подтверждение заказа по SMS и юридические уточнения."
          />
        </aside>
      </div>
    </PageContainer>
  );
}
