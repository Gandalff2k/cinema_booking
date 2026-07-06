function formatDate(value) {
    return new Intl.DateTimeFormat('uk-UA', {
        day: 'numeric',
        month: 'long',
    }).format(new Date(value));
}

function formatTime(value) {
    return new Intl.DateTimeFormat('uk-UA', {
        hour: '2-digit',
        minute: '2-digit',
    }).format(new Date(value));
}

async function loadMoviePage() {
    const movieId = new URLSearchParams(window.location.search).get('movie_id');
    const showsList = document.getElementById('shows-list');
    const movieTitle = document.getElementById('movie-title');
    const movieTags = document.getElementById('movie-tags');
    const movieDescription = document.getElementById('movie-description');
    const movieDirector = document.getElementById('movie-director');
    const movieCast = document.getElementById('movie-cast');
    const moviePoster = document.getElementById('movie-poster');

    if (!movieId) {
        showsList.innerHTML = '<div class="date-btn active">Не вибрано фільм</div>';
        return;
    }

    const shows = await apiFetch(`/movies/shows/${movieId}`);

    if (!shows.length) {
        showsList.innerHTML = '<div class="date-btn active">Сеансів поки немає</div>';
        return;
    }

    const movie = shows[0].movie;
    movieTitle.innerText = movie.title;
    movieTags.innerText = [
        movie.genres.map((genre) => genre.name).join(', '),
        `${movie.duration_minutes} хв`,
        movie.age_rating,
    ].filter(Boolean).join(' • ');
    movieDescription.innerText = movie.description || 'Опис недоступний.';
    movieDirector.innerHTML = '<strong>Режисер:</strong> CinemaX Studio';
    movieCast.innerHTML = '<strong>В ролях:</strong> Акторський склад недоступний';
    moviePoster.src = resolveAssetUrl(movie.poster_url);
    moviePoster.alt = movie.title;

    const activeShowId = new URLSearchParams(window.location.search).get('show_id');
    const defaultShowId = activeShowId || shows[0].id;

    showsList.innerHTML = shows.map((show) => `
        <button class="date-btn ${String(show.id) === String(defaultShowId) ? 'active' : ''}" data-show-id="${show.id}">
            <span class="day">${formatDate(show.start_time)}</span>
            <span class="date">${formatTime(show.start_time)}</span>
            <small>${show.format} • ${show.base_price} грн</small>
        </button>
    `).join('');

    showsList.querySelectorAll('.date-btn').forEach((button) => {
        button.addEventListener('click', () => {
            const showId = button.dataset.showId;
            window.location.href = `../booking/index.html?movie_id=${movieId}&show_id=${showId}`;
        });
    });
}

loadMoviePage().catch((error) => console.error(error));