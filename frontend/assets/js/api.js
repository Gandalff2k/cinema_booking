window.API_BASE_URL = window.API_BASE_URL || '/v1';

function getAccessToken() {
    return localStorage.getItem('access_token');
}

function setAuthTokens(payload) {
    if (payload?.access_token) {
        localStorage.setItem('access_token', payload.access_token);
    }

    if (payload?.refresh_token) {
        localStorage.setItem('refresh_token', payload.refresh_token);
    }
}

function resolveAssetUrl(path) {
    if (!path) {
        return '';
    }

    if (path.startsWith('http://') || path.startsWith('https://') || path.startsWith('/')) {
        return path;
    }

    return `/${path}`;
}

async function apiFetch(path, options = {}) {
    const url = path.startsWith('http://') || path.startsWith('https://')
        ? path
        : `${window.API_BASE_URL}${path.startsWith('/') ? path : `/${path}`}`;

    const headers = new Headers(options.headers || {});
    const token = getAccessToken();

    if (token && !headers.has('Authorization')) {
        headers.set('Authorization', `Bearer ${token}`);
    }

    let body = options.body;
    if (body && !(body instanceof FormData) && typeof body !== 'string') {
        headers.set('Content-Type', 'application/json');
        body = JSON.stringify(body);
    }

    const response = await fetch(url, {
        ...options,
        body,
        headers,
    });

    if (response.status === 204) {
        return null;
    }

    // Only trust JSON bodies. Non-JSON responses (nginx 502/504 HTML pages,
    // tracebacks, proxy errors) are NEVER surfaced to the user verbatim.
    const isJson = (response.headers.get('content-type') || '').includes('application/json');
    const data = isJson ? await response.json().catch(() => null) : null;

    if (response.status === 401) {
        // Token invalid/expired — drop it and bounce to login (once).
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        if (!window.location.pathname.includes('/login/')) {
            if (window.showToast) {
                window.showToast('Session expired. Please sign in again.', 'error');
            }
            setTimeout(() => {
                window.location.href = '/pages/login/index.html';
            }, 1200);
        }
        throw new Error('Unauthorized');
    }

    if (!response.ok) {
        throw new Error(extractErrorMessage(data, response.status));
    }

    return data;
}

function extractErrorMessage(data, status) {
    // Structured error from our API (JSON only).
    if (data && typeof data === 'object') {
        if (Array.isArray(data.detail)) {
            const first = data.detail[0] || {};
            return first.message || first.msg || data.message || 'Invalid data';
        }
        const message = data.detail || data.message || data.error;
        if (typeof message === 'string' && message) {
            return message;
        }
    }
    // Anything else (HTML/gateway/proxy errors): safe, generic text.
    if (status >= 500) {
        return 'Service temporarily unavailable. Try again later.';
    }
    return 'Request failed.';
}

function isTokenValid() {
    // Client-side check of the JWT's exp so we can prompt login without a round-trip.
    const token = getAccessToken();
    if (!token) {
        return false;
    }
    try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        return typeof payload.exp === 'number' && payload.exp * 1000 > Date.now();
    } catch {
        return false;
    }
}

function escapeHtml(value) {
    if (value === null || value === undefined) {
        return '';
    }
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

/* ---------- Toasts & modal (self-injecting, no per-page markup) ---------- */

function injectUiStyles() {
    if (document.getElementById('cx-ui-styles')) {
        return;
    }
    const style = document.createElement('style');
    style.id = 'cx-ui-styles';
    style.textContent = `
        #cx-toast-container {
            position: fixed; top: 20px; right: 20px; z-index: 9999;
            display: flex; flex-direction: column; gap: 10px;
        }
        .cx-toast {
            min-width: 240px; max-width: 360px; padding: 14px 18px;
            border-radius: 10px; color: #f8fafc; font-family: 'Inter', sans-serif;
            font-size: 14px; box-shadow: 0 10px 30px rgba(0,0,0,0.4);
            background: #1e293b; border-left: 4px solid #38bdf8;
            opacity: 0; transform: translateX(20px); transition: .25s ease;
        }
        .cx-toast.show { opacity: 1; transform: translateX(0); }
        .cx-toast.success { border-left-color: #22c55e; }
        .cx-toast.error { border-left-color: #ef4444; }
        .cx-modal-overlay {
            position: fixed; inset: 0; z-index: 10000;
            background: rgba(2, 6, 23, 0.7); backdrop-filter: blur(4px);
            display: flex; align-items: center; justify-content: center;
            opacity: 0; transition: .2s ease; pointer-events: none;
        }
        .cx-modal-overlay.show { opacity: 1; pointer-events: auto; }
        .cx-modal {
            background: #1e293b; border: 1px solid rgba(255,255,255,0.1);
            border-radius: 16px; padding: 28px; max-width: 420px; width: 90%;
            color: #f8fafc; font-family: 'Inter', sans-serif;
            transform: scale(.95); transition: .2s ease;
        }
        .cx-modal-overlay.show .cx-modal { transform: scale(1); }
        .cx-modal p { margin: 0 0 22px; line-height: 1.5; }
        .cx-modal-actions { display: flex; gap: 12px; justify-content: flex-end; }
        .cx-btn {
            padding: 10px 18px; border-radius: 8px; border: none; cursor: pointer;
            font-weight: 600; font-family: inherit;
        }
        .cx-btn-cancel { background: #334155; color: #f8fafc; }
        .cx-btn-confirm { background: #38bdf8; color: #0f172a; }
    `;
    document.head.appendChild(style);
}

function showToast(message, type = 'info', timeout = 3500) {
    injectUiStyles();
    let container = document.getElementById('cx-toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'cx-toast-container';
        document.body.appendChild(container);
    }
    const toast = document.createElement('div');
    toast.className = `cx-toast ${type}`;
    toast.innerText = message;
    container.appendChild(toast);
    requestAnimationFrame(() => toast.classList.add('show'));
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, timeout);
}

function showConfirm(message, { confirmText = 'Yes', cancelText = 'Cancel' } = {}) {
    injectUiStyles();
    return new Promise((resolve) => {
        const overlay = document.createElement('div');
        overlay.className = 'cx-modal-overlay';
        overlay.innerHTML = `
            <div class="cx-modal">
                <p>${escapeHtml(message)}</p>
                <div class="cx-modal-actions">
                    <button class="cx-btn cx-btn-cancel">${escapeHtml(cancelText)}</button>
                    <button class="cx-btn cx-btn-confirm">${escapeHtml(confirmText)}</button>
                </div>
            </div>
        `;
        document.body.appendChild(overlay);
        requestAnimationFrame(() => overlay.classList.add('show'));

        const close = (result) => {
            overlay.classList.remove('show');
            setTimeout(() => overlay.remove(), 200);
            resolve(result);
        };
        overlay.querySelector('.cx-btn-confirm').onclick = () => close(true);
        overlay.querySelector('.cx-btn-cancel').onclick = () => close(false);
        overlay.onclick = (e) => { if (e.target === overlay) close(false); };
    });
}

// Fallback shown when a movie poster is missing from storage.
const POSTER_PLACEHOLDER = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='300' height='450'%3E%3Crect width='300' height='450' fill='%231e293b'/%3E%3Ctext x='150' y='225' fill='%2364748b' font-family='sans-serif' font-size='22' text-anchor='middle'%3ECinemaX%3C/text%3E%3C/svg%3E";

window.apiFetch = apiFetch;
window.resolveAssetUrl = resolveAssetUrl;
window.getAccessToken = getAccessToken;
window.setAuthTokens = setAuthTokens;
window.escapeHtml = escapeHtml;
window.showToast = showToast;
window.showConfirm = showConfirm;
window.isTokenValid = isTokenValid;
window.POSTER_PLACEHOLDER = POSTER_PLACEHOLDER;

// Global safety net — any uncaught error surfaces as a toast, never a raw
// browser alert/dialog.
window.addEventListener('unhandledrejection', (event) => {
    console.error('Unhandled rejection:', event.reason);
    if (event.reason && event.reason.message === 'Unauthorized') {
        return; // already handled by the 401 flow
    }
    showToast('Something went wrong. Please try again.', 'error');
});
window.addEventListener('error', (event) => {
    console.error('Uncaught error:', event.error || event.message);
});