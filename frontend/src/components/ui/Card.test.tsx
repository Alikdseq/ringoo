import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Card } from './Card';

describe('Card', () => {
  it('renders children', () => {
    render(<Card>Контент карточки</Card>);
    expect(screen.getByText('Контент карточки')).toBeInTheDocument();
  });

  it('applies variant class', () => {
    const { container } = render(<Card variant="interactive">Текст</Card>);
    const card = container.firstChild as HTMLElement;
    expect(card.className).toMatch(/rounded-2xl/);
  });
});
