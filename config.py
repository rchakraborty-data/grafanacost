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
# Corrected Gemini API Endpoint using v1beta and a standard model
GEMINI_API_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro-latest:generateContent"

# Databricks SQL Warehouse settings
DATABRICKS_SERVER_HOSTNAME = os.environ.get('DATABRICKS_SERVER_HOSTNAME', '')
DATABRICKS_HTTP_PATH = os.environ.get('DATABRICKS_HTTP_PATH', '')
DATABRICKS_ACCESS_TOKEN = os.environ.get('DATABRICKS_ACCESS_TOKEN', '')

# MCP Server settings
USE_MCP = os.environ.get('USE_MCP', 'True').lower() == 'true'
MCP_HOST = os.environ.get('MCP_HOST', 'localhost')
MCP_PORT = int(os.environ.get('MCP_PORT', '8090'))
START_MCP_SERVER = os.environ.get('START_MCP_SERVER', 'True').lower() == 'true'

# Application settings
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key')

# Validate essential configuration
if not all([GRAFANA_URL, GRAFANA_SERVICE_TOKEN, GEMINI_API_KEY]):
    raise ValueError("Missing essential environment variables (Grafana URL/Token, Gemini API Key)")