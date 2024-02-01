import os
import csv
import calendar
from io import StringIO
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, jsonify, Response
from flask_sqlalchemy import SQLAlchemy
import logging

# Initialize Flask app
app = Flask(__name__)

# Configure SQLAlchemy for database management
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///schedule.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your_secret_key_here')

# Initialize SQLAlchemy database instance
db = SQLAlchemy(app)

# Define Schedule model
class Schedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    schedule = db.Column(db.String(200), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.now)

# Define routes
@app.route('/')
def index():
    schedules = Schedule.query.all()
    names_count = {}
    for schedule in schedules:
        names_count[schedule.name] = names_count.get(schedule.name, 0) + 1
    return render_template('index.html', schedules=schedules, names_count=names_count)

@app.route('/submit', methods=['POST'])
def submit():
    try:
        name = request.form['name']
        preferred_dates = request.form.getlist('preferred_dates[]')
        timestamp = datetime.now()
        schedule_entry = Schedule(name=name, schedule=', '.join(preferred_dates), timestamp=timestamp)
        db.session.add(schedule_entry)
        db.session.commit()
        return redirect(url_for('index'))
    except Exception as e:
        app.logger.error(f"Error submitting data: {str(e)}")
        return "An error occurred while submitting data."

# Other routes (export_csv, delete_schedule, get_calendar_data) remain unchanged

# Create database tables within application context
with app.app_context():
    db.create_all()

# Run the app
if __name__ == "__main__":
    # Use PORT provided by Heroku's environment variables
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
