import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { Order } from '@/types';
import OrderSuccessPage from './page';

vi.mock('@/lib/api/services/orders.service', () => ({
  getOrder: vi.fn().mockResolvedValue({
    id: 'o1',
    order_number: 'R-1001',
    full_name: 'Иван Иванов',
    phone: '+7 777 123 45 67',
    email: 'test@example.com',
    delivery_type: 'pickup',
    delivery_address: {},
    store: null,
    payment_type: 'cash',
    status: 'created',
    total_amount: '1000.00',
    delivery_cost: '0.00',
    bonus_used: '0.00',
    bonus_earned: '0.00',
    comment: null,
    items: [
      {
        id: 'oi1',
        product_title: 'Тестовый товар',
        quantity: 1,
        price: '1000.00',
        item_total: '1000.00',
      },
    ],
    created_at: '',
    updated_at: '',
  } satisfies Order),
}));

function renderWithClient(ui: React.ReactElement) {
  const client = new QueryClient();
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe('OrderSuccessPage', () => {
  it('renders order info', async () => {
    renderWithClient(<OrderSuccessPage params={{ id: 'o1' }} />);

    expect(await screen.findByText('Заказ оформлен')).toBeInTheDocument();
    expect(screen.getByText('R-1001')).toBeInTheDocument();
    expect(screen.getByText('Тестовый товар')).toBeInTheDocument();
  });
});
