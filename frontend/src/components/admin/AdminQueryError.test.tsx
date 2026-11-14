import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { AdminQueryError } from './AdminQueryError';

describe('AdminQueryError (B8-007)', () => {
  it('shows not-found title for 404 without eternal loading', () => {
    render(
      <AdminQueryError
        error={{ response: { status: 404 } }}
        resourceLabel="товар"
        backHref="/admin/products"
      />
    );
    expect(screen.getByText(/товар не найден/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Назад/i })).toHaveAttribute(
      'href',
      '/admin/products'
    );
  });

  it('shows forbidden for 403', () => {
    render(
      <AdminQueryError error={{ response: { status: 403 } }} resourceLabel="пользователь" />
    );
    expect(screen.getByText('Недостаточно прав')).toBeInTheDocument();
  });

  it('offers retry for 500', async () => {
    const onRetry = vi.fn();
    const user = userEvent.setup();
    render(
      <AdminQueryError
        error={{ response: { status: 500 } }}
        resourceLabel="заявка"
        onRetry={onRetry}
      />
    );
    await user.click(screen.getByRole('button', { name: /Повторить/i }));
    expect(onRetry).toHaveBeenCalled();
  });
});
