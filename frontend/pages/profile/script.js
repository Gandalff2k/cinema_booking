// Route guard: no token -> redirect to login
if (!getAccessToken()) {
    window.location.href = '../login/index.html';
}

async function updatePassword() {
    const oldPassword = document.getElementById('old-password').value;
    const newPassword = document.getElementById('new-password').value;
    if (!oldPassword || !newPassword) {
        return showToast('Fill in both fields', 'error');
    }
    if (newPassword.length < 8) {
        return showToast('New password must be at least 8 characters', 'error');
    }
    try {
        await apiFetch('/users/me/password', {
            method: 'PUT',
            body: { old_password: oldPassword, new_password: newPassword },
        });
        document.getElementById('old-password').value = '';
        document.getElementById('new-password').value = '';
        showToast('Password updated', 'success');
    } catch (error) {
        showToast(error.message, 'error');
    }
}

async function loadProfile() {
    const user = await apiFetch('/auth/me');
    document.getElementById('profile-username').innerText = `User: ${user.username}`;
    document.getElementById('profile-email').innerText = `Email: ${user.email}`;

    // Show admins a link to the dashboard.
    if (user.role === 'admin' && !document.getElementById('admin-link')) {
        const link = document.createElement('a');
        link.id = 'admin-link';
        link.href = '../admin/index.html';
        link.className = 'btn-primary';
        link.style.cssText = 'display:inline-block;margin-top:14px;text-decoration:none;';
        link.innerText = '⚙️ Admin panel';
        document.getElementById('profile-email').insertAdjacentElement('afterend', link);
    }
}

async function loadMyTickets() {
    const ticketsContainer = document.getElementById('my-tickets-list');
    ticketsContainer.innerHTML = '<p style="color: var(--text-muted);">Loading tickets...</p>';

    try {
        const orders = await apiFetch('/booking/orders/me'); 
        
        if (orders.length === 0) {
            ticketsContainer.innerHTML = `
                <div class="ticket-card">
                    <div class="ticket-info">
                        <h3>You have no tickets yet</h3>
                        <p>Time to pick a movie!</p>
                    </div>
                </div>
            `;
            return;
        }

        // Keep only the paid ones
        const paidOrders = orders.filter(order => order.status.toLowerCase() === 'paid');

        ticketsContainer.innerHTML = paidOrders.map(order => {
            // Build the HTML for each ticket within the order
            const ticketsHTML = order.tickets.map(t => {
                const dateObj = new Date(t.start_time);
                const formattedDate = dateObj.toLocaleDateString('en-GB', { day: '2-digit', month: 'long', year: 'numeric' });
                const formattedTime = dateObj.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
                
                return `
                    <div style="background: rgba(0, 0, 0, 0.2); border-left: 4px solid #38bdf8; border-radius: 8px; padding: 12px; margin-top: 10px; display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <h4 style="margin: 0 0 5px 0; color: #f8fafc;"> ${t.movie_title}</h4>
                            <p style="margin: 0; color: #94a3b8; font-size: 14px;"> ${formattedDate} at ${formattedTime}</p>
                            <p style="margin: 5px 0 0 0; color: #cbd5e1; font-weight: 600;">
                                 ${t.hall_name} | Row: ${t.row} | Seat: ${t.seat}
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

            // Wrap the tickets in an order card
            return `
                <div class="ticket-card" style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; padding: 20px; margin-bottom: 20px;">
                    <div style="display: flex; justify-content: space-between; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 10px; margin-bottom: 10px;">
                        <div>
                            <span style="color: #94a3b8; font-size: 12px;">Order #${order.id}</span>
                            <h3 style="margin: 0; color: #f8fafc;">Total: ${order.total_price} UAH</h3>
                        </div>
                        <div style="text-align: right;">
                            <span style="background: #22c55e; color: #fff; padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: bold;">PAID</span>
                        </div>
                    </div>
                    <div class="tickets-wrapper">
                        ${ticketsHTML}
                    </div>
                </div>
            `;
        }).join('');

    } catch (error) {
        console.error("Failed to load tickets:", error);
        ticketsContainer.innerHTML = `<p style="color: var(--danger);">Failed to load tickets: ${error.message}</p>`;
    }
}
loadProfile().then(() => {
    loadMyTickets();
}).catch((error) => {
    showToast(`Failed to load profile: ${error.message}`, 'error');
});
