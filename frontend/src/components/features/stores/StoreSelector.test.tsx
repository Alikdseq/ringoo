import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { StoreSelector } from './StoreSelector';

vi.mock('@/components/features/stores/StoresMap', () => ({
  StoresMap: ({
    stores,
    selectedStoreId,
    onSelectStore,
  }: {
    stores: { id: string; name: string }[];
    selectedStoreId: string | null;
    onSelectStore: (id: string) => void;
  }) => (
    <div data-testid="stores-map">
      <span>Map: {stores.length} stores</span>
      {selectedStoreId && <span data-testid="map-selected">{selectedStoreId}</span>}
      <button type="button" onClick={() => onSelectStore(stores[0]?.id ?? '')}>
        Select first
      </button>
    </div>
  ),
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

describe('StoreSelector', () => {
  it('renders list and map with stores', () => {
    const onSelect = vi.fn();
    render(<StoreSelector stores={mockStores} selectedStoreId={null} onSelectStore={onSelect} />);

    expect(screen.getByText('Выберите магазин')).toBeInTheDocument();
    expect(screen.getByText('Магазины на карте')).toBeInTheDocument();
    expect(screen.getByText('Магазин Центр')).toBeInTheDocument();
    expect(screen.getByText('Магазин Юг')).toBeInTheDocument();
    expect(screen.getByText('Магазин Астана')).toBeInTheDocument();
    expect(screen.getByTestId('stores-map')).toBeInTheDocument();
    expect(screen.getByRole('combobox', { name: /Сортировка магазинов/ })).toBeInTheDocument();
  });

  it('calls onSelectStore when list item is clicked', async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(<StoreSelector stores={mockStores} selectedStoreId={null} onSelectStore={onSelect} />);

    await user.click(screen.getByText('Магазин Юг'));
    expect(onSelect).toHaveBeenCalledWith('s2');
  });

  it('filters list by search', async () => {
    const user = userEvent.setup();
    render(<StoreSelector stores={mockStores} selectedStoreId={null} onSelectStore={() => {}} />);

    const search = screen.getByPlaceholderText(/Поиск по городу или адресу/);
    await user.type(search, 'Астана');
    expect(screen.getByText('Магазин Астана')).toBeInTheDocument();
    expect(screen.queryByText('Магазин Центр')).not.toBeInTheDocument();
  });

  it('shows error message when error prop is set', () => {
    render(
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
    render(<StoreSelector stores={[]} selectedStoreId={null} onSelectStore={() => {}} />);
    expect(screen.getByText(/Нет доступных магазинов/)).toBeInTheDocument();
  });
});
