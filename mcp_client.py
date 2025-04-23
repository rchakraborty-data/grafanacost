"""
MCP Client for Grafana Cost Analyzer

This module provides a client interface to interact with the MCP server
for cost analysis and recommendations.
"""

import json
import logging
import requests
import pandas as pd
import datetime
from typing import Dict, Any, Optional, List, Union

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Custom JSON encoder to handle non-serializable types
class MCPJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles pandas and datetime objects."""
    
    def default(self, obj):
        # Handle datetime objects
        if isinstance(obj, (datetime.datetime, datetime.date, datetime.time)):
            return obj.isoformat()
        # Handle any other non-serializable types
        try:
            return super().default(obj)
        except TypeError:
            return str(obj)  # Convert any other non-serializable objects to strings

class MCPClient:
    """Client for interacting with the Grafana Cost MCP Server."""
    
    def __init__(self, host: str = "localhost", port: int = 8090):
        """Initialize the MCP client.
        
        Args:
            host: The host where the MCP server is running
            port: The port on which the MCP server is listening
        """
        self.base_url = f"http://{host}:{port}"
        logger.info(f"Initializing MCP client for server at {self.base_url}")
    
    def execute_action(self, action_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an action on the MCP server.
        
        Args:
            action_name: The name of the action to execute
            params: Parameters for the action
            
        Returns:
            The response from the MCP server
            
        Raises:
            Exception: If the action execution fails
        """
        url = f"{self.base_url}/actions/{action_name}"
        
        try:
            logger.info(f"Executing MCP action: {action_name}")
            
            # Use our custom JSON encoder to handle non-serializable types like dates
            json_data = json.dumps(params, cls=MCPJSONEncoder)
            
            response = requests.post(
                url,
                data=json_data,  # Use pre-encoded JSON string
                headers={"Content-Type": "application/json"},
                timeout=300  # Longer timeout for AI operations
            )
            response.raise_for_status()
            
            result = response.json()
            
            if result.get("status") == "success":
                logger.info(f"Successfully executed MCP action: {action_name}")
                return result.get("data", {})
            else:
                error_message = result.get("error", "Unknown error")
                logger.error(f"MCP action {action_name} failed: {error_message}")
                raise Exception(f"MCP action failed: {error_message}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error communicating with MCP server: {str(e)}")
            raise Exception(f"MCP communication error: {str(e)}")
    
    def get_dashboard_analysis(self, uid: str) -> Dict[str, Any]:
        """Get a complete analysis of a dashboard.
        
        This is a convenience method that chains multiple MCP actions
        to provide a complete dashboard analysis.
        
        Args:
            uid: The unique identifier of the Grafana dashboard
            
        Returns:
            Dictionary containing the analysis results
        """
        try:
            # Step 1: Retrieve dashboard
            dashboard_data = self.execute_action("get_dashboard", {"uid": uid})
            
            # Step 2: Generate recommendations based on dashboard structure
            recommendations = self.execute_action(
                "generate_recommendations", 
                {"dashboard_data": dashboard_data}
            )
            
            return {
                "dashboard": dashboard_data.get("dashboard", {}),
                "recommendations": recommendations.get("recommendations", ""),
                "format": recommendations.get("format", "markdown")
            }
            
        except Exception as e:
            logger.error(f"Error getting dashboard analysis: {str(e)}")
            raise
    
    def analyze_query_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze query results for cost patterns.
        
        Args:
            results: Dictionary containing query results
            
        Returns:
            Dictionary containing the analysis results
        """
        try:
            # Convert any DataFrame objects to JSON-serializable dictionaries
            serializable_results = {}
            
            for key, value in results.items():
                if isinstance(value, pd.DataFrame):
                    # Convert DataFrame to a dictionary representation
                    serializable_results[key] = {
                        "type": "dataframe",
                        "rows": value.shape[0],
                        "columns": list(value.columns),
                        "data": value.to_dict(orient="records")
                    }
                    logger.info(f"Converted DataFrame '{key}' with {value.shape[0]} rows to serializable format")
                else:
                    # Keep non-DataFrame values as they are
                    serializable_results[key] = value
            
            # Analyze cost patterns using serializable data
            patterns = self.execute_action(
                "analyze_cost_patterns",
                {"data": serializable_results}
            )
            
            return {
                "analysis": patterns.get("analysis", ""),
                "patterns_identified": patterns.get("patterns_identified", False)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing query results: {str(e)}")
            raise
    
    def get_recommendations_from_analysis(self, 
                                        dashboard_data: Dict[str, Any],
                                        analysis_results: Dict[str, Any]) -> str:
        """Get recommendations based on dashboard data and analysis results.
        
        Args:
            dashboard_data: The Grafana dashboard structure
            analysis_results: Results from query analysis
            
        Returns:
            String containing recommendations in Markdown format
        """
        try:
            recommendations = self.execute_action(
                "generate_recommendations",
                {
                    "dashboard_data": dashboard_data,
                    "analysis_results": analysis_results
                }
            )
            
            return recommendations.get("recommendations", "")
            
        except Exception as e:
            logger.error(f"Error getting recommendations: {str(e)}")
            raise