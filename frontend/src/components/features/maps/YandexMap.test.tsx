import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { YandexMap } from './YandexMap';

vi.mock('next/script', () => ({
  __esModule: true,
  default: (props: any) => <>{props.children}</>,
}));

describe('YandexMap', () => {
  it('renders map container when markers are provided', () => {
    process.env.NEXT_PUBLIC_YANDEX_MAPS_API_KEY = 'test-key';

    render(
      <YandexMap
        markers={[
          {
            id: 'm1',
            coordinates: [55.751244, 37.618423],
            title: 'Test marker',
          },
        ]}
      />
    );

    expect(screen.getByTestId('yandex-map-container')).toBeInTheDocument();
  });
});
