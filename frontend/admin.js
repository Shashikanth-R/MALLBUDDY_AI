// BACKEND_URL - uses config.js if available, otherwise fallback to localhost
const BACKEND_URL = window.BACKEND_URL || 'http://localhost:5000';
let currentEditId = null;
let editMode = false;
let categories = [];
let stores = [];

// Chart instances
let charts = {
    mallPulse: null,
    visitorTrend: null,
    categoryDist: null,
    segmentation: null
};

// Error and Loading Handlers
function showLoading(elementId, message = 'Loading data...') {
    const el = document.getElementById(elementId);
    if (el) el.innerHTML = `<div class="state-container"><div class="skeleton"></div><div class="skeleton" style="width:70%"></div><div style="font-size:12px">${message}</div></div>`;
}

function showError(elementId, message = 'Failed to load data', retryFn = null) {
    const el = document.getElementById(elementId);
    if (!el) return;
    const retryBtn = retryFn ? `<button class="btn-secondary" style="margin-top: 12px" onclick="${retryFn}()">Retry</button>` : '';
    el.innerHTML = `<div class="state-container" style="color: var(--danger)"><i data-lucide="alert-circle" size="24"></i><p>${message}</p>${retryBtn}</div>`;
    if(window.lucide) window.lucide.createIcons();
}

function showEmpty(elementId, message = 'No data available yet') {
    const el = document.getElementById(elementId);
    if (!el) return;
    el.innerHTML = `<div class="state-container"><i data-lucide="inbox" size="24"></i><p>${message}</p></div>`;
    if(window.lucide) window.lucide.createIcons();
}

// Initialize charts
function initCharts() {
    Chart.defaults.font.family = "'Inter', sans-serif";
    Chart.defaults.color = "#6B6B6B";
    
    // Mall Pulse
    const pulseCtx = document.getElementById('mallPulseChart');
    if (pulseCtx) {
        charts.mallPulse = new Chart(pulseCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Live Activity',
                    data: [],
                    borderColor: '#C9A45C',
                    backgroundColor: 'rgba(201, 164, 92, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: { 
                    y: { beginAtZero: true, grid: { color: 'rgba(0,0,0,0.04)' } },
                    x: { grid: { display: false } }
                }
            }
        });
    }

    // Visitor Trend
    const visitorCtx = document.getElementById('visitorTrendChart');
    if (visitorCtx) {
        charts.visitorTrend = new Chart(visitorCtx, {
            type: 'bar',
            data: {
                labels: [],
                datasets: [{
                    label: 'Visitors',
                    data: [],
                    backgroundColor: '#1C1C1C',
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: { legend: { display: false } }
            }
        });
    }

    // Category Distribution
    const catCtx = document.getElementById('categoryDistChart');
    if (catCtx) {
        charts.categoryDist = new Chart(catCtx, {
            type: 'doughnut',
            data: {
                labels: [],
                datasets: [{
                    data: [],
                    backgroundColor: ['#1C1C1C', '#C9A45C', '#10B981', '#F59E0B', '#3B82F6', '#8B5CF6']
                }]
            },
            options: { responsive: true, maintainAspectRatio: false }
        });
    }

    // Segmentation
    const segCtx = document.getElementById('segmentationChart');
    if (segCtx) {
        charts.segmentation = new Chart(segCtx, {
            type: 'pie',
            data: {
                labels: [],
                datasets: [{
                    data: [],
                    backgroundColor: ['#8B5CF6', '#10B981', '#3B82F6', '#F59E0B']
                }]
            },
            options: { responsive: true, maintainAspectRatio: false }
        });
    }
}

// Check admin role
function checkAuth() {
    const userType = localStorage.getItem('userType');
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    if (userType !== 'admin') {
        window.location.replace('index.html');
        return;
    }
    if (document.getElementById('adminName')) {
        document.getElementById('adminName').textContent = user.name || 'Admin';
    }
    initCharts();
    loadOverviewData();
}

const API_HEADERS = () => ({
    'Authorization': `Bearer ${localStorage.getItem('token')}`
});

// Load Overview (KPIs + Pulse)
async function loadOverviewData() {
    try {
        const liveRes = await fetch(`${BACKEND_URL}/api/admin/stats/live`, { headers: API_HEADERS() });
        const live = await liveRes.json();
        
        document.getElementById('kpiActiveVisitors').textContent = live.active_sessions || 0;
        document.getElementById('kpiAiQueries').textContent = live.today_messages || 0;

        const overviewRes = await fetch(`${BACKEND_URL}/api/admin/analytics/overview`, { headers: API_HEADERS() });
        if (!overviewRes.ok) throw new Error('API failed');
        const overview = await overviewRes.json();
        
        document.getElementById('kpiTotalVisitors').textContent = overview.total_visitors || 'No data';
        document.getElementById('kpiNavRequests').textContent = overview.navigation_requests || 'No data';
        document.getElementById('kpiStoreEngagement').textContent = overview.store_engagements || 'No data';
        document.getElementById('kpiOfferInteractions').textContent = overview.offer_interactions || 'No data';
        document.getElementById('kpiUpcomingEvents').textContent = overview.upcoming_events || '0';
        document.getElementById('kpiFeedback').textContent = overview.pending_feedback || '0';

        // Update pulse chart
        if (charts.mallPulse && overview.visitor_trend) {
            charts.mallPulse.data.labels = overview.visitor_trend.map(d => d.date);
            charts.mallPulse.data.datasets[0].data = overview.visitor_trend.map(d => d.count);
            charts.mallPulse.update();
        }
    } catch (e) { 
        console.error('Error loading overview:', e); 
    }
}

// Load MallBuddy Insights
async function loadInsightsData() {
    showLoading('insightsContainer');
    try {
        const res = await fetch(`${BACKEND_URL}/api/admin/analytics/insights`, { headers: API_HEADERS() });
        if (!res.ok) throw new Error('Network error');
        const data = await res.json();
        const container = document.getElementById('insightsContainer');
        
        if (!data.insights || data.insights.length === 0) {
            showEmpty('insightsContainer', 'No business insights generated yet.');
            return;
        }

        container.innerHTML = data.insights.map(i => `
            <div class="insight-card insight-${i.severity || 'low'}">
                <span class="insight-type-badge">${i.insight_type}</span>
                <div class="insight-title">✦ ${i.title}</div>
                <p style="color: var(--text-secondary); margin-bottom: 12px; font-size: 14px;">${i.summary}</p>
                <div class="insight-evidence">
                    <strong>Evidence:</strong> ${i.evidence || 'N/A'}
                </div>
                <div class="insight-action">
                    <i data-lucide="zap" size="18" style="color: var(--warning); margin-top: 2px;"></i>
                    <div>
                        <strong style="display: block; margin-bottom: 4px;">Recommended Action:</strong>
                        ${i.recommendation}
                    </div>
                </div>
            </div>
        `).join('');
        if(window.lucide) window.lucide.createIcons();
    } catch (e) { 
        console.error(e);
        showEmpty('insightsContainer', 'No data available yet (Pending Backend Deployment)'); 
    }
}

// Load Store Performance (Custom visual bars + Category Chart)
async function loadStoresPerfData() {
    showLoading('topStoresContainer');
    try {
        const overviewRes = await fetch(`${BACKEND_URL}/api/admin/analytics/overview`, { headers: API_HEADERS() });
        const overview = await overviewRes.json();
        const container = document.getElementById('topStoresContainer');
        
        if (!overview.top_stores || overview.top_stores.length === 0) {
            showEmpty('topStoresContainer', 'No store engagement data available.');
        } else {
            // Calculate max views for relative bar width
            const maxViews = Math.max(...overview.top_stores.map(s => s.views));
            container.innerHTML = overview.top_stores.map((s, idx) => {
                const widthPercent = (s.views / maxViews) * 100;
                return `
                <div class="store-ranking-item">
                    <div class="store-rank">#${idx + 1}</div>
                    <div class="store-name">${s.store_name}</div>
                    <div class="store-bar-track">
                        <div class="store-bar-fill" style="width: ${widthPercent}%"></div>
                    </div>
                    <div class="store-value">${s.views}</div>
                </div>
                `;
            }).join('');
        }

        const statsRes = await fetch(`${BACKEND_URL}/api/admin/analytics`, { headers: API_HEADERS() });
        const stats = await statsRes.json();
        if (charts.categoryDist && stats.stores_by_category) {
            charts.categoryDist.data.labels = stats.stores_by_category.map(c=>c.category);
            charts.categoryDist.data.datasets[0].data = stats.stores_by_category.map(c=>c.count);
            charts.categoryDist.update();
        }
    } catch (e) {
        showError('topStoresContainer', 'Failed to load store performance', 'loadStoresPerfData');
    }
}

// Hook into switchTab
window.switchTab = window.switchTab || function(tab) {
    // UI changes handled in HTML script block, just call the logic here
    
    // Close sidebar on mobile after clicking
    const sidebar = document.getElementById('sidebar');
    if (sidebar && sidebar.classList.contains('open')) {
        sidebar.classList.remove('open');
    }

    if (tab === 'overview') loadOverviewData();
    else if (tab === 'insights') loadInsightsData();
    else if (tab === 'stores-perf') loadStoresPerfData();
    else if (tab === 'segments') {
        fetch(`${BACKEND_URL}/api/admin/analytics/segments`, { headers: API_HEADERS() })
        .then(r => {
            if (!r.ok) throw new Error('API missing');
            return r.json();
        })
        .then(data => {
            if (charts.segmentation && data.segments && data.segments.length > 0) {
                charts.segmentation.data.labels = data.segments.map(s => s.segment_name);
                charts.segmentation.data.datasets[0].data = data.segments.map(s => s.count);
                charts.segmentation.update();
            } else if (data.segments && data.segments.length === 0) {
                document.getElementById('segmentsContainer').innerHTML = '<div class="state-container">No data available yet</div>';
            }
        })
        .catch(() => {
            document.getElementById('segmentsContainer').innerHTML = '<div class="state-container">No data available yet (Pending Backend Deployment)</div>';
        });
    }
    else if (tab === 'visitors') {
        fetch(`${BACKEND_URL}/api/admin/analytics/visitors`, { headers: API_HEADERS() })
        .then(r=>r.json()).then(data => {
            if (charts.visitorTrend && data.daily_stats) {
                charts.visitorTrend.data.labels = data.daily_stats.map(d=>d.date);
                charts.visitorTrend.data.datasets[0].data = data.daily_stats.map(d=>d.count);
                charts.visitorTrend.update();
            }
        });
    }
    else if (tab === 'search-intel') {
        showLoading('searchKeywordsContainer');
        fetch(`${BACKEND_URL}/api/admin/chats/popular-questions`, { headers: API_HEADERS() })
        .then(r=>r.json()).then(data => {
            const container = document.getElementById('searchKeywordsContainer');
            if (container && data.popular_keywords && data.popular_keywords.length > 0) {
                container.innerHTML = data.popular_keywords.map(k => 
                    `<div style="background: var(--bg-main); padding: 8px 16px; border-radius: 20px; font-size: 13px; font-weight: 500; color: var(--text-primary); border: 1px solid var(--border-light);">${k.word} <span style="color: var(--text-secondary); margin-left: 4px;">${k.count}</span></div>`
                ).join('');
            } else if (container) {
                showEmpty('searchKeywordsContainer', 'No search queries logged yet.');
            }
        }).catch(() => showError('searchKeywordsContainer', 'Failed to load search data'));
    }
    else if (tab === 'nav-intel') {
        fetch(`${BACKEND_URL}/api/admin/analytics/navigation`, { headers: API_HEADERS() })
        .then(r=>r.json()).then(data => {
            const tbody = document.getElementById('navDestTbody');
            if (tbody && data.top_destinations && data.top_destinations.length > 0) {
                tbody.innerHTML = data.top_destinations.map(d => `<tr><td>${d.destination}</td><td style="font-weight:600">${d.requests}</td></tr>`).join('');
            } else if (tbody) {
                tbody.innerHTML = '<tr><td colspan="2" class="text-center" style="color:var(--text-secondary)">No destination data available.</td></tr>';
            }
        }).catch(() => {
            const tbody = document.getElementById('navDestTbody');
            if(tbody) tbody.innerHTML = '<tr><td colspan="2" class="text-center" style="color:var(--text-secondary)">No data available yet</td></tr>';
        });
    }
    else if (tab === 'users') loadUsers();
    else if (tab === 'chats') loadChats();
    else if (tab === 'stores') loadStores();
    else if (tab === 'offers') loadOffers();
    else if (tab === 'events') loadEvents();
    else if (tab === 'facilities') loadFacilities();
    else if (tab === 'feedback') loadFeedback();
    else if (tab === 'logs') loadLogs();
    else if (tab === 'settings') loadSettings();
}

async function loadAnalytics() {
    loadOverviewData();
}


// ================= EXISTING CRUD (STORES/OFFERS/EVENTS) =================

// Load categories
async function loadCategories() {
    try {
        console.log('Loading categories from:', `${BACKEND_URL}/api/stores/categories`);
        const response = await fetch(`${BACKEND_URL}/api/stores/categories`);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        console.log('Categories loaded:', data);
        categories = data.categories || [];

        const select = document.getElementById('storeCategory');
        if (select) {
            select.innerHTML = '<option value="">Select Category</option>';
            if (categories.length === 0) {
                select.innerHTML += '<option value="" disabled>No categories available - please refresh</option>';
                console.warn('No categories found in database');
            } else {
                categories.forEach(cat => {
                    select.innerHTML += `<option value="${cat.id}">${cat.icon || ''} ${cat.name}</option>`;
                });
                console.log(`${categories.length} categories loaded into dropdown`);
            }
        }

        // Load stores after categories are ready (for offers dropdown)
        await loadStores();

    } catch (error) {
        console.error('Error loading categories:', error);
        const select = document.getElementById('storeCategory');
        if (select) {
            select.innerHTML = '<option value="">Error loading categories - please refresh</option>';
        }
        // Show user-friendly alert for critical errors
        if (!navigator.onLine) {
            alert('Network error: Please check your internet connection and refresh the page.');
        }
    }
}

// Load stores
async function loadStores() {
    try {
        const response = await fetch(`${BACKEND_URL}/api/admin/stores`);
        const data = await response.json();
        stores = data.stores;

        const tbody = document.querySelector('#storesTable tbody');
        tbody.innerHTML = '';

        stores.forEach(store => {
            tbody.innerHTML += `
                <tr>
                    <td>${store.name}</td>
                    <td>${store.category_name || 'N/A'}</td>
                    <td>${store.floor}</td>
                    <td>${store.unit}</td>
                    <td>${store.status}</td>
                    <td>
                        <button class="btn-edit" onclick="editStore(${store.id})">Edit</button>
                        <button class="btn-delete" onclick="deleteStore(${store.id})">Delete</button>
                    </td>
                </tr>
            `;
        });

        // Update store select in offer form
        const offerStoreSelect = document.getElementById('offerStore');
        if (offerStoreSelect) {
            offerStoreSelect.innerHTML = '<option value="">Select Store</option>';
            stores.forEach(store => {
                offerStoreSelect.innerHTML += `<option value="${store.id}">${store.name}</option>`;
            });
        }
    } catch (error) {
        console.error('Error loading stores:', error);
    }
}

// Store Modal
function openStoreModal() {
    editMode = false;
    currentEditId = null;
    document.getElementById('storeModalTitle').textContent = 'Add Store';
    document.getElementById('storeForm').reset();
    document.getElementById('storeModal').style.display = 'block';
}

function closeStoreModal() {
    document.getElementById('storeModal').style.display = 'none';
}

function editStore(id) {
    const store = stores.find(s => s.id === id);
    if (!store) return;

    editMode = true;
    currentEditId = id;
    document.getElementById('storeModalTitle').textContent = 'Edit Store';
    document.getElementById('storeName').value = store.name;
    document.getElementById('storeCategory').value = store.category_id;
    document.getElementById('storeFloor').value = store.floor;
    document.getElementById('storeUnit').value = store.unit;
    document.getElementById('storeDescription').value = store.description || '';
    document.getElementById('storeModal').style.display = 'block';
}

async function deleteStore(id) {
    if (!confirm('Are you sure you want to delete this store?')) return;

    try {
        const response = await fetch(`${BACKEND_URL}/api/admin/stores/${id}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            alert('Store deleted successfully!');
            loadStores();
            loadAnalytics();
        } else {
            alert('Failed to delete store');
        }
    } catch (error) {
        console.error('Error deleting store:', error);
        alert('Error deleting store');
    }
}

document.getElementById('storeForm').addEventListener('submit', async (e) => {
    e.preventDefault();

    const storeData = {
        name: document.getElementById('storeName').value,
        category_id: parseInt(document.getElementById('storeCategory').value),
        floor: document.getElementById('storeFloor').value,
        unit: document.getElementById('storeUnit').value,
        description: document.getElementById('storeDescription').value,
        mall_id: 1
    };

    try {
        const url = editMode
            ? `${BACKEND_URL}/api/admin/stores/${currentEditId}`
            : `${BACKEND_URL}/api/admin/stores`;

        const response = await fetch(url, {
            method: editMode ? 'PUT' : 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(storeData)
        });

        if (response.ok) {
            alert(editMode ? 'Store updated!' : 'Store created!');
            closeStoreModal();
            loadStores();
            loadAnalytics();
        } else {
            const data = await response.json();
            alert(data.error || 'Operation failed');
        }
    } catch (error) {
        console.error('Error saving store:', error);
        alert('Error saving store');
    }
});

// Load offers
async function loadOffers() {
    try {
        const response = await fetch(`${BACKEND_URL}/api/admin/offers`);
        const data = await response.json();

        const tbody = document.querySelector('#offersTable tbody');
        tbody.innerHTML = '';

        data.offers.forEach(offer => {
            tbody.innerHTML += `
                <tr>
                    <td>${offer.title}</td>
                    <td>${offer.store_name || 'N/A'}</td>
                    <td>${new Date(offer.start_date).toLocaleDateString()}</td>
                    <td>${new Date(offer.end_date).toLocaleDateString()}</td>
                    <td>${offer.is_featured ? 'Yes' : 'No'}</td>
                    <td>
                        <button class="btn-edit" onclick="editOffer(${offer.id})">Edit</button>
                        <button class="btn-delete" onclick="deleteOffer(${offer.id})">Delete</button>
                    </td>
                </tr>
            `;
        });
    } catch (error) {
        console.error('Error loading offers:', error);
    }
}

// Offer Modal
function openOfferModal() {
    document.getElementById('offerModalTitle').textContent = 'Add Offer';
    document.getElementById('offerForm').reset();
    document.getElementById('offerModal').style.display = 'block';
}

function closeOfferModal() {
    document.getElementById('offerModal').style.display = 'none';
}

async function deleteOffer(id) {
    if (!confirm('Are you sure you want to delete this offer?')) return;

    try {
        const response = await fetch(`${BACKEND_URL}/api/admin/offers/${id}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            alert('Offer deleted!');
            loadOffers();
            loadAnalytics();
        }
    } catch (error) {
        console.error('Error deleting offer:', error);
    }
}

document.getElementById('offerForm').addEventListener('submit', async (e) => {
    e.preventDefault();

    const offerData = {
        store_id: parseInt(document.getElementById('offerStore').value),
        title: document.getElementById('offerTitle').value,
        description: document.getElementById('offerDescription').value,
        start_date: document.getElementById('offerStartDate').value,
        end_date: document.getElementById('offerEndDate').value
    };

    try {
        const response = await fetch(`${BACKEND_URL}/api/admin/offers`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(offerData)
        });

        if (response.ok) {
            alert('Offer created!');
            closeOfferModal();
            loadOffers();
            loadAnalytics();
        }
    } catch (error) {
        console.error('Error creating offer:', error);
    }
});

// Load events
async function loadEvents() {
    try {
        const response = await fetch(`${BACKEND_URL}/api/admin/events`);
        const data = await response.json();

        const tbody = document.querySelector('#eventsTable tbody');
        tbody.innerHTML = '';

        data.events.forEach(event => {
            tbody.innerHTML += `
                <tr>
                    <td>${event.name}</td>
                    <td>${new Date(event.event_date).toLocaleString()}</td>
                    <td>${event.location}</td>
                    <td>
                        <button class="btn-delete" onclick="deleteEvent(${event.id})">Delete</button>
                    </td>
                </tr>
            `;
        });
    } catch (error) {
        console.error('Error loading events:', error);
    }
}

// Event Modal
function openEventModal() {
    document.getElementById('eventModalTitle').textContent = 'Add Event';
    document.getElementById('eventForm').reset();
    document.getElementById('eventModal').style.display = 'block';
}

function closeEventModal() {
    document.getElementById('eventModal').style.display = 'none';
}

async function deleteEvent(id) {
    if (!confirm('Are you sure you want to delete this event?')) return;

    try {
        const response = await fetch(`${BACKEND_URL}/api/admin/events/${id}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            alert('Event deleted!');
            loadEvents();
        }
    } catch (error) {
        console.error('Error deleting event:', error);
    }
}

// Logout Modal Logic
function showLogoutModal() {
    document.getElementById('logoutModal').style.display = 'flex';
}

function closeLogoutModal() {
    document.getElementById('logoutModal').style.display = 'none';
}

async function confirmLogout() {
    if (window.logout) {
        // use the global logout function if available (which now clears auth and redirects to home)
        await window.logout();
    } else {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        localStorage.removeItem('userType');
        window.location.replace('index.html');
    }
}

document.getElementById('eventForm').addEventListener('submit', async (e) => {
    e.preventDefault();

    const eventData = {
        mall_id: 1,
        name: document.getElementById('eventName').value,
        description: document.getElementById('eventDescription').value,
        event_date: document.getElementById('eventDate').value,
        location: document.getElementById('eventLocation').value
    };

    try {
        const response = await fetch(`${BACKEND_URL}/api/admin/events`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(eventData)
        });

        if (response.ok) {
            alert('Event created!');
            closeEventModal();
            loadEvents();
        }
    } catch (error) {
        console.error('Error creating event:', error);
    }
});

// Utility function for debounce
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Admin AI BI Assistant chat messaging function
async function sendAdminAIChatMessage() {
    const input = document.getElementById('aiChatInput');
    const message = input.value.trim();
    if (!message) return;

    input.value = '';

    const chatMessages = document.getElementById('aiChatMessages');
    
    // Add user message
    const userMsgDiv = document.createElement('div');
    userMsgDiv.style.cssText = 'background: #9B7BC7; color: white; padding: 12px 16px; border-radius: 12px; max-width: 80%; align-self: flex-end; line-height: 1.5; font-size: 14px; box-shadow: 0 1px 2px rgba(0,0,0,0.05); margin-bottom: 5px;';
    userMsgDiv.textContent = message;
    chatMessages.appendChild(userMsgDiv);
    
    // Scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;

    // Add typing indicator
    const typingDiv = document.createElement('div');
    typingDiv.style.cssText = 'background: #efe7f7; color: #666; padding: 12px 16px; border-radius: 12px; max-width: 80%; align-self: flex-start; line-height: 1.5; font-size: 14px; font-style: italic; margin-bottom: 5px;';
    typingDiv.textContent = 'Thinking...';
    chatMessages.appendChild(typingDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    try {
        const response = await fetch(`${BACKEND_URL}/api/admin/ai/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            },
            body: JSON.stringify({ message: message })
        });

        if (chatMessages.contains(typingDiv)) {
            chatMessages.removeChild(typingDiv);
        }

        if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.error || errData.msg || 'Failed to get response');
        }

        const data = await response.json();
        
        // Add agent message
        const agentMsgDiv = document.createElement('div');
        agentMsgDiv.style.cssText = 'background: #efe7f7; color: #333; padding: 12px 16px; border-radius: 12px; max-width: 80%; align-self: flex-start; line-height: 1.5; font-size: 14px; box-shadow: 0 1px 2px rgba(0,0,0,0.05); margin-bottom: 5px;';
        
        // Let's format the answer: replace newlines with br, bolding, bullets
        let formattedAnswer = data.answer
            .replace(/\n/g, '<br>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/^- (.*?)(?:<br>|$)/gm, '• $1<br>');
            
        agentMsgDiv.innerHTML = formattedAnswer;
        
        // Add collapsed debug tools details
        if (data.tools_used && data.tools_used.length > 0) {
            const debugDiv = document.createElement('div');
            debugDiv.style.cssText = 'font-size: 11px; color: #888; margin-top: 5px; border-top: 1px dashed #ddd; padding-top: 5px;';
            debugDiv.innerHTML = `<strong>Tools called:</strong> ${data.tools_used.join(', ')} (Confidence: ${data.confidence})`;
            agentMsgDiv.appendChild(debugDiv);
        }
        
        chatMessages.appendChild(agentMsgDiv);

    } catch (error) {
        if (chatMessages.contains(typingDiv)) {
            chatMessages.removeChild(typingDiv);
        }
        const errorDiv = document.createElement('div');
        errorDiv.style.cssText = 'background: #FEE2E2; color: #991B1B; padding: 12px 16px; border-radius: 12px; max-width: 80%; align-self: flex-start; line-height: 1.5; font-size: 14px; margin-bottom: 5px;';
        errorDiv.textContent = `Error: ${error.message}`;
        chatMessages.appendChild(errorDiv);
    }
    
    chatMessages.scrollTop = chatMessages.scrollHeight;
}


// Initialize
document.addEventListener('DOMContentLoaded', () => {
    checkAuth();
    initCharts();
    loadLiveStats();
    loadAnalytics();
    loadCategories();
    // Refresh live stats every 30 seconds
    setInterval(loadLiveStats, 30000);
});


// RESTORED FUNCTIONS FROM PHASE 2
async function loadUsers() {
    try {
        const searchInput = document.getElementById('userSearch');
        const search = searchInput ? searchInput.value : '';
        console.log('Fetching users with search:', search);

        const response = await fetch(`${BACKEND_URL}/api/admin/users?search=${search}`, {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        console.log('Users data:', data);

        const tbody = document.querySelector('#usersTable tbody');
        if (!tbody) {
            console.error('Users table body not found');
            return;
        }

        if (!data.users || data.users.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-center">No users found</td></tr>';
            return;
        }

        tbody.innerHTML = data.users.map(user => `
            <tr>
                <td>${user.name}</td>
                <td>${user.email}</td>
                <td>${new Date(user.created_at).toLocaleDateString()}</td>
                <td>${user.last_login ? new Date(user.last_login).toLocaleString() : 'Never'}</td>
                <td><span class="status-badge ${user.is_active ? 'active' : 'inactive'}">${user.is_active ? 'Active' : 'Inactive'}</span></td>
                <td>
                    <button class="btn-sm btn-outline" onclick="toggleUserStatus(${user.id}, ${!user.is_active})">
                        ${user.is_active ? 'Deactivate' : 'Activate'}
                    </button>
                </td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Error loading users:', error);
        // Only alert if it's a real network error, to avoid annoying user
        if (!navigator.onLine) alert('Network error: Please check your connection');
    }
}

async function toggleUserStatus(userId, isActive) {
    if (!confirm(`Are you sure you want to ${isActive ? 'activate' : 'deactivate'} this user?`)) return;

    try {
        const response = await fetch(`${BACKEND_URL}/api/admin/users/${userId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            },
            body: JSON.stringify({ is_active: isActive })
        });

        if (response.ok) loadUsers();
    } catch (error) {
        console.error('Error updating user:', error);
    }
}

async function loadChats() {
    try {
        const response = await fetch(`${BACKEND_URL}/api/admin/chats`);
        const data = await response.json();

        const tbody = document.querySelector('#chatsTable tbody');
        tbody.innerHTML = data.sessions.map(session => `
            <tr>
                <td>${session.session_id.substring(0, 8)}...</td>
                <td>${new Date(session.created_at).toLocaleString()}</td>
                <td>${session.message_count}</td>
                <td class="text-truncate" style="max-width: 200px;">${session.last_message || 'N/A'}</td>
                <td>
                    <button class="btn-sm btn-primary" onclick="viewChat('${session.id}')">View</button>
                </td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Error loading chats:', error);
    }
}

function viewChat(sessionId) {
    alert('Detailed chat view coming soon!');
    // TODO: Implement chat detail modal
}

async function loadFacilities() {
    try {
        const response = await fetch(`${BACKEND_URL}/api/admin/facilities`);
        const data = await response.json();

        const tbody = document.querySelector('#facilitiesTable tbody');
        tbody.innerHTML = data.facilities.map(f => `
            <tr>
                <td>${f.name}</td>
                <td>${f.type}</td>
                <td>Floor ${f.floor} ${f.unit ? '- ' + f.unit : ''}</td>
                <td>${f.is_active ? 'Active' : 'Inactive'}</td>
                <td>
                    <button class="btn-delete" onclick="deleteFacility(${f.id})">Delete</button>
                </td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Error loading facilities:', error);
    }
}

async function deleteFacility(id) {
    if (!confirm('Are you sure?')) return;
    try {
        const response = await fetch(`${BACKEND_URL}/api/admin/facilities/${id}`, { method: 'DELETE' });
        if (response.ok) loadFacilities();
    } catch (error) {
        console.error('Error:', error);
    }
}


