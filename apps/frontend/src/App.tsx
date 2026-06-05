import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { TopologyCanvas } from './canvas/TopologyCanvas';
import { ReactFlowProvider } from '@xyflow/react';
import { useUiStore } from './store';
import { LogOut, Moon, Sun } from 'lucide-react';
import { api, type CurrentUser } from './services/api';
import { clearAuthToken, getAuthToken } from './services/authToken';
import './App.css';

function App() {
  const { theme, toggleTheme } = useUiStore();
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [authLoading, setAuthLoading] = useState(Boolean(getAuthToken()));
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('teacher@octet.local');
  const [password, setPassword] = useState('');
  const [authError, setAuthError] = useState<string | null>(null);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  useEffect(() => {
    const token = getAuthToken();
    if (!token) {
      return;
    }

    api.getCurrentUser()
      .then(setUser)
      .catch(() => {
        clearAuthToken();
        setUser(null);
      })
      .finally(() => setAuthLoading(false));
  }, []);

  const handleAuthSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setAuthError(null);
    setAuthLoading(true);
    try {
      const response = authMode === 'login'
        ? await api.login(email, password)
        : await api.register(email, password);
      setUser(response.user);
      setPassword('');
    } catch {
      setAuthError(authMode === 'login'
        ? 'Login failed. Check your email and password.'
        : 'Registration failed. Try another email or a longer password.');
    } finally {
      setAuthLoading(false);
    }
  };

  const handleLogout = () => {
    clearAuthToken();
    setUser(null);
    setPassword('');
  };

  if (!user) {
    return (
      <div className="auth-shell">
        <div className="auth-panel">
          <div>
            <h1>Octet</h1>
            <p>Sign in to save topologies, run simulations, and export reports.</p>
          </div>

          <div className="auth-tabs" role="tablist" aria-label="Authentication mode">
            <button
              className={authMode === 'login' ? 'active' : ''}
              type="button"
              onClick={() => setAuthMode('login')}
            >
              Login
            </button>
            <button
              className={authMode === 'register' ? 'active' : ''}
              type="button"
              onClick={() => setAuthMode('register')}
            >
              Register
            </button>
          </div>

          <form className="auth-form" onSubmit={handleAuthSubmit}>
            <label>
              Email
              <input
                autoComplete="email"
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required
              />
            </label>
            <label>
              Password
              <input
                autoComplete={authMode === 'login' ? 'current-password' : 'new-password'}
                minLength={8}
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
              />
            </label>
            {authError && <div className="auth-error">{authError}</div>}
            <button className="auth-submit" type="submit" disabled={authLoading}>
              {authLoading ? 'Working...' : authMode === 'login' ? 'Login' : 'Create account'}
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div style={{ width: '100vw', height: '100vh', display: 'flex', flexDirection: 'column' }}>
      <div style={{ height: '50px', background: 'var(--bg-canvas)', borderBottom: '1px solid var(--panel-border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 20px', fontWeight: 600 }}>
        <span>Octet</span>
        <div className="app-header-actions">
          <span className="user-pill">{user.email} · {user.accountTier}</span>
          <button className="icon-button" onClick={toggleTheme} aria-label="Toggle theme">
            {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
          </button>
          <button className="icon-button" onClick={handleLogout} aria-label="Logout">
            <LogOut size={18} />
          </button>
        </div>
      </div>
      <div style={{ flex: 1, position: 'relative' }}>
        <ReactFlowProvider>
          <TopologyCanvas />
        </ReactFlowProvider>
      </div>
    </div>
  );
}

export default App;
