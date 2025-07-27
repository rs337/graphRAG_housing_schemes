/**
 * JavaScript for GraphRAG Chat Interface
 * Handles AJAX communication, real-time updates, and user interactions
 */

// Global variables
let isSearching = false;
let chatHistory = [];

// DOM elements
const chatForm = document.getElementById('chat-form');
const queryInput = document.getElementById('query-input');
const sendButton = document.getElementById('send-button');
const sendText = document.getElementById('send-text');
const loadingText = document.getElementById('loading-text');
const chatMessages = document.getElementById('chat-messages');
const statusIndicator = document.getElementById('status-indicator');

// Initialize the application
$(document).ready(function() {
    console.log('GraphRAG Chat Interface initialized');
    
    // Set up event listeners
    setupEventListeners();
    
    // Check system health
    checkSystemHealth();
    
    // Focus on input
    queryInput.focus();
});

/**
 * Set up all event listeners
 */
function setupEventListeners() {
    // Form submission
    chatForm.addEventListener('submit', handleFormSubmission);
    
    // Example query clicks
    $(document).on('click', '.example-query', handleExampleQuery);
    
    // Search type card clicks
    $('.search-type-card').on('click', function() {
        const searchType = $(this).data('search-type');
        $(`#search_${searchType}`).prop('checked', true);
        updateSearchTypeCards();
    });
    
    // Search type radio button changes
    $('input[name="search_type"]').on('change', updateSearchTypeCards);
    
    // Enter key handling
    queryInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (!isSearching) {
                chatForm.dispatchEvent(new Event('submit'));
            }
        }
    });
    
    // Initialize search type cards
    updateSearchTypeCards();
}

/**
 * Handle form submission
 */
async function handleFormSubmission(e) {
    e.preventDefault();
    
    if (isSearching) return;
    
    const query = queryInput.value.trim();
    const searchType = $('input[name="search_type"]:checked').val();
    
    // Validate input
    if (!query) {
        queryInput.focus();
        return;
    }
    
    // Add user message to chat
    addUserMessage(query, searchType);
    
    // Clear input and set loading state
    queryInput.value = '';
    setLoadingState(true);
    
    try {
        // Send AJAX request
        const response = await sendChatQuery(query, searchType);
        
        if (response.success) {
            addBotMessage(response.response, response.context, searchType);
        } else {
            addErrorMessage(response.error || 'An unknown error occurred');
        }
    } catch (error) {
        console.error('Chat error:', error);
        addErrorMessage('Failed to communicate with server. Please try again.');
    } finally {
        setLoadingState(false);
        queryInput.focus();
    }
}

/**
 * Send chat query to Django backend
 */
async function sendChatQuery(query, searchType) {
    const csrfToken = $('[name=csrfmiddlewaretoken]').val();
    
    const response = await fetch('/query/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken,
        },
        body: JSON.stringify({
            query: query,
            search_type: searchType
        })
    });
    
    if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    return await response.json();
}

/**
 * Add user message to chat
 */
function addUserMessage(query, searchType) {
    const timestamp = new Date().toLocaleTimeString();
    const searchTypeLabel = getSearchTypeLabel(searchType);
    
    const messageHtml = `
        <div class="message user-message">
            <div class="message-content">
                <div class="d-flex align-items-start">
                    <div class="flex-grow-1">
                        <div class="message-bubble">
                            <p class="mb-1">${escapeHtml(query)}</p>
                            <div class="message-timestamp">
                                <i class="fas fa-search me-1"></i>
                                ${searchTypeLabel} • ${timestamp}
                            </div>
                        </div>
                    </div>
                    <div class="avatar bg-success text-white">
                        <i class="fas fa-user"></i>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    $(chatMessages).append(messageHtml);
    scrollToBottom();
    
    // Save to history
    chatHistory.push({
        type: 'user',
        query: query,
        searchType: searchType,
        timestamp: new Date()
    });
}

/**
 * Add bot response message to chat
 */
function addBotMessage(response, context, searchType) {
    const timestamp = new Date().toLocaleTimeString();
    const searchTypeLabel = getSearchTypeLabel(searchType);
    
    // Convert markdown-style bold text to HTML
    const formattedResponse = response.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    // Convert line breaks to proper HTML
    const htmlResponse = formattedResponse.replace(/\n/g, '<br>');
    
    const contextToggleId = `context-${Date.now()}`;
    
    const messageHtml = `
        <div class="message bot-message">
            <div class="message-content">
                <div class="d-flex align-items-start">
                    <div class="avatar bg-primary text-white me-3">
                        <i class="fas fa-robot"></i>
                    </div>
                    <div class="flex-grow-1">
                        <div class="message-bubble">
                            <div class="mb-2">${htmlResponse}</div>
                            <div class="message-timestamp">
                                <i class="fas fa-robot me-1"></i>
                                ${searchTypeLabel} Response • ${timestamp}
                            </div>
                            ${context && context.trim() !== 'No context data available' ? `
                                <div class="context-toggle mt-2">
                                    <button class="btn btn-sm btn-outline-secondary w-100" 
                                            data-bs-toggle="collapse" 
                                            data-bs-target="#${contextToggleId}">
                                        <i class="fas fa-info-circle me-1"></i>
                                        View Context Information
                                    </button>
                                    <div class="collapse mt-2" id="${contextToggleId}">
                                        <div class="context-content p-2">
                                            <pre class="mb-0 small">${escapeHtml(context)}</pre>
                                        </div>
                                    </div>
                                </div>
                            ` : ''}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    $(chatMessages).append(messageHtml);
    scrollToBottom();
    
    // Save to history
    chatHistory.push({
        type: 'bot',
        response: response,
        context: context,
        searchType: searchType,
        timestamp: new Date()
    });
}

/**
 * Add error message to chat
 */
function addErrorMessage(error) {
    const timestamp = new Date().toLocaleTimeString();
    
    const messageHtml = `
        <div class="message bot-message">
            <div class="message-content">
                <div class="d-flex align-items-start">
                    <div class="avatar bg-danger text-white me-3">
                        <i class="fas fa-exclamation-triangle"></i>
                    </div>
                    <div class="flex-grow-1">
                        <div class="message-bubble border-danger">
                            <div class="text-danger mb-2">
                                <strong>Error:</strong> ${escapeHtml(error)}
                            </div>
                            <div class="message-timestamp">
                                <i class="fas fa-exclamation-triangle me-1"></i>
                                Error • ${timestamp}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    $(chatMessages).append(messageHtml);
    scrollToBottom();
}

/**
 * Handle example query clicks
 */
function handleExampleQuery(e) {
    e.preventDefault();
    
    if (isSearching) return;
    
    const query = $(this).data('query');
    const searchType = $(this).data('search-type');
    
    // Set the form values
    queryInput.value = query;
    $(`#search_${searchType}`).prop('checked', true);
    updateSearchTypeCards();
    
    // Submit the form
    setTimeout(() => {
        chatForm.dispatchEvent(new Event('submit'));
    }, 100);
}

/**
 * Set loading state
 */
function setLoadingState(loading) {
    isSearching = loading;
    
    if (loading) {
        sendText.classList.add('d-none');
        loadingText.classList.remove('d-none');
        sendButton.disabled = true;
        queryInput.disabled = true;
        statusIndicator.className = 'badge bg-warning';
        statusIndicator.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Searching...';
    } else {
        sendText.classList.remove('d-none');
        loadingText.classList.add('d-none');
        sendButton.disabled = false;
        queryInput.disabled = false;
        statusIndicator.className = 'badge bg-success';
        statusIndicator.innerHTML = '<i class="fas fa-circle me-1"></i>Ready';
    }
}

/**
 * Update search type card styling
 */
function updateSearchTypeCards() {
    const selectedType = $('input[name="search_type"]:checked').val();
    
    $('.search-type-card').removeClass('active');
    $(`.search-type-card[data-search-type="${selectedType}"]`).addClass('active');
}

/**
 * Get search type label
 */
function getSearchTypeLabel(searchType) {
    const labels = {
        'global': 'Global Search',
        'local': 'Local Search',
        'basic': 'Basic Search'
    };
    return labels[searchType] || searchType;
}

/**
 * Scroll chat to bottom
 */
function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

/**
 * Clear chat history
 */
function clearChat() {
    if (isSearching) return;
    
    if (confirm('Are you sure you want to clear the chat history?')) {
        chatHistory = [];
        
        // Keep only the welcome message
        const welcomeMessage = $(chatMessages).find('.message').first();
        $(chatMessages).empty().append(welcomeMessage);
        
        queryInput.focus();
    }
}

/**
 * Check system health
 */
async function checkSystemHealth() {
    try {
        const response = await fetch('/health/');
        const data = await response.json();
        
        if (data.status === 'healthy') {
            console.log('System health check passed:', data.message);
        } else {
            console.warn('System health check failed:', data.message);
            statusIndicator.className = 'badge bg-danger';
            statusIndicator.innerHTML = '<i class="fas fa-exclamation-triangle me-1"></i>System Error';
        }
    } catch (error) {
        console.error('Health check failed:', error);
        statusIndicator.className = 'badge bg-danger';
        statusIndicator.innerHTML = '<i class="fas fa-exclamation-triangle me-1"></i>Offline';
    }
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Export chat history (future feature)
 */
function exportChatHistory() {
    const dataStr = JSON.stringify(chatHistory, null, 2);
    const dataBlob = new Blob([dataStr], {type: 'application/json'});
    
    const link = document.createElement('a');
    link.href = URL.createObjectURL(dataBlob);
    link.download = `graphrag-chat-${new Date().toISOString().split('T')[0]}.json`;
    link.click();
} 