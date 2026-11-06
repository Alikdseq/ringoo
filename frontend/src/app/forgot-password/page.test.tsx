import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ForgotPasswordPage from './page';

vi.mock('@/lib/api/services/auth.service', () => ({
  requestPasswordReset: vi.fn(),
}));

vi.mock('@/lib/errors', () => ({
  getFriendlyErrorMessage: () => 'Ошибка',
}));

import { requestPasswordReset } from '@/lib/api/services/auth.service';

describe('ForgotPasswordPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders form and shows success after submit', async () => {
    vi.mocked(requestPasswordReset).mockResolvedValue({
      detail: 'Если аккаунт с таким email существует, мы отправили инструкции.',
    });
    render(<ForgotPasswordPage />);
    expect(screen.getByRole('heading', { name: /забыли пароль/i })).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText(/email/i), 'buyer@example.com');
    await userEvent.click(screen.getByRole('button', { name: /отправить ссылку/i }));
    await waitFor(() => {
      expect(requestPasswordReset).toHaveBeenCalledWith('buyer@example.com');
    });
    expect(
      await screen.findByText(/если аккаунт с таким email существует/i)
    ).toBeInTheDocument();
  });
});
