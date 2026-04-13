import { useContext, useState, useEffect } from "react";
import { ChatContext } from "../../context/ChatContext";

export default function ProfileDropdown({ onLogout }) {
    const { user, login, logout } = useContext(ChatContext);
    const [showDropdown, setShowDropdown] = useState(false);
    const [showLoginForm, setShowLoginForm] = useState(false);
    const [name, setName] = useState("");
    const [email, setEmail] = useState("");
    const [userId, setUserId] = useState(null);
    const [displayName, setDisplayName] = useState("");

    useEffect(() => {
        // Check for JWT authentication
        const savedUserId = localStorage.getItem('userId');
        const savedName = localStorage.getItem('userName');
        if (savedUserId) {
            setUserId(savedUserId);
            setDisplayName(savedName || "User");
        }
        if (user) {
            setDisplayName(user.name);
        }
    }, [user]);

    const handleLogin = (e) => {
        e.preventDefault();
        if (name.trim() && email.trim()) {
            login(name, email);
            localStorage.setItem('userName', name);
            setDisplayName(name);
            setShowLoginForm(false);
            setShowDropdown(false);
            setName("");
            setEmail("");
        }
    };

    const handleLogout = () => {
        logout();
        localStorage.removeItem('userId');
        localStorage.removeItem('userName');
        setUserId(null);
        setDisplayName("");
        if (onLogout) {
            onLogout();
        }
        setShowDropdown(false);
    };

    // Check if user is logged in via JWT or context
    const isLoggedIn = user || userId;
    const userInitial = displayName?.charAt(0).toUpperCase() || "U";

    return (
        <div className="profile-dropdown">
            <button
                className={`profile-btn ${isLoggedIn ? "profile-btn-logged-in" : ""}`}
                onClick={() => setShowDropdown(!showDropdown)}
                title={isLoggedIn ? "Account" : "Login"}
            >
                <div className="profile-btn-content">
                    <div className="profile-avatar">{userInitial}</div>
                    {isLoggedIn && (
                        <span className="profile-username">{displayName}</span>
                    )}
                    {!isLoggedIn && (
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <circle cx="12" cy="8" r="3.5" />
                            <path d="M5 20.5c0-3.87 3.13-7 7-7s7 3.13 7 7" />
                        </svg>
                    )}
                </div>
            </button>

            {showDropdown && (
                <div className="dropdown-menu">
                    {isLoggedIn ? (
                        <>
                            <div className="user-info">
                                <div className="user-avatar-large">{userInitial}</div>
                                <div className="user-name">{displayName}</div>
                                {user && <div className="user-email">{user.email}</div>}
                                {userId && !user && <div className="user-email">ID: {userId.substring(0, 8)}...</div>}
                            </div>
                            
                            <button className="dropdown-item dropdown-item-icon">
                                <span className="item-icon">⚙</span>
                                <span className="item-text">Settings</span>
                            </button>
                            <button className="dropdown-item dropdown-item-icon">
                                <span className="item-icon">✎</span>
                                <span className="item-text">Preferences</span>
                            </button>
                            <button className="dropdown-item dropdown-item-icon">
                                <span className="item-icon">💬</span>
                                <span className="item-text">Feedback</span>
                            </button>
                            <button className="dropdown-item dropdown-item-icon">
                                <span className="item-icon">?</span>
                                <span className="item-text">Help</span>
                            </button>
                            
                            <div className="dropdown-divider"></div>
                            
                            <button className="dropdown-item logout-btn" onClick={handleLogout}>
                                <span className="item-icon">×</span>
                                <span className="item-text">Logout</span>
                            </button>
                        </>
                    ) : (
                        <>
                            {showLoginForm ? (
                                <form onSubmit={handleLogin} className="login-form">
                                    <input
                                        type="text"
                                        placeholder="Name"
                                        value={name}
                                        onChange={(e) => setName(e.target.value)}
                                        required
                                    />
                                    <input
                                        type="email"
                                        placeholder="Email"
                                        value={email}
                                        onChange={(e) => setEmail(e.target.value)}
                                        required
                                    />
                                    <button type="submit">Login</button>
                                    <button
                                        type="button"
                                        onClick={() => setShowLoginForm(false)}
                                    >
                                        Cancel
                                    </button>
                                </form>
                            ) : (
                                <button
                                    className="dropdown-item"
                                    onClick={() => setShowLoginForm(true)}
                                >
                                    Login
                                </button>
                            )}
                        </>
                    )}
                </div>
            )}
        </div>
    );
}
