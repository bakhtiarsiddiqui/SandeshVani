import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import AppShell from '../layout/AppShell';

describe('AppShell layout', () => {
  it('renders persistent sandbox warning strip', () => {
    render(
      <AppShell>
        <div>Test Content</div>
      </AppShell>
    );

    expect(screen.getByRole('region', { name: /sandbox environment banner/i })).toBeInTheDocument();
    expect(screen.getByText(/sandbox \/ mock mode/i)).toBeInTheDocument();
    expect(screen.getByText(/simulated messaging channels only/i)).toBeInTheDocument();
  });

  it('renders active organization name and tenant badge', () => {
    render(
      <AppShell organizationName="State Literacy Mission">
        <div>Content</div>
      </AppShell>
    );

    expect(screen.getByText('State Literacy Mission')).toBeInTheDocument();
    expect(screen.getByText(/tenant isolated/i)).toBeInTheDocument();
  });

  it('renders main navigation and main children content', () => {
    render(
      <AppShell>
        <div data-testid="dashboard-content">Dashboard Area</div>
      </AppShell>
    );

    expect(screen.getByRole('navigation', { name: /main navigation/i })).toBeInTheDocument();
    expect(screen.getByTestId('dashboard-content')).toBeInTheDocument();
  });
});

