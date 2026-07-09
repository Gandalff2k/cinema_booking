function formatDate(value) {
    return new Intl.DateTimeFormat('en-GB', {
        day: 'numeric',
        month: 'long',
    }).format(new Date(value));
}

function formatTime(value) {
    return new Intl.DateTimeFormat('en-GB', {
        hour: '2-digit',
        minute: '2-digit',
    }).format(new Date(value));
}

function loadMoviePage() {
    const movieId = new URLSearchParams(window.location.search).get('movie_id');

    if (!movieId) {
        document.getElementById('movie-title').innerText = 'No movie selected';
        document.getElementById('shows-list').innerHTML =
            '<div class="date-btn active">No movie selected</div>';
        return;
    }

    // Three independent sections — one failing never blocks the others.
    loadMovieDetails(movieId);
    loadShows(movieId);
    setupReviewForm(movieId);
    loadReviews(movieId);
}

async function loadMovieDetails(movieId) {
    const moviePoster = document.getElementById('movie-poster');
    moviePoster.onerror = () => {
        moviePoster.onerror = null;
        moviePoster.src = window.POSTER_PLACEHOLDER;
    };

    try {
        const movie = await apiFetch(`/movies/${movieId}`);
        document.getElementById('movie-title').innerText = movie.title;
        document.getElementById('movie-tags').innerText = [
            movie.genres.map((genre) => genre.name).join(', '),
            `${movie.duration_minutes} min`,
            movie.age_rating,
        ].filter(Boolean).join(' • ');
        document.getElementById('movie-description').innerText =
            movie.description || 'No description available.';
        document.getElementById('movie-director').innerHTML =
            '<strong>Director:</strong> CinemaX Studio';
        document.getElementById('movie-cast').innerHTML =
            '<strong>Cast:</strong> Cast unavailable';
        moviePoster.src = resolveAssetUrl(movie.poster_url) || window.POSTER_PLACEHOLDER;
        moviePoster.alt = movie.title;
    } catch (error) {
        console.error('Failed to load movie:', error);
        document.getElementById('movie-title').innerText = 'Movie not found';
        moviePoster.src = window.POSTER_PLACEHOLDER;
    }
}

async function loadShows(movieId) {
    const showsList = document.getElementById('shows-list');
    try {
        const shows = await apiFetch(`/movies/shows/${movieId}`);
        if (!shows.length) {
            showsList.innerHTML =
                '<div class="date-btn active">No showtimes yet</div>';
            return;
        }

        const activeShowId = new URLSearchParams(window.location.search).get('show_id');
        const defaultShowId = activeShowId || shows[0].id;

        showsList.innerHTML = shows.map((show) => `
            <button class="date-btn ${String(show.id) === String(defaultShowId) ? 'active' : ''}" data-show-id="${show.id}">
                <span class="day">${formatDate(show.start_time)}</span>
                <span class="date">${formatTime(show.start_time)}</span>
                <small>${show.format} • ${show.base_price} UAH</small>
            </button>
        `).join('');

        showsList.querySelectorAll('.date-btn').forEach((button) => {
            button.addEventListener('click', () => {
                const showId = button.dataset.showId;
                window.location.href = `../booking/index.html?movie_id=${movieId}&show_id=${showId}`;
            });
        });
    } catch (error) {
        console.error('Failed to load showtimes:', error);
        showsList.innerHTML = '<div class="date-btn active">Failed to load showtimes</div>';
    }
}

function renderRatingSummary(data) {
    const summary = document.getElementById('rating-summary');
    if (!data.count) {
        summary.innerHTML = '<span class="no-rating">No ratings yet</span>';
        return;
    }
    summary.innerHTML = `
        <span class="rating-star">★</span>
        <span class="rating-value">${data.average.toFixed(1)}</span>
        <span class="rating-count">/ 10 · ${data.count} reviews</span>
    `;
}

const reviewsState = { movieId: null, loaded: 0, total: 0 };
const REVIEWS_PAGE = 6;

function renderReviewCard(review) {
    return `
        <div class="review-card">
            <div class="review-top">
                <span class="review-author">${escapeHtml(review.username)}</span>
                <span class="review-rating">★ ${escapeHtml(review.rating)}/10</span>
            </div>
            <p class="review-comment">${escapeHtml(review.comment) || '<em>No comment</em>'}</p>
        </div>`;
}

function renderLoadMore() {
    if (reviewsState.loaded >= reviewsState.total) {
        return '';
    }
    const remaining = reviewsState.total - reviewsState.loaded;
    return `<button id="load-more-reviews" class="load-more-btn">Show more (${remaining})</button>`;
}

function wireLoadMore() {
    const btn = document.getElementById('load-more-reviews');
    if (btn) {
        btn.onclick = loadMoreReviews;
    }
}

async function loadReviews(movieId) {
    const list = document.getElementById('reviews-list');
    try {
        const data = await apiFetch(`/reviews/movies/${movieId}`);
        renderRatingSummary(data);
        reviewsState.movieId = movieId;
        reviewsState.loaded = data.reviews.length;
        reviewsState.total = data.count;

        if (!data.reviews.length) {
            list.innerHTML = '<p class="no-reviews">Be the first to review!</p>';
            return;
        }
        list.innerHTML = data.reviews.map(renderReviewCard).join('') + renderLoadMore();
        wireLoadMore();
    } catch (error) {
        console.error('Failed to load reviews:', error);
        list.innerHTML = '<p class="no-reviews">Failed to load reviews.</p>';
    }
}

async function loadMoreReviews() {
    const list = document.getElementById('reviews-list');
    const btn = document.getElementById('load-more-reviews');
    if (btn) {
        btn.disabled = true;
        btn.innerText = 'Loading...';
    }
    try {
        const more = await apiFetch(
            `/reviews/movies/${reviewsState.movieId}/list?offset=${reviewsState.loaded}&limit=${REVIEWS_PAGE}`,
        );
        reviewsState.loaded += more.length;
        if (btn) {
            btn.remove();
        }
        list.insertAdjacentHTML(
            'beforeend',
            more.map(renderReviewCard).join('') + renderLoadMore(),
        );
        wireLoadMore();
    } catch (error) {
        console.error('Failed to load more reviews:', error);
        if (btn) {
            btn.disabled = false;
            btn.innerText = 'Show more';
        }
    }
}

function setupReviewForm(movieId) {
    const form = document.getElementById('review-form');
    const loginHint = document.getElementById('review-login-hint');

    // Only a validly-authenticated user may write a review.
    if (!isTokenValid()) {
        loginHint.hidden = false;
        form.hidden = true;
        return;
    }
    loginHint.hidden = true;
    form.hidden = false;

    const ratingSelect = document.getElementById('review-rating');
    ratingSelect.innerHTML = Array.from({ length: 10 }, (_, i) => i + 1)
        .map((n) => `<option value="${n}">${n}</option>`)
        .join('');
    ratingSelect.value = '8';

    form.addEventListener('submit', async (event) => {
        event.preventDefault();
        const errorEl = document.getElementById('review-error');
        errorEl.innerText = '';
        const submitBtn = form.querySelector('button[type="submit"]');
        submitBtn.disabled = true;

        try {
            await apiFetch(`/reviews/movies/${movieId}`, {
                method: 'POST',
                body: {
                    rating: Number(ratingSelect.value),
                    comment: document.getElementById('review-comment').value.trim() || null,
                },
            });
            document.getElementById('review-comment').value = '';
            await loadReviews(movieId);
        } catch (error) {
            errorEl.innerText = error.message;
        } finally {
            submitBtn.disabled = false;
        }
    });
}

loadMoviePage();