import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

const push = vi.fn();
const searchParams = new URLSearchParams('uid=abc&token=tok-123');

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push }),
  useSearchParams: () => searchParams,
}));

vi.mock('@/lib/api/services/auth.service', () => ({
  confirmPasswordReset: vi.fn(),
}));

vi.mock('@/lib/errors', () => ({
  getFriendlyErrorMessage: () => 'Ссылка недействительна',
}));

import { confirmPasswordReset } from '@/lib/api/services/auth.service';
import ResetPasswordPage from './page';

describe('ResetPasswordPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('submits new password with uid and token from query', async () => {
    vi.mocked(confirmPasswordReset).mockResolvedValue({ detail: 'ok' });
    render(<ResetPasswordPage />);
    expect(screen.getByRole('heading', { name: /новый пароль/i })).toBeInTheDocument();
    const inputs = screen.getAllByDisplayValue('');
    // two password fields
    await userEvent.type(screen.getByLabelText(/новый пароль/i), 'NewPassword2!');
    await userEvent.type(screen.getByLabelText(/повторите пароль/i), 'NewPassword2!');
    await userEvent.click(screen.getByRole('button', { name: /сохранить пароль/i }));
    await waitFor(() => {
      expect(confirmPasswordReset).toHaveBeenCalledWith({
        uid: 'abc',
        token: 'tok-123',
        new_password: 'NewPassword2!',
      });
    });
    expect(await screen.findByText(/пароль обновлён/i)).toBeInTheDocument();
    void inputs;
  });
});
