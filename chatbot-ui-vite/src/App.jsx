import { useState, useEffect } from "react";
import Login from "./components/auth/Login";
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

  if (loading) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '100vh',
        background: 'linear-gradient(135deg, #0f1419 0%, #1a1f2e 100%)',
        fontSize: '18px',
        color: '#ffd700'
      }}>
        Loading...
      </div>
    );
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