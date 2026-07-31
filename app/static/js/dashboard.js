const Dashboard = {
    init() {
        this.initAutoRefresh();
        this.initQuickActions();
        this.initDateFilters();
    },

    initAutoRefresh() {
        setInterval(() => this.refreshStats(), 300000);
    },

    async refreshStats() {
        try {
            const data = await App.fetchData('/api/dashboard/stats');
            Object.keys(data).forEach(key => {
                const el = document.getElementById(`stat-${key}`);
                if (el) el.textContent = data[key];
            });
        } catch (e) { console.error('Failed to refresh stats:', e); }
    },

    initQuickActions() {
        document.querySelectorAll('.quick-action').forEach(action => {
            action.addEventListener('click', () => {
                const url = action.dataset.url;
                if (url) window.location.href = url;
            });
        });
    },

    initDateFilters() {
        document.querySelectorAll('[data-date-filter]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const filter = btn.dataset.dateFilter;
                document.querySelectorAll('[data-date-filter]').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.applyDateFilter(filter);
            });
        });
    },

    async applyDateFilter(filter) {
        try {
            const data = await App.fetchData(`/api/appointments?filter=${filter}`);
            this.updateAppointmentsTable(data.appointments);
        } catch (e) { console.error('Failed to filter:', e); }
    },

    updateAppointmentsTable(appointments) {
        const tbody = document.getElementById('appointments-tbody');
        if (!tbody || !appointments) return;
        if (appointments.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="text-center py-4"><div class="empty-state"><i class="far fa-calendar-check"></i><h3>No appointments</h3></div></td></tr>';
            return;
        }
        tbody.innerHTML = appointments.map(a => `
            <tr>
                <td><span class="fw-medium">${a.reference}</span></td>
                <td>${a.patient_name}</td>
                <td>${a.service_name}</td>
                <td>${a.practitioner_name || 'N/A'}</td>
                <td>${a.date} ${a.time}</td>
                <td><span class="badge badge-${a.status_color}">${a.status}</span></td>
                <td><a href="/admin/appointments/${a.id}" class="btn btn-sm btn-ghost"><i class="fas fa-eye"></i></a></td>
            </tr>
        `).join('');
    }
};

document.addEventListener('DOMContentLoaded', () => {
    if (document.querySelector('.dashboard-layout')) Dashboard.init();
});
