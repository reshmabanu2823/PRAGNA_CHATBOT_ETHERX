import { useEffect, useState } from 'react';
import '../../styles/auth.css';
import { authAPI } from '../../api/authAPI';
import { API_BASE } from '../../api/api';
import PasswordInput from '../ui/PasswordInput';
import pragnaLogo from '../../assets/pragna-logo-full.png';
import InteractiveNeuralVortex from './InteractiveNeuralVortex';

// Full-page navigation, not fetch - the browser has to actually leave the
// SPA to hit Google/GitHub's own login screen, then comes back to
// /api/auth/<provider>/callback on the backend, which redirects to `/`
// with the result in the query string (see App.jsx's oauth handling).
const startOAuthLogin = (provider) => {
  window.location.href = `${API_BASE}/api/auth/${provider}/login`;
};

const OAUTH_ERROR_MESSAGES = {
  invalid_state: 'That sign-in attempt expired or was already used. Please try again.',
  login_failed: 'Sign-in failed. Please try again, or use your username and password.',
  access_denied: 'Sign-in was cancelled.',
};

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
  // Picks up ?oauth_error=... left by a failed /api/auth/<provider>/callback
  // redirect (see App.jsx for the success-path equivalent).
  const [error, setError] = useState(() => {
    const oauthError = new URLSearchParams(window.location.search).get('oauth_error');
    return oauthError ? (OAUTH_ERROR_MESSAGES[oauthError] || 'Sign-in failed. Please try again.') : '';
  });
  const [loading, setLoading] = useState(false);
  const [showRegister, setShowRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [showForgotPassword, setShowForgotPassword] = useState(false);
  const [resetEmail, setResetEmail] = useState('');
  const [resetSent, setResetSent] = useState(false);
  const [resetLoading, setResetLoading] = useState(false);

  // Registration is two steps: request-otp emails a code without creating
  // the account, verify-otp creates it once the code checks out.
  // pendingEmail/pendingUsername/pendingPassword hold what was submitted in
  // step 1 - needed again in step 2 (verify-otp only takes email+code, but
  // resending needs all three, and username/password are used to log the
  // account in immediately after verify-otp is what actually creates it).
  const [showOtpVerify, setShowOtpVerify] = useState(false);
  const [pendingUsername, setPendingUsername] = useState('');
  const [pendingEmail, setPendingEmail] = useState('');
  const [pendingPassword, setPendingPassword] = useState('');
  const [otpCode, setOtpCode] = useState('');
  const [otpLoading, setOtpLoading] = useState(false);
  const [otpResendLoading, setOtpResendLoading] = useState(false);
  const [otpNotice, setOtpNotice] = useState('');

  useEffect(() => {
    if (!window.location.search.includes('oauth_error')) return;
    const url = new URL(window.location.href);
    url.searchParams.delete('oauth_error');
    window.history.replaceState({}, '', url.pathname + url.search);
  }, []);

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
      const data = await authAPI.requestRegistrationOtp(trimmedUsername, trimmedEmail, password);

      if (data.error) {
        setError(data.error || 'Registration failed');
        return;
      }

      // Account doesn't exist yet - request-otp only emailed a code.
      // Hold onto what was submitted so verify (and resend) can use it.
      setPendingUsername(trimmedUsername);
      setPendingEmail(trimmedEmail);
      setPendingPassword(password);
      setOtpCode('');
      setOtpNotice('');
      setShowOtpVerify(true);
    } catch {
      setError('Network error. Try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOtp = async (e) => {
    e.preventDefault();
    setError('');

    const trimmedCode = otpCode.trim();
    if (!trimmedCode) {
      setError('Enter the code from your email.');
      return;
    }

    setOtpLoading(true);

    try {
      const data = await authAPI.verifyRegistrationOtp(pendingEmail, trimmedCode);

      if (data.error) {
        setError(data.error || 'Verification failed');
        return;
      }

      // verify-otp is what actually creates the account, so this is the
      // first point account+token exist - same login-completion steps as
      // the old single-step register.
      localStorage.setItem('authToken', data.token);
      localStorage.setItem('userId', data.user_id);
      localStorage.setItem('authUsername', pendingUsername);
      localStorage.setItem('authEmail', pendingEmail);

      onLoginSuccess(data.user_id, data.token, {
        username: pendingUsername,
        email: pendingEmail,
      });
    } catch {
      setError('Network error. Try again.');
    } finally {
      setOtpLoading(false);
    }
  };

  const handleResendOtp = async () => {
    setError('');
    setOtpNotice('');
    setOtpResendLoading(true);
    try {
      const data = await authAPI.requestRegistrationOtp(pendingUsername, pendingEmail, pendingPassword);
      if (data.error) {
        setError(data.error || 'Failed to resend code');
        return;
      }
      setOtpCode('');
      setOtpNotice('A new code has been sent.');
    } catch {
      setError('Network error. Try again.');
    } finally {
      setOtpResendLoading(false);
    }
  };

  const backToRegisterForm = () => {
    setShowOtpVerify(false);
    setOtpCode('');
    setOtpNotice('');
    setError('');
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
      <InteractiveNeuralVortex />

      <div className="auth-box">
        <div className="auth-logo-wrapper">
          <img src={pragnaLogo} alt="Pragna Logo" className="auth-logo-centered" />
        </div>
        {showOtpVerify ? (
          <>
            <h1>Verify your email</h1>

            {error && <div className="auth-error">{error}</div>}

            <form onSubmit={handleVerifyOtp}>
              <p style={{ color: 'var(--pragna-text-muted, #a89878)', fontSize: '13.5px', lineHeight: 1.5, margin: '4px 0 16px 0' }}>
                Enter the 6-digit code sent to <strong>{pendingEmail}</strong>. It expires in 10 minutes.
              </p>
              <input
                type="text"
                inputMode="numeric"
                placeholder="6-digit code"
                value={otpCode}
                onChange={(e) => setOtpCode(e.target.value)}
                required
                autoFocus
                maxLength={6}
                disabled={otpLoading}
              />
              {otpNotice && (
                <p style={{ color: 'var(--pragna-gold-soft, #e5c76b)', fontSize: '13px', margin: '-4px 0 4px 0' }}>
                  {otpNotice}
                </p>
              )}
              <button type="submit" disabled={otpLoading} className="auth-btn">
                {otpLoading ? 'Verifying…' : 'Verify & Create Account'}
              </button>
            </form>

            <p className="auth-toggle">
              <button type="button" onClick={handleResendOtp} disabled={otpResendLoading || otpLoading}>
                {otpResendLoading ? 'Resending…' : 'Resend code'}
              </button>
            </p>
            <p className="auth-toggle">
              <button type="button" onClick={backToRegisterForm} disabled={otpLoading}>
                Back
              </button>
            </p>
          </>
        ) : showForgotPassword ? (
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

              <PasswordInput
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
                  ? (showRegister ? 'Sending code…' : 'Signing in…')
                  : (showRegister ? 'Register' : 'Login')}
              </button>
            </form>

            <div className="auth-divider">
              <span>or continue with</span>
            </div>

            <div className="auth-oauth-row">
              <button
                type="button"
                className="auth-oauth-btn"
                onClick={() => startOAuthLogin('google')}
                disabled={loading}
              >
                <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
                  <path fill="#4285F4" d="M17.64 9.2c0-.64-.06-1.25-.16-1.84H9v3.48h4.84a4.14 4.14 0 0 1-1.8 2.72v2.26h2.92c1.7-1.57 2.68-3.88 2.68-6.62z"/>
                  <path fill="#34A853" d="M9 18c2.43 0 4.47-.8 5.96-2.18l-2.92-2.26c-.81.54-1.85.86-3.04.86-2.34 0-4.32-1.58-5.03-3.7H.96v2.33A9 9 0 0 0 9 18z"/>
                  <path fill="#FBBC05" d="M3.97 10.72A5.4 5.4 0 0 1 3.68 9c0-.6.1-1.18.29-1.72V4.95H.96A9 9 0 0 0 0 9c0 1.45.35 2.83.96 4.05l3.01-2.33z"/>
                  <path fill="#EA4335" d="M9 3.58c1.32 0 2.51.46 3.44 1.35l2.59-2.59C13.46.89 11.43 0 9 0A9 9 0 0 0 .96 4.95l3.01 2.33C4.68 5.16 6.66 3.58 9 3.58z"/>
                </svg>
                Google
              </button>
              <button
                type="button"
                className="auth-oauth-btn"
                onClick={() => startOAuthLogin('github')}
                disabled={loading}
              >
                <svg width="18" height="18" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
                  <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8z"/>
                </svg>
                GitHub
              </button>
            </div>

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
