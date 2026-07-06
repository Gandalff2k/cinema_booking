function checkAuth() {
    const authBtn = document.getElementById('auth-btn');

    if (getAccessToken() && authBtn) {
        authBtn.innerText = 'Особистий кабінет';
        authBtn.onclick = () => window.location.href = '../profile/index.html';
    }
}

function createCard(movie, badgeType = null, badgeText = '') {
    let badgeHtml = '';
    if (badgeType === 'hot') badgeHtml = `<div class="badge-hot">${badgeText}</div>`;
    if (badgeType === 'rank') badgeHtml = `<div class="badge-rank">${badgeText}</div>`;

    const genres = movie.genres?.map((genre) => genre.name).join(' • ') || 'У прокаті';
    const tags = [genres, `${movie.duration_minutes} хв`, movie.age_rating].filter(Boolean).join(' • ');

    return `
    <div class="movie-card" onclick="window.location.href='/pages/movie/index.html?movie_id=${movie.id}'">
        ${badgeHtml}
        <img src="${movie.poster_url}" alt="${movie.title}" class="movie-poster">
        <h3 class="movie-title">${movie.title}</h3>
        <p class="movie-info">${tags}</p>
    </div>`;
}

async function renderMovies() {
    const hotGrid = document.getElementById('hot-movies-grid');
    const premieresGrid = document.getElementById('premieres-movies-grid');
    const topGrid = document.getElementById('top-movies-grid');
    const allGrid = document.getElementById('all-movies-grid');

    const movies = await apiFetch('/movies');
    const hotMovies = movies.slice(0, 2);
    const topMovies = movies.slice(2, 5);
    const premiereMovies = movies.slice(5, 8);

    hotGrid.innerHTML = hotMovies.map((movie) => createCard(movie, 'hot', 'Останні місця!')).join('');
    topGrid.innerHTML = topMovies.map((movie, index) => createCard(movie, 'rank', `#${index + 1}`)).join('');
    premieresGrid.innerHTML = premiereMovies.map((movie) => createCard(movie)).join('');
    allGrid.innerHTML = movies.map((movie) => createCard(movie)).join('');
}

checkAuth();
renderMovies().catch((error) => console.error(error));