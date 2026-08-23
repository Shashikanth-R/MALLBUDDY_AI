// Session management
let sessionId = generateSessionId();
let chatHistory = [];
let isFirstMessage = true;



// Generate unique session ID
function generateSessionId() {
    return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
}

// Navigation functions
function navigateTo(page) {
    if (page === 'login') {
        window.location.href = 'login.html';
    } else if (page === 'signup') {
        window.location.href = 'signup.html';
    } else if (page === 'navigate') {
        alert('Navigation feature - Coming soon!');
    } else if (page === 'map') {
        alert('Mall map feature - Coming soon!');
    }
}

// Send quick question
function sendQuickQuestion(question) {
    document.getElementById('chatInput').value = question;
    sendMessage();
}

// Handle key press
function handleKeyPress(event) {
    if (event.key === 'Enter') {
        sendMessage();
    }
}

// Send message
async function sendMessage() {
    const input = document.getElementById('chatInput');
    const message = input.value.trim();

    if (!message) return;

    // Show chat messages container on first message
    if (isFirstMessage) {
        document.getElementById('welcomeCard').style.display = 'none';
        document.getElementById('chatMessagesContainer').style.display = 'block';
        isFirstMessage = false;
    }

    // Add user message to chat
    addMessage(message, 'user');

    // Clear input
    input.value = '';

    // Show typing indicator
    showTypingIndicator();

    // Fire-and-forget telemetry; it cannot delay or affect the chat request.
    MallBuddyAnalytics.track('ai_query', { search_query: message });

    // Send to backend - BACKEND_URL is provided by config.js
    const backendUrl = window.BACKEND_URL || 'http://localhost:5000';

    try {
        const response = await fetch(`${backendUrl}/api/chat/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                session_id: sessionId,
                user_message: message,
                mall_id: 1 // TODO: Get from user selection
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        // Remove typing indicator
        removeTypingIndicator();

        // Add bot response with suggestions
        if (data.suggestions && Array.isArray(data.suggestions)) {
            // Convert string suggestions to button format
            const formattedSuggestions = data.suggestions.map(s => ({
                label: s,
                action: 'send_message',
                data: { message: s }
            }));
            formattedSuggestions.forEach(s => MallBuddyAnalytics.track('recommendation_view', {
                metadata: { recommendation: s.label, action: s.action }
            }));
            addMessage(data.response, 'bot', formattedSuggestions);
        } else {
            addMessage(data.response, 'bot');
        }

    } catch (error) {
        console.error('Error connecting to backend:', error);
        removeTypingIndicator();

        // Show error message to user
        addMessage('Sorry, I\'m having trouble connecting to the server. Please make sure the backend is running on port 5000. 🔌', 'bot');
    }
}

// Generate demo response (for testing without backend)
function generateDemoResponse(message) {
    const lowerMessage = message.toLowerCase();

    if (lowerMessage.includes('adidas')) {
        return {
            text: "Adidas is located on Floor 2, Unit 205. It's near the central atrium, next to Nike.",
            suggestions: [
                { label: 'Navigate', action: 'navigate', data: { destination: 'Adidas' } },
                { label: 'View Offers', action: 'view_offers', data: { store: 'Adidas' } }
            ]
        };
    } else if (lowerMessage.includes('food court')) {
        return {
            text: "The Food Court is on Floor 3. You can find a variety of cuisines including Indian, Chinese, Italian, and fast food options.",
            suggestions: [
                { label: 'Navigate', action: 'navigate', data: { destination: 'Food Court' } },
                { label: 'View Restaurants', action: 'view_stores', data: { category: 'food' } }
            ]
        };
    } else if (lowerMessage.includes('offers') || lowerMessage.includes('deals')) {
        return {
            text: "Today's top offers:\n• Zara - 30% off on winter collection\n• Nike - Buy 2 Get 1 Free\n• PVR - 20% off on movie tickets\n• Food Court - Combo meals starting at ₹199",
            suggestions: [
                { label: 'View All Offers', action: 'view_offers', data: {} }
            ]
        };
    } else if (lowerMessage.includes('pvr') || lowerMessage.includes('cinema') || lowerMessage.includes('movie')) {
        return {
            text: "PVR Cinemas is located on Floor 4. From the main entrance, take the elevator to Floor 4 and turn right. You'll find it next to the gaming zone.",
            suggestions: [
                { label: 'Navigate', action: 'navigate', data: { destination: 'PVR' } },
                { label: 'Current Offers', action: 'view_offers', data: { store: 'PVR' } }
            ]
        };
    } else if (lowerMessage.includes('fashion') || lowerMessage.includes('clothing')) {
        return {
            text: "Popular fashion stores in the mall:\n• Zara (Floor 1)\n• H&M (Floor 1)\n• Nike (Floor 2)\n• Adidas (Floor 2)\n• Levi's (Floor 2)\n• Mango (Floor 1)",
            suggestions: [
                { label: 'View All Fashion Stores', action: 'view_stores', data: { category: 'fashion' } }
            ]
        };
    } else if (lowerMessage.includes('timing') || lowerMessage.includes('hours') || lowerMessage.includes('open')) {
        return {
            text: "Mall Timings:\n• Monday - Thursday: 10:00 AM - 10:00 PM\n• Friday - Sunday: 10:00 AM - 11:00 PM\n\nIndividual store timings may vary.",
            suggestions: []
        };
    } else {
        return {
            text: "I can help you with:\n• Finding store locations\n• Getting directions\n• Checking current offers\n• Mall timings and facilities\n• Restaurant recommendations\n\nWhat would you like to know?",
            suggestions: []
        };
    }
}

// Add message to chat
function addMessage(text, sender, suggestions = null) {
    const chatMessages = document.getElementById('chatMessages');

    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    
    // Premium SVG Icons
    const botSvg = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/></svg>`;
    const userSvg = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>`;
    
    avatar.innerHTML = sender === 'bot' ? botSvg : userSvg;

    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';

    // Convert newlines to <br> tags for proper formatting
    // First escape HTML to prevent XSS, then convert newlines
    const escapeHtml = (str) => {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    };
    bubble.innerHTML = escapeHtml(text).replace(/\n/g, '<br>');

    // Add action buttons if suggestions provided
    if (suggestions && suggestions.length > 0) {
        const actionsDiv = document.createElement('div');
        actionsDiv.className = 'action-buttons';

        suggestions.forEach(suggestion => {
            const btn = document.createElement('button');
            btn.className = 'action-btn';
            btn.textContent = suggestion.label;
            btn.onclick = () => handleSuggestionClick(suggestion);
            actionsDiv.appendChild(btn);
        });

        bubble.appendChild(actionsDiv);
    }

    messageDiv.appendChild(avatar);
    messageDiv.appendChild(bubble);

    chatMessages.appendChild(messageDiv);

    // Scroll to bottom
    const container = document.getElementById('chatMessagesContainer');
    container.scrollTop = container.scrollHeight;

    // Add to history
    chatHistory.push({ sender, text, timestamp: new Date() });
}

// Show typing indicator
function showTypingIndicator() {
    const chatMessages = document.getElementById('chatMessages');

    const typingDiv = document.createElement('div');
    typingDiv.className = 'message bot typing-message';
    typingDiv.id = 'typingIndicator';

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.innerHTML = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/></svg>`;

    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';

    const indicator = document.createElement('div');
    indicator.className = 'typing-indicator';
    indicator.innerHTML = `
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
    `;

    bubble.appendChild(indicator);
    typingDiv.appendChild(avatar);
    typingDiv.appendChild(bubble);

    chatMessages.appendChild(typingDiv);

    const container = document.getElementById('chatMessagesContainer');
    container.scrollTop = container.scrollHeight;
}

// Remove typing indicator
function removeTypingIndicator() {
    const indicator = document.getElementById('typingIndicator');
    if (indicator) {
        indicator.remove();
    }
}

// Handle suggestion click
function handleSuggestionClick(suggestion) {
    MallBuddyAnalytics.track('recommendation_click', {
        metadata: { recommendation: suggestion.label, action: suggestion.action }
    });
    if (suggestion.action === 'send_message') {
        // Send the suggestion as a new message
        document.getElementById('chatInput').value = suggestion.data.message;
        sendMessage();
    } else if (suggestion.action === 'navigate') {
        console.log('Navigate to:', suggestion.data);
        addMessage(`Starting navigation to ${suggestion.data.destination}...`, 'bot');
    } else if (suggestion.action === 'view_offers') {
        console.log('View offers for:', suggestion.data);
        addMessage('Here are the current offers. (Feature coming soon!)', 'bot');
    } else if (suggestion.action === 'view_stores') {
        console.log('View stores:', suggestion.data);
        addMessage('Showing stores in this category. (Feature coming soon!)', 'bot');
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    console.log('MallBuddy initialized');
    console.log('Session ID:', sessionId);

    // Focus on input
    document.getElementById('chatInput').focus();
});

// Export for testing
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        sendMessage,
        addMessage,
        generateSessionId
    };
}

// ==========================================
// SCROLL ANIMATIONS
// ==========================================
document.addEventListener('DOMContentLoaded', () => {
    // Add scroll-animate class to sections and cards dynamically
    const elementsToAnimate = document.querySelectorAll('.ai-section, .features-grid, .facilities-grid, .feature-card, .facility-item, .store-card, .offer-card, .filter-section');
    elementsToAnimate.forEach(el => el.classList.add('scroll-animate'));

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('is-visible');
                observer.unobserve(entry.target);
            }
        });
    }, {
        root: null,
        rootMargin: '0px',
        threshold: 0.1
    });

    // We delay slightly to allow DOM to settle before observing
    setTimeout(() => {
        document.querySelectorAll('.scroll-animate').forEach(el => observer.observe(el));
    }, 100);
});
