const API_BASE_URL = 'http://localhost:8000';
let currentSessionId = null;

function showCareerError(message) {
    const errorEl = document.getElementById('careerChatError');
    errorEl.textContent = message;
    errorEl.style.display = 'block';
}

function appendMessage(role, content) {
    const chatMessages = document.getElementById('chatMessages');
    const wrap = document.createElement('div');
    wrap.className = `message ${role}`;

    const bubble = document.createElement('div');
    bubble.className = 'bubble markdown-body';
    
    if (typeof marked !== 'undefined') {
        bubble.innerHTML = marked.parse(content);
    } else {
        bubble.textContent = content;
    }

    wrap.appendChild(bubble);
    chatMessages.appendChild(wrap);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function setMessages(messages) {
    const chatMessages = document.getElementById('chatMessages');
    chatMessages.innerHTML = '';

    if (!messages.length) {
        appendMessage('assistant', 'Ask me anything about your career path.');
        return;
    }

    messages.forEach((m) => appendMessage(m.role, m.content));
}

async function loadSessions() {
    const sessionList = document.getElementById('sessionList');
    sessionList.innerHTML = 'Loading...';

    try {
        const response = await fetch(`${API_BASE_URL}/career-chat/sessions?limit=30`);
        const sessions = await response.json();

        if (!response.ok) {
            throw new Error('Failed to load chat history');
        }

        if (!sessions.length) {
            sessionList.innerHTML = '<div class="session-empty">No chats yet</div>';
            return;
        }

        sessionList.innerHTML = sessions
            .map((s) => `
                <button class="session-item ${currentSessionId === s.id ? 'active' : ''}" data-session-id="${s.id}">
                    <div class="title">${s.title || 'New Chat'}</div>
                    <div class="meta">${new Date(s.updated_at).toLocaleString()}</div>
                </button>
            `)
            .join('');

        document.querySelectorAll('.session-item').forEach((btn) => {
            btn.addEventListener('click', async () => {
                const id = Number(btn.dataset.sessionId);
                await selectSession(id);
            });
        });
    } catch (error) {
        sessionList.innerHTML = '<div class="session-empty">Failed to load</div>';
    }
}

async function selectSession(sessionId) {
    currentSessionId = sessionId;
    await loadSessions();

    try {
        const response = await fetch(`${API_BASE_URL}/career-chat/history/${sessionId}?limit=200`);
        const messages = await response.json();
        if (!response.ok) {
            throw new Error('Failed to load messages');
        }
        setMessages(messages);
    } catch (error) {
        showCareerError(error.message || 'Unable to load this chat.');
    }
}

function newChat() {
    currentSessionId = null;
    setMessages([]);
    document.getElementById('careerQuestion').value = '';
    document.getElementById('careerLiveJobQuery').value = '';
    document.getElementById('careerForceLive').checked = false;
    loadSessions();
}

async function onCareerChatSubmit(event) {
    event.preventDefault();

    const loadingEl = document.getElementById('careerChatLoading');
    const errorEl = document.getElementById('careerChatError');
    const sendBtn = document.getElementById('careerSendBtn');

    errorEl.style.display = 'none';
    loadingEl.style.display = 'block';
    sendBtn.disabled = true;

    try {
        const question = document.getElementById('careerQuestion').value.trim();
        const liveJobQuery = document.getElementById('careerLiveJobQuery').value.trim();
        const forceLive = document.getElementById('careerForceLive').checked;
        const resumeInput = document.getElementById('careerResume');

        if (!question) {
            throw new Error('Please enter a question for CareerLens.');
        }

        appendMessage('user', question);
        document.getElementById('careerQuestion').value = '';

        const formData = new FormData();
        formData.append('question', question);

        if (currentSessionId) {
            formData.append('session_id', String(currentSessionId));
        }

        if (liveJobQuery) {
            formData.append('live_job_query', liveJobQuery);
        }

        formData.append('force_live_jobs', forceLive ? 'true' : 'false');

        if (resumeInput.files && resumeInput.files[0]) {
            formData.append('resume', resumeInput.files[0]);
        }

        const response = await fetch(`${API_BASE_URL}/career-chat`, {
            method: 'POST',
            body: formData,
        });

        const payload = await response.json();

        if (!response.ok) {
            throw new Error(payload.detail || 'Failed to get CareerLens response.');
        }

        if (!currentSessionId && payload.session_id) {
            currentSessionId = payload.session_id;
        }

        appendMessage('assistant', payload.answer || 'No response generated.');
        await loadSessions();

        loadingEl.style.display = 'none';
    } catch (error) {
        loadingEl.style.display = 'none';
        showCareerError(error.message || 'Unable to process career chat request.');
    } finally {
        sendBtn.disabled = false;
    }
}

function initCareerChat() {
    const form = document.getElementById('careerChatForm');
    const newChatBtn = document.getElementById('newChatBtn');
    if (!form) {
        return;
    }

    form.addEventListener('submit', onCareerChatSubmit);
    newChatBtn.addEventListener('click', newChat);
    loadSessions();
}

document.addEventListener('DOMContentLoaded', initCareerChat);
