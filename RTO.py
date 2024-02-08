import os
import csv
from io import StringIO
from datetime import datetime
import requests
import json
import base64
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

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
        save_to_github()
        return redirect(url_for('index'))
    except Exception as e:
        app.logger.error(f"Error submitting data: {str(e)}")
        return "An error occurred while submitting data."

def save_to_github():
    github_username = os.environ.get('GITHUB_USERNAME', 'DefaultUsername')
    repository_name = os.environ.get('GITHUB_REPOSITORY', 'DefaultRepository')
    branch_name = 'main'
    file_path = 'data/schedule.csv'
    commit_message = 'Update schedule.csv'
    access_token = os.environ.get('GITHUB_ACCESS_TOKEN')

    url = f'https://api.github.com/repos/{github_username}/{repository_name}/contents/{file_path}'
    
    schedules = Schedule.query.all()
    rows = [['Name', 'Schedule', 'Timestamp']]
    for schedule in schedules:
        rows.append([schedule.name, schedule.schedule, schedule.timestamp.strftime('%Y-%m-%d %H:%M:%S')])

    csv_data = StringIO()
    writer = csv.writer(csv_data)
    writer.writerows(rows)
    
    headers = {
        'Authorization': f'token {access_token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        file_content = json.loads(response.content.decode('utf-8'))
        file_content['content'] = base64.b64encode(csv_data.getvalue().encode()).decode()
        payload = {
            'message': commit_message,
            'content': file_content['content'],
            'branch': branch_name,
            'sha': file_content['sha']
        }
        response = requests.put(url, headers=headers, json=payload)
    else:
        payload = {
            'message': commit_message,
            'content': base64.b64encode(csv_data.getvalue().encode()).decode(),
            'branch': branch_name
        }
        response = requests.put(url, headers=headers, json=payload)

    if response.status_code in [200, 201]:
        print('Data saved to GitHub successfully.')
    else:
        print('Failed to save data to GitHub.')
        print(response.content)

with app.app_context():
    db.create_all()
