import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';

// ---------------------------------------------------------------------------
// Mock AuthContext — Login only uses useAuth().login
// ---------------------------------------------------------------------------
const mockLogin = vi.fn();

vi.mock('../context', () => ({
  useAuth: () => ({ login: mockLogin }),
  AuthProvider: ({ children }) => children,
}));

import Login from '../pages/auth/Login';

beforeEach(() => {
  vi.clearAllMocks();
});

describe('Login page', () => {
  it('renders email, password fields and sign in button', () => {
    render(
      <Login
        onNavigateRegister={() => {}}
        onNavigateForgot={() => {}}
        onNavigateVerify={() => {}}
        onSuccess={() => {}}
      />
    );

    expect(screen.getByRole('heading', { name: /institutional sign in/i })).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/officer@department\.gov\.in/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/••••••••/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
  });

  it('shows validation error when submitted with empty fields', async () => {
    render(
      <Login
        onNavigateRegister={() => {}}
        onNavigateForgot={() => {}}
        onNavigateVerify={() => {}}
        onSuccess={() => {}}
      />
    );

    await userEvent.click(screen.getByRole('button', { name: /sign in/i }));

    expect(
      await screen.findByText(/please enter both email and password/i)
    ).toBeInTheDocument();
    expect(mockLogin).not.toHaveBeenCalled();
  });

  it('calls login with email and password on valid submission', async () => {
    mockLogin.mockResolvedValueOnce({ user: { email: 'admin@dept.gov.in' } });

    const onSuccess = vi.fn();
    render(
      <Login
        onNavigateRegister={() => {}}
        onNavigateForgot={() => {}}
        onNavigateVerify={() => {}}
        onSuccess={onSuccess}
      />
    );

    await userEvent.type(
      screen.getByPlaceholderText(/officer@department\.gov\.in/i),
      'admin@dept.gov.in'
    );
    await userEvent.type(screen.getByPlaceholderText(/••••••••/), 'SecurePass!99');
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith('admin@dept.gov.in', 'SecurePass!99');
      expect(onSuccess).toHaveBeenCalledOnce();
    });
  });

  it('shows error alert on login failure', async () => {
    mockLogin.mockRejectedValueOnce(new Error('Invalid credentials.'));

    render(
      <Login
        onNavigateRegister={() => {}}
        onNavigateForgot={() => {}}
        onNavigateVerify={() => {}}
        onSuccess={() => {}}
      />
    );

    await userEvent.type(
      screen.getByPlaceholderText(/officer@department\.gov\.in/i),
      'bad@example.com'
    );
    await userEvent.type(screen.getByPlaceholderText(/••••••••/), 'wrongpassword');
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }));

    expect(
      await screen.findByText(/invalid credentials/i)
    ).toBeInTheDocument();
  });

  it('shows unverified state and verify link when server says not verified', async () => {
    mockLogin.mockRejectedValueOnce(new Error('Email is not verified.'));

    const onNavigateVerify = vi.fn();
    render(
      <Login
        onNavigateRegister={() => {}}
        onNavigateForgot={() => {}}
        onNavigateVerify={onNavigateVerify}
        onSuccess={() => {}}
      />
    );

    await userEvent.type(
      screen.getByPlaceholderText(/officer@department\.gov\.in/i),
      'pending@example.com'
    );
    await userEvent.type(screen.getByPlaceholderText(/••••••••/), 'anypassword');
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }));

    // Verify link appears
    const verifyLink = await screen.findByText(/verify your email now/i);
    expect(verifyLink).toBeInTheDocument();

    await userEvent.click(verifyLink);
    expect(onNavigateVerify).toHaveBeenCalledWith('pending@example.com');
  });

  it('calls onNavigateRegister when Create an account is clicked', async () => {
    const onNavigateRegister = vi.fn();
    render(
      <Login
        onNavigateRegister={onNavigateRegister}
        onNavigateForgot={() => {}}
        onNavigateVerify={() => {}}
        onSuccess={() => {}}
      />
    );

    await userEvent.click(screen.getByRole('button', { name: /create an account/i }));
    expect(onNavigateRegister).toHaveBeenCalledOnce();
  });

  it('calls onNavigateForgot when Forgot password is clicked', async () => {
    const onNavigateForgot = vi.fn();
    render(
      <Login
        onNavigateRegister={() => {}}
        onNavigateForgot={onNavigateForgot}
        onNavigateVerify={() => {}}
        onSuccess={() => {}}
      />
    );

    await userEvent.click(screen.getByRole('button', { name: /forgot password/i }));
    expect(onNavigateForgot).toHaveBeenCalledOnce();
  });
});

