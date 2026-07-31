# Venus Medical Clinic - Booking System

A modern, production-ready Multi-Service Clinic Booking System built with Flask, featuring a Calendly-style public booking experience, comprehensive admin dashboard, and patient portal.

## Features

### Public Booking (Calendly-style)
- Multi-step booking flow: Service → Practitioner → Date/Time → Patient Info → Confirmation
- Real-time availability checking
- Automatic booking reference generation
- Google Calendar integration
- Responsive design for all devices

### Admin Dashboard
- Real-time appointment statistics
- Interactive calendar with FullCalendar.js (Month/Week/Day views)
- Drag-and-drop appointment management
- Service and practitioner management
- Patient management
- Reports with Chart.js visualizations
- Clinic settings configuration
- Notification management

### Patient Portal
- View upcoming and past appointments
- Appointment history
- Profile management
- Quick rebooking

### Smart Scheduling Engine
- Dynamic time slot calculation
- Double-booking prevention
- Buffer time support
- Practitioner leave management
- Blocked time handling
- Holiday support
- Multi-day scheduling

### Notifications
- Email notifications (confirmation, reminder, rescheduled, cancelled)
- WhatsApp integration
- Google Calendar sync
- Automated reminder scheduling (48h, 24h, 2h before)

### Security
- Role-based access control (Admin, Receptionist, Patient)
- Password hashing with Werkzeug
- CSRF protection
- Rate limiting
- Secure session management

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Python Flask |
| ORM | SQLAlchemy |
| Auth | Flask-Login |
| Migrations | Flask-Migrate |
| Email | Flask-Mail |
| Forms | Flask-WTF |
| Scheduler | APScheduler |
| Frontend | Bootstrap 5, Vanilla JS |
| Calendar | FullCalendar.js |
| Charts | Chart.js |
| Database | PostgreSQL / MySQL / SQLite |

## Installation

### Prerequisites
- Python 3.9+
- pip
- PostgreSQL (or SQLite for development)

### Setup

1. **Clone the repository**
```bash
cd "venus booking system"
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment**
```bash
copy .env.example .env
```
Edit `.env` with your settings.

5. **Initialize database**
```bash
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

6. **Seed database**
```bash
python -m seeds.seed_data
```

7. **Run development server**
```bash
flask run
```

## Demo Accounts

| Role | Email | Password |
|------|-------|----------|
| Administrator | admin@venusclinic.com | admin123 |
| Receptionist | reception@venusclinic.com | reception123 |

## Project Structure

```
venus booking system/
├── app/
│   ├── __init__.py          # App factory
│   ├── config.py            # Configuration
│   ├── extensions.py        # Flask extensions
│   ├── models/              # SQLAlchemy models
│   ├── auth/                # Authentication
│   ├── main/                # Public pages
│   ├── admin/               # Admin dashboard
│   ├── booking/             # Public booking
│   ├── patient/             # Patient portal
│   ├── api/                 # REST API
│   ├── services/            # Business logic
│   ├── templates/           # Jinja2 templates
│   ├── static/              # CSS, JS, images
│   └── utils/               # Helpers, decorators
├── migrations/              # Database migrations
├── seeds/                   # Seed data
├── tests/                   # Test files
├── requirements.txt
├── run.py                   # Entry point
└── gunicorn_config.py       # Production config
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/services` | List all services |
| GET | `/api/services/<id>/practitioners` | Service practitioners |
| GET | `/api/booking/available-dates` | Available dates |
| GET | `/api/booking/slots` | Available time slots |
| POST | `/api/booking/create` | Create booking |
| GET | `/api/calendar/events` | Calendar events |
| GET | `/api/dashboard/stats` | Dashboard statistics |

## Deployment

### Using Gunicorn
```bash
gunicorn -c gunicorn_config.py run:app
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `FLASK_APP` | App entry point | `run.py` |
| `FLASK_ENV` | Environment | `development` |
| `FLASK_SECRET_KEY` | Secret key | Required |
| `DATABASE_URL` | Database URL | `sqlite:///venus_booking.db` |
| `MAIL_SERVER` | SMTP server | `smtp.gmail.com` |
| `MAIL_USERNAME` | SMTP username | Required |
| `MAIL_PASSWORD` | SMTP password | Required |
| `GOOGLE_CALENDAR_CLIENT_ID` | Google OAuth client ID | Optional |
| `GOOGLE_CALENDAR_CLIENT_SECRET` | Google OAuth secret | Optional |
| `WHATSAPP_API_URL` | WhatsApp API endpoint | Optional |

## License

MIT License
