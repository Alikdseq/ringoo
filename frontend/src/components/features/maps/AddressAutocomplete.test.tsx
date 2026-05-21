import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AddressAutocomplete } from './AddressAutocomplete';

const originalFetch = globalThis.fetch;

describe('AddressAutocomplete', () => {
  beforeEach(() => {
    vi.stubEnv('NEXT_PUBLIC_YANDEX_MAPS_API_KEY', 'test-key');
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.unstubAllEnvs();
  });

  it('renders input with value and placeholder', () => {
    const onChange = vi.fn();
    render(<AddressAutocomplete value="ул. Абая" onChange={onChange} placeholder="Улица, дом" />);

    const input = screen.getByRole('combobox', { name: undefined });
    expect(input).toHaveValue('ул. Абая');
    expect(input).toHaveAttribute('placeholder', 'Улица, дом');
  });

  it('calls onChange when user types', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<AddressAutocomplete value="" onChange={onChange} minLength={3} />);

    const input = screen.getByRole('combobox');
    await user.type(input, 'Алма');
    expect(onChange).toHaveBeenCalled();
    expect(onChange).toHaveBeenCalledTimes(4);
  });

  it('shows suggestions and calls onSelect when suggestion is clicked', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    const onSelect = vi.fn();

    globalThis.fetch = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          results: [
            {
              title: { text: 'Казахстан, Алматы, ул. Абая, 1' },
              subtitle: { text: '' },
              address: { formatted_address: 'Казахстан, Алматы, ул. Абая, 1' },
            },
          ],
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          response: {
            GeoObjectCollection: {
              featureMember: [
                {
                  GeoObject: {
                    Point: { pos: '76.945 43.238' },
                  },
                },
              ],
            },
          },
        }),
      });

    render(
      <AddressAutocomplete
        value="Абая"
        onChange={onChange}
        onSelect={onSelect}
        minLength={1}
        debounceMs={0}
      />
    );

    await new Promise(r => setTimeout(r, 20));
    const suggestion = await screen.findByRole('option', {
      name: /Казахстан.*Алматы.*Абая/,
    });
    await user.click(suggestion);

    expect(onChange).toHaveBeenCalledWith('Казахстан, Алматы, ул. Абая, 1');
    expect(onSelect).toHaveBeenCalledWith(
      expect.objectContaining({
        address: 'Казахстан, Алматы, ул. Абая, 1',
        coordinates: { lat: 43.238, lon: 76.945 },
      })
    );
  });

  it('does not request suggest when api key is missing', async () => {
    vi.stubEnv('NEXT_PUBLIC_YANDEX_MAPS_API_KEY', '');
    vi.stubEnv('NEXT_PUBLIC_YANDEX_SUGGEST_API_KEY', '');

    const fetchSpy = vi.fn();
    globalThis.fetch = fetchSpy;

    const user = userEvent.setup();
    render(<AddressAutocomplete value="" onChange={() => {}} minLength={1} debounceMs={0} />);

    await user.type(screen.getByRole('combobox'), 'Алматы');
    await new Promise(r => setTimeout(r, 50));

    expect(fetchSpy).not.toHaveBeenCalled();
  });
});
