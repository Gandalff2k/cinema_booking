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

    const contentType = response.headers.get('content-type') || '';
    const data = contentType.includes('application/json')
        ? await response.json()
        : await response.text();

    if (!response.ok) {
        const errorMessage = typeof data === 'string'
            ? data
            : data?.detail || data?.message || data?.error || 'Request failed';
        throw new Error(errorMessage);
    }

    return data;
}

window.apiFetch = apiFetch;
window.resolveAssetUrl = resolveAssetUrl;
window.getAccessToken = getAccessToken;
window.setAuthTokens = setAuthTokens;