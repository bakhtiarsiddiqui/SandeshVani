import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';

// ---------------------------------------------------------------------------
// Mock AuthContext — ProtectedRoute imports useAuth; we control its output
// ---------------------------------------------------------------------------
const mockUseAuth = vi.fn();

vi.mock('../context', () => ({
  useAuth: () => mockUseAuth(),
  AuthProvider: ({ children }) => children,
}));

import ProtectedRoute from '../routes/ProtectedRoute';

beforeEach(() => {
  vi.clearAllMocks();
});

function ChildContent() {
  return <div data-testid="protected-content">Protected Content</div>;
}

describe('ProtectedRoute', () => {
  it('shows loading skeleton while auth is resolving', () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: false,
      isLoading: true,
      permissions: [],
    });

    render(
      <ProtectedRoute onNavigateToLogin={() => {}}>
        <ChildContent />
      </ProtectedRoute>
    );

    expect(
      screen.getByText(/authenticating institutional session/i)
    ).toBeInTheDocument();
    expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument();
  });

  it('shows authentication required prompt when unauthenticated', () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: false,
      isLoading: false,
      permissions: [],
    });

    render(
      <ProtectedRoute onNavigateToLogin={() => {}}>
        <ChildContent />
      </ProtectedRoute>
    );

    expect(
      screen.getByRole('heading', { name: /authentication required/i })
    ).toBeInTheDocument();
    expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument();
  });

  it('calls onNavigateToLogin when Sign In button is clicked while unauthenticated', async () => {
    const navigate = vi.fn();
    mockUseAuth.mockReturnValue({
      isAuthenticated: false,
      isLoading: false,
      permissions: [],
    });

    render(
      <ProtectedRoute onNavigateToLogin={navigate}>
        <ChildContent />
      </ProtectedRoute>
    );

    await userEvent.click(screen.getByRole('button', { name: /sign in/i }));
    expect(navigate).toHaveBeenCalledOnce();
  });

  it('renders children when authenticated with no required permissions', () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      permissions: [],
    });

    render(
      <ProtectedRoute onNavigateToLogin={() => {}}>
        <ChildContent />
      </ProtectedRoute>
    );

    expect(screen.getByTestId('protected-content')).toBeInTheDocument();
  });

  it('renders children when user holds all required permissions', () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      permissions: ['campaigns:create', 'campaigns:view'],
    });

    render(
      <ProtectedRoute
        requiredPermissions={['campaigns:create', 'campaigns:view']}
        onNavigateToLogin={() => {}}
      >
        <ChildContent />
      </ProtectedRoute>
    );

    expect(screen.getByTestId('protected-content')).toBeInTheDocument();
  });

  it('shows Access Denied when user is missing a required permission', () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      permissions: ['campaigns:view'],
    });

    render(
      <ProtectedRoute
        requiredPermissions={['campaigns:create', 'campaigns:approve']}
        onNavigateToLogin={() => {}}
      >
        <ChildContent />
      </ProtectedRoute>
    );

    expect(
      screen.getByRole('heading', { name: /access denied/i })
    ).toBeInTheDocument();
    expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument();
  });
});
