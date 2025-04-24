"""
MCP Server for Grafana Cost Analyzer

This module implements a Model Context Protocol server for the Grafana Cost Analyzer,
providing AI-powered analysis capabilities through standardized actions.
"""

import os
import json
import logging
import threading
import socket
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from grafana_api import GrafanaAPI
from databricks_client import execute_databricks_query
from config import GEMINI_API_KEY, GEMINI_API_ENDPOINT, GEMINI_MODEL_NAME, GEMINI_TEMPERATURE, GEMINI_TOP_P, GEMINI_TOP_K, GEMINI_MAX_OUTPUT_TOKENS, GEMINI_RESPONSE_MIME_TYPE, GEMINI_SAFETY_SETTINGS, GEMINI_API_URL
import requests
import pandas as pd
from grafana_graphql import GrafanaMCPGraphQL  # Import the GraphQL handler

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Simple custom implementation of MCP components
class ActionResponse:
    """Response from an MCP action."""
    
    def __init__(self, status, data=None, error=None):
        self.status = status
        self.data = data if data is not None else {}
        self.error = error
        
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        result = {
            "status": self.status,
        }
        
        if self.data:
            result["data"] = self.data
        
        if self.error:
            result["error"] = self.error
            
        return result

class MCPServer:
    """Custom implementation of MCP Server for Grafana Cost Analyzer."""
    
    def __init__(self, host="localhost", port=8090):
        """Initialize the MCP server."""
        self.host = host
        self.port = port
        self.running = False
        self.server = None
        self.actions = {}
        self.grafana_api = GrafanaAPI()
        self.graphql_handler = GrafanaMCPGraphQL(self.grafana_api)  # Initialize GraphQL handler
        logger.info(f"Initializing Grafana Cost MCP Server on {host}:{port}")
        
        # Register built-in actions
        self.register_action("get_dashboard", self.get_dashboard)
        self.register_action("execute_query", self.execute_query)
        self.register_action("analyze_cost_patterns", self.analyze_cost_patterns)
        self.register_action("generate_recommendations", self.generate_recommendations)
        self.register_action("analyze_sql_query", self.analyze_sql_query)  # Register SQL query analysis action
        
        # Register GraphQL endpoint handler
        self.register_graphql_handler()
    
    def register_action(self, name, func):
        """Register an action function."""
        self.actions[name] = func
        logger.info(f"Registered action: {name}")
    
    def register_graphql_handler(self):
        """Register the GraphQL handler in the MCP server."""
        self.actions["graphql"] = self.handle_graphql_request
        logger.info("Registered GraphQL endpoint handler")
    
    def handle_graphql_request(self, params):
        """Handle a GraphQL request.
        
        Args:
            params: Dictionary containing 'query' and optional 'variables'
            
        Returns:
            ActionResponse containing the GraphQL execution result
        """
        query = params.get("query")
        variables = params.get("variables", {})
        
        if not query:
            return ActionResponse("error", error="No GraphQL query provided")
        
        try:
            result = self.graphql_handler.execute_query(query, variables)
            return ActionResponse("success", data=result)
        except Exception as e:
            logger.error(f"Error executing GraphQL query: {str(e)}")
            return ActionResponse("error", error=f"GraphQL execution error: {str(e)}")
    
    def start(self):
        """Start the server in the current thread."""
        if self.running:
            logger.warning("Server is already running")
            return
            
        self.running = True
        
        class MCPRequestHandler(BaseHTTPRequestHandler):
            outer = self  # Reference to the outer class
            
            def do_GET(self):
                """Handle GET requests - health check."""
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "ok"}).encode())
            
            def do_POST(self):
                """Handle POST requests - actions."""
                try:
                    parsed_url = urlparse(self.path)
                    
                    # Extract action name from URL path
                    path_parts = parsed_url.path.strip('/').split('/')
                    if len(path_parts) < 2 or path_parts[0] != "actions":
                        self.send_error(404, "Not Found")
                        return
                    
                    action_name = path_parts[1]
                    
                    # Read request body
                    content_length = int(self.headers.get('Content-Length', 0))
                    body = self.rfile.read(content_length).decode('utf-8')
                    
                    if body:
                        try:
                            params = json.loads(body)
                        except json.JSONDecodeError:
                            self.send_error(400, "Invalid JSON")
                            return
                    else:
                        params = {}
                    
                    # Execute action
                    if action_name in self.outer.actions:
                        logger.info(f"Executing action: {action_name}")
                        try:
                            result = self.outer.actions[action_name](**params)
                            
                            # Convert to dictionary if it's an ActionResponse
                            if isinstance(result, ActionResponse):
                                result = result.to_dict()
                                
                            # Send response
                            self.send_response(200)
                            self.send_header('Content-type', 'application/json')
                            self.end_headers()
                            self.wfile.write(json.dumps(result).encode())
                        except Exception as e:
                            logger.error(f"Error executing action {action_name}: {str(e)}", exc_info=True)
                            self.send_error(500, f"Error executing action: {str(e)}")
                    else:
                        self.send_error(404, f"Action not found: {action_name}")
                except Exception as e:
                    logger.error(f"Error processing request: {str(e)}", exc_info=True)
                    self.send_error(500, f"Internal Server Error: {str(e)}")
            
            def log_message(self, format, *args):
                """Override to use our logger."""
                logger.info(f"MCP Server: {format % args}")
        
        try:
            # Create and start HTTP server
            self.server = HTTPServer((self.host, self.port), MCPRequestHandler)
            logger.info(f"Starting MCP server on {self.host}:{self.port}")
            self.server.serve_forever()
        except Exception as e:
            self.running = False
            logger.error(f"Error starting MCP server: {str(e)}", exc_info=True)
            raise
    
    def stop(self):
        """Stop the server."""
        if self.server:
            self.server.shutdown()
            self.running = False
            logger.info("MCP server stopped")
    
    # Action implementations
    def get_dashboard(self, uid=None, data=None):
        """Retrieve dashboard structure from Grafana or use provided data.
        
        This method can be called in two ways:
        1. With a UID to fetch a dashboard from Grafana
        2. With pre-loaded dashboard data passed directly
        
        Args:
            uid: Dashboard UID to fetch from Grafana (optional)
            data: Pre-loaded dashboard data (optional)
            
        Returns:
            ActionResponse with dashboard data
        """
        try:
            if data:
                # Using pre-loaded dashboard data
                logger.info("Using provided dashboard data instead of fetching")
                return ActionResponse(
                    status="success",
                    data={"dashboard": data}
                )
            elif uid:
                # Fetch from Grafana using UID
                logger.info(f"Fetching dashboard with UID: {uid}")
                dashboard_details = self.grafana_api.get_dashboard(uid)
                return ActionResponse(
                    status="success",
                    data=dashboard_details
                )
            else:
                return ActionResponse(
                    status="error",
                    error="Either dashboard UID or data must be provided"
                )
        except Exception as e:
            logger.error(f"Error processing dashboard: {str(e)}")
            return ActionResponse(
                status="error",
                error=f"Failed to process dashboard: {str(e)}"
            )
    
    def execute_query(self, sql, time_from=None, time_to=None):
        """Execute SQL query on Databricks."""
        try:
            result = execute_databricks_query(sql)
            
            if isinstance(result, pd.DataFrame):
                return ActionResponse(
                    status="success",
                    data={
                        "rows": len(result),
                        "columns": list(result.columns),
                        "data": result.to_dict(orient="records")
                    }
                )
            else:
                return ActionResponse(
                    status="error",
                    error=f"Query execution failed: {result}"
                )
        except Exception as e:
            logger.error(f"Error executing query: {str(e)}")
            return ActionResponse(
                status="error",
                error=f"Failed to execute query: {str(e)}"
            )
    
    def analyze_cost_patterns(self, data):
        """Analyze cost patterns in the provided data."""
        try:
            # Use Gemini API for analysis
            response = self._call_gemini_api(
                "Analyze the following Databricks cost data and identify patterns, " +
                "anomalies, and optimization opportunities. Focus on cost efficiency " +
                "and resource utilization patterns.\n\n" +
                f"Data: {json.dumps(data, indent=2)}"
            )
            
            return ActionResponse(
                status="success",
                data={
                    "analysis": response,
                    "patterns_identified": True
                }
            )
        except Exception as e:
            logger.error(f"Error analyzing cost patterns: {str(e)}")
            return ActionResponse(
                status="error",
                error=f"Failed to analyze cost patterns: {str(e)}"
            )
    
    def generate_recommendations(self, dashboard_data, analysis_results=None):
        """Generate cost optimization recommendations."""
        try:
            # Prepare prompt based on available data
            if analysis_results:
                prompt = (
                    "Based on the following dashboard data and analysis results, "
                    "provide specific cost optimization recommendations for Databricks "
                    "usage. Include expected impact, implementation difficulty, and "
                    "specific steps for each recommendation.\n\n"
                    "IMPORTANT INSTRUCTIONS:\n"
                    "1. For EACH recommendation, include a detailed cost-benefit analysis with monthly, quarterly, and yearly savings\n"
                    "2. When you identify inefficient SQL queries, provide a fully rewritten optimized version of the query with clear explanations\n"
                    "3. Explain specific configuration changes with exact parameter values\n"
                    "4. Provide concrete implementation steps that can be immediately actioned\n"
                    "5. Include performance impact metrics whenever possible\n"
                    "6. Prioritize recommendations based on implementation effort vs. cost savings\n\n"
                    f"Dashboard: {json.dumps(dashboard_data, indent=2)}\n\n"
                    f"Analysis: {json.dumps(analysis_results, indent=2)}"
                )
            else:
                prompt = (
                    "Analyze this Grafana dashboard structure and provide specific "
                    "cost optimization recommendations for Databricks usage. Focus on "
                    "query efficiency, resource utilization, and storage optimization.\n\n"
                    "IMPORTANT INSTRUCTIONS:\n"
                    "1. For EACH recommendation, include a detailed cost-benefit analysis with monthly, quarterly, and yearly savings\n"
                    "2. When you identify inefficient SQL queries, provide a fully rewritten optimized version of the query with clear explanations\n"
                    "3. Explain specific configuration changes with exact parameter values\n"
                    "4. Provide concrete implementation steps that can be immediately actioned\n"
                    "5. Include performance impact metrics whenever possible\n"
                    "6. Prioritize recommendations based on implementation effort vs. cost savings\n\n"
                    "FORMAT EACH RECOMMENDATION AS FOLLOWS:\n"
                    "## Recommendation: [Title]\n"
                    "[Detailed explanation with specific actions]\n\n"
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
                    "- **Quarterly Savings**: $X,XXX\n"
                    "- **Yearly Savings**: $X,XXX\n"
                    "- **Performance Improvement**: X%\n"
                    "- **Implementation Effort**: [Low/Medium/High]\n"
                    "- **Priority**: [High/Medium/Low]\n\n"
                    f"Dashboard: {json.dumps(dashboard_data, indent=2)}"
                )
            
            response = self._call_gemini_api(prompt)
            
            # Structure the recommendations
            return ActionResponse(
                status="success",
                data={
                    "recommendations": response,
                    "format": "markdown"
                }
            )
        except Exception as e:
            logger.error(f"Error generating recommendations: {str(e)}")
            return ActionResponse(
                status="error",
                error=f"Failed to generate recommendations: {str(e)}"
            )
    
    def analyze_sql_query(self, sql_query, execution_stats=None):
        """Analyze a SQL query and provide optimization recommendations.
        
        Args:
            sql_query: The SQL query to analyze
            execution_stats: Optional execution statistics (runtime, rows processed, etc.)
            
        Returns:
            ActionResponse with optimization recommendations
        """
        try:
            # Build a specialized prompt for SQL optimization
            prompt = (
                "You are a Databricks SQL optimization expert. Analyze the following SQL query "
                "and provide specific, actionable optimization recommendations to improve performance "
                "and reduce cost. If the query is inefficient, provide a fully rewritten optimized version.\n\n"
                "QUERY TO ANALYZE:\n"
                f"```sql\n{sql_query}\n```\n\n"
            )
            
            if execution_stats:
                prompt += (
                    "EXECUTION STATISTICS:\n"
                    f"{json.dumps(execution_stats, indent=2)}\n\n"
                )
                
            prompt += (
                "REQUIRED OUTPUT FORMAT:\n"
                "1. First, provide a clear assessment of the query's efficiency (1-2 paragraphs)\n"
                "2. List specific inefficiencies found (bullet points)\n"
                "3. Provide a fully rewritten optimized version of the query in ```sql code blocks\n"
                "4. Explain each optimization made and its impact (bullet points)\n"
                "5. Provide the estimated performance improvement as a percentage\n\n"
                "SQL OPTIMIZATION TECHNIQUES TO CONSIDER:\n"
                "- Filter pushdown opportunities\n"
                "- Join order optimization\n"
                "- Predicate optimization (removing redundant conditions)\n"
                "- Partition pruning improvements\n"
                "- Data skew handling\n"
                "- Caching strategies\n"
                "- Column pruning (SELECT only needed columns)\n"
                "- Proper JOIN types (broadcast vs. shuffle)\n"
                "- Subquery optimization or elimination\n"
                "- Using appropriate data types\n"
                "- Removing unnecessary functions in WHERE clauses\n"
                "- Leveraging materialized views or Delta caching\n"
            )
            
            # Call Gemini API with specialized SQL optimization prompt
            response = self._call_gemini_api(prompt)
            
            return ActionResponse(
                status="success",
                data={
                    "analysis": response,
                    "format": "markdown"
                }
            )
        except Exception as e:
            logger.error(f"Error analyzing SQL query: {str(e)}")
            return ActionResponse(
                status="error",
                error=f"Failed to analyze SQL query: {str(e)}"
            )
    
    def _call_gemini_api(self, prompt):
        """Call the Gemini API with the given prompt."""
        if not GEMINI_API_KEY:
            raise ValueError("Gemini API Key not configured")

        headers = {
            'Content-Type': 'application/json',
        }

        # Use the experimental Gemini model
        model_name = "gemini-2.0-flash-thinking-exp" 
        # Ensure GEMINI_API_ENDPOINT is set to v1beta in config.py
        api_endpoint = f"{GEMINI_API_ENDPOINT}/models/{model_name}:generateContent"
        
        logger.info(f"Using experimental Gemini model: {model_name}")
        
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
            logger.info(f"Calling Gemini API with model: {model_name} via endpoint: {api_endpoint}")
            response = requests.post(
                f"{api_endpoint}?key={GEMINI_API_KEY}", 
                headers=headers, 
                json=data,
                timeout=120
            )
            
            # More detailed error handling
            if response.status_code != 200:
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
                
                if response.status_code == 404:
                    raise ValueError(f"Model '{model_name}' not found. Please check your configuration.")
                elif response.status_code == 403:
                    raise ValueError("API key may be invalid or lacks permission.")
                else:
                    response.raise_for_status()
            
            result = response.json()
            
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
            return "Error: Unexpected response format from Gemini API."

        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling Gemini API: {str(e)}")
            raise

# Server startup function
def start_mcp_server(host="localhost", port=8090):
    """Start the MCP server on the specified host and port."""
    server = MCPServer(host, port)
    server_thread = threading.Thread(target=server.start, daemon=True)
    server_thread.start()
    
    # Wait for server to start up (optional)
    retry_count = 0
    max_retries = 5
    while retry_count < max_retries:
        try:
            # Try to connect to check if server is up
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((host, port))
                logger.info(f"MCP server successfully started on {host}:{port}")
                return server
        except ConnectionRefusedError:
            retry_count += 1
            if retry_count >= max_retries:
                logger.warning(f"MCP server may not have started correctly after {max_retries} attempts")
                return server
            logger.info(f"Waiting for MCP server to start (attempt {retry_count}/{max_retries})...")
            time.sleep(1)
    
    return server

if __name__ == "__main__":
    # Start the server when the script is run directly
    server = start_mcp_server()
    try:
        # Keep the main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.stop()