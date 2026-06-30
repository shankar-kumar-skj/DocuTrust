const API_BASE = 'http://localhost:8000/api';

let currentSessionId = null;

document.addEventListener('DOMContentLoaded', async function() {
    const token = localStorage.getItem('token');
    if (!token) return;

    // Load sessions list
    await loadSessions();

    // New session button
    document.getElementById('newSessionBtn').addEventListener('click', function() {
        currentSessionId = null;
        document.getElementById('chatMessages').innerHTML = '<div class="empty-state">Start a new session by asking a question.</div>';
        // Clear active class in list
        document.querySelectorAll('#sessionList li').forEach(li => li.classList.remove('active'));
    });

    // Send message
    document.getElementById('sendBtn').addEventListener('click', sendMessage);
    document.getElementById('chatInput').addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
});

async function loadSessions() {
    const token = localStorage.getItem('token');
    try {
        const res = await fetch(`${API_BASE}/chat/history`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
            const sessions = await res.json();
            const list = document.getElementById('sessionList');
            list.innerHTML = '';
            sessions.forEach(s => {
                const li = document.createElement('li');
                li.textContent = s.title || 'Untitled';
                li.dataset.id = s._id;
                li.addEventListener('click', () => loadSession(s._id));
                if (currentSessionId === s._id) li.classList.add('active');
                list.appendChild(li);
            });
        }
    } catch (e) {
        console.error('Failed to load sessions:', e);
    }
}

async function loadSession(sessionId) {
    const token = localStorage.getItem('token');
    try {
        const res = await fetch(`${API_BASE}/chat/session/${sessionId}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
            const session = await res.json();
            currentSessionId = sessionId;
            const messages = session.messages || [];
            const container = document.getElementById('chatMessages');
            container.innerHTML = '';
            messages.forEach(msg => {
                const div = document.createElement('div');
                div.className = `message ${msg.role}`;
                div.innerHTML = msg.content;
                if (msg.sources && msg.sources.length) {
                    const src = document.createElement('div');
                    src.className = 'source';
                    src.textContent = `Sources: ${msg.sources.map(s => s.chunk_id).join(', ')}`;
                    div.appendChild(src);
                }
                container.appendChild(div);
            });
            container.scrollTop = container.scrollHeight;
            // Highlight session in list
            document.querySelectorAll('#sessionList li').forEach(li => {
                li.classList.toggle('active', li.dataset.id === sessionId);
            });
        }
    } catch (e) {
        console.error('Failed to load session:', e);
    }
}

async function sendMessage() {
    const input = document.getElementById('chatInput');
    const text = input.value.trim();
    if (!text) return;
    input.value = '';

    const token = localStorage.getItem('token');
    const container = document.getElementById('chatMessages');

    // Show user message immediately
    const userDiv = document.createElement('div');
    userDiv.className = 'message user';
    userDiv.textContent = text;
    container.appendChild(userDiv);
    container.scrollTop = container.scrollHeight;

    // Show loading indicator
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'message assistant';
    loadingDiv.textContent = 'Thinking...';
    container.appendChild(loadingDiv);
    container.scrollTop = container.scrollHeight;

    try {
        const body = { query: text };
        if (currentSessionId) body.session_id = currentSessionId;

        const res = await fetch(`${API_BASE}/chat/ask`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(body)
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Request failed');
        }

        const data = await res.json();
        // Remove loading indicator
        container.removeChild(loadingDiv);

        // Add assistant response
        const assDiv = document.createElement('div');
        assDiv.className = 'message assistant';
        assDiv.innerHTML = data.answer || 'No answer.';
        if (data.sources && data.sources.length) {
            const src = document.createElement('div');
            src.className = 'source';
            src.textContent = `Sources: ${data.sources.map(s => s.chunk_id).join(', ')}`;
            assDiv.appendChild(src);
        }
        container.appendChild(assDiv);
        container.scrollTop = container.scrollHeight;

        // Update session ID
        if (data.session_id) {
            currentSessionId = data.session_id;
            await loadSessions(); // refresh list
        }
    } catch (err) {
        container.removeChild(loadingDiv);
        const errDiv = document.createElement('div');
        errDiv.className = 'message assistant';
        errDiv.textContent = `Error: ${err.message}`;
        container.appendChild(errDiv);
        container.scrollTop = container.scrollHeight;
    }
}