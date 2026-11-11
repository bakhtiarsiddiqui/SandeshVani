import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import ConfirmDialog from '../ui/ConfirmDialog';

describe('ConfirmDialog component', () => {
  it('does not render when isOpen is false', () => {
    render(
      <ConfirmDialog
        isOpen={false}
        title="Revoke Membership"
        description="Are you sure you want to revoke this user access?"
      />
    );
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
  });

  it('renders modal with title, description, and focus on cancel button', async () => {
    render(
      <ConfirmDialog
        isOpen={true}
        title="Revoke Membership"
        description="Are you sure you want to revoke this user access?"
        cancelText="Keep Member"
        confirmText="Revoke Access"
      />
    );

    expect(screen.getByRole('alertdialog')).toBeInTheDocument();
    expect(screen.getByText('Revoke Membership')).toBeInTheDocument();
    expect(screen.getByText(/are you sure you want to revoke/i)).toBeInTheDocument();

    const cancelBtn = screen.getByRole('button', { name: /keep member/i });
    await waitFor(() => {
      expect(cancelBtn).toHaveFocus();
    });
  });

  it('calls onConfirm when confirm button clicked', async () => {
    const handleConfirm = vi.fn();
    render(
      <ConfirmDialog
        isOpen={true}
        title="Delete Segment"
        onConfirm={handleConfirm}
      />
    );

    await userEvent.click(screen.getByRole('button', { name: /confirm/i }));
    expect(handleConfirm).toHaveBeenCalledTimes(1);
  });

  it('calls onCancel when Escape key is pressed', async () => {
    const handleCancel = vi.fn();
    render(
      <ConfirmDialog
        isOpen={true}
        title="Cancel Campaign"
        onCancel={handleCancel}
      />
    );

    await userEvent.keyboard('{Escape}');
    expect(handleCancel).toHaveBeenCalledTimes(1);
  });
});

