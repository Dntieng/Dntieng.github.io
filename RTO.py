import os
import yaml
import requests  # Ensure requests is imported
import json  # Ensure json is imported
import base64
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Load configuration from YAML file
config_path = 'config.yaml'
if os.path.exists(config_path):
    with open(config_path, 'r') as file:
        config = yaml.safe_load(file)
    app.config['SQLALCHEMY_DATABASE_URI'] = config['flask']['database_url']
    app.config['SECRET_KEY'] = config['flask']['secret_key']
else:
    # Fallback configurations if config.yaml is not found
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///schedule.db')
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'fallback_secret_key')

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

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
        save_to_github(schedule_entry)
        return redirect(url_for('index'))
    except Exception as e:
        app.logger.error(f"Error submitting data: {str(e)}")
        return "An error occurred while submitting data."

def save_to_github(schedule_entry):
    try:
        # Access the GitHub token from the YAML configuration if available, else from environment variable
        github_token = config.get('github', {}).get('token', os.environ.get('GITHUB_TOKEN'))
        if not github_token:
            raise ValueError("GitHub token not found. Please set the GITHUB_TOKEN environment variable or configure it in config.yaml.")

        github_username = 'Dntieng'
        repository_name = 'Dntieng.github.io'
        branch_name = 'main'
        file_path = 'data/schedule.csv'
        commit_message = 'Update schedule.csv'

        url = f'https://api.github.com/repos/{github_username}/{repository_name}/contents/{file_path}'
        headers = {'Authorization': f'token {github_token}', 'Accept': 'application/vnd.github.v3+json'}

        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            file_content = json.loads(response.content.decode('utf-8'))
            content_decoded = base64.b64decode(file_content['content']).decode('utf-8')
            new_row = f"{schedule_entry.name},{schedule_entry.schedule},{schedule_entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
            updated_content = content_decoded + new_row
            updated_encoded_content = base64.b64encode(updated_content.encode()).decode()
            payload = {
                'message': commit_message,
                'content': updated_encoded_content,
                'branch': branch_name,
                'sha': file_content['sha']
            }
            update_response = requests.put(url, headers=headers, json=payload)
            if update_response.status_code not in [200, 201]:
                app.logger.error('Failed to update data on GitHub.')
        else:
            app.logger.error('Failed to fetch existing data from GitHub.')
    except Exception as e:
        app.logger.error(f"Error saving data to GitHub: {str(e)}")

# Initialize database
with app.app_context():
    db.create_all()

# Main entry
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
