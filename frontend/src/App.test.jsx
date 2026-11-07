import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import App from './App';

describe('App component', () => {
  it('renders the SandeshVani brand and tagline', () => {
    render(<App />);

    expect(screen.getByText('SANDESHVANI')).toBeInTheDocument();
    expect(
      screen.getByRole('heading', {
        name: /har zaroori baat, har zaroori insaan tak\./i,
      })
    ).toBeInTheDocument();
    expect(
      screen.getByText(/your public communication workspace is being prepared\./i)
    ).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: /first ui checkpoint/i })
    ).toBeInTheDocument();
  });
});

