/**
 * DAIZZY IMS — Core Frontend Utilities, Drawer Navigation & Toast Framework
 * Tailored for https://www.daizzy.online
 */

class ToastManager {
  constructor() {
    this.container = document.getElementById('toast-container');
    if (!this.container) {
      this.container = document.createElement('div');
      this.container.id = 'toast-container';
      document.body.appendChild(this.container);
    }
  }

  show(message, type = 'info', duration = 3500) {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
      <div class="toast-content" style="display:flex;align-items:center;gap:8px;">
        <span>${message}</span>
      </div>
      <button class="toast-close" style="background:none;border:none;cursor:pointer;font-size:1.2rem;color:var(--brand-muted);margin-left:12px;padding:2px 6px;">&times;</button>
    `;

    toast.querySelector('.toast-close').addEventListener('click', () => {
      toast.remove();
    });

    this.container.appendChild(toast);

    if (duration > 0) {
      setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(10px)';
        toast.style.transition = 'all 0.25s ease';
        setTimeout(() => toast.remove(), 250);
      }, duration);
    }
  }

  success(msg, dur) { this.show(msg, 'success', dur); }
  error(msg, dur) { this.show(msg, 'error', dur); }
  warning(msg, dur) { this.show(msg, 'warning', dur); }
}

window.Toast = new ToastManager();

// CSRF Token Extractor for AJAX requests
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

window.getCSRFToken = () => getCookie('csrftoken');

// Global API helper
window.apiFetch = async function(url, options = {}) {
  const headers = options.headers || {};
  headers['X-CSRFToken'] = window.getCSRFToken();
  headers['Content-Type'] = headers['Content-Type'] || 'application/json';

  const response = await fetch(url, { ...options, headers });
  const data = await response.json();

  if (!response.ok) {
    const errorMsg = data.error?.message || data.detail || 'An error occurred';
    throw new Error(errorMsg);
  }
  return data;
};

// Mobile Drawer Navigation Initialization
document.addEventListener('DOMContentLoaded', () => {
  const sidebar = document.querySelector('.app-sidebar');
  const backdrop = document.getElementById('sidebar-backdrop');
  const btnToggle = document.getElementById('btn-toggle-sidebar');
  const btnClose = document.getElementById('btn-close-sidebar');
  const btnMobileMenuNav = document.getElementById('btn-mobile-nav-menu');

  function openDrawer() {
    if (sidebar) sidebar.classList.add('open');
    if (backdrop) backdrop.classList.add('active');
    document.body.style.overflow = 'hidden';
  }

  function closeDrawer() {
    if (sidebar) sidebar.classList.remove('open');
    if (backdrop) backdrop.classList.remove('active');
    document.body.style.overflow = '';
  }

  if (btnToggle) btnToggle.addEventListener('click', openDrawer);
  if (btnClose) btnClose.addEventListener('click', closeDrawer);
  if (backdrop) backdrop.addEventListener('click', closeDrawer);
  if (btnMobileMenuNav) btnMobileMenuNav.addEventListener('click', openDrawer);

  // Close on Escape
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeDrawer();
  });
});
