// Захист роуту: якщо немає токена, викидаємо на логін
if (!getAccessToken()) {
    window.location.href = '../login/index.html';
}

async function updatePassword() {
    const newPassword = document.getElementById('new-password').value;
    if (!newPassword) return alert("Введіть новий пароль");
    
    try {
        // Заглушка для API
        // await apiFetch('/users/me/password', 'PUT', { password: newPassword });
        alert("Пароль успішно змінено!");
        document.getElementById('new-password').value = '';
    } catch (error) {
        alert("Помилка зміни пароля: " + error.message);
    }
}

async function loadProfile() {
    const user = await apiFetch('/auth/me');
    document.getElementById('profile-username').innerText = `Користувач: ${user.username}`;
    document.getElementById('profile-email').innerText = `Email: ${user.email}`;
}

async function loadMyTickets() {
    const ticketsContainer = document.getElementById('my-tickets-list');
    ticketsContainer.innerHTML = '<p style="color: var(--text-muted);">Завантаження квитків...</p>';

    try {
        const orders = await apiFetch('/booking/orders/me'); 
        
        if (orders.length === 0) {
            ticketsContainer.innerHTML = `
                <div class="ticket-card">
                    <div class="ticket-info">
                        <h3>У вас ще немає квитків</h3>
                        <p>Час обрати цікавий фільм!</p>
                    </div>
                </div>
            `;
            return;
        }

        // Залишаємо тільки оплачені
        const paidOrders = orders.filter(order => order.status.toLowerCase() === 'paid');

        ticketsContainer.innerHTML = paidOrders.map(order => {
            // Генеруємо HTML для кожного квитка всередині замовлення
            const ticketsHTML = order.tickets.map(t => {
                const dateObj = new Date(t.start_time);
                const formattedDate = dateObj.toLocaleDateString('uk-UA', { day: '2-digit', month: 'long', year: 'numeric' });
                const formattedTime = dateObj.toLocaleTimeString('uk-UA', { hour: '2-digit', minute: '2-digit' });
                
                return `
                    <div style="background: rgba(0, 0, 0, 0.2); border-left: 4px solid #38bdf8; border-radius: 8px; padding: 12px; margin-top: 10px; display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <h4 style="margin: 0 0 5px 0; color: #f8fafc;"> ${t.movie_title}</h4>
                            <p style="margin: 0; color: #94a3b8; font-size: 14px;"> ${formattedDate} о ${formattedTime}</p>
                            <p style="margin: 5px 0 0 0; color: #cbd5e1; font-weight: 600;">
                                 ${t.hall_name} | Ряд: ${t.row} | Місце: ${t.seat}
                            </p>
                        </div>
                        <div style="text-align: center; padding-left: 15px; border-left: 1px dashed rgba(255,255,255,0.1);">
                            <div style="background: #fff; padding: 5px; border-radius: 4px; display: inline-block;">
                                <img src="https://api.qrserver.com/v1/create-qr-code/?size=60x60&data=${t.qr_code || t.ticket_id}&color=0f172a" alt="QR" style="display: block;">
                            </div>
                            <p style="margin: 5px 0 0 0; font-size: 10px; color: #64748b;">ID: ${t.ticket_id}</p>
                        </div>
                    </div>
                `;
            }).join('');

            // Загортаємо квитки у картку замовлення
            return `
                <div class="ticket-card" style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; padding: 20px; margin-bottom: 20px;">
                    <div style="display: flex; justify-content: space-between; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 10px; margin-bottom: 10px;">
                        <div>
                            <span style="color: #94a3b8; font-size: 12px;">Замовлення #${order.id}</span>
                            <h3 style="margin: 0; color: #f8fafc;">Сума: ${order.total_price} грн</h3>
                        </div>
                        <div style="text-align: right;">
                            <span style="background: #22c55e; color: #fff; padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: bold;">ОПЛАЧЕНО</span>
                        </div>
                    </div>
                    <div class="tickets-wrapper">
                        ${ticketsHTML}
                    </div>
                </div>
            `;
        }).join('');

    } catch (error) {
        console.error("Помилка завантаження квитків:", error);
        ticketsContainer.innerHTML = `<p style="color: var(--danger);">Не вдалося завантажити квитки: ${error.message}</p>`;
    }
}
loadProfile().then(() => {
    loadMyTickets();
}).catch((error) => {
    alert(`Не вдалося завантажити профіль: ${error.message}`);
});
