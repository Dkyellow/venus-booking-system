const BookingFlow = {
    currentStep: 1,
    selectedService: null,
    selectedPractitioner: null,
    selectedDate: null,
    selectedTime: null,
    patientInfo: {},

    init() {
        this.renderStep(1);
    },

    renderStep(step) {
        this.currentStep = step;
        document.querySelectorAll('.booking-step').forEach((el, i) => {
            el.classList.remove('active', 'completed');
            if (i + 1 < step) el.classList.add('completed');
            if (i + 1 === step) el.classList.add('active');
        });
        document.querySelectorAll('.booking-step-content').forEach((el, i) => {
            el.style.display = (i + 1 === step) ? 'block' : 'none';
        });
        this.updateSummary();
    },

    async loadServices() {
        try {
            const data = await App.fetchData('/api/services');
            const container = document.getElementById('services-list');
            if (!container) return;
            container.innerHTML = data.services.map(s => `
                <div class="service-card" data-id="${s.id}" onclick="BookingFlow.selectService(${s.id})">
                    <div class="service-card-icon" style="background: ${s.color}20; color: ${s.color};">
                        <i class="fas ${s.icon || 'fa-stethoscope'}"></i>
                    </div>
                    <div class="service-card-info">
                        <h4>${s.name}</h4>
                        <p>${s.description || ''}</p>
                        <div class="service-card-meta">
                            <span><i class="far fa-clock"></i> ${s.duration} min</span>
                            ${s.price > 0 ? `<span><i class="fas fa-dollar-sign"></i> $${parseFloat(s.price).toFixed(2)}</span>` : ''}
                        </div>
                    </div>
                </div>
            `).join('');
        } catch (e) { console.error('Failed to load services:', e); }
    },

    selectService(id) {
        this.selectedService = id;
        this.selectedPractitioner = null;
        this.selectedDate = null;
        this.selectedTime = null;
        document.querySelectorAll('.service-card').forEach(c => c.classList.remove('selected'));
        document.querySelector(`.service-card[data-id="${id}"]`)?.classList.add('selected');
        this.loadPractitioners(id);
        this.renderStep(2);
    },

    async loadPractitioners(serviceId) {
        try {
            const data = await App.fetchData(`/api/services/${serviceId}/practitioners`);
            const container = document.getElementById('practitioners-list');
            if (!container) return;
            container.innerHTML = data.practitioners.map(p => `
                <div class="practitioner-card" data-id="${p.id}" onclick="BookingFlow.selectPractitioner(${p.id})">
                    <div class="practitioner-avatar">${p.photo_url ? `<img src="${p.photo_url}" alt="${p.name}">` : '<i class="fas fa-user-md"></i>'}</div>
                    <div class="practitioner-info">
                        <h4>${p.name}</h4>
                        <p>${p.specialization || ''}</p>
                    </div>
                </div>
            `).join('');
        } catch (e) { console.error('Failed to load practitioners:', e); }
    },

    selectPractitioner(id) {
        this.selectedPractitioner = id;
        this.selectedDate = null;
        this.selectedTime = null;
        document.querySelectorAll('.practitioner-card').forEach(c => c.classList.remove('selected'));
        document.querySelector(`.practitioner-card[data-id="${id}"]`)?.classList.add('selected');
        this.loadCalendar();
        this.renderStep(3);
    },

    loadCalendar() {
        this.loadAvailableDates();
    },

    async loadAvailableDates() {
        try {
            let url = `/api/booking/available-dates?service_id=${this.selectedService}`;
            if (this.selectedPractitioner) url += `&practitioner_id=${this.selectedPractitioner}`;
            const container = document.getElementById('dates-list');
            if (!container) return;
            container.innerHTML = '<div class="date-loading"><div class="spinner"></div><span>Finding available dates...</span></div>';
            const data = await App.fetchData(url);
            if (!data.dates || data.dates.length === 0) {
                container.innerHTML = '<div class="empty-state"><i class="far fa-calendar-xmark"></i><h3>No available dates</h3><p>Try a different service or practitioner.</p></div>';
                return;
            }
            const months = {};
            data.dates.forEach(d => {
                const dt = new Date(d.date + 'T00:00:00');
                const key = `${dt.getFullYear()}-${String(dt.getMonth()).padStart(2, '0')}`;
                if (!months[key]) months[key] = { label: dt.toLocaleDateString('en-US', { month: 'long', year: 'numeric' }), dates: [] };
                months[key].dates.push(d);
            });
            let html = '';
            Object.values(months).forEach(m => {
                html += `<div class="date-month-group"><div class="date-month-header">${m.label}</div>`;
                html += '<div class="date-weekdays"><span>Mon</span><span>Tue</span><span>Wed</span><span>Thu</span><span>Fri</span></div>';
                const firstDow = new Date(m.dates[0].date + 'T00:00:00').getDay();
                const offset = firstDow === 0 ? 4 : firstDow - 1;
                html += '<div class="date-grid">';
                for (let i = 0; i < offset; i++) html += '<div class="date-cell empty"></div>';
                m.dates.forEach(d => {
                    const dt = new Date(d.date + 'T00:00:00');
                    const dayNum = dt.getDate();
                    const isSelected = this.selectedDate === d.date;
                    html += `<button class="date-cell${isSelected ? ' selected' : ''}" data-date="${d.date}" onclick="BookingFlow.selectDate('${d.date}')">
                        <span class="date-day-num">${dayNum}</span>
                        <span class="date-slots-badge">${d.slots_count} slot${d.slots_count !== 1 ? 's' : ''}</span>
                    </button>`;
                });
                html += '</div></div>';
            });
            container.innerHTML = html;
        } catch (e) { console.error('Failed to load dates:', e); }
    },

    selectDate(date) {
        this.selectedDate = date;
        this.selectedTime = null;
        document.querySelectorAll('#dates-list .date-cell').forEach(c => c.classList.remove('selected'));
        const cell = document.querySelector(`#dates-list .date-cell[data-date="${date}"]`);
        if (cell) {
            cell.classList.add('selected');
            const dt = new Date(date + 'T00:00:00');
            const formatted = dt.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' });
            document.getElementById('selected-date-display').textContent = formatted;
            document.getElementById('selected-date-display').style.display = 'block';
        }
        this.loadTimeSlots(date);
    },

    async loadTimeSlots(date) {
        try {
            let url = `/api/booking/slots?service_id=${this.selectedService}&date=${date}`;
            if (this.selectedPractitioner) url += `&practitioner_id=${this.selectedPractitioner}`;
            const container = document.getElementById('time-slots-list');
            if (!container) return;
            container.innerHTML = '<div class="date-loading"><div class="spinner"></div><span>Loading times...</span></div>';
            document.getElementById('times-section').style.display = 'block';
            const data = await App.fetchData(url);
            if (!data.slots || data.slots.length === 0) {
                container.innerHTML = '<div class="empty-state small"><i class="far fa-clock"></i><h3>No times available</h3><p>This date is fully booked. Pick another date.</p></div>';
                return;
            }
            const amSlots = data.slots.filter(s => {
                const h = parseInt(s.start_time.split(':')[0]);
                return h < 12;
            });
            const pmSlots = data.slots.filter(s => {
                const h = parseInt(s.start_time.split(':')[0]);
                return h >= 12;
            });
            let html = '';
            if (amSlots.length) {
                html += '<div class="time-group"><div class="time-group-header"><i class="fas fa-sun"></i> Morning</div>';
                html += '<div class="time-slots-grid">';
                amSlots.forEach(s => {
                    html += `<button class="time-slot" data-time="${s.start_time}" onclick="BookingFlow.selectTime('${s.start_time}', '${s.end_time}', '${s.display}')">
                        <span class="time-text">${s.display}</span>
                    </button>`;
                });
                html += '</div></div>';
            }
            if (pmSlots.length) {
                html += '<div class="time-group"><div class="time-group-header"><i class="fas fa-cloud-sun"></i> Afternoon</div>';
                html += '<div class="time-slots-grid">';
                pmSlots.forEach(s => {
                    html += `<button class="time-slot" data-time="${s.start_time}" onclick="BookingFlow.selectTime('${s.start_time}', '${s.end_time}', '${s.display}')">
                        <span class="time-text">${s.display}</span>
                    </button>`;
                });
                html += '</div></div>';
            }
            container.innerHTML = html;
        } catch (e) { console.error('Failed to load time slots:', e); }
    },

    selectTime(startTime, endTime, display) {
        this.selectedTime = { start: startTime, end: endTime, display: display };
        document.querySelectorAll('#time-slots-list .time-slot').forEach(c => c.classList.remove('selected'));
        document.querySelector(`#time-slots-list .time-slot[data-time="${startTime}"]`)?.classList.add('selected');
        this.renderStep(4);
    },

    updateSummary() {
        const summary = document.getElementById('booking-summary-content');
        if (!summary) return;
        let html = '';
        if (this.selectedService) html += `<div class="summary-row"><span class="summary-label">Service</span><span class="summary-value" id="summary-service"></span></div>`;
        if (this.selectedPractitioner) html += `<div class="summary-row"><span class="summary-label">Practitioner</span><span class="summary-value" id="summary-practitioner"></span></div>`;
        if (this.selectedDate) html += `<div class="summary-row"><span class="summary-label">Date</span><span class="summary-value" id="summary-date"></span></div>`;
        if (this.selectedTime) html += `<div class="summary-row"><span class="summary-label">Time</span><span class="summary-value" id="summary-time"></span></div>`;
        summary.innerHTML = html;
    },

    async submitBooking() {
        const form = document.getElementById('booking-form');
        if (!form) return;
        const formData = new FormData(form);
        const data = {
            service_id: this.selectedService,
            practitioner_id: this.selectedPractitioner,
            date: this.selectedDate,
            start_time: this.selectedTime.start,
            end_time: this.selectedTime.end,
            first_name: formData.get('first_name'),
            last_name: formData.get('last_name'),
            email: formData.get('email'),
            phone: formData.get('phone'),
            date_of_birth: formData.get('date_of_birth'),
            gender: formData.get('gender'),
            reason: formData.get('reason'),
            notes: formData.get('notes')
        };
        try {
            App.showLoading();
            const result = await App.fetchData('/api/booking/create', {
                method: 'POST',
                body: JSON.stringify(data)
            });
            App.hideLoading();
            if (result.success) {
                window.location.href = `/booking/confirmation/${result.reference}`;
            } else {
                App.showToast(result.message || 'Booking failed. Please try again.', 'error');
            }
        } catch (e) {
            App.hideLoading();
            App.showToast('An error occurred. Please try again.', 'error');
        }
    },

    goBack(step) { this.renderStep(step); }
};

document.addEventListener('DOMContentLoaded', () => {
    if (document.querySelector('.booking-page')) {
        BookingFlow.init();
    }
});
