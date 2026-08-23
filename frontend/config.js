// MallBuddy Frontend Configuration
// This file manages the backend API URL for different environments

(function () {
    // Detect environment and set appropriate backend URL
    const hostname = window.location.hostname;

    let backendUrl;

    // Set this to true to use the live Render backend even when running locally
    // Set to false to use your local Flask server (http://localhost:5000)
    const USE_LIVE_BACKEND = true;

    if (USE_LIVE_BACKEND || hostname.includes('onrender.com')) {
        // Production on Render
        backendUrl = 'https://mallbuddy.onrender.com';
    } else if (hostname === 'localhost' || hostname === '127.0.0.1') {
        // Local development
        backendUrl = 'http://localhost:5000';
    } else {
        // Fallback - assume same origin or update for your custom domain
        backendUrl = 'https://mallbuddy.onrender.com';
    }

    // Make BACKEND_URL globally available
    window.BACKEND_URL = backendUrl;

    console.log('MallBuddy Config loaded. Backend URL:', backendUrl);
})();
