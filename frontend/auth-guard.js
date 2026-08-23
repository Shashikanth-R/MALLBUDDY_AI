/**
 * auth-guard.js
 * Centralized authentication and session management for MallBuddy.
 * Must be loaded synchronously in the <head> of protected pages after config.js.
 */

(function () {
    // Determine page category
    const currentPath = window.location.pathname;
    
    // Guest-only pages (redirect away if logged in)
    const guestOnlyPages = ['login.html', 'signup.html'];
    const isGuestOnly = guestOnlyPages.some(page => currentPath.endsWith(page));
    
    // Hybrid pages (accessible to everyone, but shows user info if logged in)
    const hybridPages = ['index.html'];
    const isHybrid = hybridPages.some(page => currentPath.endsWith(page)) || currentPath === '/' || currentPath.endsWith('/MALLBUDDY-main/frontend/');
    
    // Protected pages (redirect to login if not logged in)
    const isProtected = !isGuestOnly && !isHybrid;

    // Handle bfcache (Back/Forward Cache) restores
    window.addEventListener('pageshow', function (event) {
        if (event.persisted) {
            // Re-verify auth when page is restored from cache
            verifyAuth();
        }
    });

    async function verifyAuth() {
        const token = localStorage.getItem('token');

        if (!token) {
            if (isProtected) {
                requireLogin();
            }
            return;
        }

        try {
            // Use BACKEND_URL from config.js (ensure config.js is loaded first)
            const backendUrl = window.BACKEND_URL || 'http://localhost:5000';
            const response = await fetch(`${backendUrl}/api/auth/profile`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Cache-Control': 'no-cache, no-store, must-revalidate',
                    'Pragma': 'no-cache'
                }
            });

            if (!response.ok) {
                // Token invalid or expired
                if (isProtected) {
                    requireLogin();
                } else {
                    // Clear invalid state on hybrid/guest pages too
                    localStorage.removeItem('token');
                    localStorage.removeItem('user');
                    localStorage.removeItem('userType');
                }
            } else {
                // Token is valid
                if (isGuestOnly) {
                    // Active session, redirect away from login/signup
                    window.location.replace('index.html');
                } else {
                    // Valid session on protected or hybrid page. Apply user info if DOM is ready.
                    applyUserInfo();
                }
            }
        } catch (error) {
            console.error('Auth verification failed:', error);
            // On network error, apply user info from local storage if available so offline works
            if (!isGuestOnly) {
                applyUserInfo();
            }
        }
    }

    // Forcefully clear session and redirect to login (for unauthorized access)
    function requireLogin() {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        localStorage.removeItem('userType');
        
        // Prevent back-button navigation to protected state
        window.location.replace('login.html');
    }

    // Apply user info to DOM elements (called on DOMContentLoaded)
    function applyUserInfo() {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', updateDOM);
        } else {
            updateDOM();
        }

        function updateDOM() {
            const user = JSON.parse(localStorage.getItem('user') || '{}');
            const token = localStorage.getItem('token');
            if (token && user.name) {
                const loginBtn = document.getElementById('loginBtn');
                const signupBtn = document.getElementById('signupBtn');
                const userInfo = document.getElementById('userInfo');
                const logoutBtn = document.getElementById('logoutBtn');
                const welcomeTitle = document.getElementById('welcomeTitle');
                const welcomeSubtitle = document.getElementById('welcomeSubtitle');

                if (loginBtn) loginBtn.style.display = 'none';
                if (signupBtn) signupBtn.style.display = 'none';
                if (userInfo) {
                    userInfo.style.display = 'inline';
                    userInfo.textContent = `Hello, ${user.name}!`;
                }
                if (logoutBtn) logoutBtn.style.display = 'inline';
                if (welcomeTitle) welcomeTitle.textContent = `Welcome back, ${user.name}!`;
                if (welcomeSubtitle) welcomeSubtitle.textContent = `Great to see you again! How can I assist you today?`;
            }
        }
    }

    // Global logout function accessible by UI
    window.logout = async function () {
        const token = localStorage.getItem('token');
        if (token) {
            try {
                const backendUrl = window.BACKEND_URL || 'http://localhost:5000';
                // Best-effort server logout
                await fetch(`${backendUrl}/api/auth/logout`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                });
            } catch (error) {
                console.error('Server logout failed:', error);
            }
        }
        forceLogout();
    };

    // Run verification immediately on load
    verifyAuth();
})();
