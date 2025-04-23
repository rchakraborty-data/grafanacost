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
from config import GEMINI_API_KEY, GEMINI_API_ENDPOINT
import requests
import pandas as pd

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
        logger.info(f"Initializing Grafana Cost MCP Server on {host}:{port}")
        
        # Register built-in actions
        self.register_action("get_dashboard", self.get_dashboard)
        self.register_action("execute_query", self.execute_query)
        self.register_action("analyze_cost_patterns", self.analyze_cost_patterns)
        self.register_action("generate_recommendations", self.generate_recommendations)
    
    def register_action(self, name, func):
        """Register an action function."""
        self.actions[name] = func
        logger.info(f"Registered action: {name}")
    
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
    def get_dashboard(self, uid):
        """Retrieve dashboard structure from Grafana."""
        try:
            dashboard_details = self.grafana_api.get_dashboard(uid)
            return ActionResponse(
                status="success",
                data=dashboard_details
            )
        except Exception as e:
            logger.error(f"Error fetching dashboard {uid}: {str(e)}")
            return ActionResponse(
                status="error",
                error=f"Failed to retrieve dashboard: {str(e)}"
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
                    f"Dashboard: {json.dumps(dashboard_data, indent=2)}\n\n"
                    f"Analysis: {json.dumps(analysis_results, indent=2)}"
                )
            else:
                prompt = (
                    "Analyze this Grafana dashboard structure and provide specific "
                    "cost optimization recommendations for Databricks usage. Focus on "
                    "query efficiency, resource utilization, and storage optimization.\n\n"
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
    
    def _call_gemini_api(self, prompt):
        """Call the Gemini API with the given prompt."""
        if not GEMINI_API_KEY:
            raise ValueError("Gemini API Key not configured")

        headers = {
            'Content-Type': 'application/json',
        }

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
                    return content['parts'][0].get('text', "")
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