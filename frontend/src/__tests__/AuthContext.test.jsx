import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { AuthProvider, useAuth } from '../context';

// ---------------------------------------------------------------------------
// Shared mock for the Axios client
// ---------------------------------------------------------------------------
const mockPost = vi.fn();
const mockGet = vi.fn();

vi.mock('../api/client', () => ({
  default: {
    post: (...args) => mockPost(...args),
    get: (...args) => mockGet(...args),
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
    defaults: { headers: { common: {} } },
  },
  setAccessToken: vi.fn(),
  clearAccessToken: vi.fn(),
  setCsrfToken: vi.fn(),
  setActiveOrgId: vi.fn(),
  registerAuthFailureCallback: vi.fn(),
}));

beforeEach(() => {
  vi.clearAllMocks();
  // Default: refresh endpoint returns 401 (unauthenticated)
  mockPost.mockRejectedValue({ response: { status: 401 } });
  mockGet.mockRejectedValue({ response: { status: 401 } });
});

// ---------------------------------------------------------------------------
// Helper: a consumer component that exposes auth state via data-testid
// ---------------------------------------------------------------------------
function AuthConsumer() {
  const { isAuthenticated, isLoading, user, error } = useAuth();
  return (
    <div>
      <span data-testid="loading">{String(isLoading)}</span>
      <span data-testid="auth">{String(isAuthenticated)}</span>
      <span data-testid="email">{user?.email ?? 'none'}</span>
      <span data-testid="error">{error ?? ''}</span>
    </div>
  );
}


function LoginConsumer({ email = 'test@example.com', password = 'password' }) {
  const { login, isAuthenticated, error } = useAuth();

  return (
    <div>
      <span data-testid="auth">{String(isAuthenticated)}</span>
      <span data-testid="error">{error ?? ''}</span>

      <button
        onClick={async () => {
          try {
            await login(email, password);
          } catch {
            // Expected in tests that verify failed authentication.
          }
        }}
      >
        Login
      </button>
    </div>
  );
}


// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------
describe('AuthContext', () => {
  it('starts in loading state and resolves to unauthenticated when refresh fails', async () => {
    render(
      <AuthProvider>
        <AuthConsumer />
      </AuthProvider>
    );

    // Initially loading
    expect(screen.getByTestId('loading').textContent).toBe('true');

    // After mount effect resolves (refresh returned 401)
    await waitFor(() => {
      expect(screen.getByTestId('loading').textContent).toBe('false');
    });

    expect(screen.getByTestId('auth').textContent).toBe('false');
    expect(screen.getByTestId('email').textContent).toBe('none');
  });

  it('restores session when refresh token is valid', async () => {
    // Arrange: refresh succeeds, then /me returns user data
    mockPost.mockResolvedValueOnce({
      data: { access_token: 'jwt.access.token', csrf_token: 'csrf123' },
    });
    mockGet.mockResolvedValueOnce({
      data: {
        user: { id: 'u1', email: 'restored@example.com' },
        active_organization: { id: 'org1', name: 'Dept', slug: 'dept' },
        organizations: [{ id: 'org1', name: 'Dept', slug: 'dept' }],
        roles: ['org_admin'],
        permissions: ['campaigns:create'],
      },
    });

    render(
      <AuthProvider>
        <AuthConsumer />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('loading').textContent).toBe('false');
    });

    expect(screen.getByTestId('auth').textContent).toBe('true');
    expect(screen.getByTestId('email').textContent).toBe('restored@example.com');
  });

  it('sets authenticated state after successful login', async () => {
    // Arrange: refresh returns 401 (unauthenticated); then login succeeds
    mockPost
      .mockRejectedValueOnce({ response: { status: 401 } }) // initial refresh
      .mockResolvedValueOnce({
        // login
        data: {
          access_token: 'login.token',
          csrf_token: 'csrf.login',
          user: { id: 'u2', email: 'admin@dept.gov.in' },
          active_organization: { id: 'org2', name: 'Public Health', slug: 'pub-health' },
          roles: ['campaign_manager'],
          permissions: ['campaigns:view'],
        },
      });

    mockGet.mockResolvedValueOnce({
      data: {
        user: { id: 'u2', email: 'admin@dept.gov.in' },
        active_organization: { id: 'org2', name: 'Public Health', slug: 'pub-health' },
        organizations: [{ id: 'org2', name: 'Public Health', slug: 'pub-health' }],
        roles: ['campaign_manager'],
        permissions: ['campaigns:view'],
      },
    });

    render(
      <AuthProvider>
        <LoginConsumer email="admin@dept.gov.in" password="secure123" />
      </AuthProvider>
    );

    // Wait for initial loading to finish
    await waitFor(() => {
      expect(screen.getByTestId('auth').textContent).toBe('false');
    });

    // Trigger login
    await act(async () => {
      await userEvent.click(screen.getByRole('button', { name: 'Login' }));
    });

    await waitFor(() => {
      expect(screen.getByTestId('auth').textContent).toBe('true');
    });
  });

  it('sets error message on failed login', async () => {
    // Both refresh and login fail
    mockPost
      .mockRejectedValueOnce({ response: { status: 401 } }) // refresh
      .mockRejectedValueOnce({
        response: { status: 401, data: { detail: 'Invalid credentials.' } },
      }); // login

    render(
      <AuthProvider>
        <LoginConsumer />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('auth').textContent).toBe('false');
    });

    await act(async () => {
      await userEvent.click(screen.getByRole('button', { name: 'Login' }));
    });

    await waitFor(() => {
      expect(screen.getByTestId('error').textContent).toBe('Invalid credentials.');
    });

    expect(screen.getByTestId('auth').textContent).toBe('false');
  });

  it('throws when useAuth is used outside AuthProvider', () => {
    // Suppress React error boundary noise
    const spy = vi.spyOn(console, 'error').mockImplementation(() => { });

    expect(() => render(<AuthConsumer />)).toThrow(
      'useAuth must be used within an AuthProvider'
    );

    spy.mockRestore();
  });
});
