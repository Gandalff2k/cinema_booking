const PAGE = 10;

// --- Access gate ---
async function guardAdmin() {
    if (!getAccessToken()) {
        window.location.href = '../login/index.html';
        return false;
    }
    try {
        const me = await apiFetch('/auth/me');
        if (me.role !== 'admin') {
            showToast('Admins only', 'error');
            setTimeout(() => { window.location.href = '../home/index.html'; }, 1200);
            return false;
        }
        return true;
    } catch {
        return false;
    }
}

function setupTabs() {
    document.querySelectorAll('.admin-tab').forEach((tab) => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.admin-tab').forEach((t) => t.classList.remove('active'));
            document.querySelectorAll('.admin-panel').forEach((p) => p.classList.remove('active'));
            tab.classList.add('active');
            document.getElementById(`tab-${tab.dataset.tab}`).classList.add('active');
        });
    });
}

function debounce(fn, ms = 250) {
    let t;
    return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
}

function tbodyOf(id, headHtml) {
    const table = document.getElementById(id);
    table.innerHTML = `${headHtml}<tbody></tbody>`;
    return table.querySelector('tbody');
}

// ---------------- Movies ----------------
const moviesState = { offset: 0 };

function movieRow(m) {
    return `
        <tr>
            <td>${m.id}</td>
            <td>${escapeHtml(m.title)}</td>
            <td class="muted">${escapeHtml(m.genres.join(', ')) || '—'}</td>
            <td>${m.duration_minutes}</td>
            <td>${escapeHtml(m.age_rating) || '—'}</td>
            <td>${m.is_active
                ? '<span class="badge badge-ok">active</span>'
                : '<span class="badge badge-off">hidden</span>'}</td>
            <td class="row-actions">
                <button class="btn-sm" data-action="poster" data-id="${m.id}">Poster</button>
                <button class="btn-sm" data-action="toggle" data-id="${m.id}" data-active="${m.is_active}">
                    ${m.is_active ? 'Hide' : 'Show'}
                </button>
                <button class="btn-sm btn-danger" data-action="delete" data-id="${m.id}">Delete</button>
            </td>
        </tr>`;
}

async function loadMovies(reset) {
    const moreBtn = document.getElementById('movies-more');
    let tbody = document.querySelector('#movies-table tbody');
    if (reset || !tbody) {
        moviesState.offset = 0;
        tbody = tbodyOf('movies-table',
            '<thead><tr><th>ID</th><th>Title</th><th>Genres</th><th>Min</th><th>Age</th><th>Status</th><th></th></tr></thead>');
    }
    const params = new URLSearchParams({ offset: moviesState.offset, limit: PAGE });
    const search = document.getElementById('movie-search').value.trim();
    const genre = document.getElementById('movie-genre').value;
    if (search) params.set('search', search);
    if (genre) params.set('genre_id', genre);

    const movies = await apiFetch(`/admin/movies?${params}`);
    tbody.insertAdjacentHTML('beforeend', movies.map(movieRow).join(''));
    moviesState.offset += movies.length;
    moreBtn.hidden = movies.length < PAGE;
    if (moviesState.offset === 0 || (reset && !movies.length)) {
        tbody.innerHTML = '<tr><td colspan="7" class="muted">No movies found.</td></tr>';
    }
}

let posterMovieId = null;

function setupPosterUpload() {
    const input = document.getElementById('poster-input');
    input.addEventListener('change', async () => {
        const file = input.files[0];
        if (!file || !posterMovieId) return;
        const form = new FormData();
        form.append('file', file);
        try {
            await apiFetch(`/admin/movies/${posterMovieId}/poster`, { method: 'POST', body: form });
            showToast('Poster uploaded', 'success');
            await loadMovies(true);
        } catch (error) {
            showToast(error.message, 'error');
        } finally {
            input.value = '';
            posterMovieId = null;
        }
    });
}

async function handleMovieAction(action, id, active) {
    if (action === 'poster') {
        posterMovieId = id;
        document.getElementById('poster-input').click();
        return;
    }
    try {
        if (action === 'toggle') {
            await apiFetch(`/admin/movies/${id}`, { method: 'PUT', body: { is_active: active !== 'true' } });
            showToast('Updated', 'success');
        } else if (action === 'delete') {
            if (!(await showConfirm('Hide this movie?', { confirmText: 'Delete' }))) return;
            await apiFetch(`/admin/movies/${id}`, { method: 'DELETE' });
            showToast('Movie hidden', 'success');
        }
        await loadMovies(true);
    } catch (error) {
        showToast(error.message, 'error');
    }
}

// ---------------- Reviews ----------------
const reviewsState = { offset: 0 };

function reviewRow(r) {
    return `
        <tr>
            <td>${r.id}</td>
            <td>${escapeHtml(r.movie_title)}</td>
            <td>#${r.user_id}</td>
            <td>★ ${r.rating}</td>
            <td class="comment-cell">${escapeHtml(r.comment) || '—'}</td>
            <td><button class="btn-sm btn-danger" data-action="del-review" data-id="${r.id}">Delete</button></td>
        </tr>`;
}

async function loadReviews(reset) {
    const moreBtn = document.getElementById('reviews-more');
    let tbody = document.querySelector('#reviews-table tbody');
    if (reset || !tbody) {
        reviewsState.offset = 0;
        tbody = tbodyOf('reviews-table',
            '<thead><tr><th>ID</th><th>Movie</th><th>User</th><th>Rating</th><th>Comment</th><th></th></tr></thead>');
    }
    const params = new URLSearchParams({ offset: reviewsState.offset, limit: PAGE });
    const search = document.getElementById('review-search').value.trim();
    if (search) params.set('search', search);

    const reviews = await apiFetch(`/admin/reviews?${params}`);
    tbody.insertAdjacentHTML('beforeend', reviews.map(reviewRow).join(''));
    reviewsState.offset += reviews.length;
    moreBtn.hidden = reviews.length < PAGE;
    if (reviewsState.offset === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="muted">No reviews found.</td></tr>';
    }
}

async function handleDeleteReview(id) {
    if (!(await showConfirm('Delete this review?', { confirmText: 'Delete' }))) return;
    try {
        await apiFetch(`/admin/reviews/${id}`, { method: 'DELETE' });
        showToast('Review deleted', 'success');
        await loadReviews(true);
    } catch (error) {
        showToast(error.message, 'error');
    }
}

// ---------------- Orders ----------------
const ordersState = { offset: 0 };

function orderRow(o) {
    return `
        <tr>
            <td>${o.id}</td>
            <td>${escapeHtml(o.user_email) || '—'}</td>
            <td>${o.total_price} UAH</td>
            <td>${o.tickets_count}</td>
            <td><span class="badge badge-${o.status}">${escapeHtml(o.status)}</span></td>
            <td>${o.status === 'paid'
                ? `<button class="btn-sm btn-danger" data-action="refund" data-id="${o.id}">Refund</button>`
                : ''}</td>
        </tr>`;
}

async function loadOrders(reset) {
    const moreBtn = document.getElementById('orders-more');
    let tbody = document.querySelector('#orders-table tbody');
    if (reset || !tbody) {
        ordersState.offset = 0;
        tbody = tbodyOf('orders-table',
            '<thead><tr><th>ID</th><th>Email</th><th>Total</th><th>Tickets</th><th>Status</th><th></th></tr></thead>');
    }
    const params = new URLSearchParams({ offset: ordersState.offset, limit: PAGE });
    const email = document.getElementById('order-email').value.trim();
    if (email) params.set('email', email);

    const orders = await apiFetch(`/admin/orders?${params}`);
    tbody.insertAdjacentHTML('beforeend', orders.map(orderRow).join(''));
    ordersState.offset += orders.length;
    moreBtn.hidden = orders.length < PAGE;
    if (ordersState.offset === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="muted">No orders found.</td></tr>';
    }
}

async function handleRefund(id) {
    if (!(await showConfirm('Refund this order? Seats will be released.', { confirmText: 'Refund' }))) return;
    try {
        const res = await apiFetch(`/admin/orders/${id}/refund`, { method: 'POST' });
        showToast(res.stripe_refund ? 'Refunded via Stripe' : 'Order refunded', 'success');
        await loadOrders(true);
    } catch (error) {
        showToast(error.message, 'error');
    }
}

// ---------------- Wiring ----------------
function setupMovieForm() {
    document.getElementById('movie-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        try {
            await apiFetch('/admin/movies', {
                method: 'POST',
                body: {
                    title: document.getElementById('m-title').value.trim(),
                    poster_url: document.getElementById('m-poster').value.trim() || null,
                    duration_minutes: Number(document.getElementById('m-duration').value),
                    age_rating: document.getElementById('m-age').value.trim() || null,
                    description: document.getElementById('m-description').value.trim() || null,
                },
            });
            showToast('Movie created', 'success');
            e.target.reset();
            await loadMovies(true);
        } catch (error) {
            showToast(error.message, 'error');
        }
    });
}

async function loadGenres() {
    try {
        const genres = await apiFetch('/admin/genres');
        document.getElementById('movie-genre').innerHTML = '<option value="">All genres</option>'
            + genres.map((g) => `<option value="${g.id}">${escapeHtml(g.name)}</option>`).join('');
    } catch (error) {
        console.error(error);
    }
}

function delegate(tableId, handlers) {
    document.getElementById(tableId).addEventListener('click', (e) => {
        const btn = e.target.closest('button[data-action]');
        if (btn) handlers(btn);
    });
}

async function init() {
    if (!(await guardAdmin())) return;
    setupTabs();
    setupMovieForm();
    setupPosterUpload();
    await loadGenres();

    document.getElementById('movie-search').addEventListener('input', debounce(() => loadMovies(true).catch(console.error)));
    document.getElementById('movie-genre').addEventListener('change', () => loadMovies(true).catch(console.error));
    document.getElementById('review-search').addEventListener('input', debounce(() => loadReviews(true).catch(console.error)));
    document.getElementById('order-email').addEventListener('input', debounce(() => loadOrders(true).catch(console.error)));

    document.getElementById('movies-more').addEventListener('click', () => loadMovies(false).catch(console.error));
    document.getElementById('reviews-more').addEventListener('click', () => loadReviews(false).catch(console.error));
    document.getElementById('orders-more').addEventListener('click', () => loadOrders(false).catch(console.error));

    delegate('movies-table', (btn) => handleMovieAction(btn.dataset.action, btn.dataset.id, btn.dataset.active));
    delegate('reviews-table', (btn) => handleDeleteReview(btn.dataset.id));
    delegate('orders-table', (btn) => handleRefund(btn.dataset.id));

    await Promise.all([loadMovies(true), loadReviews(true), loadOrders(true)]);
}

init().catch((error) => console.error(error));
