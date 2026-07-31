const App = {
    init() {
        this.initTheme();
        this.initCSRF();
        this.initToasts();
        this.initModals();
        this.initSidebar();
        this.initSearch();
        this.initDeleteConfirmations();
        this.initFormValidation();
        console.log('Venus Booking System initialized');
    },

    initTheme() {
        const saved = localStorage.getItem('theme') || 'light';
        document.documentElement.setAttribute('data-theme', saved);
        document.querySelectorAll('[data-theme-toggle]').forEach(btn => {
            btn.addEventListener('click', () => {
                const current = document.documentElement.getAttribute('data-theme');
                const next = current === 'dark' ? 'light' : 'dark';
                document.documentElement.setAttribute('data-theme', next);
                localStorage.setItem('theme', next);
            });
        });
    },

    initCSRF() {
        const csrfToken = document.querySelector('meta[name="csrf-token"]');
        if (csrfToken) {
            window.csrfToken = csrfToken.getAttribute('content');
        }
        document.addEventListener('ajaxSend', (event, xhr) => {
            if (window.csrfToken) {
                xhr.setRequestHeader('X-CSRFToken', window.csrfToken);
            }
        });
    },

    initToasts() {
        this.toastContainer = document.getElementById('toast-container');
        if (!this.toastContainer) {
            this.toastContainer = document.createElement('div');
            this.toastContainer.id = 'toast-container';
            this.toastContainer.className = 'toast-container';
            document.body.appendChild(this.toastContainer);
        }
        const flashMessages = document.querySelectorAll('.flash-message');
        flashMessages.forEach(msg => {
            this.showToast(msg.dataset.message, msg.dataset.type || 'info');
            msg.remove();
        });
    },

    showToast(message, type = 'info', duration = 5000) {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        const icons = { success: 'fa-check-circle', error: 'fa-exclamation-circle', warning: 'fa-exclamation-triangle', info: 'fa-info-circle' };
        toast.innerHTML = `<i class="fas ${icons[type] || icons.info}"></i><span>${message}</span>`;
        this.toastContainer.appendChild(toast);
        setTimeout(() => { toast.style.animation = 'slideInRight 0.3s ease reverse'; setTimeout(() => toast.remove(), 300); }, duration);
    },

    initModals() {
        document.querySelectorAll('[data-modal-target]').forEach(btn => {
            btn.addEventListener('click', () => this.openModal(btn.dataset.modalTarget));
        });
        document.querySelectorAll('[data-modal-close]').forEach(btn => {
            btn.addEventListener('click', () => this.closeModal(btn.closest('.modal-overlay')));
        });
        document.querySelectorAll('.modal-overlay').forEach(overlay => {
            overlay.addEventListener('click', (e) => { if (e.target === overlay) this.closeModal(overlay); });
        });
    },

    openModal(id) {
        const modal = document.getElementById(id);
        if (modal) { modal.classList.add('active'); document.body.style.overflow = 'hidden'; }
    },

    closeModal(modal) {
        if (modal) { modal.classList.remove('active'); document.body.style.overflow = ''; }
    },

    initSidebar() {
        const toggle = document.querySelector('.mobile-menu-toggle');
        const sidebar = document.getElementById('sidebar');
        const overlay = document.getElementById('sidebarOverlay');
        const closeBtn = document.getElementById('sidebarClose');
        if (!sidebar) return;

        const openSidebar = () => {
            sidebar.classList.add('active');
            if (overlay) overlay.classList.add('active');
            document.body.style.overflow = 'hidden';
        };
        const closeSidebar = () => {
            sidebar.classList.remove('active');
            if (overlay) overlay.classList.remove('active');
            document.body.style.overflow = '';
        };

        if (toggle) toggle.addEventListener('click', openSidebar);
        if (closeBtn) closeBtn.addEventListener('click', closeSidebar);
        if (overlay) overlay.addEventListener('click', closeSidebar);

        document.addEventListener('click', (e) => {
            if (sidebar.classList.contains('active') && !sidebar.contains(e.target) && !toggle?.contains(e.target)) {
                closeSidebar();
            }
        });

        let resizeTimer;
        window.addEventListener('resize', () => {
            clearTimeout(resizeTimer);
            resizeTimer = setTimeout(() => {
                if (window.innerWidth > 992) closeSidebar();
            }, 100);
        });
    },

    initSearch() {
        document.querySelectorAll('[data-search]').forEach(input => {
            let debounceTimer;
            input.addEventListener('input', (e) => {
                clearTimeout(debounceTimer);
                debounceTimer = setTimeout(() => {
                    const query = e.target.value.toLowerCase();
                    const target = document.querySelectorAll(input.dataset.search);
                    target.forEach(item => {
                        const text = item.textContent.toLowerCase();
                        item.style.display = text.includes(query) ? '' : 'none';
                    });
                }, 300);
            });
        });
    },

    initDeleteConfirmations() {
        document.querySelectorAll('[data-confirm-delete]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const message = btn.dataset.confirmDelete || 'Are you sure you want to delete this?';
                if (confirm(message)) {
                    const form = btn.closest('form');
                    if (form) form.submit();
                }
            });
        });
    },

    initFormValidation() {
        document.querySelectorAll('form[data-validate]').forEach(form => {
            form.addEventListener('submit', (e) => {
                let valid = true;
                form.querySelectorAll('[required]').forEach(field => {
                    if (!field.value.trim()) {
                        field.classList.add('is-invalid');
                        valid = false;
                    } else {
                        field.classList.remove('is-invalid');
                    }
                });
                if (!valid) { e.preventDefault(); this.showToast('Please fill in all required fields.', 'error'); }
            });
        });
    },

    async fetchData(url, options = {}) {
        const defaults = { headers: { 'Content-Type': 'application/json', 'X-CSRFToken': window.csrfToken || '' } };
        const config = { ...defaults, ...options, headers: { ...defaults.headers, ...options.headers } };
        try {
            const response = await fetch(url, config);
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return await response.json();
        } catch (error) {
            console.error('Fetch error:', error);
            this.showToast('An error occurred. Please try again.', 'error');
            throw error;
        }
    },

    showLoading() {
        const overlay = document.createElement('div');
        overlay.id = 'loading-overlay';
        overlay.className = 'loading-overlay';
        overlay.innerHTML = '<div class="spinner-lg"></div>';
        document.body.appendChild(overlay);
    },

    hideLoading() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) overlay.remove();
    },

    printPage() { window.print(); },

    exportCSV(tableId, filename = 'export.csv') {
        const table = document.getElementById(tableId);
        if (!table) return;
        let csv = [];
        const rows = table.querySelectorAll('tr');
        rows.forEach(row => {
            const cols = row.querySelectorAll('td, th');
            const rowData = [];
            cols.forEach(col => rowData.push('"' + col.textContent.replace(/"/g, '""').trim() + '"'));
            csv.push(rowData.join(','));
        });
        const blob = new Blob([csv.join('\n')], { type: 'text/csv' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = filename;
        link.click();
    },

    formatTime(timeStr) {
        if (!timeStr) return '';
        const [hours, minutes] = timeStr.split(':');
        const h = parseInt(hours);
        const ampm = h >= 12 ? 'PM' : 'AM';
        const h12 = h % 12 || 12;
        return `${h12}:${minutes} ${ampm}`;
    }
};

document.addEventListener('DOMContentLoaded', () => App.init());
