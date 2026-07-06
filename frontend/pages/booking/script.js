const container = document.getElementById('seats-container');
const count = document.getElementById('count');
const total = document.getElementById('total');
const timeSelect = document.getElementById('session-time');
const bookBtn = document.getElementById('book-btn');
const movieTitle = document.getElementById('movie-title');
const selectedDate = document.getElementById('selected-date');

let currentMovieId = null;
let currentShow = null;

function formatDate(value) {
    return new Intl.DateTimeFormat('uk-UA', {
        day: 'numeric',
        month: 'long',
        year: 'numeric',
    }).format(new Date(value));
}

function formatTime(value) {
    return new Intl.DateTimeFormat('uk-UA', {
        hour: '2-digit',
        minute: '2-digit',
    }).format(new Date(value));
}

function renderSeatRows(seats) {
    const rows = new Map();

    seats.forEach((seat) => {
        if (!rows.has(seat.row_number)) {
            rows.set(seat.row_number, []);
        }
        rows.get(seat.row_number).push(seat);
    });

    container.innerHTML = Array.from(rows.entries())
        .map(([rowNumber, rowSeats]) => {
            const seatMarkup = rowSeats
                .map((seat) => {
                    const classes = ['seat'];
                    if (seat.seat_type !== 'standard') {
                        classes.push('vip');
                    }
                    if (seat.is_occupied) {
                        classes.push('occupied');
                    }

                    return `<button type="button" class="${classes.join(' ')}" data-seat-id="${seat.id}" data-price-multiplier="${seat.price_multiplier}"></button>`;
                })
                .join('');

            return `<div class="row" data-row-number="${rowNumber}">${seatMarkup}</div>`;
        })
        .join('');
}

function updateSelectedCount() {
    const selectedSeats = container.querySelectorAll('.seat.selected');
    let totalPrice = 0;

    selectedSeats.forEach((seat) => {
        const multiplier = Number(seat.dataset.priceMultiplier || '1');
        totalPrice += Number(currentShow.base_price) * multiplier;
    });

    count.innerText = String(selectedSeats.length);
    total.innerText = totalPrice.toFixed(2).replace(/\.00$/, '');
    bookBtn.disabled = selectedSeats.length === 0;
}

async function loadShow(showId) {
    const shows = await apiFetch(`/movies/shows/${currentMovieId}`);
    if (!shows.length) {
        movieTitle.innerText = 'Сеансів поки немає';
        selectedDate.innerText = '';
        container.innerHTML = '<div style="text-align:center; color: var(--text-muted); padding: 24px;">Для цього фільму ще немає доступних сеансів</div>';
        count.innerText = '0';
        total.innerText = '0';
        bookBtn.disabled = true;
        return;
    }

    currentShow = shows.find((show) => String(show.id) === String(showId)) || shows[0];

    timeSelect.innerHTML = shows.map((show) => `
        <option value="${show.id}" ${String(show.id) === String(currentShow.id) ? 'selected' : ''}>
            ${formatTime(show.start_time)} - ${show.format} (${show.base_price} грн)
        </option>
    `).join('');

    movieTitle.innerText = currentShow.movie.title;
    selectedDate.innerText = `📅 ${formatDate(currentShow.start_time)} • ${formatTime(currentShow.start_time)}`;

    const seats = await apiFetch(`/booking/shows/${currentShow.id}/seats`);
    renderSeatRows(seats);
    updateSelectedCount();
}

timeSelect.addEventListener('change', async (event) => {
    const showId = event.target.value;
    const searchParams = new URLSearchParams(window.location.search);
    searchParams.set('show_id', showId);
    window.history.replaceState({}, '', `${window.location.pathname}?${searchParams.toString()}`);
    await loadShow(showId);
});

container.addEventListener('click', (event) => {
    const seat = event.target.closest('.seat');
    if (!seat || seat.classList.contains('occupied')) {
        return;
    }

    seat.classList.toggle('selected');
    updateSelectedCount();
});
document.getElementById('book-btn').addEventListener('click', async (e) => {
    const btn = e.target;
    
const selectedSeatIds = [...document.querySelectorAll('.seats-wrapper .seat.selected')].map(s => Number(s.dataset.seatId));    
    // Блокуємо кнопку
    btn.innerText = 'Бронювання...';
    btn.disabled = true;

    try {
        const token = localStorage.getItem('access_token');
        
        const response = await fetch('/v1/booking/orders', { 
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}` 
            },
            body: JSON.stringify({
                show_id: Number(currentShow.id), // <-- ВИПРАВЛЕНО (Беремо ID з поточного об'єкта)
                seat_ids: selectedSeatIds        // <-- ВИПРАВЛЕНО (Передаємо зібраний масив)
            })
        });

        const data = await response.json();

       if (!response.ok) {
    const errorMessage = Array.isArray(data.detail) ? data.detail[0].msg : (data.detail || 'Помилка при бронюванні');
    throw new Error(errorMessage);
}

        // Редирект на Stripe
        if (data.checkout_url || data.url) {
            window.location.href = data.checkout_url || data.url; 
        } else {
            throw new Error('Бекенд не повернув посилання на оплату');
        }

    } catch (error) {
        console.error("Помилка бронювання:", error);
        alert(error.message); 
        
        // Розблоковуємо кнопку
        btn.innerText = 'Перейти до оплати';
        btn.disabled = false;
    }
});
async function initBookingPage() {
    const params = new URLSearchParams(window.location.search);
    currentMovieId = params.get('movie_id');
    const showId = params.get('show_id');

    if (!currentMovieId) {
        movieTitle.innerText = 'Не вибрано фільм';
        return;
    }

    await loadShow(showId);
}

initBookingPage().catch((error) => console.error(error));