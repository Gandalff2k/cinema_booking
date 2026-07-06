// --- ЛОГІКА ПЕРЕМИКАННЯ ТАБІВ ---
const tabBtns = document.querySelectorAll('.tab-btn');
const forms = document.querySelectorAll('.auth-form');

tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        // Забираємо active у всіх
        tabBtns.forEach(b => b.classList.remove('active'));
        forms.forEach(f => f.classList.remove('active'));
        
        // Вішаємо active на натиснутий таб і відповідну форму
        btn.classList.add('active');
        document.getElementById(btn.dataset.target).classList.add('active');
    });
});

// --- ЛОГІКА ВІДПРАВКИ ФОРМ НА FASTAPI ---

// ЛОГІН
document.getElementById('login-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const contact = document.getElementById('login-contact').value.trim();
    const password = document.getElementById('login-password').value;
    const errorMsg = document.getElementById('login-error');
    
    errorMsg.innerText = ''; // Очищаємо старі помилки

    try {
        const response = await apiFetch('/auth/login', {
            method: 'POST',
            body: { contact, password },
        });

        setAuthTokens(response);
        
        // Перекидаємо на головну
        alert('Успішний вхід!');
        window.location.href = '../home/index.html'; 
        
    } catch (err) {
        errorMsg.innerText = err.message;
    }
});

document.getElementById('register-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = document.getElementById('reg-contact').value.trim();
    const username = document.getElementById('reg-username').value.trim();
    const pass = document.getElementById('reg-password').value;
    const confirmPass = document.getElementById('reg-password-confirm').value;
    const errorMsg = document.getElementById('reg-error');

    if (pass !== confirmPass) {
        return errorMsg.innerText = 'Паролі не співпадають!';
    }

    try {
        await apiFetch('/auth/register', {
            method: 'POST',
            body: { email, username, password: pass },
        });
        
        alert('Реєстрація успішна!');
        
        // Магія автозаповнення:
        tabBtns[0].click();
        document.getElementById('login-contact').value = email;
        document.getElementById('login-password').focus();
        
    } catch (err) {
        errorMsg.innerText = err.message;
    }
});