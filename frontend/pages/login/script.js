// --- TAB SWITCHING LOGIC ---
const tabBtns = document.querySelectorAll('.tab-btn');
const forms = document.querySelectorAll('.auth-form');

tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        tabBtns.forEach(b => b.classList.remove('active'));
        forms.forEach(f => f.classList.remove('active'));
        btn.classList.add('active');
        document.getElementById(btn.dataset.target).classList.add('active');
    });
});

// Open the requested tab, e.g. ?tab=register (used by the booking flow).
if (new URLSearchParams(window.location.search).get('tab') === 'register') {
    document.querySelector('.tab-btn[data-target="register-form"]')?.click();
}

// --- FORM SUBMISSION LOGIC (FASTAPI) ---

// LOGIN
document.getElementById('login-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const contact = document.getElementById('login-contact').value.trim();
    const password = document.getElementById('login-password').value;
    const errorMsg = document.getElementById('login-error');
    
    errorMsg.innerText = ''; // Clear previous errors

    try {
        const response = await apiFetch('/auth/login', {
            method: 'POST',
            body: { contact, password },
        });

        setAuthTokens(response);
        showToast('Signed in!', 'success');

        // Send admins to the dashboard, everyone else to the home page.
        let destination = '../home/index.html';
        try {
            const me = await apiFetch('/auth/me');
            localStorage.setItem('user_role', me.role);
            if (me.role === 'admin') {
                destination = '../admin/index.html';
            }
        } catch (meError) {
            console.error('Could not determine role:', meError);
        }
        setTimeout(() => {
            window.location.href = destination;
        }, 700);

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
        return errorMsg.innerText = 'Passwords do not match!';
    }

    try {
        await apiFetch('/auth/register', {
            method: 'POST',
            body: { email, username, password: pass },
        });
        
        showToast('Registration successful! Now sign in.', 'success');

        // Auto-fill magic:
        tabBtns[0].click();
        document.getElementById('login-contact').value = email;
        document.getElementById('login-password').focus();
        
    } catch (err) {
        errorMsg.innerText = err.message;
    }
});