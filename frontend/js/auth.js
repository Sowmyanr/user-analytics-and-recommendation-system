/**
 * Punjab Rozgar Authentication System
 * Handles user authentication, role management, and session persistence
 */

class AuthManager {
    constructor() {
        this.currentUser = null;
        this.userRoles = {
            ADMIN: 'admin',
            EMPLOYER: 'employer', 
            JOB_SEEKER: 'job_seeker'
        };
        this.apiBaseUrl = 'http://127.0.0.1:8000/api/v1';
        this.accessToken = null;
        this.init();
    }

    init() {
        // Load user from localStorage on page load
        this.loadUserFromStorage();
        this.loadTokenFromStorage();
        this.setupAuthUI();
        // Ensure UI updates once DOM is ready (in case script loads in <head>)
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.setupAuthUI());
        }
    }

    // Authentication Methods
    async login(email, password, rememberMe = false) {
        try {
            console.log('Attempting login with:', { email, apiUrl: `${this.apiBaseUrl}/auth/login` });
            
            const response = await fetch(`${this.apiBaseUrl}/auth/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ email, password })
            });

            console.log('Login response status:', response.status);
            const data = await response.json();
            console.log('Login response data:', data);
            
            if (response.ok && data.success) {
                this.accessToken = data.access_token;
                this.setCurrentUser(data.user, rememberMe);
                this.setAccessToken(data.access_token, rememberMe);
                // Don't redirect in test mode
                if (!window.location.pathname.includes('test-auth')) {
                    this.redirectAfterLogin(data.user.role);
                }
                return { success: true, user: data.user };
            } else {
                return { success: false, error: data.message || 'Login failed' };
            }
        } catch (error) {
            console.error('Login error:', error);
            return { success: false, error: 'Network error. Please try again.' };
        }
    }

    async register(userData) {
        try {
            console.log('Attempting registration with:', { userData, apiUrl: `${this.apiBaseUrl}/auth/register` });
            
            // Normalize role to allowed values
            const allowedRoles = ['job_seeker', 'employer'];
            const normalizedRole = allowedRoles.includes(userData.role) ? userData.role : 'job_seeker';

            const response = await fetch(`${this.apiBaseUrl}/auth/register`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    email: userData.email,
                    password: userData.password,
                    first_name: userData.firstName,
                    last_name: userData.lastName,
                    phone: userData.phone,
                    role: normalizedRole,
                    city: userData.city
                })
            });

            console.log('Registration response status:', response.status);
            const data = await response.json();
            console.log('Registration response data:', data);
            
            if (response.ok && data.success) {
                this.accessToken = data.access_token;
                this.setCurrentUser(data.user, false);
                this.setAccessToken(data.access_token, false);
                // Don't redirect in test mode
                if (!window.location.pathname.includes('test-auth')) {
                    this.redirectAfterLogin(data.user.role);
                }
                return { success: true, user: data.user };
            } else {
                const backendMsg = data?.detail || data?.message;
                // Friendly error for role mismatch
                const friendly = (backendMsg && backendMsg.toLowerCase().includes('role must be'))
                    ? 'Please choose Job Seeker or Employer as your role.'
                    : (backendMsg || 'Registration failed');
                return { success: false, error: friendly };
            }
        } catch (error) {
            console.error('Registration error:', error);
            return { success: false, error: 'Network error. Please try again.' };
        }
    }

    logout() {
        this.currentUser = null;
        this.accessToken = null;
        localStorage.removeItem('user');
        localStorage.removeItem('access_token');
        sessionStorage.removeItem('user');
        sessionStorage.removeItem('access_token');
        
        // Redirect to home page
        window.location.href = '/index.html';
    }

    // User Management
    setCurrentUser(user, persistent = false) {
        this.currentUser = user;
        
        const userData = {
            id: user.id,
            email: user.email,
            name: user.name,
            role: user.role,
            profile: user.profile || {},
            loginTime: new Date().toISOString()
        };

        if (persistent) {
            localStorage.setItem('user', JSON.stringify(userData));
        } else {
            sessionStorage.setItem('user', JSON.stringify(userData));
        }
        
        this.setupAuthUI();
    }

    loadUserFromStorage() {
        const userData = localStorage.getItem('user') || sessionStorage.getItem('user');
        if (userData) {
            try {
                this.currentUser = JSON.parse(userData);
                this.setupAuthUI();
            } catch (error) {
                console.error('Error loading user data:', error);
                this.logout();
            }
        }
    }

    loadTokenFromStorage() {
        this.accessToken = localStorage.getItem('access_token') || sessionStorage.getItem('access_token');
    }

    setAccessToken(token, persistent = false) {
        this.accessToken = token;
        if (persistent) {
            localStorage.setItem('access_token', token);
        } else {
            sessionStorage.setItem('access_token', token);
        }
    }

    getAuthHeaders() {
        return {
            'Content-Type': 'application/json',
            ...(this.accessToken && { 'Authorization': `Bearer ${this.accessToken}` })
        };
    }

    getCurrentUser() {
        return this.currentUser;
    }

    isLoggedIn() {
        return this.currentUser !== null;
    }

    hasRole(role) {
        return this.currentUser && this.currentUser.role === role;
    }

    isAdmin() {
        return this.hasRole(this.userRoles.ADMIN);
    }

    isEmployer() {
        return this.hasRole(this.userRoles.EMPLOYER);
    }

    isJobSeeker() {
        return this.hasRole(this.userRoles.JOB_SEEKER);
    }

    // API Helper Methods
    async makeApiCall(endpoint, options = {}) {
        try {
            const response = await fetch(`${this.apiBaseUrl}${endpoint}`, {
                headers: this.getAuthHeaders(),
                ...options
            });

            if (response.status === 401) {
                // Token expired or invalid
                this.logout();
                return null;
            }

            return await response.json();
        } catch (error) {
            console.error('API call error:', error);
            throw error;
        }
    }

    async getCurrentUserProfile() {
        if (!this.isLoggedIn()) return null;
        
        try {
            const data = await this.makeApiCall('/users/profile');
            return data;
        } catch (error) {
            console.error('Error fetching user profile:', error);
            return null;
        }
    }

    async updateUserProfile(profileData) {
        if (!this.isLoggedIn()) return { success: false, error: 'Not logged in' };
        
        try {
            const data = await this.makeApiCall('/users/profile', {
                method: 'PUT',
                body: JSON.stringify(profileData)
            });
            return data;
        } catch (error) {
            console.error('Error updating user profile:', error);
            return { success: false, error: 'Failed to update profile' };
        }
    }

    // Redirect Logic
    redirectAfterLogin(role) {
        switch (role) {
            case this.userRoles.ADMIN:
                window.location.href = '/pages/admin/dashboard.html';
                break;
            case this.userRoles.EMPLOYER:
                window.location.href = '/pages/employer/dashboard.html';
                break;
            case this.userRoles.JOB_SEEKER:
                window.location.href = '/pages/jobseeker/dashboard.html';
                break;
            default:
                window.location.href = '/index.html';
        }
    }

    // UI Management
    setupAuthUI() {
        this.updateNavigation();
        this.updateUserProfile();
        this.enforceRoleBasedAccess();
    }

    updateNavigation() {
        const authButtons = document.querySelector('.auth-buttons');
        const userMenu = document.querySelector('.user-menu');
        
        if (this.isLoggedIn()) {
            // Hide login/register buttons
            if (authButtons) {
                authButtons.style.display = 'none';
            }
            
            // Show user menu
            if (userMenu) {
                userMenu.style.display = 'block';
                this.populateUserMenu();
            } else {
                this.createUserMenu();
            }
        } else {
            // Show login/register buttons
            if (authButtons) {
                authButtons.style.display = 'flex';
            }
            
            // Hide user menu
            if (userMenu) {
                userMenu.style.display = 'none';
            }
        }
    }

    createUserMenu() {
        const nav = document.querySelector('.nav') || document.querySelector('.navbar');
        if (!nav) return;

        const userMenuHTML = `
            <div class="user-menu" style="display: flex; align-items: center; gap: 1rem;">
                <span class="user-greeting">Hello, ${this.currentUser?.name || this.currentUser?.email || 'User'}</span>
                <div class="user-dropdown">
                    <button class="user-avatar" onclick="toggleUserDropdown()">
                        <i class="fas fa-user-circle"></i>
                    </button>
                    <div class="dropdown-menu" id="userDropdownMenu">
                        <a href="${this.getDashboardUrl()}" class="dropdown-item">
                            <i class="fas fa-tachometer-alt"></i> Dashboard
                        </a>
                        <a href="/pages/profile/view.html" class="dropdown-item">
                            <i class="fas fa-user"></i> Profile
                        </a>
                        <div class="dropdown-divider"></div>
                        <button onclick="authManager.logout()" class="dropdown-item logout-btn">
                            <i class="fas fa-sign-out-alt"></i> Logout
                        </button>
                    </div>
                </div>
            </div>
        `;

        nav.insertAdjacentHTML('beforeend', userMenuHTML);
    }

    populateUserMenu() {
        const userGreeting = document.querySelector('.user-greeting');
        if (userGreeting) {
            userGreeting.textContent = `Hello, ${this.currentUser.name}`;
        }
    }

    getDashboardUrl() {
        switch (this.currentUser.role) {
            case this.userRoles.ADMIN:
                return '/pages/admin/dashboard.html';
            case this.userRoles.EMPLOYER:
                return '/pages/employer/dashboard.html';
            case this.userRoles.JOB_SEEKER:
                return '/pages/jobseeker/dashboard.html';
            default:
                return '/index.html';
        }
    }

    updateUserProfile() {
        const profileElements = document.querySelectorAll('[data-user-name]');
        const roleElements = document.querySelectorAll('[data-user-role]');
        
        if (this.isLoggedIn()) {
            profileElements.forEach(el => el.textContent = this.currentUser.name);
            roleElements.forEach(el => el.textContent = this.currentUser.role);
        }
    }

    enforceRoleBasedAccess() {
        // Hide/show elements based on user role
        const adminOnly = document.querySelectorAll('[data-role="admin"]');
        const employerOnly = document.querySelectorAll('[data-role="employer"]');
        const jobSeekerOnly = document.querySelectorAll('[data-role="job_seeker"]');
        const loggedInOnly = document.querySelectorAll('[data-auth="required"]');
        const loggedOutOnly = document.querySelectorAll('[data-auth="guest"]');

        // Show/hide based on authentication status
        loggedInOnly.forEach(el => {
            el.style.display = this.isLoggedIn() ? 'block' : 'none';
        });
        
        loggedOutOnly.forEach(el => {
            el.style.display = this.isLoggedIn() ? 'none' : 'block';
        });

        if (this.isLoggedIn()) {
            // Show/hide based on role
            adminOnly.forEach(el => {
                el.style.display = this.isAdmin() ? 'block' : 'none';
            });
            
            employerOnly.forEach(el => {
                el.style.display = this.isEmployer() ? 'block' : 'none';
            });
            
            jobSeekerOnly.forEach(el => {
                el.style.display = this.isJobSeeker() ? 'block' : 'none';
            });
        }
    }

    // Page Protection
    requireAuth(redirectUrl = '/pages/auth/login.html') {
        if (!this.isLoggedIn()) {
            window.location.href = redirectUrl;
            return false;
        }
        return true;
    }

    requireRole(requiredRole, redirectUrl = '/index.html') {
        if (!this.isLoggedIn() || !this.hasRole(requiredRole)) {
            window.location.href = redirectUrl;
            return false;
        }
        return true;
    }

    requireRoles(requiredRoles, redirectUrl = '/index.html') {
        if (!this.isLoggedIn() || !requiredRoles.includes(this.currentUser.role)) {
            window.location.href = redirectUrl;
            return false;
        }
        return true;
    }
}

// Global functions for dropdown
function toggleUserDropdown() {
    const dropdown = document.getElementById('userDropdownMenu');
    if (dropdown) {
        dropdown.classList.toggle('show');
    }
}

// Close dropdown when clicking outside
document.addEventListener('click', function(event) {
    const dropdown = document.getElementById('userDropdownMenu');
    const userAvatar = document.querySelector('.user-avatar');
    
    if (dropdown && (!userAvatar || !userAvatar.contains(event.target))) {
        dropdown.classList.remove('show');
    }
});

// Initialize global auth manager
const authManager = new AuthManager();

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AuthManager;
}