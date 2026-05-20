import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import type { ReactNode } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('./canvas/TopologyCanvas', () => ({
  TopologyCanvas: () => <div>Canvas Ready</div>,
}));

vi.mock('@xyflow/react', () => ({
  ReactFlowProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
}));

vi.mock('./services/api', () => ({
  api: {
    getCurrentUser: vi.fn(),
    login: vi.fn(),
    register: vi.fn(),
  },
}));

const { api } = await import('./services/api');
const { setAuthToken } = await import('./services/authToken');
const { default: App } = await import('./App');

const mockedApi = vi.mocked(api);

describe('App auth flow', () => {
  beforeEach(() => {
    cleanup();
    window.localStorage.clear();
    vi.clearAllMocks();
  });

  it('logs in and renders the canvas for an authenticated user', async () => {
    mockedApi.login.mockResolvedValue({
      accessToken: 'token',
      tokenType: 'bearer',
      user: {
        id: 'user-1',
        email: 'teacher@example.com',
        role: 'designer',
        accountTier: 'free',
      },
    });

    render(<App />);

    fireEvent.change(screen.getByLabelText('Email'), {
      target: { value: 'teacher@example.com' },
    });
    fireEvent.change(screen.getByLabelText('Password'), {
      target: { value: 'valid-pass' },
    });
    fireEvent.click(screen.getAllByRole('button', { name: 'Login' }).at(-1)!);

    await waitFor(() => expect(screen.getByText('Canvas Ready')).toBeTruthy());
    expect(mockedApi.login).toHaveBeenCalledWith('teacher@example.com', 'valid-pass');
  });

  it('shows login errors and supports logout', async () => {
    mockedApi.login.mockRejectedValueOnce(new Error('nope'));

    render(<App />);
    fireEvent.change(screen.getByLabelText('Password'), {
      target: { value: 'wrong-pass' },
    });
    fireEvent.click(screen.getAllByRole('button', { name: 'Login' }).at(-1)!);

    await waitFor(() => {
      expect(screen.getByText('Login failed. Check your email and password.')).toBeTruthy();
    });

    setAuthToken('token');
    mockedApi.login.mockResolvedValueOnce({
      accessToken: 'token',
      tokenType: 'bearer',
      user: {
        id: 'user-1',
        email: 'teacher@example.com',
        role: 'designer',
        accountTier: 'free',
      },
    });
    fireEvent.change(screen.getByLabelText('Password'), {
      target: { value: 'valid-pass' },
    });
    fireEvent.click(screen.getAllByRole('button', { name: 'Login' }).at(-1)!);

    await waitFor(() => expect(screen.getByText('Canvas Ready')).toBeTruthy());
    fireEvent.click(screen.getByLabelText('Logout'));
    expect(screen.getAllByRole('button', { name: 'Login' }).length).toBeGreaterThan(0);
  });
});
