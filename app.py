from flask import Flask, render_template, request, redirect, url_for, jsonify
import os
import requests
import json
import re  # Import the regex module
from grafana_api import GrafanaAPI
from config import DEBUG, SECRET_KEY, GEMINI_API_KEY, GEMINI_API_ENDPOINT

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
app.config['DEBUG'] = DEBUG

grafana_api = GrafanaAPI()

def get_insights_from_gemini(dashboard_data):
    """Sends dashboard data to Gemini API and returns insights."""
    if not GEMINI_API_KEY:
        return "Error: Gemini API Key not configured."

    headers = {
        'Content-Type': 'application/json',
    }
    # Prepare the prompt for Gemini
    prompt = f"Analyze the following Grafana dashboard JSON definition and provide insights and recommendations regarding cost optimization, potential issues, or interesting patterns. Focus on actionable advice based on the dashboard structure, panels, and queries if available.\n\nDashboard JSON:\n```json\n{json.dumps(dashboard_data, indent=2)}\n```\n\nInsights and Recommendations:"

    data = {
        "contents": [{
            "parts": [{
                "text": prompt
            }]
        }]
    }
    
    try:
        response = requests.post(
            f"{GEMINI_API_ENDPOINT}?key={GEMINI_API_KEY}", 
            headers=headers, 
            json=data,
            timeout=120
        )
        response.raise_for_status()
        
        result = response.json()
        
        if 'candidates' in result and len(result['candidates']) > 0:
            content = result['candidates'][0].get('content', {})
            if 'parts' in content and len(content['parts']) > 0:
                return content['parts'][0].get('text', "Error: Could not extract insights from Gemini response.")
        return "Error: Unexpected response format from Gemini API."

    except requests.exceptions.RequestException as e:
        return f"Error calling Gemini API: {str(e)}"
    except Exception as e:
        return f"An unexpected error occurred while processing Gemini response: {str(e)}"

@app.route('/')
def index():
    """Renders the main page with the URL input form."""
    return render_template('index.html')

@app.route('/analyze-url', methods=['POST'])
def analyze_url():
    """Handles the form submission, extracts UID, and redirects."""
    dashboard_url = request.form.get('dashboard_url')
    if not dashboard_url:
        return render_template('index.html', error="Dashboard URL is required.")

    # Extract UID using regex: looks for content between /d/ and the next /
    match = re.search(r'/d/([^/]+)/', dashboard_url)
    if match:
        uid = match.group(1)
        return redirect(url_for('view_dashboard', uid=uid))
    else:
        return render_template('index.html', error="Could not extract dashboard UID from the provided URL. Ensure it follows the format '.../d/UID/...' ")

@app.route('/dashboard/<uid>')
def view_dashboard(uid):
    """Fetches dashboard, gets insights from Gemini, and displays them."""
    try:
        dashboard_details = grafana_api.get_dashboard(uid)
        dashboard_data = dashboard_details.get('dashboard', {})
        dashboard_title = dashboard_data.get('title', 'Dashboard')

        if not dashboard_data:
             return render_template('error.html', error=f"Could not fetch dashboard details for UID: {uid}")

        insights = get_insights_from_gemini(dashboard_data)
        
        return render_template(
            'dashboard.html', 
            dashboard_title=dashboard_title, 
            insights=insights
        )
    except Exception as e:
        app.logger.error(f"Error processing dashboard {uid}: {str(e)}", exc_info=True)
        return render_template('error.html', error=f"An error occurred: {str(e)}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))