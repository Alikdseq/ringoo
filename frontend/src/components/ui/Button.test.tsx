import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Button } from './Button';

describe('Button', () => {
  it('renders children', () => {
    render(<Button>Нажми</Button>);
    expect(screen.getByRole('button', { name: /нажми/i })).toBeInTheDocument();
  });

  it('calls onClick when clicked', () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Кнопка</Button>);
    fireEvent.click(screen.getByRole('button', { name: /кнопка/i }));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it('is disabled when disabled prop is true', () => {
    render(<Button disabled>Кнопка</Button>);
    expect(screen.getByRole('button')).toBeDisabled();
  });

  it('is disabled when loading', () => {
    render(<Button loading>Кнопка</Button>);
    expect(screen.getByRole('button')).toBeDisabled();
  });

  it('applies variant and size classes', () => {
    const { container } = render(
      <Button variant="outline" size="sm">
        Кнопка
      </Button>
    );
    const btn = container.querySelector('button');
    expect(btn).toHaveClass('rounded-full', 'h-9');
  });
});
