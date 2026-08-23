/* Invisible, failure-isolated visitor analytics for existing MallBuddy pages. */
(function () {
    const STORAGE_KEY = 'mallbuddy_visitor_session_id';
    const MALL_ID = 1;
    let sessionPromise;

    function apiUrl(path) {
        return `${window.BACKEND_URL || 'http://localhost:5000'}${path}`;
    }

    function authHeaders() {
        const token = localStorage.getItem('token');
        return token ? { 'Authorization': `Bearer ${token}` } : {};
    }

    async function ensureSession() {
        if (sessionPromise) return sessionPromise;
        sessionPromise = (async () => {
            const existing = localStorage.getItem(STORAGE_KEY);
            const response = await fetch(apiUrl('/api/tracking/session'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', ...authHeaders() },
                body: JSON.stringify({ mall_id: MALL_ID, session_id: existing || undefined })
            });
            if (!response.ok) throw new Error('Analytics session unavailable');
            const data = await response.json();
            localStorage.setItem(STORAGE_KEY, data.session_id);
            return data.session_id;
        })().catch(error => {
            console.debug('Analytics session unavailable:', error);
            sessionPromise = null;
            return null;
        });
        return sessionPromise;
    }

    async function track(eventType, details) {
        try {
            const sessionId = await ensureSession();
            if (!sessionId) return;
            const response = await fetch(apiUrl('/api/tracking/event'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', ...authHeaders() },
                body: JSON.stringify({
                    event_type: eventType,
                    mall_id: MALL_ID,
                    session_id: sessionId,
                    metadata: {},
                    ...(details || {})
                })
            });
            if (!response.ok) console.debug('Analytics event was rejected');
        } catch (error) {
            // Telemetry must never interfere with the customer action.
            console.debug('Analytics event unavailable:', error);
        }
    }

    window.MallBuddyAnalytics = { ensureSession, track };
    document.addEventListener('DOMContentLoaded', () => { ensureSession(); });
})();
