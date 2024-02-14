import os
import yaml
import requests
import json
import base64
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# Define a function to load configurations
def load_configurations():
    config_path = 'config.yaml'
    default_config = {
        'flask': {
            'secret_key': 'fallback_secret_key',
        },
        'github': {
            'token': os.environ.get('GITHUB_TOKEN', ''),
            'username': 'Dntieng',
            'repository_name': 'Dntieng.github.io',
            'branch_name': 'main',
            'file_path': 'data/schedule.csv',
        }
    }

    if os.path.exists(config_path):
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
    else:
        print(f"No config.yaml found. Using default configurations.")
        config = default_config

    return config

config = load_configurations()

# Set Flask configurations
app.config['SECRET_KEY'] = config['flask']['secret_key']

@app.route('/')
def index():
    # This route can still display the form for submitting schedule entries
    # You might want to fetch the current content of `schedule.csv` from GitHub to display it
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit():
    try:
        name = request.form['name']
        preferred_dates = request.form.getlist('preferred_dates[]')
        timestamp = datetime.now()
        schedule_entry = f"{name},{', '.join(preferred_dates)},{timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
        save_to_github(schedule_entry)
        return redirect(url_for('index'))
    except Exception as e:
        app.logger.error(f"Error submitting data: {str(e)}")
        return "An error occurred while submitting data."

def save_to_github(schedule_entry):
    try:
        github_config = config['github']
        url = f"https://api.github.com/repos/{github_config['username']}/{github_config['repository_name']}/contents/{github_config['file_path']}"
        headers = {
            'Authorization': f"token {github_config['token']}",
            'Accept': 'application/vnd.github.v3+json'
        }

        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            file_content = json.loads(response.content.decode('utf-8'))
            content_decoded = base64.b64decode(file_content['content']).decode('utf-8')
            updated_content = content_decoded + schedule_entry
            updated_encoded_content = base64.b64encode(updated_content.encode()).decode()
            payload = {
                'message': 'Update schedule.csv',
                'content': updated_encoded_content,
                'branch': github_config['branch_name'],
                'sha': file_content['sha']
            }
            update_response = requests.put(url, headers=headers, json=payload)
            if update_response.status_code not in [200, 201]:
                app.logger.error('Failed to update data on GitHub.')
        else:
            app.logger.error('Failed to fetch existing data from GitHub.')
    except Exception as e:
        app.logger.error(f"Error saving data to GitHub: {str(e)}")
