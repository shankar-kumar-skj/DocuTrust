const API_BASE = 'http://localhost:8000/api';

// Check if user is logged in, redirect if not
function checkAuth() {
    const token = localStorage.getItem('token');
    if (!token && !window.location.pathname.includes('index.html')) {
        window.location.href = 'index.html';
    }
    return token;
}

// Logout
document.addEventListener('DOMContentLoaded', function() {
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', function(e) {
            e.preventDefault();
            localStorage.removeItem('token');
            localStorage.removeItem('user');
            window.location.href = 'index.html';
        });
    }

    // Display user info if on protected pages
    const userStr = localStorage.getItem('user');
    if (userStr) {
        try {
            const user = JSON.parse(userStr);
            const nameEl = document.getElementById('userName');
            const roleEl = document.getElementById('userRole');
            if (nameEl) nameEl.textContent = user.full_name || user.email;
            if (roleEl) roleEl.textContent = user.role || 'employee';
            // Show admin link if role is admin
            if (user.role === 'admin') {
                const adminLink = document.getElementById('adminLink');
                if (adminLink) adminLink.style.display = 'block';
            }
        } catch (e) {}
    }
});

// --- Login ---
document.addEventListener('DOMContentLoaded', function() {
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            const email = document.getElementById('loginEmail').value;
            const password = document.getElementById('loginPassword').value;
            const errorEl = document.getElementById('loginError');

            try {
                const formData = new URLSearchParams();
                formData.append('username', email);
                formData.append('password', password);

                const res = await fetch(`${API_BASE}/auth/login`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                    body: formData
                });

                if (!res.ok) {
                    const err = await res.json();
                    throw new Error(err.detail || 'Login failed');
                }

                const data = await res.json();
                localStorage.setItem('token', data.access_token);
                localStorage.setItem('user', JSON.stringify({
                    email: email,
                    role: data.role,
                    tenant_id: data.tenant_id
                }));
                window.location.href = 'dashboard.html';
            } catch (err) {
                errorEl.textContent = err.message;
            }
        });
    }

    // --- Register ---
    const registerForm = document.getElementById('registerForm');
    if (registerForm) {
        registerForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            const full_name = document.getElementById('regFullName').value;
            const email = document.getElementById('regEmail').value;
            const password = document.getElementById('regPassword').value;
            const tenant_id = document.getElementById('regTenant').value;
            const errorEl = document.getElementById('registerError');

            try {
                const res = await fetch(`${API_BASE}/auth/register`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ full_name, email, password, tenant_id })
                });

                if (!res.ok) {
                    const err = await res.json();
                    throw new Error(err.detail || 'Registration failed');
                }

                alert('Registration successful! Please login.');
                // Switch to login tab
                document.getElementById('loginTab').click();
                document.getElementById('loginEmail').value = email;
            } catch (err) {
                errorEl.textContent = err.message;
            }
        });
    }

    // --- Tabs ---
    const loginTab = document.getElementById('loginTab');
    const registerTab = document.getElementById('registerTab');
    if (loginTab && registerTab) {
        loginTab.addEventListener('click', () => {
            document.getElementById('loginForm').classList.add('active');
            document.getElementById('registerForm').classList.remove('active');
            loginTab.classList.add('active');
            registerTab.classList.remove('active');
        });
        registerTab.addEventListener('click', () => {
            document.getElementById('registerForm').classList.add('active');
            document.getElementById('loginForm').classList.remove('active');
            registerTab.classList.add('active');
            loginTab.classList.remove('active');
        });
    }
});