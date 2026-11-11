import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import DataTable from '../ui/DataTable';

describe('DataTable component', () => {
  const columns = [
    { key: 'name', header: 'Campaign Name' },
    { key: 'status', header: 'Status' },
  ];

  const data = [
    { id: 1, name: 'Polio Awareness', status: 'Delivered' },
    { id: 2, name: 'Nutrition Outreach', status: 'Pending' },
  ];

  it('renders table headers and rows correctly', () => {
    render(<DataTable columns={columns} data={data} />);

    expect(screen.getByRole('columnheader', { name: /campaign name/i })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: /status/i })).toBeInTheDocument();
    expect(screen.getByText('Polio Awareness')).toBeInTheDocument();
    expect(screen.getByText('Nutrition Outreach')).toBeInTheDocument();
  });

  it('renders loading skeletons when isLoading is true', () => {
    render(<DataTable columns={columns} data={[]} isLoading={true} />);
    const loadingRows = screen.getAllByRole('status');
    expect(loadingRows.length).toBeGreaterThan(0);
  });

  it('renders empty state when data is empty', () => {
    render(<DataTable columns={columns} data={[]} emptyTitle="No campaigns found" />);
    expect(screen.getByText('No campaigns found')).toBeInTheDocument();
  });

  it('renders error message and handles retry', async () => {
    const handleRetry = vi.fn();
    render(<DataTable columns={columns} data={[]} error="Failed to fetch campaigns" onRetry={handleRetry} />);

    expect(screen.getByText(/failed to fetch campaigns/i)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /retry/i }));
    expect(handleRetry).toHaveBeenCalledTimes(1);
  });
});

