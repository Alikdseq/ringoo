import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import OrderSuccessPage from './page';

vi.mock('next/navigation', () => ({
  useSearchParams: () => new URLSearchParams('order_number=R-GUEST-42'),
}));

describe('Public OrderSuccessPage (/orders/success)', () => {
  it('shows order_number from query without calling order APIs', async () => {
    render(<OrderSuccessPage />);

    expect(await screen.findByText('Заказ оформлен')).toBeInTheDocument();
    expect(screen.getByText('R-GUEST-42')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Проверить статус заказа/i })).toHaveAttribute(
      'href',
      '/order-status'
    );
  });
});
