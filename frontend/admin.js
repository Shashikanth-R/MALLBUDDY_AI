// BACKEND_URL - uses config.js if available, otherwise fallback to localhost
const BACKEND_URL = window.BACKEND_URL || 'http://localhost:5000';
let currentEditId = null;
let editMode = false;
let categories = [];
let stores = [];
let chatChart = null;
let categoryChart = null;

// Initialize charts
function initCharts() {
    // Chat Activity Chart
    const chatCtx = document.createElement('canvas');
    document.getElementById('chatActivityChart').appendChild(chatCtx);

    chatChart = new Chart(chatCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Daily Sessions',
                data: [],
                borderColor: '#6366F1',
                tension: 0.4,
                fill: true,
                backgroundColor: 'rgba(99, 102, 241, 0.1)'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        display: false
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            }
        }
    });

    // Category Distribution Chart
    const catCtx = document.createElement('canvas');
    document.getElementById('categoryChart').appendChild(catCtx);

    categoryChart = new Chart(catCtx, {
        type: 'doughnut',
        data: {
            labels: [],
            datasets: [{
                data: [],
                backgroundColor: [
                    '#6366F1', '#10B981', '#F59E0B', '#EF4444',
                    '#8B5CF6', '#EC4899', '#3B82F6', '#64748B'
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right'
                }
            }
        }
    });
}

// Check admin role
function checkAuth() {
    const userType = localStorage.getItem('userType');
    const user = JSON.parse(localStorage.getItem('user') || '{}');

    if (userType !== 'admin') {
        window.location.replace('index.html');
        return;
    }

    document.getElementById('adminName').textContent = user.name || 'Admin';
}

// Switch tabs
function switchTab(tab) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

    event.target.classList.add('active');
    document.getElementById(`${tab}-tab`).classList.add('active');

    // Load data for the selected tab
    switch (tab) {
        case 'analytics': loadAnalytics(); break;
        case 'users': loadUsers(); break;
        case 'chats': loadChats(); break;
        case 'stores': loadStores(); break;
        case 'offers': loadOffers(); break;
        case 'events': loadEvents(); break;
        case 'facilities': loadFacilities(); break;
        case 'feedback': loadFeedback(); break;
        case 'logs': loadLogs(); break;
        case 'settings': loadSettings(); break;
    }
}

// Load live stats
async function loadLiveStats() {
    try {
        const response = await fetch(`${BACKEND_URL}/api/admin/stats/live`, {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
        });
        const data = await response.json();

        document.getElementById('activeVisitors').textContent = data.active_sessions || 0;
        document.getElementById('todayChats').textContent = data.today_messages || 0;
    } catch (error) {
        console.error('Error loading live stats:', error);
    }
}

// Load comprehensive analytics
async function loadAnalytics() {
    try {
        const response = await fetch(`${BACKEND_URL}/api/admin/analytics`, {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
        });
        const data = await response.json();

        // Update stats cards
        document.getElementById('totalUsers').textContent = data.stats.total_users || 0;
        document.getElementById('pendingFeedback').textContent = data.stats.total_feedback || 0; // Using total for now

        // Update charts
        if (chatChart && data.daily_sessions) {
            chatChart.data.labels = data.daily_sessions.map(d => new Date(d.date).toLocaleDateString());
            chatChart.data.datasets[0].data = data.daily_sessions.map(d => d.count);
            chatChart.update();
        }

        if (categoryChart && data.stores_by_category) {
            categoryChart.data.labels = data.stores_by_category.map(c => c.category);
            categoryChart.data.datasets[0].data = data.stores_by_category.map(c => c.count);
            categoryChart.update();
        }

        // Popular keywords (mock or from API if available)
        loadPopularKeywords();

    } catch (error) {
        console.error('Error loading analytics:', error);
    }
}

async function loadPopularKeywords() {
    try {
        const response = await fetch(`${BACKEND_URL}/api/admin/chats/popular-questions`, {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
        });
        const data = await response.json();

        const container = document.getElementById('popularKeywords');
        container.innerHTML = data.popular_keywords.map(k =>
            `<span class="keyword-tag">${k.word} (${k.count})</span>`
        ).join('');

    } catch (error) {
        console.error('Error loading keywords:', error);
    }
}

// ================= USERS MANAGEMENT =================

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

// ================= CHATS MANAGEMENT =================

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

// ================= FEEDBACK MANAGEMENT =================

async function loadFeedback() {
    try {
        const response = await fetch(`${BACKEND_URL}/api/admin/feedback`);
        const data = await response.json();

        const tbody = document.querySelector('#feedbackTable tbody');
        tbody.innerHTML = data.feedback.map(fb => `
            <tr>
                <td>${fb.type}</td>
                <td>${fb.message}</td>
                <td>${new Date(fb.created_at).toLocaleDateString()}</td>
                <td><span class="status-badge ${fb.status}">${fb.status}</span></td>
                <td>
                    ${fb.status === 'open' ?
                `<button class="btn-sm btn-success" onclick="resolveFeedback(${fb.id})">Resolve</button>` :
                '<span class="text-muted">Resolved</span>'}
                </td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Error loading feedback:', error);
    }
}

async function resolveFeedback(id) {
    try {
        const response = await fetch(`${BACKEND_URL}/api/admin/feedback/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: 'resolved' })
        });

        if (response.ok) loadFeedback();
    } catch (error) {
        console.error('Error resolving feedback:', error);
    }
}

// ================= FACILITIES MANAGEMENT =================

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

// ================= LOGS MANAGEMENT =================

async function loadLogs() {
    try {
        const response = await fetch(`${BACKEND_URL}/api/admin/audit-logs`);
        const data = await response.json();

        const tbody = document.querySelector('#logsTable tbody');
        tbody.innerHTML = data.logs.map(log => `
            <tr>
                <td>${new Date(log.timestamp).toLocaleString()}</td>
                <td>${log.admin_email || 'System'}</td>
                <td><span class="badge badge-info">${log.action}</span></td>
                <td>${log.entity_type}</td>
                <td><small>${JSON.stringify(log.details).substring(0, 50)}...</small></td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Error loading logs:', error);
    }
}

// ================= SETTINGS MANAGEMENT =================

async function loadSettings() {
    try {
        const response = await fetch(`${BACKEND_URL}/api/admin/settings`);
        const data = await response.json();

        const form = document.getElementById('settingsForm');
        form.innerHTML = data.settings.map(s => `
            <div class="form-group">
                <label class="form-label">${s.key.replace(/_/g, ' ').toUpperCase()}</label>
                <input type="text" class="form-input setting-input" name="${s.key}" value="${s.value}">
                <small class="text-muted">${s.description || ''}</small>
            </div>
        `).join('');
    } catch (error) {
        console.error('Error loading settings:', error);
    }
}

async function saveSettings() {
    const inputs = document.querySelectorAll('.setting-input');
    const settings = {};
    inputs.forEach(input => {
        settings[input.name] = input.value;
    });

    try {
        const response = await fetch(`${BACKEND_URL}/api/admin/settings/bulk`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ settings })
        });

        if (response.ok) alert('Settings saved successfully!');
    } catch (error) {
        console.error('Error saving settings:', error);
    }
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
            throw new Error(errData.error || 'Failed to get response');
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
