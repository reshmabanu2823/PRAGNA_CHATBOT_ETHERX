import { useState, useEffect } from "react";
import Login from "./components/auth/Login";
import ResetPassword from "./components/auth/ResetPassword";
import SharedChatView from "./components/chat/SharedChatView";
import SplashScreen, { SPLASH_TOTAL_MS, SPLASH_FADE_MS } from "./components/SplashScreen";
import PragnaApp from "./pragna/App";
import { ChatProvider } from "./context/ChatContext";

import "./styles/auth.css";
import "./styles/chat.css";
import "./styles/input.css";
import "./styles/chat_modes.css";
import "./styles/dashboard.css";

export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);
  const [userProfile, setUserProfile] = useState({ username: '', email: '' });

  // The password reset email links to /reset-password?token=... - no router
  // in this app, so read it directly. Checked once on initial load; the
  // token is single-use anyway so there's no need for this to react to
  // later URL changes within the same session. isResetPasswordRoute is
  // tracked separately from the token itself so that visiting the path
  // with a missing/stripped token still shows an explicit "invalid link"
  // state instead of silently falling through to the normal app/login.
  const [resetToken] = useState(() => new URLSearchParams(window.location.search).get('token'));
  const [isResetPasswordRoute] = useState(() => window.location.pathname === '/reset-password');

  // /share/<token> is a public read-only link - viewable while logged out,
  // so it's checked before the auth gate below, same as the reset-password route.
  const [shareToken] = useState(() => {
    const match = window.location.pathname.match(/^\/share\/([^/]+)$/);
    return match ? decodeURIComponent(match[1]) : null;
  });

  // Splash plays on every load of the primary app entry - people following a
  // reset-password or share link land straight on that page rather than
  // sitting through branding first. App owns the timers (not the SplashScreen
  // component) so dismissal never depends on a child callback firing.
  const [showSplash, setShowSplash] = useState(() => {
    return window.location.pathname !== '/reset-password' && !window.location.pathname.startsWith('/share/');
  });
  const [splashVisible, setSplashVisible] = useState(true);

  useEffect(() => {
    if (!showSplash) return undefined;
    // Durations come from the SplashScreen frame timeline itself, so App's
    // dismissal always matches the full Figma sequence length.
    const fadeTimer = setTimeout(() => setSplashVisible(false), SPLASH_TOTAL_MS - SPLASH_FADE_MS);
    const removeTimer = setTimeout(() => setShowSplash(false), SPLASH_TOTAL_MS);
    return () => {
      clearTimeout(fadeTimer);
      clearTimeout(removeTimer);
    };
    // Mount-once: showSplash only ever transitions true -> false, so this
    // effect's cleanup runs exactly once (on unmount) and never restarts.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const clearResetToken = () => {
    const url = new URL(window.location.href);
    url.pathname = '/';
    url.searchParams.delete('token');
    window.history.replaceState({}, '', url.pathname + url.search);
    window.location.reload();
  };

  const goHome = () => {
    const url = new URL(window.location.href);
    url.pathname = '/';
    window.history.replaceState({}, '', url.pathname);
    window.location.reload();
  };

  useEffect(() => {
    // Check if user is already logged in
    const savedToken = localStorage.getItem('authToken');
    const savedUserId = localStorage.getItem('userId');
    const savedUsername = localStorage.getItem('authUsername') || '';
    const savedEmail = localStorage.getItem('authEmail') || '';
    
    if (savedToken && savedUserId) {
      setIsAuthenticated(true);
      setUserProfile({ username: savedUsername, email: savedEmail });
    }
    
    setLoading(false);
  }, []);

  const handleLoginSuccess = (_userId, _token, profile) => {
    setIsAuthenticated(true);
    if (profile) {
      setUserProfile({
        username: profile.username || '',
        email: profile.email || '',
      });
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('authToken');
    localStorage.removeItem('userId');
    localStorage.removeItem('authUsername');
    localStorage.removeItem('authEmail');
    setUserProfile({ username: '', email: '' });
    setIsAuthenticated(false);
  };

  if (showSplash) {
    return <SplashScreen visible={splashVisible} />;
  }

  if (resetToken || isResetPasswordRoute) {
    return <ResetPassword token={resetToken} onDone={clearResetToken} />;
  }

  if (shareToken) {
    return <SharedChatView token={shareToken} onDone={goHome} />;
  }

  // Reuse the branded splash as the loading state too - the old placeholder
  // here was an off-brand blue-grey "Loading..." screen that clashed with the
  // black/gold identity and caused a visible flash between the two.
  if (loading) {
    return <SplashScreen visible={true} />;
  }

  if (!isAuthenticated) {
    return <Login onLoginSuccess={handleLoginSuccess} />;
  }

  return (
    <ChatProvider>
      <PragnaApp onLogout={handleLogout} userProfile={userProfile} />
    </ChatProvider>
  );
}