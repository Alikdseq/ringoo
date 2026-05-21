import { describe, expect, it, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import type { CartItem as CartItemType } from '@/types';
import { CartItem } from './CartItem';

const item: CartItemType = {
  id: 'item1',
  quantity: 2,
  price_at_add: '1000.00',
  item_total: '2000.00',
  created_at: '',
  updated_at: '',
  product: {
    id: 'p1',
    title: 'Тестовый товар',
    slug: 'test-product',
    price: '1000.00',
    old_price: null,
    rating: 4.5,
    reviews_count: 10,
    category: {
      id: 'c1',
      title: 'Категория',
      slug: 'cat',
      parent: null,
      description: null,
    },
  },
  store: null,
};

describe('CartItem', () => {
  it('renders product title and total', () => {
    render(<CartItem item={item} onIncrease={vi.fn()} onDecrease={vi.fn()} onRemove={vi.fn()} />);

    expect(screen.getByText('Тестовый товар')).toBeInTheDocument();
    expect(screen.getByText('2000.00 ₽')).toBeInTheDocument();
  });

  it('calls handlers on actions', () => {
    const onIncrease = vi.fn();
    const onDecrease = vi.fn();
    const onRemove = vi.fn();

    render(
      <CartItem item={item} onIncrease={onIncrease} onDecrease={onDecrease} onRemove={onRemove} />
    );

    fireEvent.click(screen.getByLabelText('Увеличить количество'));
    fireEvent.click(screen.getByLabelText('Уменьшить количество'));
    fireEvent.click(screen.getByLabelText('Удалить из корзины'));

    expect(onIncrease).toHaveBeenCalled();
    expect(onDecrease).toHaveBeenCalled();
    expect(onRemove).toHaveBeenCalled();
  });
});
