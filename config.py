import os
from dotenv import load_dotenv

load_dotenv()

# Grafana settings
GRAFANA_URL = os.environ.get('GRAFANA_URL', 'http://localhost:3000')
GRAFANA_SERVICE_TOKEN = os.environ.get('GRAFANA_SERVICE_TOKEN', '')
GRAFANA_ORG_ID = os.environ.get('GRAFANA_ORG_ID', '1')
GRAFANA_COST_DASHBOARD_ID = os.environ.get('GRAFANA_COST_DASHBOARD_ID', '')

# Gemini API settings
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
GEMINI_MODEL_NAME = os.environ.get('GEMINI_MODEL_NAME', 'gemini-1.0-pro') # Default model
GEMINI_API_URL_TEMPLATE = os.environ.get(
    'GEMINI_API_URL_TEMPLATE',
    'https://generativelanguage.googleapis.com/v1/models/{model_name}:generateContent' # Default URL template
)

# Construct the final endpoint URL
GEMINI_API_ENDPOINT = GEMINI_API_URL_TEMPLATE.format(model_name=GEMINI_MODEL_NAME)

# Application settings
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key')

# Validate essential configuration
if not all([GRAFANA_URL, GRAFANA_SERVICE_TOKEN, GEMINI_API_KEY]):
    raise ValueError("Missing essential environment variables (Grafana URL/Token, Gemini API Key)")