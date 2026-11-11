import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import App from './App';

// ---------------------------------------------------------------------------
// Mock the Axios client so no real network calls are made.
// AuthProvider calls POST /auth/refresh on mount; we return 401 to simulate
// an unauthenticated session, which puts the app on the login screen.
// ---------------------------------------------------------------------------
vi.mock('./api/client', () => {
  const mockClient = {
    post: vi.fn(() => Promise.reject({ response: { status: 401 } })),
    get: vi.fn(() => Promise.reject({ response: { status: 401 } })),
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
    defaults: { headers: { common: {} } },
  };
  return {
    default: mockClient,
    setAccessToken: vi.fn(),
    clearAccessToken: vi.fn(),
    setCsrfToken: vi.fn(),
    setActiveOrgId: vi.fn(),
    registerAuthFailureCallback: vi.fn(),
  };
});

beforeEach(() => {
  vi.clearAllMocks();
});

describe('App component — unauthenticated (login screen)', () => {
  it('shows the SandeshVani brand and tagline on the login screen', async () => {
    render(<App />);

    // Loading spinner first; wait for it to resolve
    const heading = await screen.findByRole('heading', { name: /sandeshvani/i });
    expect(heading).toBeInTheDocument();

    // Tagline present
    expect(
      screen.getByText(/har zaroori baat, har zaroori insaan tak/i)
    ).toBeInTheDocument();

    // Login form present
    expect(
      screen.getByRole('heading', { name: /institutional sign in/i })
    ).toBeInTheDocument();
  });

  it('renders the Sign In button on the login screen', async () => {
    render(<App />);

    const signInBtn = await screen.findByRole('button', { name: /sign in/i });
    expect(signInBtn).toBeInTheDocument();
  });

  it('renders the Create an account link on the login screen', async () => {
    render(<App />);

    const createLink = await screen.findByRole('button', { name: /create an account/i });
    expect(createLink).toBeInTheDocument();
  });

  it('renders the Forgot password link on the login screen', async () => {
    render(<App />);

    const forgotBtn = await screen.findByRole('button', { name: /forgot password/i });
    expect(forgotBtn).toBeInTheDocument();
  });
});

