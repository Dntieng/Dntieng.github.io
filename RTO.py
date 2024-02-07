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
        # After saving to the database, also save to GitHub
        save_to_github()
        return redirect(url_for('index'))
    except Exception as e:
        app.logger.error(f"Error submitting data: {str(e)}")
        return "An error occurred while submitting data."

# Function to save data to GitHub repository
def save_to_github():
    try:
        # GitHub repository information
        github_username = 'Dntieng'
        repository_name = 'Dntieng.github.io'
        branch_name = 'main'
        file_path = 'data/schedule.csv'
        commit_message = 'Update schedule.csv'

        # GitHub API URL
        url = f'https://api.github.com/repos/{github_username}/{repository_name}/contents/{file_path}'

        # GitHub personal access token
        access_token = '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'

        # Data to be saved (fetch from the database)
        schedules = Schedule.query.all()
        rows = [['Name', 'Schedule', 'Timestamp']]
        for schedule in schedules:
            rows.append([schedule.name, schedule.schedule, schedule.timestamp.strftime('%Y-%m-%d %H:%M:%S')])

        # Convert data to CSV format
        csv_data = StringIO()
        writer = csv.writer(csv_data)
        writer.writerows(rows)

        # Headers with authorization
        headers = {
            'Authorization': f'token {access_token}',
            'Accept': 'application/vnd.github.v3+json'
        }

        # Check if file exists
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            # File exists, update it
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
            # File does not exist, create it
            payload = {
                'message': commit_message,
                'content': base64.b64encode(csv_data.getvalue().encode()).decode(),
                'branch': branch_name
            }
            response = requests.put(url, headers=headers, json=payload)

        # Check response
        if response.status_code == 200:
            print('Data saved to GitHub successfully.')
        else:
            print('Failed to save data to GitHub.')
            print(response.content)  # Print response content for debugging
    except Exception as e:
        app.logger.error(f"Error saving data to GitHub: {str(e)}")

# Create database tables within application context
with app.app_context():
    db.create_all()

# Run the app
if __name__ == "__main__":
    # Use PORT provided by Heroku's environment variables
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
