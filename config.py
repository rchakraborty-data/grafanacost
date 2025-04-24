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
# Read the API URL from environment, then use it to construct the endpoint
GEMINI_API_URL = os.environ.get('GEMINI_API_URL', 'https://generativelanguage.googleapis.com/v1beta')
# Define the full endpoint that will be used by the code
GEMINI_API_ENDPOINT = GEMINI_API_URL  # For backward compatibility with existing code
# Model name will be set dynamically or in the calling function
GEMINI_MODEL_NAME = os.environ.get('GEMINI_MODEL_NAME', 'gemini-2.0-flash-thinking-exp')

# Gemini API advanced configuration
GEMINI_TEMPERATURE = float(os.environ.get('GEMINI_TEMPERATURE', '0.2'))  # Lower temperature for more precise recommendations
GEMINI_TOP_P = float(os.environ.get('GEMINI_TOP_P', '0.95'))  # Slightly lower top_p for more focused outputs
GEMINI_TOP_K = int(os.environ.get('GEMINI_TOP_K', '40'))     # Higher top_k for better SQL optimizations
GEMINI_MAX_OUTPUT_TOKENS = int(os.environ.get('GEMINI_MAX_OUTPUT_TOKENS', '8192'))  # Increased token limit for detailed SQL recommendations
# Gemini 2.5 specific parameters
GEMINI_RESPONSE_MIME_TYPE = os.environ.get('GEMINI_RESPONSE_MIME_TYPE', 'text/plain')
GEMINI_SAFETY_SETTINGS = os.environ.get('GEMINI_SAFETY_SETTINGS', '{}')

# Databricks SQL Warehouse settings
DATABRICKS_SERVER_HOSTNAME = os.environ.get('DATABRICKS_SERVER_HOSTNAME', '')
DATABRICKS_HTTP_PATH = os.environ.get('DATABRICKS_HTTP_PATH', '')
DATABRICKS_ACCESS_TOKEN = os.environ.get('DATABRICKS_ACCESS_TOKEN', '')

# MCP Server settings
USE_MCP = os.environ.get('USE_MCP', 'True').lower() == 'true'
MCP_HOST = os.environ.get('MCP_HOST', 'localhost')
MCP_PORT = int(os.environ.get('MCP_PORT', '8090'))
START_MCP_SERVER = os.environ.get('START_MCP_SERVER', 'True').lower() == 'true'

# Email settings
MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
MAIL_PORT = int(os.environ.get('MAIL_PORT', '587'))
MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'False').lower() == 'true'
MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')
MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', '')
USE_RECIPIENT_AS_SENDER = os.environ.get('USE_RECIPIENT_AS_SENDER', 'False').lower() == 'true'

# Application settings
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key')

# Validate essential configuration
if not all([GRAFANA_URL, GRAFANA_SERVICE_TOKEN, GEMINI_API_KEY]):
    raise ValueError("Missing essential environment variables (Grafana URL/Token, Gemini API Key)")