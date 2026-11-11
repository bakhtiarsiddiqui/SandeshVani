import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import StatusBadge from '../ui/StatusBadge';

describe('StatusBadge component', () => {
  it('renders status text and appropriate role', () => {
    render(<StatusBadge status="delivered" />);
    const badge = screen.getByRole('status');
    expect(badge).toHaveTextContent(/delivered/i);
  });

  it('renders custom label when provided', () => {
    render(<StatusBadge status="pending" label="Under Human Review" />);
    expect(screen.getByRole('status')).toHaveTextContent(/under human review/i);
  });

  it('renders mock sandbox indicator correctly', () => {
    render(<StatusBadge status="mock_sandbox" />);
    expect(screen.getByRole('status')).toHaveTextContent(/sandbox mode/i);
  });
});

