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
            const data = await App.fetchData(url);
            const container = document.getElementById('dates-list');
            if (!container) return;
            if (!data.dates || data.dates.length === 0) {
                container.innerHTML = '<div class="empty-state"><i class="far fa-calendar"></i><h3>No available dates</h3><p>Please try a different service or practitioner.</p></div>';
                return;
            }
            container.innerHTML = '<div class="time-slots-grid" style="grid-template-columns: repeat(7, 1fr); gap: 6px;">' +
                data.dates.map(d => `
                    <button class="time-slot" data-date="${d.date}" onclick="BookingFlow.selectDate('${d.date}')">
                        <div style="font-size:0.7rem;color:var(--text-tertiary)">${d.day_name.substring(0,3)}</div>
                        <div>${new Date(d.date + 'T00:00:00').getDate()}</div>
                    </button>
                `).join('') + '</div>';
        } catch (e) { console.error('Failed to load dates:', e); }
    },

    selectDate(date) {
        this.selectedDate = date;
        this.selectedTime = null;
        document.querySelectorAll('#dates-list .time-slot').forEach(c => c.classList.remove('selected'));
        document.querySelector(`#dates-list .time-slot[data-date="${date}"]`)?.classList.add('selected');
        this.loadTimeSlots(date);
    },

    async loadTimeSlots(date) {
        try {
            let url = `/api/booking/slots?service_id=${this.selectedService}&date=${date}`;
            if (this.selectedPractitioner) url += `&practitioner_id=${this.selectedPractitioner}`;
            const data = await App.fetchData(url);
            const container = document.getElementById('time-slots-list');
            if (!container) return;
            if (!data.slots || data.slots.length === 0) {
                container.innerHTML = '<div class="empty-state"><i class="far fa-clock"></i><h3>No available times</h3><p>This date is fully booked.</p></div>';
                return;
            }
            container.innerHTML = '<div class="time-slots-grid">' +
                data.slots.map(s => `
                    <button class="time-slot" data-time="${s.start_time}" onclick="BookingFlow.selectTime('${s.start_time}', '${s.end_time}', '${s.display}')">
                        ${s.display}
                    </button>
                `).join('') + '</div>';
            this.renderStep(3);
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
