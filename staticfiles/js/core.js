/**
 * DAIZZY IMS — Core Frontend Utilities & Toast Framework
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
      <div class="toast-content">
        <span>${message}</span>
      </div>
      <button class="toast-close" style="background:none;border:none;cursor:pointer;font-size:1.1rem;color:#888;margin-left:12px;">&times;</button>
    `;

    toast.querySelector('.toast-close').addEventListener('click', () => {
      toast.remove();
    });

    this.container.appendChild(toast);

    if (duration > 0) {
      setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.3s ease';
        setTimeout(() => toast.remove(), 300);
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
