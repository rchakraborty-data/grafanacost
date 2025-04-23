from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file
import os
import requests
import json
import re
import pandas as pd
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta  # For month/year parsing
from grafana_api import GrafanaAPI
from config import DEBUG, SECRET_KEY, GEMINI_API_KEY, GEMINI_API_ENDPOINT, USE_MCP, MCP_HOST, MCP_PORT, START_MCP_SERVER
from databricks_client import execute_databricks_query
import markdown  # Added for converting Markdown to HTML
import tempfile
import pdfkit  # Added for PDF generation
import logging
import threading
from mcp_client import MCPClient  # Import the MCP client
from grafana_mcp_server import start_mcp_server  # Import the MCP server starter from renamed module

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
app.config['DEBUG'] = DEBUG

grafana_api = GrafanaAPI()

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
    if not GEMINI_API_KEY:
        return "Error: Gemini API Key not configured."

    headers = {
        'Content-Type': 'application/json',
    }

    prompt = ""
    if query_results:
        prompt += "Analyze the following data retrieved from a Grafana dashboard's queries. Provide insights, identify potential issues or anomalies, and suggest recommendations based *only* on this data.\n\n"
        for panel_title, result in query_results.items():
            prompt += f"--- Data from Panel: {panel_title} ---\n"
            if isinstance(result, pd.DataFrame):
                if not result.empty:
                    prompt += result.to_markdown(index=False, numalign="left", stralign="left")
                else:
                    prompt += "(No data returned from query)"
            else:
                prompt += f"Error fetching data: {result}"
            prompt += "\n\n"
        prompt += "Insights and Recommendations based on the data above:"
    else:
        prompt = f"""Analyze the following Grafana dashboard JSON definition. Provide insights and recommendations regarding cost optimization, potential issues, or interesting patterns. 

IMPORTANT: When providing an insight or recommendation, clearly state which part of the dashboard it refers to (e.g., 'Regarding Panel "Panel Title"...', 'For the query in Panel X...', 'Based on the variable "Variable Name"...'). Focus on actionable advice based on the dashboard structure, panels (including their titles, types, and queries), and variables.

Dashboard JSON:
```json
{json.dumps(dashboard_data, indent=2)}
```

Insights and Recommendations (referencing specific dashboard elements):"""

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
        dashboard_details = grafana_api.get_dashboard(uid)
        dashboard_data = dashboard_details.get('dashboard', {})
        dashboard_title = dashboard_data.get('title', 'Dashboard')

        if not dashboard_data:
             return render_template('error.html', error=f"Could not fetch dashboard details for UID: {uid}")

        template_variables = {var['name']: var.get('current', {}).get('value', '') 
                              for var in dashboard_data.get('templating', {}).get('list', [])}
        time_from = dashboard_data.get('time', {}).get('from', 'now-6h')
        time_to = dashboard_data.get('time', {}).get('to', 'now')

        databricks_results = {}
        panels = dashboard_data.get('panels', [])
        databricks_datasource_uid = "ddjmooc1so54wc"

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

        if not databricks_results:
            app.logger.warning("No Databricks query results obtained. Falling back to dashboard structure analysis.")
            if USE_MCP and mcp_client:
                app.logger.info("Using MCP for dashboard structure analysis")
                insights = get_insights_from_mcp(dashboard_data, query_results=None)
            else:
                app.logger.info("Using direct Gemini API for dashboard structure analysis")
                insights = get_insights_from_gemini(dashboard_data, query_results=None)
        else:
            app.logger.info(f"Sending {len(databricks_results)} query results for analysis.")
            if USE_MCP and mcp_client:
                app.logger.info("Using MCP for query results analysis")
                insights = get_insights_from_mcp(dashboard_data, query_results=databricks_results)
            else:
                app.logger.info("Using direct Gemini API for query results analysis")
                insights = get_insights_from_gemini(dashboard_data, query_results=databricks_results)
        
        if insights:
            html_insights = markdown.markdown(
                insights,
                extensions=['tables', 'fenced_code', 'codehilite']
            )
            app.logger.info("Converted Markdown insights to HTML")
        else:
            html_insights = ""
            app.logger.warning("No insights content to convert to HTML")

        return render_template(
            'dashboard.html',
            dashboard_title=dashboard_title,
            insights=html_insights,
            using_mcp=USE_MCP and mcp_client is not None
        )
    except Exception as e:
        app.logger.error(f"Error processing dashboard {uid}: {str(e)}", exc_info=True)
        return render_template('error.html', error=f"An error occurred: {str(e)}")

@app.route('/dashboard/<uid>/pdf')
def download_pdf_report(uid):
    """Generates and returns a PDF version of the dashboard analysis."""
    try:
        dashboard_details = grafana_api.get_dashboard(uid)
        dashboard_data = dashboard_details.get('dashboard', {})
        dashboard_title = dashboard_data.get('title', 'Dashboard')

        if not dashboard_data:
             return render_template('error.html', error=f"Could not fetch dashboard details for UID: {uid}")

        # Reuse the same data fetching logic as in view_dashboard
        template_variables = {var['name']: var.get('current', {}).get('value', '') 
                             for var in dashboard_data.get('templating', {}).get('list', [])}
        time_from = dashboard_data.get('time', {}).get('from', 'now-6h')
        time_to = dashboard_data.get('time', {}).get('to', 'now')

        databricks_results = {}
        panels = dashboard_data.get('panels', [])
        databricks_datasource_uid = "ddjmooc1so54wc"

        # Similar panel processing logic as in view_dashboard
        # ...Getting insights (reusing the same logic)...
        if not databricks_results:
            app.logger.warning("No Databricks query results obtained for PDF. Falling back to dashboard structure analysis.")
            insights = get_insights_from_gemini(dashboard_data, query_results=None)
        else:
            app.logger.info(f"Sending {len(databricks_results)} query results to Gemini for PDF analysis.")
            insights = get_insights_from_gemini(dashboard_data, query_results=databricks_results)
        
        # Convert Markdown content to HTML
        if insights:
            html_insights = markdown.markdown(
                insights,
                extensions=['tables', 'fenced_code', 'codehilite']
            )
        else:
            html_insights = "<p>No insights available for this dashboard.</p>"

        # Generate PDF filename based on dashboard title
        safe_title = re.sub(r'[^\w\s-]', '', dashboard_title).strip().lower()
        safe_title = re.sub(r'[-\s]+', '-', safe_title)
        filename = f"{safe_title}-cost-analysis.pdf"
        
        # Create a temporary file for the PDF
        report_date = datetime.now().strftime("%B %d, %Y")
        
        # Generate HTML for PDF with embedded styles
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{dashboard_title} - Cost Analysis</title>
            <style>
                @page {{
                    margin: 1cm;
                    size: letter;
                    @top-right {{
                        content: "Page " counter(page) " of " counter(pages);
                        font-size: 9pt;
                        color: #666;
                    }}
                }}
                body {{
                    font-family: Arial, sans-serif;
                    font-size: 11pt;
                    line-height: 1.5;
                    color: #333;
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
                .recommendation {{
                    background-color: #f0f7f0;
                    border-left: 4px solid #38b249;
                    padding: 15px;
                    margin: 15px 0;
                }}
                .key-insight {{
                    background-color: #f0f5fa;
                    border-left: 4px solid #0066cc;
                    padding: 15px;
                    margin: 15px 0;
                }}
                .warning-item {{
                    background-color: #fff9e6;
                    border-left: 4px solid #ffc107;
                    padding: 15px;
                    margin: 15px 0;
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
                tr:nth-child(even) {{
                    background-color: #f9f9f9;
                }}
                code {{
                    font-family: Courier, monospace;
                    background-color: #f1f3f8;
                    padding: 2px 4px;
                    font-size: 90%;
                    border-radius: 3px;
                }}
                pre {{
                    background-color: #f1f3f8;
                    padding: 10px;
                    border-radius: 5px;
                    white-space: pre-wrap;
                    font-size: 9pt;
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
        
        # Generate PDF from HTML
        pdfkit.from_string(html_content, pdf_path)
        
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