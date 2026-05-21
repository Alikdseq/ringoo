import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Input } from './Input';

describe('Input', () => {
  it('renders input with placeholder', () => {
    render(<Input placeholder="Введите текст" />);
    expect(screen.getByPlaceholderText('Введите текст')).toBeInTheDocument();
  });

  it('shows error message when error prop is set', () => {
    render(<Input error="Обязательное поле" />);
    expect(screen.getByText('Обязательное поле')).toBeInTheDocument();
  });

  it('renders prefix and suffix', () => {
    render(<Input prefix="+" suffix="₽" />);
    expect(screen.getByText('+')).toBeInTheDocument();
    expect(screen.getByText('₽')).toBeInTheDocument();
  });

  it('is disabled when disabled prop is true', () => {
    render(<Input disabled />);
    expect(screen.getByRole('textbox')).toBeDisabled();
  });
});
