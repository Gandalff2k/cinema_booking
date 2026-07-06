// Функція перевірки токена і оновлення шапки
function initNavbar() {
    const token = localStorage.getItem('access_token');
    const authBtn = document.getElementById('auth-btn');
    const logoutBtn = document.getElementById('logout-btn');
    
    // Якщо кнопка авторизації є на сторінці
    if (authBtn) {
        if (token) {
            // Юзер залогінений
            authBtn.innerText = 'Особистий кабінет';
            authBtn.onclick = () => window.location.href = '../profile/index.html';
        } else {
            // Юзер не залогінений
            authBtn.innerText = 'Увійти';
            authBtn.onclick = () => window.location.href = '../login/index.html';
        }
    }

    if (logoutBtn) {
        logoutBtn.onclick = logout;
    }
}

// Універсальна функція виходу (Логаут)
function logout() {
    localStorage.removeItem('access_token');
    alert('Ви успішно вийшли з акаунту');
    window.location.href = '../home/index.html'; // Кидаємо на головну
}

// Запускаємо перевірку при завантаженні будь-якої сторінки
document.addEventListener('DOMContentLoaded', initNavbar);