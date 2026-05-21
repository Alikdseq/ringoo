'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { MapPin, Plus, Pencil, Trash2 } from 'lucide-react';
import { useAuth } from '@/lib/hooks/useAuth';
import {
  getAddresses,
  createAddress,
  updateAddress,
  deleteAddress,
  type CreateAddressBody,
} from '@/lib/api/services/addresses.service';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Loading } from '@/components/ui/Loading';
import type { DeliveryAddress } from '@/types';

const emptyForm: CreateAddressBody = {
  title: '',
  city: '',
  street: '',
  house: '',
  apartment: '',
  postal_code: '',
  is_default: false,
};

export default function ProfileAddressesPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { isAuthenticated, isLoading: authLoading, hasToken } = useAuth();
  const [editingId, setEditingId] = useState<number | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<CreateAddressBody & { id?: number }>(emptyForm);

  const { data, isLoading } = useQuery({
    queryKey: ['addresses'],
    queryFn: getAddresses,
    enabled: isAuthenticated,
  });
  const addresses = Array.isArray(data) ? data : [];

  const createMutation = useMutation({
    mutationFn: createAddress,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['addresses'] });
      setForm(emptyForm);
      setShowForm(false);
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, body }: { id: number; body: Partial<CreateAddressBody> }) =>
      updateAddress(id, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['addresses'] });
      setEditingId(null);
      setForm(emptyForm);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteAddress,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['addresses'] }),
  });

  useEffect(() => {
    if (authLoading) return;
    if (hasToken) return;
    if (!isAuthenticated) {
      router.replace(`/login?next=${encodeURIComponent('/profile/addresses')}`);
    }
  }, [authLoading, hasToken, isAuthenticated, router]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (form.id != null) {
      updateMutation.mutate({
        id: form.id,
        body: {
          title: form.title,
          city: form.city,
          street: form.street,
          house: form.house,
          apartment: form.apartment || null,
          postal_code: form.postal_code || null,
          is_default: form.is_default,
        },
      });
    } else {
      createMutation.mutate({
        title: form.title,
        city: form.city,
        street: form.street,
        house: form.house,
        apartment: form.apartment || null,
        postal_code: form.postal_code || null,
        is_default: form.is_default,
      });
    }
  };

  const startEdit = (addr: DeliveryAddress) => {
    setEditingId(addr.id);
    setForm({
      id: addr.id,
      title: addr.title,
      city: addr.city,
      street: addr.street,
      house: addr.house,
      apartment: addr.apartment ?? '',
      postal_code: addr.postal_code ?? '',
      is_default: addr.is_default,
    });
    setShowForm(false);
  };

  if (authLoading || !isAuthenticated) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <Loading />
      </div>
    );
  }

  return (
    <div className="mx-auto w-full max-w-2xl px-4 py-8 sm:px-6 lg:px-8">
      <nav
        className="mb-6 flex items-center gap-2 text-sm text-foreground-muted"
        aria-label="Хлебные крошки"
      >
        <Link href="/" className="hover:text-foreground">
          Главная
        </Link>
        <span aria-hidden>/</span>
        <Link href="/profile" className="hover:text-foreground">
          Профиль
        </Link>
        <span aria-hidden>/</span>
        <span className="text-foreground">Адреса доставки</span>
      </nav>

      <h1 className="mb-6 text-2xl font-semibold text-foreground">Мои адреса</h1>

      {!showForm && editingId === null && (
        <Button
          variant="secondary"
          className="mb-4 flex items-center gap-2"
          onClick={() => {
            setForm(emptyForm);
            setShowForm(true);
            setEditingId(null);
          }}
        >
          <Plus className="h-4 w-4" />
          Добавить адрес
        </Button>
      )}

      {(showForm || editingId !== null) && (
        <Card className="mb-6 p-4">
          <form onSubmit={handleSubmit} className="space-y-3">
            <Input
              placeholder="Название (Дом, Работа)"
              value={form.title}
              onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
              required
            />
            <Input
              placeholder="Город"
              value={form.city}
              onChange={e => setForm(f => ({ ...f, city: e.target.value }))}
              required
            />
            <div className="grid grid-cols-2 gap-2">
              <Input
                placeholder="Улица"
                value={form.street}
                onChange={e => setForm(f => ({ ...f, street: e.target.value }))}
                required
              />
              <Input
                placeholder="Дом"
                value={form.house}
                onChange={e => setForm(f => ({ ...f, house: e.target.value }))}
                required
              />
            </div>
            <div className="flex gap-2">
              <Input
                placeholder="Квартира"
                value={form.apartment ?? ''}
                onChange={e => setForm(f => ({ ...f, apartment: e.target.value || null }))}
              />
              <Input
                placeholder="Индекс"
                value={form.postal_code ?? ''}
                onChange={e => setForm(f => ({ ...f, postal_code: e.target.value || null }))}
              />
            </div>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={form.is_default}
                onChange={e => setForm(f => ({ ...f, is_default: e.target.checked }))}
                className="rounded border-border"
              />
              Адрес по умолчанию
            </label>
            <div className="flex gap-2">
              <Button type="submit" loading={createMutation.isPending || updateMutation.isPending}>
                {form.id != null ? 'Сохранить' : 'Добавить'}
              </Button>
              <Button
                type="button"
                variant="secondary"
                onClick={() => {
                  setShowForm(false);
                  setEditingId(null);
                  setForm(emptyForm);
                }}
              >
                Отмена
              </Button>
            </div>
          </form>
        </Card>
      )}

      {isLoading ? (
        <Loading />
      ) : addresses.length === 0 ? (
        <Card className="p-8 text-center text-foreground-muted">
          <MapPin className="mx-auto mb-2 h-10 w-10 opacity-50" />
          <p>Нет сохранённых адресов.</p>
        </Card>
      ) : (
        <ul className="space-y-4">
          {addresses.map(addr => (
            <li key={addr.id}>
              <Card className="flex items-start justify-between gap-4 p-4">
                <div>
                  <p className="font-medium text-foreground">
                    {addr.title}
                    {addr.is_default && (
                      <span className="ml-2 text-xs text-foreground-muted">(по умолчанию)</span>
                    )}
                  </p>
                  <p className="text-sm text-foreground-muted">
                    {addr.city}, {addr.street}, {addr.house}
                    {addr.apartment ? `, кв. ${addr.apartment}` : ''}
                    {addr.postal_code ? `, ${addr.postal_code}` : ''}
                  </p>
                </div>
                <div className="flex shrink-0 gap-1">
                  <button
                    type="button"
                    onClick={() => startEdit(addr)}
                    className="rounded p-2 text-foreground-muted hover:bg-zinc-100 hover:text-foreground"
                    aria-label="Редактировать"
                  >
                    <Pencil className="h-4 w-4" />
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      if (confirm('Удалить адрес?')) deleteMutation.mutate(addr.id);
                    }}
                    className="rounded p-2 text-foreground-muted hover:bg-red-50 hover:text-danger"
                    aria-label="Удалить"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </Card>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
