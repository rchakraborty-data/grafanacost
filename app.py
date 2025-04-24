from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file, session
import os
import requests
import json
import re
import pandas as pd
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta  # For month/year parsing
from grafana_api import GrafanaAPI
from databricks_client import execute_databricks_query  # Import the function from databricks_client
from config import (
    DEBUG, SECRET_KEY, GEMINI_API_KEY, GEMINI_API_ENDPOINT, GEMINI_MODEL_NAME, 
    USE_MCP, MCP_HOST, MCP_PORT, START_MCP_SERVER, GEMINI_TEMPERATURE, 
    GEMINI_TOP_P, GEMINI_TOP_K, GEMINI_MAX_OUTPUT_TOKENS, GEMINI_RESPONSE_MIME_TYPE,
    GEMINI_SAFETY_SETTINGS
)
import markdown  # Added for converting Markdown to HTML
import tempfile
import logging
import threading
from mcp_client import MCPClient  # Import the MCP client
from grafana_mcp_server import start_mcp_server  # Import the MCP server starter from renamed module
import io
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
import hashlib  # For generating cache keys
from functools import lru_cache  # For in-memory caching
import pickle  # For file-based caching
import time  # For cache expiration
import concurrent.futures  # For parallel processing

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
app.config['DEBUG'] = DEBUG

# Cache directory setup
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache')
os.makedirs(CACHE_DIR, exist_ok=True)

# Cache expiration time (24 hours)
CACHE_EXPIRATION = 24 * 60 * 60  # seconds

def generate_cache_key(data):
    """Generate a consistent cache key from input data."""
    if isinstance(data, dict):
        # For dashboard data, use consistent serialization
        s = json.dumps(data, sort_keys=True)
    elif isinstance(data, str):
        s = data
    else:
        # For query results, serialize in a consistent way
        s = str(data)
    
    # Create a hash of the content for the cache key
    return hashlib.md5(s.encode('utf-8')).hexdigest()

def get_from_cache(cache_key):
    """Retrieve data from cache if it exists and is not expired."""
    # Caching disabled to avoid stale model references
    return None

def save_to_cache(cache_key, data):
    """Save data to cache with current timestamp."""
    # Caching disabled to avoid stale model references
    return

def get_insights_from_gemini_async(dashboard_data, query_results=None):
    """
    Asynchronously sends dashboard data OR query results to Gemini API and returns a future.
    This allows the caller to do other work while waiting for the API response.
    """
    # Create a Future object to store the result
    future = concurrent.futures.Future()
    
    # Start a thread to do the actual work
    def worker():
        try:
            result = get_insights_from_gemini(dashboard_data, query_results)
            future.set_result(result)
        except Exception as e:
            future.set_exception(e)
    
    thread = threading.Thread(target=worker)
    thread.daemon = True
    thread.start()
    
    return future

# Testing mode for Gemini API
GEMINI_TESTING_MODE = False
GEMINI_MOCK_RESPONSE = "## Mock Insights for Testing\n\nThis is a mock response for testing purposes. No actual Gemini API call was made."

def set_gemini_testing_mode(enable=False, mock_response=None):
    """
    Enable or disable testing mode for Gemini API calls.
    
    Args:
        enable (bool): Whether to enable testing mode
        mock_response (str): Mock response to return instead of calling Gemini API
    """
    global GEMINI_TESTING_MODE, GEMINI_MOCK_RESPONSE
    GEMINI_TESTING_MODE = enable
    if mock_response:
        GEMINI_MOCK_RESPONSE = mock_response
    
    if enable:
        logger.info("[TEST MODE] Gemini API calls are now in testing mode")
        if mock_response:
            logger.info(f"[TEST MODE] Mock response has been set ({len(mock_response)} characters)")

grafana_api = GrafanaAPI()

# Add MCP-specific code to initialize and start the MCP server if enabled
mcp_client = None

if USE_MCP:
    logger.info("MCP integration is enabled")
    
    # Initialize MCP client
    mcp_client = MCPClient(host=MCP_HOST, port=MCP_PORT)
    
    # Start MCP server in a background thread if enabled
    if START_MCP_SERVER:
        def run_mcp_server():
            logger.info(f"Starting MCP server on {MCP_HOST}:{MCP_PORT}")
            start_mcp_server(host=MCP_HOST, port=MCP_PORT)
            
        mcp_thread = threading.Thread(target=run_mcp_server, daemon=True)
        mcp_thread.start()
        logger.info("MCP server thread started")
else:
    logger.info("MCP integration is disabled")

# Global testing mode flag for Gemini API
GEMINI_TESTING_MODE = False
GEMINI_MOCK_RESPONSE = "## Mock Insights from Gemini API\nThis is a mock response used during testing to avoid real API calls."

def set_gemini_testing_mode(enable=True, mock_response=None):
    """
    Enable or disable testing mode for Gemini API with optional mock response.
    
    In testing mode, no real Gemini API calls are made. Instead, predefined
    mock responses are returned.
    
    Args:
        enable: Whether to enable testing mode
        mock_response: Optional custom mock response to return
    """
    global GEMINI_TESTING_MODE, GEMINI_MOCK_RESPONSE
    GEMINI_TESTING_MODE = enable
    if mock_response:
        GEMINI_MOCK_RESPONSE = mock_response
    logger.info(f"Gemini API testing mode {'enabled' if enable else 'disabled'}")

# --- Helper Function for Time Range Parsing ---
def parse_grafana_time_range(time_from, time_to, column_name):
    """
    Parses Grafana's time range (basic relative and absolute) into an SQL WHERE clause.
    Returns a tuple: (sql_condition, error_message or None)
    """
    now = datetime.utcnow()
    sql_conditions = []
    error_msg = None

    # --- Parse 'from' time ---
    dt_from = None
    if time_from.startswith('now-'):
        match = re.match(r'now-(\d+)([hdwmMy])(/([hdwmMy]))?', time_from)
        if match:
            value = int(match.group(1))
            unit = match.group(2)

            delta = None
            if unit == 'h': delta = timedelta(hours=value)
            elif unit == 'd': delta = timedelta(days=value)
            elif unit == 'w': delta = timedelta(weeks=value)
            elif unit == 'M': delta = relativedelta(months=value)
            elif unit == 'y': delta = relativedelta(years=value)
            
            if delta:
                dt_from = now - delta
            else:
                error_msg = f"Unsupported relative time unit: {unit}"
        else:
            error_msg = f"Could not parse relative 'from' time: {time_from}"
    elif time_from == 'now':
         dt_from = now
    else:
        try:
            if time_from.isdigit():
                 dt_from = datetime.utcfromtimestamp(int(time_from) / 1000.0)
            else:
                 dt_from = datetime.fromisoformat(time_from.replace('Z', '+00:00'))
        except ValueError:
             error_msg = f"Could not parse absolute 'from' time: {time_from}"

    # --- Parse 'to' time ---
    dt_to = None
    if time_to == 'now':
        dt_to = now
    elif time_to.startswith('now-'):
        match = re.match(r'now-(\d+)([hdwmMy])(/([hdwmMy]))?', time_to)
        if match:
            value = int(match.group(1))
            unit = match.group(2)
            delta = None
            if unit == 'h': delta = timedelta(hours=value)
            elif unit == 'd': delta = timedelta(days=value)
            elif unit == 'w': delta = timedelta(weeks=value)
            elif unit == 'M': delta = relativedelta(months=value)
            elif unit == 'y': delta = relativedelta(years=value)
            if delta:
                dt_to = now - delta
            else:
                 error_msg = error_msg or f"Unsupported relative time unit: {unit}"
        else:
             error_msg = error_msg or f"Could not parse relative 'to' time: {time_to}"
    else:
        try:
            if time_to.isdigit():
                 dt_to = datetime.utcfromtimestamp(int(time_to) / 1000.0)
            else:
                 dt_to = datetime.fromisoformat(time_to.replace('Z', '+00:00'))
        except ValueError:
             error_msg = error_msg or f"Could not parse absolute 'to' time: {time_to}"

    # --- Build SQL Condition ---
    if dt_from:
        sql_conditions.append(f"{column_name} >= '{dt_from.strftime('%Y-%m-%d %H:%M:%S')}'")
    if dt_to:
        sql_conditions.append(f"{column_name} <= '{dt_to.strftime('%Y-%m-%d %H:%M:%S')}'")

    if sql_conditions:
        return (" AND ".join(sql_conditions), error_msg)
    else:
        return ("1=1", error_msg or "Failed to parse time range, using 1=1")

def get_insights_from_gemini(dashboard_data, query_results=None):
    """Sends dashboard data OR query results to Gemini API and returns insights."""
    # Check if we're in testing mode
    if GEMINI_TESTING_MODE:
        logger.info("[TEST MODE] Returning mock response instead of calling Gemini API")
        return GEMINI_MOCK_RESPONSE
        
    if not GEMINI_API_KEY:
        return "Error: Gemini API Key not configured."

    headers = {
        'Content-Type': 'application/json',
    }

    # Build the prompt based on the provided data
    prompt = ""
    if query_results:
        # Build a prompt for analyzing query results
        prompt = (
            "Analyze the following Grafana dashboard and Databricks query results to provide specific "
            "cost optimization recommendations. Focus on query efficiency, resource utilization, "
            "and storage optimization patterns that can reduce costs.\n\n"
            "DASHBOARD STRUCTURE:\n"
            f"{json.dumps(dashboard_data, indent=2)}\n\n"
            "QUERY RESULTS:\n"
        )
        
        # Format each query result
        for panel_name, result in query_results.items():
            prompt += f"\nPanel: {panel_name}\n"
            if isinstance(result, pd.DataFrame):
                # Convert DataFrame to string representation
                prompt += f"Rows: {len(result)}\n"
                prompt += f"Columns: {', '.join(result.columns)}\n"
                if len(result) > 0:
                    # Include a sample of the data (first 5 rows)
                    prompt += "Sample data:\n"
                    prompt += result.head(5).to_string() + "\n"
                    
                    # Add summary statistics for numerical columns
                    num_cols = result.select_dtypes(include=['number']).columns
                    if len(num_cols) > 0:
                        prompt += "\nSummary statistics for numerical columns:\n"
                        prompt += result[num_cols].describe().to_string() + "\n"
            else:
                # Handle error case or non-DataFrame results
                prompt += f"Error or no data: {str(result)}\n"
        
        # Add specific instructions for cost optimization
        prompt += (
            "\n\nPROVIDE COST OPTIMIZATION RECOMMENDATIONS SPECIFICALLY ADDRESSING:\n"
            "1. Inefficient query patterns and how to rewrite them\n"
            "2. Resource utilization issues (compute, memory, storage)\n"
            "3. Data skew or distribution problems\n"
            "4. Overprovisioning of resources\n"
            "5. Opportunities for caching or materialization\n"
            "6. Specific configuration changes with parameter values\n"
            "\nFORMAT EACH RECOMMENDATION AS:\n"
            "## [Recommendation Title]\n"
            "[Detailed explanation]\n\n"
            "### SQL Optimization (if applicable):\n"
            "```sql\n"
            "-- Original query\n"
            "[ORIGINAL SQL]\n\n"
            "-- Optimized query\n"
            "[OPTIMIZED SQL]\n"
            "```\n\n"
            "### Implementation Steps:\n"
            "1. [Specific step with exact values/code]\n"
            "2. [Next step]\n\n"
            "### Cost-Benefit Impact:\n"
            "- **Monthly Savings**: $X,XXX\n"
            "- **Implementation Effort**: [Low/Medium/High]\n"
            "- **Priority**: [High/Medium/Low]\n"
        )
    else:
        # For dashboard-only analysis
        prompt = (
            "Analyze this Grafana dashboard structure and provide specific "
            "cost optimization recommendations for Databricks usage. Focus on "
            "query efficiency, resource utilization, and storage optimization.\n\n"
            f"Dashboard: {json.dumps(dashboard_data, indent=2)}"
        )

    # Use the experimental Gemini model and ensure we're using v1beta endpoint
    model_name = "gemini-2.0-flash-thinking-exp"
    
    # Ensure we're using the v1beta endpoint - replace "v1" with "v1beta" if needed
    api_base = GEMINI_API_ENDPOINT
    if "/v1/" in api_base:
        api_base = api_base.replace("/v1/", "/v1beta/")
    elif api_base.endswith("/v1"):
        api_base = api_base.replace("/v1", "/v1beta") 
    elif not ("/v1beta" in api_base):
        # If neither v1 nor v1beta is in the URL, append v1beta
        if api_base.endswith("/"):
            api_base = f"{api_base}v1beta"
        else:
            api_base = f"{api_base}/v1beta"
            
    # Now construct the full endpoint URL
    api_endpoint = f"{api_base}/models/{model_name}:generateContent"
    
    logger.info(f"Using experimental Gemini model: {model_name}")
    logger.info(f"Using API endpoint: {api_endpoint}")
    
    # Use parameters compatible with the API (may need adjustment for experimental models)
    data = {
        "contents": [{
            "parts": [{
                "text": prompt
            }]
        }],
        "generationConfig": {
            "temperature": GEMINI_TEMPERATURE,
            "topP": GEMINI_TOP_P,
            "topK": GEMINI_TOP_K,
            "maxOutputTokens": GEMINI_MAX_OUTPUT_TOKENS
        }
    }
    
    try:
        # Log the model name and endpoint being used
        logger.info(f"Calling Gemini API with model: {model_name} via endpoint: {api_endpoint}")
        # Add a timeout to prevent hanging on slow API responses
        response = requests.post(
            f"{api_endpoint}?key={GEMINI_API_KEY}", 
            headers=headers, 
            json=data,
            timeout=120  # Increased timeout for better responses
        )
        
        # Check for successful response
        if response.status_code == 200:
            result = response.json()
            
            # Extract the content from the response based on the Gemini API response structure
            if 'candidates' in result and len(result['candidates']) > 0:
                content = result['candidates'][0].get('content', {})
                if 'parts' in content and len(content['parts']) > 0:
                    part = content['parts'][0]
                    if isinstance(part, dict) and 'text' in part:
                        return part['text']
                    elif isinstance(part, str):
                        return part
                    else:
                        return str(part)
            
            # If we couldn't extract content via expected structure, return an error
            logger.error(f"Unexpected response structure from Gemini API: {json.dumps(result)[:500]}")
            return "Error: Received unexpected response structure from Gemini API."
        else:
            # Handle error responses
            error_message = f"Gemini API error: {response.status_code}"
            error_detail = ""
            
            try:
                error_json = response.json()
                if 'error' in error_json:
                    error_detail = f": {error_json['error'].get('message', '')}"
            except:
                error_detail = f": {response.text[:200]}..."
            
            logger.error(f"{error_message}{error_detail}")
            logger.error(f"API endpoint used: {api_endpoint}")
            return f"Error calling Gemini API: {response.status_code} {error_detail}"
    except requests.exceptions.Timeout:
        logger.error("Gemini API request timed out after 120 seconds")
        return "Error: Gemini API request timed out. Please try again later or with a simpler dashboard."
    except requests.exceptions.RequestException as e:
        logger.error(f"Error calling Gemini API: {str(e)}")
        return f"Error calling Gemini API: {str(e)}"
    except Exception as e:
        logger.error(f"An unexpected error occurred while processing Gemini response: {str(e)}")
        return f"An unexpected error occurred while processing Gemini response: {str(e)}"

def get_insights_from_mcp(dashboard_data, query_results=None):
    """Gets insights using the MCP server instead of direct Gemini API calls.
    This function provides more structured analysis through the MCP protocol.
    """
    global mcp_client
    
    if not mcp_client:
        logger.error("MCP client not initialized but get_insights_from_mcp was called")
        return "Error: MCP client not initialized."
    
    try:
        logger.info("Getting insights using MCP")
        
        if query_results:
            # First analyze the query results
            analysis_results = mcp_client.analyze_query_results(query_results)
            
            # Then generate recommendations based on both dashboard and analysis
            recommendations = mcp_client.get_recommendations_from_analysis(
                dashboard_data, analysis_results
            )
            
            return recommendations
        else:
            # Get recommendations based only on dashboard structure
            analysis = mcp_client.get_dashboard_analysis(dashboard_data)
            return analysis.get("recommendations", "No recommendations available from MCP server.")
    
    except Exception as e:
        logger.error(f"Error using MCP for analysis: {str(e)}", exc_info=True)
        # Fall back to direct Gemini API if MCP fails
        logger.info("Falling back to direct Gemini API due to MCP error")
        return get_insights_from_gemini(dashboard_data, query_results)

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

    match = re.search(r'/d/([^/]+)/', dashboard_url)
    if match:
        uid = match.group(1)
        return redirect(url_for('view_dashboard', uid=uid))
    else:
        return render_template('index.html', error="Could not extract dashboard UID from the provided URL. Ensure it follows the format '.../d/UID/...' ")

@app.route('/dashboard/<uid>')
def view_dashboard(uid):
    """Fetches dashboard, executes Databricks queries, gets insights from AI, and displays them."""
    try:
        # Start a timer to measure performance
        start_time = time.time()
        
        dashboard_details = grafana_api.get_dashboard(uid)
        dashboard_data = dashboard_details.get('dashboard', {})
        dashboard_title = dashboard_data.get('title', 'Dashboard')

        if not dashboard_data:
             return render_template('error.html', error=f"Could not fetch dashboard details for UID: {uid}")

        # Generate cache key even though caching is disabled - used as a reference in code later
        dashboard_cache_key = generate_cache_key(dashboard_data)
        
        # Skip caching completely - always perform a fresh analysis

        # Continue with normal processing
        template_variables = {var['name']: var.get('current', {}).get('value', '') 
                              for var in dashboard_data.get('templating', {}).get('list', [])}
        time_from = dashboard_data.get('time', {}).get('from', 'now-6h')
        time_to = dashboard_data.get('time', {}).get('to', 'now')

        databricks_results = {}
        panels = dashboard_data.get('panels', [])
        databricks_datasource_uid = "ddjmooc1so54wc"

        # Process panels and execute queries (existing code)
        for panel in panels:
            datasource_info = panel.get('datasource')
            panel_title = panel.get('title', 'Untitled Panel')
            targets = panel.get('targets', [])

            panel_uses_databricks = False
            if isinstance(datasource_info, dict) and datasource_info.get('uid') == databricks_datasource_uid:
                 panel_uses_databricks = True

            if panel_uses_databricks:
                app.logger.info(f"Found Databricks panel (UID: {databricks_datasource_uid}): '{panel_title}'")
                for i, target in enumerate(targets):
                    raw_sql = target.get('rawSql')
                    if raw_sql:
                        interpolated_sql = raw_sql

                        time_filter_match = re.search(r"\$__timeFilter\((\w+)\)", interpolated_sql)
                        if time_filter_match:
                            column_name = time_filter_match.group(1)
                            sql_time_condition, time_parse_error = parse_grafana_time_range(time_from, time_to, column_name)
                            if time_parse_error:
                                app.logger.warning(f"Panel '{panel_title}': Time range parsing issue ('{time_from}' to '{time_to}'): {time_parse_error}. Falling back to '{sql_time_condition}'.")
                            else:
                                app.logger.info(f"Panel '{panel_title}': Applying time filter: {sql_time_condition}")
                            interpolated_sql = interpolated_sql.replace(time_filter_match.group(0), sql_time_condition)
                        
                        if "'$Interval'" in interpolated_sql:
                             interval_value = template_variables.get('Interval', 'Monthly')
                             interpolated_sql = interpolated_sql.replace("'$Interval'", f"'{interval_value}'") 
                             app.logger.info(f"Replaced '$Interval' with '{interval_value}'")

                        variable_matches = re.findall(r"\$\{(\w+)\}", interpolated_sql)
                        replacements_to_make = {}
                        processed_conditions = set()

                        for var_name in variable_matches:
                            placeholder = f"${{{var_name}}}"
                            if placeholder in replacements_to_make:
                                continue 

                            if var_name in template_variables:
                                value = template_variables[var_name]
                                if var_name == 'business_unit':
                                    app.logger.info(f"Planning replacement for var '{var_name}'. Value: {value} (Type: {type(value)})")

                                replacement_value = None
                                is_boolean_replacement = False

                                if isinstance(value, list):
                                    if '$__all' in value and len(value) == 1:
                                        pattern = rf"(\w+)\s+IN\s+\(\s*{re.escape(placeholder)}\s*\)"
                                        match = re.search(pattern, interpolated_sql)
                                        
                                        condition_key = match.group(0) if match else None
                                        if match and condition_key not in processed_conditions:
                                            replacements_to_make[condition_key] = "1=1" 
                                            processed_conditions.add(condition_key)
                                            app.logger.info(f"Planning to replace condition '{condition_key}' with boolean '1=1' due to $__all.")
                                            replacements_to_make[placeholder] = None
                                        elif placeholder not in replacements_to_make: 
                                            app.logger.warning(f"Variable {placeholder} is '$__all' but not in a simple IN clause (or IN already handled). Planning to replace placeholder with boolean \'TRUE\'.")
                                            replacements_to_make[placeholder] = "TRUE"
                                            is_boolean_replacement = True
                                    else:
                                        quoted_values = [f"'{str(v)}'" if isinstance(v, str) else str(v) for v in value if v != '$__all']
                                        replacement_value = ", ".join(quoted_values)
                                        if placeholder not in replacements_to_make:
                                             replacements_to_make[placeholder] = replacement_value
                                else:
                                    replacement_value = f"'{str(value)}'" if isinstance(value, str) else str(value)
                                    if placeholder not in replacements_to_make:
                                         replacements_to_make[placeholder] = replacement_value
                                
                                if replacement_value is not None and not is_boolean_replacement and placeholder in replacements_to_make and replacements_to_make[placeholder] is not None:
                                     app.logger.info(f"Planning to replace {placeholder} with {replacement_value[:50]}... (Standard)")

                            else:
                                app.logger.warning(f"Variable {placeholder} found in query but not defined in dashboard templating. Placeholder will remain.")
                                replacements_to_make[placeholder] = placeholder

                        app.logger.info(f"Applying replacements: {replacements_to_make}")
                        for key in sorted(replacements_to_make, key=len, reverse=True):
                            value_to_replace = replacements_to_make[key]
                            if value_to_replace is not None:
                                interpolated_sql = interpolated_sql.replace(key, value_to_replace)
                                app.logger.info(f"Applied replacement: '{key}' -> '{value_to_replace[:50]}...'")
                            else:
                                app.logger.info(f"Skipping replacement for '{key}' as it was handled by condition replacement.")

                        app.logger.info(f"Final interpolated SQL before execution: {interpolated_sql[:300]}...")

                        app.logger.info(f"Executing query for panel '{panel_title}' (Target {i}): {interpolated_sql[:200]}...")
                        result_key = f"{panel_title} - Query {i+1}"
                        query_result = execute_databricks_query(interpolated_sql)

                        if isinstance(query_result, pd.DataFrame):
                            app.logger.info(f"Successfully executed query for '{result_key}'. Rows: {len(query_result)}")
                        else:
                            app.logger.error(f"Failed to execute query for '{result_key}'. Error: {query_result}")
                        databricks_results[result_key] = query_result
                    else:
                         app.logger.warning(f"No 'rawSql' found in target {i} for panel '{panel_title}'")

        # Start an asynchronous Gemini API call - this allows us to show a loading indicator
        if not databricks_results:
            app.logger.warning("No Databricks query results obtained. Falling back to dashboard structure analysis.")
            if USE_MCP and mcp_client:
                app.logger.info("Using MCP for dashboard structure analysis")
                insights_future = concurrent.futures.Future()
                
                def get_mcp_insights():
                    try:
                        result = get_insights_from_mcp(dashboard_data, query_results=None)
                        insights_future.set_result(result)
                    except Exception as e:
                        insights_future.set_exception(e)
                
                insights_thread = threading.Thread(target=get_mcp_insights)
                insights_thread.daemon = True
                insights_thread.start()
            else:
                app.logger.info("Using direct Gemini API for dashboard structure analysis")
                insights_future = get_insights_from_gemini_async(dashboard_data, query_results=None)
        else:
            app.logger.info(f"Sending {len(databricks_results)} query results for analysis.")
            if USE_MCP and mcp_client:
                app.logger.info("Using MCP for query results analysis")
                insights_future = concurrent.futures.Future()
                
                def get_mcp_query_insights():
                    try:
                        result = get_insights_from_mcp(dashboard_data, query_results=databricks_results)
                        insights_future.set_result(result)
                    except Exception as e:
                        insights_future.set_exception(e)
                
                insights_thread = threading.Thread(target=get_mcp_query_insights)
                insights_thread.daemon = True
                insights_thread.start()
            else:
                app.logger.info("Using direct Gemini API for query results analysis")
                insights_future = get_insights_from_gemini_async(dashboard_data, query_results=databricks_results)
        
        # Wait for the insights to be ready
        insights = insights_future.result()
        
        # Cache the insights
        if insights:
            save_to_cache(dashboard_cache_key, insights)
            app.logger.info(f"Cached insights for dashboard '{dashboard_title}' (UID: {uid})")
            
            html_insights = markdown.markdown(
                insights,
                extensions=['tables', 'fenced_code', 'codehilite']
            )
            app.logger.info("Converted Markdown insights to HTML")
            
            # Only store a reference to insights instead of the full content
            # to avoid large session cookies
            insights_file = f"insights_{uid}.html"
            insights_path = os.path.join(tempfile.gettempdir(), insights_file)
            with open(insights_path, 'w') as f:
                f.write(html_insights)
            
            # Store just the path in the session
            session[f'dashboard_{uid}_insights_path'] = insights_path
        else:
            html_insights = ""
            app.logger.warning("No insights content to convert to HTML")

        elapsed_time = time.time() - start_time
        app.logger.info(f"Dashboard analysis completed in {elapsed_time:.2f} seconds")
        
        return render_template(
            'dashboard.html',
            dashboard_title=dashboard_title,
            insights=html_insights,
            using_mcp=USE_MCP and mcp_client is not None
        )
    except Exception as e:
        app.logger.error(f"Error processing dashboard {uid}: {str(e)}", exc_info=True)
        return render_template('error.html', error=f"An error occurred: {str(e)}")

def generate_pdf_from_html(html_content, output_path=None):
    """
    Generate a better formatted PDF from HTML content using ReportLab.
    
    Args:
        html_content (str): The HTML content to convert to PDF
        output_path (str, optional): Path to save the PDF. If None, PDF is returned as bytes.
        
    Returns:
        bytes or None: If output_path is None, returns PDF as bytes, otherwise returns None.
    """
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, ListItem, ListFlowable
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
    import re
    import io
    from html.parser import HTMLParser
    from datetime import datetime
    
    class HTMLTextExtractor(HTMLParser):
        """Extract structured content from HTML with enhanced support for metadata and lists."""
        
        def __init__(self):
            super().__init__()
            self.result = []
            self.current_data = ""
            self.capture = True
            self.in_table = False
            self.current_table = []
            self.current_row = []
            self.in_header = False
            self.in_th = False
            self.in_td = False
            self.in_p = False
            self.in_h1 = False
            self.in_h2 = False
            self.in_h3 = False
            self.in_li = False
            self.in_ol = False
            self.in_ul = False
            self.list_items = []
            self.is_ordered_list = False
            self.list_counter = 1
            self.in_strong = False
            self.meta_key = None
            self.meta_items = {}
            self.current_section = None
            
        def handle_starttag(self, tag, attrs):
            if tag == 'h1':
                self.in_h1 = True
                self.flush_current_data()
                self.current_section = None
            elif tag == 'h2':
                self.in_h2 = True
                self.flush_current_data()
                self.current_section = None
            elif tag == 'h3':
                self.in_h3 = True
                self.flush_current_data()
                self.current_section = None
            elif tag == 'p':
                self.in_p = True
                self.flush_current_data()
            elif tag == 'strong' or tag == 'b':
                self.in_strong = True
                self.meta_key = ""
            elif tag == 'table':
                self.in_table = True
                self.current_table = []
            elif tag == 'tr':
                self.current_row = []
            elif tag == 'th':
                self.in_th = True
                self.current_data = ""
            elif tag == 'td':
                self.in_td = True
                self.current_data = ""
            elif tag == 'ul':
                self.in_ul = True
                self.is_ordered_list = False
                self.list_items = []
            elif tag == 'ol':
                self.in_ol = True
                self.is_ordered_list = True
                self.list_counter = 1
                self.list_items = []
            elif tag == 'li':
                self.in_li = True
                self.current_data = ""
                
        def handle_endtag(self, tag):
            if tag == 'h1':
                self.result.append(('h1', self.current_data.strip()))
                self.in_h1 = False
                self.current_data = ""
                self.current_section = self.result[-1][1]
            elif tag == 'h2':
                self.result.append(('h2', self.current_data.strip()))
                self.in_h2 = False
                self.current_data = ""
                self.current_section = self.result[-1][1]
            elif tag == 'h3':
                self.result.append(('h3', self.current_data.strip()))
                self.in_h3 = False
                self.current_data = ""
                self.current_section = self.result[-1][1]
            elif tag == 'p':
                if self.current_data.strip():
                    # Look for metadata like "Expected Impact: Moderate cost reduction"
                    meta_match = re.match(r'^\s*([A-Za-z\s]+):\s*(.+)$', self.current_data.strip())
                    if meta_match:
                        key = meta_match.group(1).strip()
                        value = meta_match.group(2).strip()
                        self.result.append(('meta', (key, value)))
                    else:
                        self.result.append(('p', self.current_data.strip()))
                self.in_p = False
                self.current_data = ""
            elif tag == 'strong' or tag == 'b':
                self.in_strong = False
                if ":" in self.meta_key.strip():
                    parts = self.meta_key.strip().split(":", 1)
                    key = parts[0].strip()
                    value = parts[1].strip() if len(parts) > 1 else ""
                    if key:
                        self.meta_items[key] = value
                        self.result.append(('meta', (key, value)))
            elif tag == 'table':
                if self.current_table:
                    self.result.append(('table', self.current_table))
                self.in_table = False
            elif tag == 'tr':
                if self.current_row:
                    self.current_table.append(self.current_row)
            elif tag == 'th':
                self.current_row.append(self.current_data.strip())
                self.in_th = False
            elif tag == 'td':
                self.current_row.append(self.current_data.strip())
                self.in_td = False
            elif tag == 'ul':
                if self.list_items:
                    self.result.append(('list', (False, self.list_items)))
                self.in_ul = False
            elif tag == 'ol':
                if self.list_items:
                    self.result.append(('list', (True, self.list_items)))
                self.in_ol = False
            elif tag == 'li':
                if self.current_data.strip():
                    if self.is_ordered_list:
                        # For ordered lists, prefix with the number
                        self.list_items.append(f"{self.list_counter}. {self.current_data.strip()}")
                        self.list_counter += 1
                    else:
                        self.list_items.append(self.current_data.strip())
                self.in_li = False
                self.current_data = ""
                
        def handle_data(self, data):
            if self.in_h1 or self.in_h2 or self.in_h3 or self.in_p or self.in_th or self.in_td or self.in_li:
                self.current_data += data
            elif self.in_strong:
                self.meta_key += data
                
        def flush_current_data(self):
            if self.current_data.strip():
                self.result.append(('p', self.current_data.strip()))
                self.current_data = ""
    
    # Extract structured content from HTML
    parser = HTMLTextExtractor()
    parser.feed(html_content)
    structured_content = parser.result
    
    # Set up the document
    buffer = io.BytesIO() if output_path is None else output_path
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=letter,
        rightMargin=0.85*inch, 
        leftMargin=0.85*inch,
        topMargin=0.75*inch, 
        bottomMargin=0.85*inch
    )
    
    # Create color palette for consistent styling
    primary_color = colors.HexColor('#1F77B4')  # Grafana blue
    secondary_color = colors.HexColor('#FF7F0E')  # Grafana orange
    accent_color = colors.HexColor('#2CA02C')  # Grafana green
    highlight_color = colors.HexColor('#D62728')  # Grafana red
    neutral_color = colors.HexColor('#7F7F7F')  # Grafana gray
    background_color = colors.HexColor('#F8F9FA')  # Light background
    
    # Create styles
    styles = getSampleStyleSheet()
    
    # Define custom styles with enhanced readability
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=22,
        leading=26,
        textColor=primary_color,
        spaceAfter=16,
        spaceBefore=12,
        alignment=TA_LEFT,
        borderWidth=0,
        borderPadding=0,
        borderColor=None,
    )
    
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Italic'],
        fontSize=12,
        leading=14,
        textColor=neutral_color,
        spaceAfter=20,
    )
    
    heading1_style = ParagraphStyle(
        'Heading1',
        parent=styles['Heading1'],
        fontSize=18,
        leading=22,
        textColor=primary_color,
        spaceBefore=16,
        spaceAfter=10,
        borderWidth=0,
        borderRadius=None,
        borderPadding=0,
        borderColor=None,
    )
    
    heading2_style = ParagraphStyle(
        'Heading2',
        parent=styles['Heading2'],
        fontSize=16,
        leading=20,
        textColor=primary_color,
        spaceBefore=14,
        spaceAfter=8,
    )
    
    heading3_style = ParagraphStyle(
        'Heading3',
        parent=styles['Heading3'],
        fontSize=14,
        leading=18,
        textColor=primary_color,
        spaceBefore=12,
        spaceAfter=6,
    )
    
    normal_style = ParagraphStyle(
        'Normal',
        parent=styles['Normal'],
        fontSize=11,
        leading=15,
        spaceBefore=8,
        spaceAfter=8,
    )
    
    # Create metadata style with background highlighting
    meta_style = ParagraphStyle(
        'MetaData',
        parent=normal_style,
        leftIndent=10,
        fontSize=11,
        leading=16,
        spaceBefore=6,
        spaceAfter=6,
        backColor=background_color,
        borderWidth=1,
        borderColor=neutral_color,
        borderPadding=5,
        borderRadius=5,
    )
    
    # Special metadata styles for different importance levels
    meta_high_style = ParagraphStyle(
        'MetaDataHigh',
        parent=meta_style,
        textColor=highlight_color,
        borderColor=highlight_color,
    )
    
    meta_medium_style = ParagraphStyle(
        'MetaDataMedium',
        parent=meta_style,
        textColor=secondary_color,
        borderColor=secondary_color,
    )
    
    meta_low_style = ParagraphStyle(
        'MetaDataLow',
        parent=meta_style,
        textColor=accent_color,
        borderColor=accent_color,
    )
    
    # Create metadata key style (bold)
    meta_key_style = ParagraphStyle(
        'MetaDataKey',
        parent=meta_style,
        fontName='Helvetica-Bold',
    )
    
    # Create list bullet style with improved indentation
    bullet_style = ParagraphStyle(
        'Bullet',
        parent=normal_style,
        leftIndent=25,
        bulletIndent=10,
        spaceBefore=4,
        spaceAfter=4,
    )
    
    # Create numbered list style with improved indentation
    numbered_style = ParagraphStyle(
        'Numbered',
        parent=normal_style,
        leftIndent=25,
        firstLineIndent=0,
        spaceBefore=4,
        spaceAfter=4,
    )
    
    # Add section separator style
    section_separator_style = ParagraphStyle(
        'SectionSeparator',
        parent=normal_style,
        alignment=TA_CENTER,
        textColor=neutral_color,
    )
    
    # Build content
    story = []
    
    # Get title from the HTML
    title = "Cost Analysis Report"
    for tag, content in structured_content:
        if tag == 'h1':
            title = content
            break
    
    # Add header with title and date
    report_date = datetime.now().strftime("%B %d, %Y")
    
    # Create a more visually distinct header
    header_table_data = [
        [Paragraph(f"<b>{title}</b>", title_style)],
        [Paragraph(f"<i>Generated on {report_date}</i>", subtitle_style)]
    ]
    
    header_table = Table(header_table_data, colWidths=[6.8*inch])
    header_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (0, 0), 12),
        ('LINEBELOW', (0, 1), (-1, 1), 1, primary_color),
        ('BACKGROUND', (0, 0), (-1, 0), background_color),
        ('ROUNDEDCORNERS', [5, 5, 5, 5]),
    ]))
    
    story.append(header_table)
    story.append(Spacer(1, 0.35*inch))
    
    # Group metadata items by section for better organization
    current_section = None
    section_metadata = {}
    
    # Process the structured content
    for tag, content in structured_content:
        if tag == 'h1':
            # Skip the title as we've already included it in the header
            current_section = content
            continue
        elif tag == 'h2':
            # Add section separator before new major sections
            if story and story[-1].__class__.__name__ != 'Spacer':
                story.append(Spacer(1, 0.2*inch))
                story.append(Paragraph("* * *", section_separator_style))
                story.append(Spacer(1, 0.2*inch))
            
            story.append(Paragraph(content, heading1_style))
            current_section = content
        elif tag == 'h3':
            story.append(Paragraph(content, heading2_style))
            current_section = content
        elif tag == 'p':
            story.append(Paragraph(content, normal_style))
        elif tag == 'meta':
            key, value = content
            
            # Format special metadata items with better styling and visual hierarchy
            meta_text = f"<b>{key}:</b> {value}"
            
            # Choose style based on key importance
            if key.lower() in ("priority", "criticality", "importance", "urgency"):
                # Determine priority level style based on value
                value_lower = value.lower()
                if any(word in value_lower for word in ["high", "critical", "urgent", "important"]):
                    meta_para = Paragraph(meta_text, meta_high_style)
                elif any(word in value_lower for word in ["medium", "moderate", "normal"]):
                    meta_para = Paragraph(meta_text, meta_medium_style)
                else:
                    meta_para = Paragraph(meta_text, meta_low_style)
            elif key.lower() in ("expected impact", "impact", "cost reduction", "savings"):
                # Determine impact level style based on value
                value_lower = value.lower()
                if any(word in value_lower for word in ["significant", "high", "major"]):
                    meta_para = Paragraph(meta_text, meta_high_style)
                elif any(word in value_lower for word in ["moderate", "medium"]):
                    meta_para = Paragraph(meta_text, meta_medium_style)
                else:
                    meta_para = Paragraph(meta_text, meta_low_style)
            elif key.lower() in ("implementation difficulty", "difficulty", "complexity", "effort"):
                # Determine difficulty level style based on value
                value_lower = value.lower()
                if any(word in value_lower for word in ["high", "complex", "difficult"]):
                    meta_para = Paragraph(meta_text, meta_high_style)
                elif any(word in value_lower for word in ["moderate", "medium"]):
                    meta_para = Paragraph(meta_text, meta_medium_style)
                else:
                    meta_para = Paragraph(meta_text, meta_low_style)
            else:
                # Regular metadata display
                meta_para = Paragraph(meta_text, meta_style)
            
            story.append(meta_para)
            story.append(Spacer(1, 0.05*inch))
            
        elif tag == 'list':
            is_ordered, items = content
            
            if is_ordered:
                # Create a properly formatted ordered list
                ordered_list_items = []
                for i, item in enumerate(items, 1):
                    # If item already starts with a number, extract the content
                    if re.match(r'^\d+\.\s+', item):
                        item_text = re.sub(r'^\d+\.\s+', '', item)
                    else:
                        item_text = item
                    
                    para = Paragraph(item_text, numbered_style)
                    bullet_text = f"{i}."
                    ordered_list_items.append(ListItem(para, leftIndent=25, value=bullet_text))
                
                list_flowable = ListFlowable(
                    ordered_list_items,
                    bulletType='bullet',
                    start=1,
                    bulletFontName='Helvetica-Bold',
                    bulletFontSize=11,
                    leftIndent=25,
                    spaceBefore=10,
                    spaceAfter=10
                )
                story.append(list_flowable)
            else:
                # Create a properly formatted bullet list
                bullet_list_items = []
                for item in items:
                    para = Paragraph(item, bullet_style)
                    bullet_list_items.append(ListItem(para, leftIndent=25, bulletColor=primary_color))
                
                list_flowable = ListFlowable(
                    bullet_list_items,
                    bulletType='bullet',
                    bulletFontName='Helvetica',
                    bulletFontSize=11,
                    leftIndent=25,
                    spaceBefore=10,
                    spaceAfter=10
                )
                story.append(list_flowable)
                
        elif tag == 'table':
            # Process table data with improved styling
            if content:
                # Better visual styling for tables
                has_header = True  # Assume first row is header
                
                # Calculate column widths based on content
                if len(content) > 0 and len(content[0]) > 0:
                    num_cols = len(content[0])
                    col_widths = [6.8*inch/num_cols] * num_cols  # Equal distribution by default
                    
                    # For tables with 2-3 columns, make the first column wider if it likely contains labels
                    if 2 <= num_cols <= 3:
                        col_widths[0] = 2.5*inch
                        remaining_width = 6.8*inch - 2.5*inch
                        for i in range(1, num_cols):
                            col_widths[i] = remaining_width / (num_cols - 1)
                else:
                    col_widths = None
                
                table = Table(content, colWidths=col_widths, repeatRows=1 if has_header else 0)
                
                # Define alternating row colors for better readability
                row_colors = [background_color, colors.white]
                
                # Build table styles
                table_styles = [
                    # Header row styling
                    ('BACKGROUND', (0, 0), (-1, 0), primary_color),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 11),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    
                    # Cell styling
                    ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                    ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                    ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 1), (-1, -1), 10),
                    ('TOPPADDING', (0, 1), (-1, -1), 6),
                    ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
                    
                    # Table grid
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('BOX', (0, 0), (-1, -1), 1, primary_color),
                    
                    # First column styling - often contains labels
                    ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
                ]
                
                # Add alternating row colors for better readability
                for i in range(1, len(content)):
                    if i % 2 == 1:
                        table_styles.append(('BACKGROUND', (0, i), (-1, i), background_color))
                
                table.setStyle(TableStyle(table_styles))
                
                # Add table with spacing
                story.append(Spacer(1, 0.1*inch))
                story.append(table)
                story.append(Spacer(1, 0.2*inch))
    
    # Add footer with page numbers and confidentiality notice
    story.append(Spacer(1, 0.5*inch))
    
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=neutral_color,
        alignment=TA_CENTER,
    )
    
    footer_text = "Generated by Grafana Cost Analyzer · Confidential · Page "
    footer = Paragraph(f"<para alignment='center'>{footer_text}<seq id='page'/></para>", footer_style)
    story.append(footer)
    
    # Build the PDF
    doc.build(story)
    
    if output_path is None:
        buffer.seek(0)
        return buffer.read()
    return None

@app.route('/dashboard/<uid>/pdf')
def download_pdf_report(uid):
    """Generates and returns a PDF version of the dashboard analysis."""
    try:
        dashboard_details = grafana_api.get_dashboard(uid)
        dashboard_data = dashboard_details.get('dashboard', {})
        dashboard_title = dashboard_data.get('title', 'Dashboard')

        if not dashboard_data:
             return render_template('error.html', error=f"Could not fetch dashboard details for UID: {uid}")

        # Get stored insights from session
        insights_path = session.get(f'dashboard_{uid}_insights_path')
        if insights_path and os.path.exists(insights_path):
            with open(insights_path, 'r') as f:
                html_insights = f.read()
        else:
            html_insights = '<p>No insights available for this dashboard.</p>'

        # Generate PDF filename based on dashboard title
        safe_title = re.sub(r'[^\w\s-]', '', dashboard_title).strip().lower()
        safe_title = re.sub(r'[-\s]+', '-', safe_title)
        filename = f"{safe_title}-cost-analysis.pdf"
        
        # Create HTML for PDF with embedded styles - no external dependencies
        report_date = datetime.now().strftime("%B %d, %Y")
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{dashboard_title} - Cost Analysis</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    font-size: 11pt;
                    line-height: 1.5;
                    color: #333;
                    margin: 2cm;
                }}
                .header {{
                    border-bottom: 1px solid #ddd;
                    padding-bottom: 15px;
                    margin-bottom: 20px;
                }}
                .footer {{
                    margin-top: 30px;
                    border-top: 1px solid #ddd;
                    padding-top: 10px;
                    font-size: 9pt;
                    color: #666;
                    text-align: center;
                }}
                h1 {{
                    color: #0066cc;
                    font-size: 20pt;
                    margin: 0 0 10px 0;
                }}
                h2 {{
                    color: #0066cc;
                    font-size: 16pt;
                    margin: 20px 0 10px 0;
                }}
                h3 {{
                    font-size: 13pt;
                    margin: 15px 0 10px 0;
                }}
                .meta {{
                    color: #666;
                    font-size: 10pt;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 15px 0;
                    font-size: 10pt;
                }}
                th {{
                    background-color: #f1f3f8;
                    border: 1px solid #ddd;
                    padding: 8px;
                    text-align: left;
                }}
                td {{
                    border: 1px solid #ddd;
                    padding: 8px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{dashboard_title}</h1>
                <div class="meta">Cost Analysis Report · Generated on {report_date}</div>
            </div>
            
            {html_insights}
            
            <div class="footer">
                <p>Generated by Grafana Cost Analyzer · Confidential</p>
            </div>
        </body>
        </html>
        """
        
        # Create a temporary file for the PDF
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            pdf_path = temp_file.name
        
        # Generate PDF using our helper function
        generate_pdf_from_html(html_content, pdf_path)
        
        # Send the file to the client
        return send_file(
            pdf_path,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        app.logger.error(f"Error generating PDF for dashboard {uid}: {str(e)}", exc_info=True)
        return render_template('error.html', error=f"An error occurred generating the PDF: {str(e)}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))