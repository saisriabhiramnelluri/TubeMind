/**
 * TubeMind — Frontend Application
 * AI-powered understanding for every YouTube video
 */

// ══════════════════════════════════════
// State
// ══════════════════════════════════════
const state = {
    videos: [],
    activeVideoId: null,
    isIngesting: false,
    isQuerying: false,
    chatHistory: [],  // Conversation memory: [{role: 'user'|'assistant', content: '...'}]
};

// ══════════════════════════════════════
// DOM Elements
// ══════════════════════════════════════
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const els = {
    // Sidebar
    sidebar: $('#sidebar'),
    sidebarToggle: $('#sidebarToggle'),
    sidebarOpenBtn: $('#sidebarOpenBtn'),
    sidebarOverlay: $('#sidebarOverlay'),
    newChatBtn: $('#newChatBtn'),
    // Ingest
    youtubeUrl: $('#youtubeUrl'),
    ingestBtn: $('#ingestBtn'),
    ingestStatus: $('#ingestStatus'),
    statusProgress: $('#statusProgress'),
    statusText: $('#statusText'),
    // Videos
    videosList: $('#videosList'),
    videoCount: $('#videoCount'),
    emptyVideos: $('#emptyVideos'),
    // Chat
    chatContainer: $('#chatContainer'),
    welcomeScreen: $('#welcomeScreen'),
    chatMessages: $('#chatMessages'),
    chatInput: $('#chatInput'),
    sendBtn: $('#sendBtn'),
    suggestedPrompts: $('#suggestedPrompts'),
    // Filter
    videoFilter: $('#videoFilter'),
    filterVideoName: $('#filterVideoName'),
    filterClear: $('#filterClear'),
};

// ══════════════════════════════════════
// API Calls
// ══════════════════════════════════════
const API_BASE = window.__API_BASE__ || '/api';

async function apiCall(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    const config = {
        headers: { 'Content-Type': 'application/json' },
        ...options,
    };

    const response = await fetch(url, config);
    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.error || data.detail || `HTTP ${response.status}`);
    }

    return data;
}

// ══════════════════════════════════════
// Video Ingestion
// ══════════════════════════════════════
async function ingestVideo() {
    const url = els.youtubeUrl.value.trim();
    if (!url) {
        showToast('Please paste a YouTube URL', 'error');
        return;
    }

    if (state.isIngesting) return;
    state.isIngesting = true;

    // UI: show loading
    els.ingestBtn.querySelector('.btn-text').hidden = true;
    els.ingestBtn.querySelector('.btn-icon').hidden = true;
    els.ingestBtn.querySelector('.btn-loader').hidden = false;
    els.ingestBtn.disabled = true;
    els.youtubeUrl.disabled = true;

    showIngestStatus('Validating URL and extracting metadata...', 15);

    try {
        // Simulate progress stages
        setTimeout(() => {
            if (state.isIngesting) showIngestStatus('Fetching transcript...', 35);
        }, 2000);
        setTimeout(() => {
            if (state.isIngesting) showIngestStatus('Cleaning and chunking transcript...', 55);
        }, 5000);
        setTimeout(() => {
            if (state.isIngesting) showIngestStatus('Generating embeddings...', 75);
        }, 8000);
        setTimeout(() => {
            if (state.isIngesting) showIngestStatus('Storing in knowledge base...', 90);
        }, 12000);

        const result = await apiCall('/ingest', {
            method: 'POST',
            body: JSON.stringify({ youtube_url: url }),
        });

        showIngestStatus('Done!', 100);

        if (result.status === 'already_exists') {
            showToast(`"${result.title}" is already in your knowledge base`, 'success');
        } else {
            showToast(`Added "${result.title}" (${result.chunks_count} chunks)`, 'success');
        }

        els.youtubeUrl.value = '';
        await loadVideos();
        enableChat();

    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        state.isIngesting = false;
        els.ingestBtn.querySelector('.btn-text').hidden = false;
        els.ingestBtn.querySelector('.btn-icon').hidden = false;
        els.ingestBtn.querySelector('.btn-loader').hidden = true;
        els.ingestBtn.disabled = false;
        els.youtubeUrl.disabled = false;

        setTimeout(() => {
            els.ingestStatus.hidden = true;
        }, 2000);
    }
}

function showIngestStatus(text, progress) {
    els.ingestStatus.hidden = false;
    els.statusText.textContent = text;
    els.statusProgress.style.width = `${progress}%`;
}

// ══════════════════════════════════════
// Video List
// ══════════════════════════════════════
async function loadVideos() {
    try {
        state.videos = await apiCall('/videos');
        renderVideoList();
        if (state.videos.length > 0) {
            enableChat();
        }
    } catch (error) {
        console.error('Failed to load videos:', error);
    }
}

function renderVideoList() {
    const { videos } = state;
    els.videoCount.textContent = videos.length;

    if (videos.length === 0) {
        els.emptyVideos.hidden = false;
        els.videosList.querySelectorAll('.video-card').forEach(c => c.remove());
        return;
    }

    els.emptyVideos.hidden = true;

    const fragment = document.createDocumentFragment();
    for (const video of videos) {
        const card = createVideoCard(video);
        fragment.appendChild(card);
    }

    els.videosList.querySelectorAll('.video-card').forEach(c => c.remove());
    els.videosList.prepend(fragment);
}

function createVideoCard(video) {
    const card = document.createElement('div');
    card.className = `video-card${state.activeVideoId === video.video_id ? ' active' : ''}`;
    card.dataset.videoId = video.video_id;

    const duration = formatDuration(video.duration);

    card.innerHTML = `
        <img class="video-thumb"
             src="${video.thumbnail_url || `https://img.youtube.com/vi/${video.video_id}/mqdefault.jpg`}"
             alt="${escapeHtml(video.title)}"
             loading="lazy"
             onerror="this.src='data:image/svg+xml,<svg xmlns=\\'http://www.w3.org/2000/svg\\' width=\\'56\\' height=\\'32\\' fill=\\'%231A2233\\'><rect width=\\'56\\' height=\\'32\\' rx=\\'4\\'/></svg>'">
        <div class="video-info">
            <div class="video-title">${escapeHtml(video.title)}</div>
            <div class="video-meta">
                <span class="video-channel">${escapeHtml(video.channel || 'Unknown')}</span>
                ${duration ? `<span class="video-duration">${duration}</span>` : ''}
            </div>
        </div>
        <button class="video-delete" title="Remove video" data-video-id="${video.video_id}">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M3 6h18"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/>
                <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
            </svg>
        </button>
    `;

    card.addEventListener('click', (e) => {
        if (e.target.closest('.video-delete')) return;
        toggleVideoFilter(video.video_id, video.title);
    });

    card.querySelector('.video-delete').addEventListener('click', (e) => {
        e.stopPropagation();
        deleteVideo(video.video_id, video.title);
    });

    return card;
}

function toggleVideoFilter(videoId, title) {
    if (state.activeVideoId === videoId) {
        state.activeVideoId = null;
        els.videoFilter.hidden = true;
    } else {
        state.activeVideoId = videoId;
        els.videoFilter.hidden = false;
        els.filterVideoName.textContent = title;
    }

    els.videosList.querySelectorAll('.video-card').forEach(card => {
        card.classList.toggle('active', card.dataset.videoId === state.activeVideoId);
    });
}

async function deleteVideo(videoId, title) {
    if (!confirm(`Remove "${title}" from your knowledge base?`)) return;

    try {
        await apiCall(`/videos/${videoId}`, { method: 'DELETE' });
        showToast(`Removed "${title}"`, 'success');

        if (state.activeVideoId === videoId) {
            state.activeVideoId = null;
            els.videoFilter.hidden = true;
        }

        await loadVideos();

        if (state.videos.length === 0) {
            disableChat();
        }
    } catch (error) {
        showToast(error.message, 'error');
    }
}

// ══════════════════════════════════════
// Chat
// ══════════════════════════════════════

// Thinking status messages for the AI indicator
const THINKING_PHASES = [
    'Analyzing video transcript...',
    'Searching relevant context...',
    'Generating insights...',
];

async function sendQuery(questionOverride) {
    const question = questionOverride || els.chatInput.value.trim();
    if (!question || state.isQuerying) return;

    state.isQuerying = true;

    // Hide welcome screen, show chat
    els.welcomeScreen.hidden = true;
    els.chatMessages.hidden = false;

    // Add user message
    addMessage('user', question);
    els.chatInput.value = '';
    autoResize(els.chatInput);
    els.sendBtn.disabled = true;

    // Track user message in conversation history
    state.chatHistory.push({ role: 'user', content: question });

    // Add thinking indicator
    const thinkingId = addThinkingIndicator();

    try {
        const assistantResponse = await sendStreamingQuery(question, thinkingId);
        // Track assistant response in conversation history
        if (assistantResponse) {
            state.chatHistory.push({ role: 'assistant', content: assistantResponse });
        }
    } catch (error) {
        removeThinkingIndicator(thinkingId);
        // Fallback: try non-streaming endpoint
        try {
            const result = await apiCall('/query', {
                method: 'POST',
                body: JSON.stringify({
                    question,
                    video_id: state.activeVideoId || undefined,
                    history: state.chatHistory.slice(0, -1),  // exclude current user msg (already in question)
                }),
            });
            addMessage('assistant', result.answer, result.citations, result.sources);
            // Track assistant response in conversation history
            state.chatHistory.push({ role: 'assistant', content: result.answer });
        } catch (fallbackError) {
            const errorMsg = `Sorry, I encountered an error: ${fallbackError.message}`;
            addMessage('assistant', errorMsg);
            // Remove the failed user message from history
            state.chatHistory.pop();
        }
    } finally {
        state.isQuerying = false;
        els.sendBtn.disabled = false;
        els.chatInput.focus();
    }
}

async function sendStreamingQuery(question, thinkingId) {
    const url = `${API_BASE}/query/stream`;
    const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            question,
            video_id: state.activeVideoId || undefined,
            history: state.chatHistory.slice(0, -1),  // exclude current user msg (already in question)
        }),
    });

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || errorData.detail || `HTTP ${response.status}`);
    }

    // Remove thinking indicator and create the AI message bubble
    removeThinkingIndicator(thinkingId);

    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant streaming';
    messageDiv.innerHTML = `
        <div class="message-avatar">AI</div>
        <div class="message-content">
            <div class="message-text"></div>
        </div>
    `;
    els.chatMessages.appendChild(messageDiv);
    const textEl = messageDiv.querySelector('.message-text');

    let fullText = '';
    let citations = [];
    let sources = [];

    // Read the SSE stream
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Parse SSE events from buffer
        const lines = buffer.split('\n');
        buffer = lines.pop(); // Keep incomplete line in buffer

        for (const line of lines) {
            if (line.startsWith('data: ')) {
                const jsonStr = line.slice(6).trim();
                if (!jsonStr) continue;

                try {
                    const event = JSON.parse(jsonStr);

                    if (event.type === 'sources') {
                        sources = event.sources || [];
                    } else if (event.type === 'chunk') {
                        fullText += event.text;
                        textEl.innerHTML = markdownToHtml(fullText);
                        scrollToBottom();
                    } else if (event.type === 'done') {
                        citations = event.citations || [];
                    }
                } catch (parseErr) {
                    // Skip malformed events
                    console.warn('SSE parse error:', parseErr, jsonStr);
                }
            }
        }
    }

    // Remove streaming cursor and render final markdown
    messageDiv.classList.remove('streaming');

    if (!fullText.trim()) {
        fullText = 'I was unable to generate a response. Please try rephrasing your question.';
    }
    textEl.innerHTML = markdownToHtml(fullText);

    // Add citations if present
    if (citations.length > 0) {
        const chips = citations.map(c => {
            const vid = c.video_id || (sources.length > 0 ? sources[0].video_id : '');
            const ytLink = vid ? `https://www.youtube.com/watch?v=${vid}&t=${c.seconds}s` : '#';
            return `<a class="citation-chip" href="${ytLink}" target="_blank" rel="noopener" title="${escapeHtml(c.text || '')}">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                ${c.timestamp}
            </a>`;
        }).join('');
        const citationsDiv = document.createElement('div');
        citationsDiv.className = 'citations';
        citationsDiv.innerHTML = chips;
        messageDiv.querySelector('.message-content').appendChild(citationsDiv);
    }

    scrollToBottom();

    // Show follow-up suggestions
    addFollowUpSuggestions();

    // Return the full answer text so the caller can track it in history
    return fullText;
}

function addMessage(role, text, citations = [], sources = []) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;

    const htmlContent = role === 'assistant' ? markdownToHtml(text) : escapeHtml(text);

    let citationsHtml = '';
    if (citations && citations.length > 0) {
        const chips = citations.map(c => {
            const vid = c.video_id || (sources.length > 0 ? sources[0].video_id : '');
            const ytLink = vid ? `https://www.youtube.com/watch?v=${vid}&t=${c.seconds}s` : '#';
            return `<a class="citation-chip" href="${ytLink}" target="_blank" rel="noopener" title="${escapeHtml(c.text || '')}">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                ${c.timestamp}
            </a>`;
        }).join('');
        citationsHtml = `<div class="citations">${chips}</div>`;
    }

    if (role === 'user') {
        messageDiv.innerHTML = `
            <div class="message-content">
                <div class="message-text">${htmlContent}</div>
            </div>
        `;
    } else {
        messageDiv.innerHTML = `
            <div class="message-avatar">AI</div>
            <div class="message-content">
                <div class="message-text">${htmlContent}</div>
                ${citationsHtml}
            </div>
        `;
    }

    els.chatMessages.appendChild(messageDiv);
    scrollToBottom();
}

function addThinkingIndicator() {
    const id = 'thinking-' + Date.now();
    const div = document.createElement('div');
    div.className = 'message assistant';
    div.id = id;
    div.innerHTML = `
        <div class="message-avatar">AI</div>
        <div class="message-content">
            <div class="thinking-indicator">
                <div class="thinking-shimmer"></div>
                <div class="thinking-shimmer"></div>
                <div class="thinking-shimmer"></div>
                <div class="thinking-status">
                    <span class="thinking-dot"></span>
                    <span class="thinking-status-text">Analyzing video transcript...</span>
                </div>
            </div>
        </div>
    `;
    els.chatMessages.appendChild(div);
    scrollToBottom();

    // Cycle through thinking phases
    let phase = 0;
    const statusText = div.querySelector('.thinking-status-text');
    const interval = setInterval(() => {
        phase = (phase + 1) % THINKING_PHASES.length;
        if (statusText) statusText.textContent = THINKING_PHASES[phase];
    }, 2500);
    div._thinkingInterval = interval;

    return id;
}

function removeThinkingIndicator(id) {
    const el = document.getElementById(id);
    if (el) {
        clearInterval(el._thinkingInterval);
        el.remove();
    }
}

function addFollowUpSuggestions() {
    const suggestions = [
        'Explain this in simpler terms',
        'What are the key takeaways?',
        'Give me more details',
        'What did the speaker say next?',
    ];

    const container = document.createElement('div');
    container.className = 'follow-ups';

    suggestions.forEach(text => {
        const chip = document.createElement('button');
        chip.className = 'follow-up-chip';
        chip.textContent = text;
        chip.addEventListener('click', () => {
            // Remove this follow-up container
            container.remove();
            sendQuery(text);
        });
        container.appendChild(chip);
    });

    els.chatMessages.appendChild(container);
    scrollToBottom();
}

function scrollToBottom() {
    requestAnimationFrame(() => {
        els.chatContainer.scrollTop = els.chatContainer.scrollHeight;
    });
}

function enableChat() {
    els.chatInput.disabled = false;
    els.chatInput.placeholder = 'Ask anything about this video...';
    els.sendBtn.disabled = false;
}

function disableChat() {
    els.chatInput.disabled = true;
    els.chatInput.placeholder = 'Add a YouTube video first to start asking questions...';
    els.sendBtn.disabled = true;
}

function startNewChat() {
    // Clear messages
    els.chatMessages.innerHTML = '';
    els.chatMessages.hidden = true;
    els.welcomeScreen.hidden = false;

    // Clear conversation history
    state.chatHistory = [];

    // Clear filter
    state.activeVideoId = null;
    els.videoFilter.hidden = true;
    els.videosList.querySelectorAll('.video-card').forEach(c => c.classList.remove('active'));

    // Reset input
    els.chatInput.value = '';
    autoResize(els.chatInput);

    // Close sidebar on mobile
    closeSidebar();
}

// ══════════════════════════════════════
// Utilities
// ══════════════════════════════════════
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDuration(seconds) {
    if (!seconds || seconds <= 0) return '';
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
    return `${m}:${String(s).padStart(2, '0')}`;
}

function markdownToHtml(text) {
    if (!text) return '';

    let html = escapeHtml(text);

    // Fenced code blocks (```lang\n...\n```)
    html = html.replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) => {
        return `<pre><code class="language-${lang || 'text'}">${code.trim()}</code></pre>`;
    });

    // Blockquotes
    html = html.replace(/^&gt;\s+(.+)$/gm, '<blockquote>$1</blockquote>');
    // Merge consecutive blockquotes
    html = html.replace(/<\/blockquote>\n?<blockquote>/g, '<br>');

    // Headers
    html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
    html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
    html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');

    // Bold
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

    // Italic
    html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');

    // Inline code (skip if inside <pre>)
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

    // Unordered lists
    html = html.replace(/^[\s]*[-*]\s+(.+)$/gm, '<li>$1</li>');
    html = html.replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>');

    // Ordered lists
    html = html.replace(/^\d+\.\s+(.+)$/gm, '<li>$1</li>');

    // Line breaks
    html = html.replace(/\n\n/g, '</p><p>');
    html = html.replace(/\n/g, '<br>');
    html = `<p>${html}</p>`;

    // Clean up
    html = html.replace(/<p>\s*<\/p>/g, '');
    html = html.replace(/<p>\s*(<[hul])/g, '$1');
    html = html.replace(/(<\/[hul]\w*>)\s*<\/p>/g, '$1');
    // Don't wrap pre blocks in p tags
    html = html.replace(/<p>\s*(<pre>)/g, '$1');
    html = html.replace(/(<\/pre>)\s*<\/p>/g, '$1');
    // Don't wrap blockquotes in p tags
    html = html.replace(/<p>\s*(<blockquote>)/g, '$1');
    html = html.replace(/(<\/blockquote>)\s*<\/p>/g, '$1');

    // Highlight timestamp references [MM:SS]
    html = html.replace(
        /\[(\d{1,2}:\d{2})\]/g,
        '<strong style="color: var(--accent-red);">[$1]</strong>'
    );

    return html;
}

let _resizeRaf = null;
function autoResize(textarea) {
    if (_resizeRaf) cancelAnimationFrame(_resizeRaf);
    _resizeRaf = requestAnimationFrame(() => {
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 140) + 'px';
        _resizeRaf = null;
    });
}

function closeSidebar() {
    els.sidebar.classList.remove('open');
    els.sidebarOverlay.classList.remove('active');
}

function openSidebar() {
    els.sidebar.classList.add('open');
    els.sidebarOverlay.classList.add('active');
}

// ── Theme Toggle ──
function initTheme() {
    const savedTheme = localStorage.getItem('tubemind-theme');
    if (savedTheme) {
        document.documentElement.setAttribute('data-theme', savedTheme);
    }
    // Default is dark (no data-theme attribute needed — :root handles it)
}

function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme');
    const next = current === 'light' ? 'dark' : 'light';

    if (next === 'dark') {
        document.documentElement.removeAttribute('data-theme');
        localStorage.setItem('tubemind-theme', 'dark');
    } else {
        document.documentElement.setAttribute('data-theme', 'light');
        localStorage.setItem('tubemind-theme', 'light');
    }
}

// ── Toast Notifications ──
let toastTimeout;
function showToast(message, type = 'info') {
    const existing = document.querySelector('.toast');
    if (existing) existing.remove();
    clearTimeout(toastTimeout);

    const icon = type === 'error'
        ? '<svg class="toast-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#EF4444" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>'
        : '<svg class="toast-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#22C55E" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="16 8 10 16 7 13"/></svg>';

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `${icon}<span>${escapeHtml(message)}</span>`;
    document.body.appendChild(toast);

    toastTimeout = setTimeout(() => {
        toast.classList.add('exiting');
        toast.addEventListener('transitionend', () => toast.remove(), { once: true });
        // Fallback removal if transitionend doesn't fire
        setTimeout(() => { if (toast.parentNode) toast.remove(); }, 300);
    }, 4000);
}

// ══════════════════════════════════════
// Event Listeners
// ══════════════════════════════════════
function initEventListeners() {
    // Ingest
    els.ingestBtn.addEventListener('click', ingestVideo);
    els.youtubeUrl.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            ingestVideo();
        }
    });

    // Chat input
    els.sendBtn.addEventListener('click', () => sendQuery());
    els.chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendQuery();
        }
    });
    els.chatInput.addEventListener('input', () => {
        autoResize(els.chatInput);
    });

    // New Chat
    els.newChatBtn.addEventListener('click', startNewChat);

    // Suggested prompts
    els.suggestedPrompts.querySelectorAll('.prompt-chip').forEach(chip => {
        chip.addEventListener('click', () => {
            const prompt = chip.dataset.prompt;
            if (prompt && state.videos.length > 0) {
                sendQuery(prompt);
            } else if (state.videos.length === 0) {
                showToast('Add a YouTube video first', 'error');
            }
        });
    });

    // Filter clear
    els.filterClear.addEventListener('click', () => {
        state.activeVideoId = null;
        els.videoFilter.hidden = true;
        els.videosList.querySelectorAll('.video-card').forEach(c => c.classList.remove('active'));
    });

    // Mobile sidebar
    els.sidebarOpenBtn.addEventListener('click', openSidebar);
    els.sidebarToggle.addEventListener('click', closeSidebar);
    els.sidebarOverlay.addEventListener('click', closeSidebar);

    // Theme toggle
    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', toggleTheme);
    }

    // Escape key closes sidebar on mobile
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeSidebar();
        }
    });
}

// ══════════════════════════════════════
// Initialize
// ══════════════════════════════════════
document.addEventListener('DOMContentLoaded', async () => {
    initTheme();
    initEventListeners();
    await loadVideos();
});
