// Checks the token and updates the navbar
function initNavbar() {
    const token = localStorage.getItem('access_token');
    const authBtn = document.getElementById('auth-btn');
    const logoutBtn = document.getElementById('logout-btn');
    
    // If the auth button exists on this page
    if (authBtn) {
        if (token) {
            // Send admins to the dashboard, regular users to their account.
            const isAdmin = localStorage.getItem('user_role') === 'admin';
            authBtn.innerText = isAdmin ? 'Admin panel' : 'My account';
            authBtn.onclick = () => {
                window.location.href = isAdmin
                    ? '../admin/index.html'
                    : '../profile/index.html';
            };
        } else {
            // User is not signed in
            authBtn.innerText = 'Sign in';
            authBtn.onclick = () => window.location.href = '../login/index.html';
        }
    }

    if (logoutBtn) {
        logoutBtn.onclick = logout;
    }
}

// Generic logout function
async function logout() {
    const confirmed = await showConfirm('Log out?', { confirmText: 'Log out' });
    if (!confirmed) {
        return;
    }
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user_role');
    showToast('You have logged out', 'success');
    setTimeout(() => {
        window.location.href = '../home/index.html';
    }, 600);
}

// Run the check whenever any page loads
document.addEventListener('DOMContentLoaded', initNavbar);