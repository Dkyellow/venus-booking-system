const CalendarManager = {
    calendar: null,

    init(containerId, events = [], options = {}) {
        const container = document.getElementById(containerId);
        if (!container) return;

        this.calendar = new FullCalendar.Calendar(container, {
            initialView: options.initialView || 'dayGridMonth',
            headerToolbar: {
                left: 'prev,next today',
                center: 'title',
                right: 'dayGridMonth,timeGridWeek,timeGridDay,listWeek'
            },
            editable: true,
            selectable: true,
            dayMaxEvents: 6,
            nowIndicator: true,
            eventDisplay: 'block',
            eventTimeFormat: { hour: 'numeric', minute: '2-digit', meridiem: 'short' },
            events: events,
            eventContent: function(arg) {
                const time = arg.timeText || '';
                const title = arg.event.title || '';
                const parts = title.split(' - ');
                const service = parts[0] || title;
                const patient = parts.slice(1).join(' - ') || '';
                return {
                    html: '<div class="fc-event-main-inner" style="padding:2px 4px;line-height:1.3;overflow:hidden;">' +
                        '<div style="font-weight:600;font-size:0.8rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">' + service + '</div>' +
                        (patient ? '<div style="font-size:0.7rem;opacity:0.9;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">' + patient + '</div>' : '') +
                        '</div>'
                };
            },
            eventClick: (info) => this.onEventClick(info),
            eventDrop: (info) => this.onEventDrop(info),
            eventResize: (info) => this.onEventResize(info),
            dateClick: (info) => this.onDateClick(info),
            ...options
        });
        this.calendar.render();
    },

    onEventClick(info) {
        const event = info.event;
        const props = event.extendedProps;
        const modal = document.getElementById('appointment-detail-modal');
        if (!modal) return;
        modal.querySelector('.modal-title').textContent = event.title;
        const body = modal.querySelector('.modal-body');
        const startStr = event.start ? event.start.toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' }) : 'N/A';
        const timeStr = event.start ? event.start.toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'}) : '';
        const endStr = event.end ? event.end.toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'}) : '';
        body.innerHTML = '<div style="display:flex;flex-direction:column;gap:12px;">' +
            '<div style="display:flex;justify-content:space-between;padding:10px 14px;background:var(--bg-secondary);border-radius:8px;"><span style="color:var(--text-secondary);font-size:0.85rem;">Reference</span><span style="font-weight:600;font-size:0.85rem;">' + (props.reference || 'N/A') + '</span></div>' +
            '<div style="display:flex;justify-content:space-between;padding:10px 14px;background:var(--bg-secondary);border-radius:8px;"><span style="color:var(--text-secondary);font-size:0.85rem;">Patient</span><span style="font-weight:600;font-size:0.85rem;">' + (props.patient || 'N/A') + '</span></div>' +
            '<div style="display:flex;justify-content:space-between;padding:10px 14px;background:var(--bg-secondary);border-radius:8px;"><span style="color:var(--text-secondary);font-size:0.85rem;">Service</span><span style="font-weight:600;font-size:0.85rem;">' + (props.service || 'N/A') + '</span></div>' +
            '<div style="display:flex;justify-content:space-between;padding:10px 14px;background:var(--bg-secondary);border-radius:8px;"><span style="color:var(--text-secondary);font-size:0.85rem;">Practitioner</span><span style="font-weight:600;font-size:0.85rem;">' + (props.practitioner || 'N/A') + '</span></div>' +
            '<div style="display:flex;justify-content:space-between;padding:10px 14px;background:var(--bg-secondary);border-radius:8px;"><span style="color:var(--text-secondary);font-size:0.85rem;">Date</span><span style="font-weight:600;font-size:0.85rem;">' + startStr + '</span></div>' +
            '<div style="display:flex;justify-content:space-between;padding:10px 14px;background:var(--bg-secondary);border-radius:8px;"><span style="color:var(--text-secondary);font-size:0.85rem;">Time</span><span style="font-weight:600;font-size:0.85rem;">' + timeStr + ' - ' + endStr + '</span></div>' +
            '<div style="display:flex;justify-content:space-between;padding:10px 14px;background:var(--bg-secondary);border-radius:8px;"><span style="color:var(--text-secondary);font-size:0.85rem;">Status</span><span><span class="badge badge-' + (props.statusColor || 'info') + '">' + (props.status || 'N/A') + '</span></span></div>' +
            (props.notes ? '<div style="padding:10px 14px;background:var(--bg-secondary);border-radius:8px;"><div style="color:var(--text-secondary);font-size:0.85rem;margin-bottom:4px;">Notes</div><div style="font-size:0.85rem;">' + props.notes + '</div></div>' : '') +
            '</div>';
        App.openModal('appointment-detail-modal');
    },

    onEventDrop(info) {
        const eventId = info.event.id;
        const newStart = info.event.start;
        const newEnd = info.event.end;
        App.fetchData('/api/appointments/' + eventId + '/reschedule', {
            method: 'POST',
            body: JSON.stringify({
                start_time: newStart.toISOString(),
                end_time: newEnd.toISOString()
            })
        }).then(function(data) {
            if (data.success) {
                App.showToast('Appointment rescheduled successfully', 'success');
            } else {
                info.revert();
                App.showToast(data.message || 'Failed to reschedule', 'error');
            }
        }).catch(function() { info.revert(); });
    },

    onEventResize(info) {
        var eventId = info.event.id;
        var newEnd = info.event.end;
        App.fetchData('/api/appointments/' + eventId + '/resize', {
            method: 'POST',
            body: JSON.stringify({ end_time: newEnd.toISOString() })
        }).then(function(data) {
            if (!data.success) { info.revert(); App.showToast('Failed to update', 'error'); }
        }).catch(function() { info.revert(); });
    },

    onDateClick(info) {
        window.location.href = '/admin/appointments/new?date=' + info.dateStr;
    },

    refreshEvents() {
        if (this.calendar) this.calendar.refetchEvents();
    },

    addEvent(event) {
        if (this.calendar) this.calendar.addEvent(event);
    },

    removeEvent(eventId) {
        if (this.calendar) {
            var event = this.calendar.getEventById(eventId);
            if (event) event.remove();
        }
    }
};
