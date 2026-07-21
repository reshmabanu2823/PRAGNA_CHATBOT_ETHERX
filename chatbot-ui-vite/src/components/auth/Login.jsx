import { useState } from 'react';
import '../../styles/auth.css';
import { authAPI } from '../../api/authAPI';
import pragnaLogo from '../../assets/pragna-logo-full.png';

// The animated backdrop used to be a Vanta.js WebGL globe pulled from two
// CDNs (three.js r128 + vanta.globe) on every mount. That cost ~600KB over a
// sequential request waterfall, ran a continuous WebGL render loop with
// mouse/touch listeners, and never cleaned up its injected <script> tags -
// which is what made typing and navigating the auth flow feel laggy. It's now
// a pure-CSS gradient drift (see .auth-canvas in auth.css) that animates only
// transform/opacity, so it stays on the compositor and never blocks input.

export default function Login({ onLoginSuccess }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [showRegister, setShowRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [showForgotPassword, setShowForgotPassword] = useState(false);
  const [resetEmail, setResetEmail] = useState('');
  const [resetSent, setResetSent] = useState(false);
  const [resetLoading, setResetLoading] = useState(false);

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');

    // Validate locally first so obvious mistakes surface instantly instead of
    // costing a network round-trip.
    const trimmedUsername = username.trim();
    if (!trimmedUsername || !password) {
      setError('Enter your username and password.');
      return;
    }

    setLoading(true);

    try {
      const data = await authAPI.login(trimmedUsername, password);

      if (data.error) {
        setError(data.error || 'Login failed');
        return;
      }

      // Save token and user info
      localStorage.setItem('authToken', data.token);
      localStorage.setItem('userId', data.user_id);
      const resolvedUsername = data.username || trimmedUsername;
      const resolvedEmail = data.email || localStorage.getItem('authEmail') || '';
      localStorage.setItem('authUsername', resolvedUsername);
      if (resolvedEmail) {
        localStorage.setItem('authEmail', resolvedEmail);
      }
      
      onLoginSuccess(data.user_id, data.token, {
        username: resolvedUsername,
        email: resolvedEmail,
      });
    } catch {
      setError('Network error. Try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setError('');

    // Mirror the backend's rules client-side so the user gets the feedback
    // immediately rather than after a failed round-trip.
    const trimmedUsername = username.trim();
    const trimmedEmail = email.trim();
    if (!trimmedUsername || !trimmedEmail || !password) {
      setError('Fill in every field to create your account.');
      return;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmedEmail)) {
      setError('Enter a valid email address.');
      return;
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }

    setLoading(true);

    try {
      const data = await authAPI.register(trimmedUsername, trimmedEmail, password);

      if (data.error) {
        setError(data.error || 'Registration failed');
        return;
      }

      // Save token and user info
      localStorage.setItem('authToken', data.token);
      localStorage.setItem('userId', data.user_id);
      const resolvedUsername = data.username || trimmedUsername;
      const resolvedEmail = data.email || trimmedEmail;
      localStorage.setItem('authUsername', resolvedUsername);
      if (resolvedEmail) {
        localStorage.setItem('authEmail', resolvedEmail);
      }
      
      onLoginSuccess(data.user_id, data.token, {
        username: resolvedUsername,
        email: resolvedEmail,
      });
    } catch {
      setError('Network error. Try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleForgotPassword = async (e) => {
    e.preventDefault();
    setError('');
    setResetLoading(true);
    try {
      await authAPI.forgotPassword(resetEmail);
      // Always show the same success state regardless of whether the email
      // is registered - the backend deliberately never reveals that.
      setResetSent(true);
    } catch {
      setError('Network error. Try again.');
    } finally {
      setResetLoading(false);
    }
  };

  const backToLogin = () => {
    setShowForgotPassword(false);
    setResetSent(false);
    setResetEmail('');
    setError('');
  };

  return (
    <div className="auth-container">
      <div className="auth-canvas" aria-hidden="true"></div>

      <div className="auth-box">
        <div className="auth-logo-wrapper">
          <img src={pragnaLogo} alt="Pragna Logo" className="auth-logo-centered" />
        </div>
        {showForgotPassword ? (
          <>
            <h1>Reset Password</h1>

            {error && <div className="auth-error">{error}</div>}

            {resetSent ? (
              <>
                <p style={{ color: 'var(--pragna-text-muted, #a89878)', fontSize: '14px', lineHeight: 1.6, margin: '4px 0 20px 0' }}>
                  If that email is registered, a password reset link has been sent. Check your inbox
                  (and spam folder) - the link expires in 60 minutes.
                </p>
                <button type="button" onClick={backToLogin} className="auth-btn">
                  Back to login
                </button>
              </>
            ) : (
              <form onSubmit={handleForgotPassword}>
                <p style={{ color: 'var(--pragna-text-muted, #a89878)', fontSize: '13.5px', lineHeight: 1.5, margin: '4px 0 16px 0' }}>
                  Enter your account email and we'll send you a link to reset your password.
                </p>
                <input
                  type="email"
                  placeholder="Email"
                  value={resetEmail}
                  onChange={(e) => setResetEmail(e.target.value)}
                  required
                  disabled={resetLoading}
                />
                <button type="submit" disabled={resetLoading} className="auth-btn">
                  {resetLoading ? 'Sending…' : 'Send reset link'}
                </button>
              </form>
            )}

            {!resetSent && (
              <p className="auth-toggle">
                <button type="button" onClick={backToLogin} disabled={resetLoading}>
                  Back to login
                </button>
              </p>
            )}
          </>
        ) : (
          <>
            <h1>{showRegister ? 'Create Account' : 'Welcome Back'}</h1>

            {error && <div className="auth-error">{error}</div>}

            {/* key forces a fresh form (and re-runs autoFocus) when switching
                between sign-in and register, so focus lands sensibly instead
                of staying wherever it was. */}
            <form key={showRegister ? 'register' : 'login'} onSubmit={showRegister ? handleRegister : handleLogin}>
              <input
                type="text"
                placeholder="Username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                autoFocus
                autoComplete="username"
                disabled={loading}
              />

              {showRegister && (
                <input
                  type="email"
                  placeholder="Email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  autoComplete="email"
                  disabled={loading}
                />
              )}

              <input
                type="password"
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete={showRegister ? 'new-password' : 'current-password'}
                disabled={loading}
              />

              {showRegister && (
                <p className="password-hint">Min 8 characters</p>
              )}

              {!showRegister && (
                <p className="auth-toggle" style={{ margin: '-8px 0 4px 0', textAlign: 'right' }}>
                  <button
                    type="button"
                    onClick={() => { setShowForgotPassword(true); setError(''); }}
                    disabled={loading}
                  >
                    Forgot password?
                  </button>
                </p>
              )}

              <button type="submit" disabled={loading} className="auth-btn">
                {loading
                  ? (showRegister ? 'Creating account…' : 'Signing in…')
                  : (showRegister ? 'Register' : 'Login')}
              </button>
            </form>

            <p className="auth-toggle">
              {showRegister ? 'Have an account?' : "Don't have an account?"}
              <button
                type="button"
                onClick={() => {
                  setShowRegister(!showRegister);
                  setError('');
                }}
                disabled={loading}
              >
                {showRegister ? ' Login' : ' Register'}
              </button>
            </p>
          </>
        )}
      </div>
    </div>
  );
}
