import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { render } from '@testing-library/react';
import { YandexMetrika } from './YandexMetrika';

vi.mock('next/script', () => ({
  default: ({ id, children }: { id: string; children?: string }) => (
    <script id={id}>{children}</script>
  ),
}));

describe('YandexMetrika', () => {
  const originalEnv = process.env.NEXT_PUBLIC_YANDEX_METRICA_ID;

  beforeEach(() => {
    process.env.NEXT_PUBLIC_YANDEX_METRICA_ID = '12345678';
  });

  afterEach(() => {
    process.env.NEXT_PUBLIC_YANDEX_METRICA_ID = originalEnv;
    vi.restoreAllMocks();
  });

  it('does not render script when disabled', () => {
    const { container } = render(<YandexMetrika enabled={false} />);
    expect(container.querySelector('#yandex-metrika')).toBeNull();
  });

  it('renders script when enabled and counter id is set', () => {
    const { container } = render(<YandexMetrika enabled={true} />);
    expect(container.querySelector('#yandex-metrika')).not.toBeNull();
  });

  it('does not render when counter id is missing', () => {
    process.env.NEXT_PUBLIC_YANDEX_METRICA_ID = '';
    const { container } = render(<YandexMetrika enabled={true} />);
    expect(container.querySelector('#yandex-metrika')).toBeNull();
  });
});
