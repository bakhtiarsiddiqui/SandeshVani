import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import ApprovalQueue from './ApprovalQueue';

const items = [
  { id: 'approval-1', title: 'Dengue advisory', requestedBy: 'A. Rao', requestedAt: '2 hours ago' },
];

describe('ApprovalQueue', () => {
  it('disables actions when no approval handlers are connected', () => {
    render(<ApprovalQueue items={items} />);

    expect(screen.getByRole('button', { name: 'Approve' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Reject' })).toBeDisabled();
    expect(screen.getByText(/unavailable in this prototype/i)).toBeInTheDocument();
  });

  it('invokes the supplied handler with the approval identifier', () => {
    const onApprove = vi.fn();
    const onReject = vi.fn();
    render(<ApprovalQueue items={items} onApprove={onApprove} onReject={onReject} />);

    fireEvent.click(screen.getByRole('button', { name: 'Approve' }));
    fireEvent.click(screen.getByRole('button', { name: 'Reject' }));

    expect(onApprove).toHaveBeenCalledWith('approval-1');
    expect(onReject).toHaveBeenCalledWith('approval-1');
  });
});
