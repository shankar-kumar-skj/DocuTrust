const API_BASE = 'http://localhost:8000/api';

document.addEventListener('DOMContentLoaded', function() {
    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = 'index.html';
        return;
    }

    // Load agent logs by default
    loadLogs('agent');

    document.getElementById('agentLogsTab').addEventListener('click', function() {
        setActiveTab('agent');
        loadLogs('agent');
    });

    document.getElementById('auditLogsTab').addEventListener('click', function() {
        setActiveTab('audit');
        loadLogs('audit');
    });
});

function setActiveTab(type) {
    const tabs = document.querySelectorAll('.log-tabs button');
    tabs.forEach(t => t.classList.remove('active'));
    if (type === 'agent') {
        document.getElementById('agentLogsTab').classList.add('active');
    } else {
        document.getElementById('auditLogsTab').classList.add('active');
    }
}

async function loadLogs(type) {
    const token = localStorage.getItem('token');
    const display = document.getElementById('logDisplay');
    display.textContent = 'Loading...';

    try {
        const endpoint = type === 'agent' ? '/agent-logs' : '/audit-logs';
        const res = await fetch(`${API_BASE}/logs${endpoint}?limit=50`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Failed to fetch logs');
        }
        const logs = await res.json();
        if (logs.length === 0) {
            display.textContent = 'No logs found.';
        } else {
            display.textContent = JSON.stringify(logs, null, 2);
        }
    } catch (err) {
        display.textContent = `Error: ${err.message}`;
    }
}