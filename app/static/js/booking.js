const BookingFlow = {
    selectedService: null,
    selectedPractitioner: null,
    selectedDate: null,
    selectedTime: null,
    calYear: null,
    calMonth: null,
    availableDates: [],
    currentPeriod: 'AM',
    allSlots: [],

    init() {
        const today = new Date();
        this.calYear = today.getFullYear();
        this.calMonth = today.getMonth();
        document.addEventListener('click', (e) => {
            const dd = document.getElementById('calendar-dropdown');
            const ci = document.getElementById('calendar-input');
            if (dd && dd.style.display !== 'none' && !dd.contains(e.target) && ci && !ci.contains(e.target)) {
                dd.style.display = 'none';
            }
        });
    },

    onServiceChange(id) {
        this.selectedService = id ? parseInt(id) : null;
        this.selectedPractitioner = null;
        this.selectedDate = null;
        this.selectedTime = null;
        this.availableDates = [];
        this.allSlots = [];
        this.updatePractitioners();
        this.resetDate();
        this.hideTimeCard();
        this.hideForm();
        this.updateSummary();
    },

    onPractitionerChange(id) {
        this.selectedPractitioner = id ? parseInt(id) : null;
        this.selectedDate = null;
        this.selectedTime = null;
        this.availableDates = [];
        this.allSlots = [];
        this.resetDate();
        this.hideTimeCard();
        this.updateSummary();
        if (this.selectedService) this.loadAvailableDates();
    },

    async updatePractitioners() {
        const sel = document.getElementById('practitioner-select');
        if (!sel || !this.selectedService) { if (sel) sel.innerHTML = '<option value="">Any available practitioner</option>'; return; }
        try {
            const data = await App.fetchData(`/api/services/${this.selectedService}/practitioners`);
            sel.innerHTML = '<option value="">Any available practitioner</option>' +
                data.practitioners.map(p => `<option value="${p.id}">${p.name}${p.specialization ? ' - ' + p.specialization : ''}</option>`).join('');
            if (this.selectedService) this.loadAvailableDates();
        } catch (e) { console.error(e); }
    },

    async loadAvailableDates() {
        if (!this.selectedService) return;
        let url = `/api/booking/available-dates?service_id=${this.selectedService}`;
        if (this.selectedPractitioner) url += `&practitioner_id=${this.selectedPractitioner}`;
        try {
            const data = await App.fetchData(url);
            this.availableDates = data.dates || [];
            this.renderCalendar();
        } catch (e) { console.error(e); }
    },

    toggleCalendar() {
        const dd = document.getElementById('calendar-dropdown');
        if (!dd) return;
        dd.style.display = dd.style.display === 'none' ? 'block' : 'none';
    },

    prevMonth() {
        this.calMonth--;
        if (this.calMonth < 0) { this.calMonth = 11; this.calYear--; }
        this.renderCalendar();
    },

    nextMonth() {
        this.calMonth++;
        if (this.calMonth > 11) { this.calMonth = 0; this.calYear++; }
        this.renderCalendar();
    },

    renderCalendar() {
        const grid = document.getElementById('cal-grid');
        const label = document.getElementById('cal-month-year');
        if (!grid || !label) return;
        const months = ['January','February','March','April','May','June','July','August','September','October','November','December'];
        label.textContent = `${months[this.calMonth]} ${this.calYear}`;

        const firstDay = new Date(this.calYear, this.calMonth, 1);
        const daysInMonth = new Date(this.calYear, this.calMonth + 1, 0).getDate();
        let startDow = firstDay.getDay();
        startDow = startDow === 0 ? 6 : startDow - 1;

        const availSet = new Set(this.availableDates.map(d => d.date));
        const today = new Date().toISOString().split('T')[0];

        let html = '';
        for (let i = 0; i < startDow; i++) html += '<div class="bp-cal-day empty"></div>';

        for (let day = 1; day <= daysInMonth; day++) {
            const dateStr = `${this.calYear}-${String(this.calMonth + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
            const isAvailable = availSet.has(dateStr);
            const isSelected = this.selectedDate === dateStr;
            const isPast = dateStr < today;
            let cls = 'bp-cal-day';
            if (isAvailable && !isPast) cls += ' available';
            else cls += ' unavailable';
            if (isSelected) cls += ' selected';
            if (isPast) cls += ' past';

            if (isAvailable && !isPast) {
                html += `<div class="${cls}" onclick="BookingFlow.pickDate('${dateStr}')">${day}</div>`;
            } else {
                html += `<div class="${cls}">${day}</div>`;
            }
        }
        grid.innerHTML = html;
    },

    pickDate(dateStr) {
        this.selectedDate = dateStr;
        this.selectedTime = null;
        const dt = new Date(dateStr + 'T00:00:00');
        const display = dt.toLocaleDateString('en-GB', { day: '2-digit', month: '2-digit', year: 'numeric' });
        document.getElementById('calendar-display').textContent = display;
        document.getElementById('calendar-dropdown').style.display = 'none';
        this.loadTimeSlots();
        this.updateSummary();
    },

    clearDate() {
        this.selectedDate = null;
        this.selectedTime = null;
        document.getElementById('calendar-display').textContent = 'Pick a date';
        document.getElementById('calendar-dropdown').style.display = 'none';
        this.hideTimeCard();
        this.hideForm();
        this.updateSummary();
    },

    resetDate() {
        this.selectedDate = null;
        this.selectedTime = null;
        const calDisp = document.getElementById('calendar-display');
        if (calDisp) calDisp.textContent = 'Pick a date';
        const dd = document.getElementById('calendar-dropdown');
        if (dd) dd.style.display = 'none';
    },

    async loadTimeSlots() {
        if (!this.selectedService || !this.selectedDate) return;
        const timeCard = document.getElementById('time-card');
        const timeList = document.getElementById('time-list');
        if (!timeCard || !timeList) return;
        timeCard.style.display = 'block';
        timeList.innerHTML = '<div class="bp-time-loading"><div class="bp-spinner"></div></div>';

        let url = `/api/booking/slots?service_id=${this.selectedService}&date=${this.selectedDate}`;
        if (this.selectedPractitioner) url += `&practitioner_id=${this.selectedPractitioner}`;
        try {
            const data = await App.fetchData(url);
            this.allSlots = data.slots || [];
            this.renderTimeList();
        } catch (e) { console.error(e); timeList.innerHTML = '<p class="bp-time-empty">Failed to load times.</p>'; }
    },

    setPeriod(p) {
        this.currentPeriod = p;
        document.querySelectorAll('.bp-amp').forEach(b => b.classList.toggle('active', b.dataset.period === p));
        this.renderTimeList();
    },

    renderTimeList() {
        const list = document.getElementById('time-list');
        if (!list) return;
        const filtered = this.allSlots.filter(s => {
            const h = parseInt(s.start_time.split(':')[0]);
            return this.currentPeriod === 'AM' ? h < 12 : h >= 12;
        });
        if (filtered.length === 0) {
            list.innerHTML = '<p class="bp-time-empty">No times available in this period.</p>';
            return;
        }
        list.innerHTML = filtered.map(s => {
            const isSelected = this.selectedTime && this.selectedTime.start === s.start_time;
            return `<button class="bp-time-item${isSelected ? ' selected' : ''}" onclick="BookingFlow.pickTime('${s.start_time}','${s.end_time}','${s.display}')">${s.display}</button>`;
        }).join('');
    },

    pickTime(start, end, display) {
        this.selectedTime = { start, end, display };
        document.querySelectorAll('.bp-time-item').forEach(b => b.classList.toggle('selected', b.textContent.trim() === display));
        document.getElementById('patient-form-section').style.display = 'block';
        this.updateSummary();
        document.getElementById('patient-form-section').scrollIntoView({ behavior: 'smooth', block: 'start' });
    },

    hideTimeCard() {
        const tc = document.getElementById('time-card');
        if (tc) tc.style.display = 'none';
    },

    hideForm() {
        const fs = document.getElementById('patient-form-section');
        if (fs) fs.style.display = 'none';
    },

    updateSummary() {
        const el = document.getElementById('summary-content');
        if (!el) return;
        const serviceSel = document.getElementById('service-select');
        const pracSel = document.getElementById('practitioner-select');
        let html = '';

        if (this.selectedService && serviceSel) {
            const opt = serviceSel.options[serviceSel.selectedIndex];
            html += `<div class="bp-sum-row"><span class="bp-sum-label">Service</span><span class="bp-sum-value">${opt.text}</span></div>`;
        }
        if (this.selectedPractitioner && pracSel) {
            const opt = pracSel.options[pracSel.selectedIndex];
            html += `<div class="bp-sum-row"><span class="bp-sum-label">Practitioner</span><span class="bp-sum-value">${opt.text}</span></div>`;
        } else if (this.selectedService) {
            html += `<div class="bp-sum-row"><span class="bp-sum-label">Practitioner</span><span class="bp-sum-value">Any available</span></div>`;
        }
        if (this.selectedDate) {
            const dt = new Date(this.selectedDate + 'T00:00:00');
            html += `<div class="bp-sum-row"><span class="bp-sum-label">Date</span><span class="bp-sum-value">${dt.toLocaleDateString('en-GB', { weekday: 'short', day: '2-digit', month: 'short', year: 'numeric' })}</span></div>`;
        }
        if (this.selectedTime) {
            html += `<div class="bp-sum-row"><span class="bp-sum-label">Time</span><span class="bp-sum-value">${this.selectedTime.display}</span></div>`;
        }


        const btn = document.getElementById('confirm-btn');
        if (btn) btn.disabled = !(this.selectedService && this.selectedDate && this.selectedTime);

        el.innerHTML = html || '<p class="bp-summary-empty">Complete the form to see your booking summary.</p>';
    },

    async submitBooking() {
        const form = document.getElementById('booking-form');
        if (!form || !this.selectedService || !this.selectedDate || !this.selectedTime) return;
        const fd = new FormData(form);
        const data = {
            service_id: this.selectedService,
            practitioner_id: this.selectedPractitioner,
            date: this.selectedDate,
            start_time: this.selectedTime.start,
            end_time: this.selectedTime.end,
            first_name: fd.get('first_name'),
            last_name: fd.get('last_name'),
            email: fd.get('email'),
            phone: fd.get('phone'),
            date_of_birth: fd.get('date_of_birth'),
            gender: fd.get('gender'),
            reason: fd.get('reason'),
            notes: fd.get('notes')
        };
        try {
            const btn = document.getElementById('confirm-btn');
            if (btn) { btn.disabled = true; btn.innerHTML = '<div class="bp-spinner" style="width:16px;height:16px;border-width:2px;"></div> Booking...'; }
            const result = await App.fetchData('/api/booking/create', { method: 'POST', body: JSON.stringify(data) });
            if (result.success) {
                window.location.href = `/booking/confirmation/${result.reference}`;
            } else {
                App.showToast(result.message || 'Booking failed. Please try again.', 'error');
                if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fas fa-check me-1"></i>Confirm Booking'; }
            }
        } catch (e) {
            App.showToast('An error occurred. Please try again.', 'error');
            const btn = document.getElementById('confirm-btn');
            if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fas fa-check me-1"></i>Confirm Booking'; }
        }
    }
};

document.addEventListener('DOMContentLoaded', () => {
    if (document.querySelector('.booking-page')) BookingFlow.init();
});
