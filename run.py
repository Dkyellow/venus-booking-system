import os
from app import create_app
from app.extensions import db
from apscheduler.schedulers.background import BackgroundScheduler

app = create_app(os.getenv('FLASK_ENV', 'development'))

scheduler = BackgroundScheduler()
scheduler.start()
app.scheduler = scheduler

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
