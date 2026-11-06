import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { StoreSelector } from './StoreSelector';

vi.mock('@/lib/api/services/stores.service', () => ({
  getStores: vi.fn(async () => []),
}));

const mockStores = [
  {
    id: 's1',
    name: 'Магазин Центр',
    slug: 'center',
    city: 'Алматы',
    address: 'ул. Абая 1',
    phone: null,
    coordinates: { latitude: '43.238', longitude: '76.945' },
    working_hours: null,
  },
  {
    id: 's2',
    name: 'Магазин Юг',
    slug: 'south',
    city: 'Алматы',
    address: 'ул. Толе би 2',
    phone: null,
    coordinates: { latitude: '43.220', longitude: '76.850' },
    working_hours: null,
  },
  {
    id: 's3',
    name: 'Магазин Астана',
    slug: 'astana',
    city: 'Астана',
    address: 'пр. Кабанбай батыра 3',
    phone: null,
    coordinates: null,
    working_hours: null,
  },
];

function renderSelector(ui: React.ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe('StoreSelector', () => {
  it('renders list and map with stores', () => {
    const onSelect = vi.fn();
    renderSelector(
      <StoreSelector stores={mockStores} selectedStoreId={null} onSelectStore={onSelect} />
    );

    expect(screen.getByText('Выберите магазин')).toBeInTheDocument();
    expect(screen.getByText('Магазины на карте')).toBeInTheDocument();
    expect(screen.getByText('Магазин Центр')).toBeInTheDocument();
    expect(screen.getByText('Магазин Юг')).toBeInTheDocument();
    expect(screen.getByText('Магазин Астана')).toBeInTheDocument();
    expect(screen.getByRole('combobox', { name: /Сортировка магазинов/ })).toBeInTheDocument();
  });

  it('calls onSelectStore when list item is clicked', async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    renderSelector(
      <StoreSelector stores={mockStores} selectedStoreId={null} onSelectStore={onSelect} />
    );

    await user.click(screen.getByText('Магазин Юг'));
    expect(onSelect).toHaveBeenCalledWith('s2');
  });

  it('filters list by search', async () => {
    const user = userEvent.setup();
    renderSelector(
      <StoreSelector stores={mockStores} selectedStoreId={null} onSelectStore={() => {}} />
    );

    const search = screen.getByPlaceholderText(/Поиск по городу или адресу/);
    await user.type(search, 'Астана');
    expect(screen.getByText('Магазин Астана')).toBeInTheDocument();
    expect(screen.queryByText('Магазин Центр')).not.toBeInTheDocument();
  });

  it('shows error message when error prop is set', () => {
    renderSelector(
      <StoreSelector
        stores={mockStores}
        selectedStoreId={null}
        onSelectStore={() => {}}
        error="Выберите магазин для самовывоза"
      />
    );
    expect(screen.getByText('Выберите магазин для самовывоза')).toBeInTheDocument();
  });

  it('shows empty state when no stores', () => {
    renderSelector(<StoreSelector stores={[]} selectedStoreId={null} onSelectStore={() => {}} />);
    expect(screen.getByText(/Нет доступных магазинов/)).toBeInTheDocument();
  });
});
