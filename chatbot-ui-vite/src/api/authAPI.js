export const authAPI = {
  // Register new user
  async register(username, email, password) {
    const response = await fetch(`/api/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, email, password })
    });
    return response.json();
  },

  // Login user
  async login(username, password) {
    const response = await fetch(`/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    return response.json();
  },

  // Verify token
  async verifyToken(token) {
    const response = await fetch(`/api/auth/verify`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    return response.json();
  },

  // Get user profile
  async getProfile(token) {
    const response = await fetch(`/api/profile`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    return response.json();
  },

  // Get all conversations
  async getConversations(token) {
    const response = await fetch(`/api/conversations`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    return response.json();
  },

  // Token management
  saveToken(token) {
    localStorage.setItem('authToken', token);
  },

  getToken() {
    return localStorage.getItem('authToken');
  },

  getUserId() {
    return localStorage.getItem('userId');
  },

  logout() {
    localStorage.removeItem('authToken');
    localStorage.removeItem('userId');
  },

  isAuthenticated() {
    return !!this.getToken();
  }
};
