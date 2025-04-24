"""
MCP Client for Grafana Cost Analyzer

This module provides a client interface to interact with the MCP server
for cost analysis and recommendations.
"""
from typing import Dict, Any, Optional, List, Union
import requests
import logging
import json
import datetime

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
    
    def execute_graphql(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a GraphQL query against the MCP server.
        
        Args:
            query: The GraphQL query string
            variables: Optional variables for the GraphQL query
            
        Returns:
            The GraphQL response data
            
        Raises:
            Exception: If the GraphQL execution fails
        """
        params = {
            "query": query,
        }
        
        if variables:
            params["variables"] = variables
            
        try:
            logger.info("Executing GraphQL query through MCP")
            return self.execute_action("graphql", params)
        except Exception as e:
            logger.error(f"Error executing GraphQL query: {str(e)}")
            raise Exception(f"GraphQL execution failed: {str(e)}")
    
    def get_cost_metrics(self, dashboard_uid: Optional[str] = None) -> Dict[str, Any]:
        """Get cost metrics using GraphQL.
        
        Args:
            dashboard_uid: Optional dashboard UID to filter metrics
            
        Returns:
            Dictionary containing cost metrics
        """
        query = """
        query GetCostMetrics($dashboardUid: String) {
            costMetrics(dashboardUid: $dashboardUid) {
                id
                name
                value
                unit
                trend
                comparisonPeriod
            }
        }
        """
        
        variables = {}
        if dashboard_uid:
            variables["dashboardUid"] = dashboard_uid
            
        try:
            result = self.execute_graphql(query, variables)
            return result.get("costMetrics", [])
        except Exception as e:
            logger.error(f"Error getting cost metrics: {str(e)}")
            raise
    
    def get_cost_trend(self, metric_id: str, period: str = "30d") -> Dict[str, Any]:
        """Get cost trend data using GraphQL.
        
        Args:
            metric_id: The ID of the cost metric
            period: Time period for trend analysis (e.g., "7d", "30d", "90d")
            
        Returns:
            Dictionary containing trend data
        """
        query = """
        query GetCostTrend($metricId: String!, $period: String) {
            costTrend(metricId: $metricId, period: $period) {
                metricId
                trendData {
                    date
                    value
                }
                changePercentage
                anomalies {
                    date
                    value
                    description
                }
            }
        }
        """
        
        variables = {
            "metricId": metric_id,
            "period": period
        }
            
        try:
            result = self.execute_graphql(query, variables)
            return result.get("costTrend", {})
        except Exception as e:
            logger.error(f"Error getting cost trend: {str(e)}")
            raise
    
    def get_dashboard_analysis(self, dashboard_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get a complete analysis of a dashboard.
        
        This is a convenience method that chains multiple MCP actions
        to provide a complete dashboard analysis.
        
        Args:
            dashboard_data: The Grafana dashboard structure
            
        Returns:
            Dictionary containing the analysis results
        """
        try:
            # Step 1: Retrieve dashboard
            dashboard_data = self.execute_action("get_dashboard", {"data": dashboard_data})
            
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
                if hasattr(value, 'to_dict'):
                    # Convert pandas DataFrame to dictionary
                    serializable_results[key] = value.to_dict(orient='records')
                else:
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
    
    # Extended specialized cost analysis methods
    
    def get_compute_cost_metrics(self, resource_type: Optional[str] = None, period: str = "30d") -> Dict[str, Any]:
        """Get specialized compute cost metrics using GraphQL.
        
        Args:
            resource_type: Optional resource type filter (e.g., "VM", "Container", "Serverless")
            period: Time period for metrics (e.g., "7d", "30d", "90d")
            
        Returns:
            Dictionary containing compute cost metrics
        """
        query = """
        query GetComputeCostMetrics($resourceType: String, $period: String) {
            computeCostMetrics(resourceType: $resourceType, period: $period) {
                id
                name
                value
                unit
                resourceType
                utilizationPercentage
                trendPercentage
                instanceCount
                recommendations {
                    id
                    description
                    potentialSavings
                    confidence
                }
            }
        }
        """
        
        variables = {"period": period}
        if resource_type:
            variables["resourceType"] = resource_type
            
        try:
            result = self.execute_graphql(query, variables)
            return result.get("computeCostMetrics", [])
        except Exception as e:
            logger.error(f"Error getting compute cost metrics: {str(e)}")
            raise
    
    def get_storage_cost_metrics(self, storage_type: Optional[str] = None, period: str = "30d") -> Dict[str, Any]:
        """Get specialized storage cost metrics using GraphQL.
        
        Args:
            storage_type: Optional storage type filter (e.g., "Block", "Object", "File")
            period: Time period for metrics (e.g., "7d", "30d", "90d")
            
        Returns:
            Dictionary containing storage cost metrics
        """
        query = """
        query GetStorageCostMetrics($storageType: String, $period: String) {
            storageCostMetrics(storageType: $storageType, period: $period) {
                id
                name
                value
                unit
                storageType
                capacityGB
                usedCapacityGB
                utilizationPercentage
                costPerGB
                recommendations {
                    id
                    description
                    potentialSavings
                    confidence
                }
            }
        }
        """
        
        variables = {"period": period}
        if storage_type:
            variables["storageType"] = storage_type
            
        try:
            result = self.execute_graphql(query, variables)
            return result.get("storageCostMetrics", [])
        except Exception as e:
            logger.error(f"Error getting storage cost metrics: {str(e)}")
            raise
    
    def get_network_cost_metrics(self, traffic_type: Optional[str] = None, period: str = "30d") -> Dict[str, Any]:
        """Get specialized network cost metrics using GraphQL.
        
        Args:
            traffic_type: Optional traffic type filter (e.g., "Ingress", "Egress", "Inter-zone")
            period: Time period for metrics (e.g., "7d", "30d", "90d")
            
        Returns:
            Dictionary containing network cost metrics
        """
        query = """
        query GetNetworkCostMetrics($trafficType: String, $period: String) {
            networkCostMetrics(trafficType: $trafficType, period: $period) {
                id
                name
                value
                unit
                trafficType
                dataTransferredGB
                costPerGB
                trendPercentage
                recommendations {
                    id
                    description
                    potentialSavings
                    confidence
                }
            }
        }
        """
        
        variables = {"period": period}
        if traffic_type:
            variables["trafficType"] = traffic_type
            
        try:
            result = self.execute_graphql(query, variables)
            return result.get("networkCostMetrics", [])
        except Exception as e:
            logger.error(f"Error getting network cost metrics: {str(e)}")
            raise
    
    def get_database_cost_metrics(self, database_type: Optional[str] = None, period: str = "30d") -> Dict[str, Any]:
        """Get specialized database cost metrics using GraphQL.
        
        Args:
            database_type: Optional database type filter (e.g., "SQL", "NoSQL", "Data Warehouse")
            period: Time period for metrics (e.g., "7d", "30d", "90d")
            
        Returns:
            Dictionary containing database cost metrics
        """
        query = """
        query GetDatabaseCostMetrics($databaseType: String, $period: String) {
            databaseCostMetrics(databaseType: $databaseType, period: $period) {
                id
                name
                value
                unit
                databaseType
                instanceCount
                provisionedIOPS
                storageSize
                utilizationPercentage
                queryPerformance
                costEfficiency
                recommendations {
                    id
                    description
                    potentialSavings
                    confidence
                    implementationComplexity
                }
            }
        }
        """
        
        variables = {"period": period}
        if database_type:
            variables["databaseType"] = database_type
            
        try:
            result = self.execute_graphql(query, variables)
            return result.get("databaseCostMetrics", [])
        except Exception as e:
            logger.error(f"Error getting database cost metrics: {str(e)}")
            raise
    
    def get_serverless_cost_metrics(self, function_type: Optional[str] = None, period: str = "30d") -> Dict[str, Any]:
        """Get specialized serverless cost metrics using GraphQL.
        
        Args:
            function_type: Optional function type filter (e.g., "Lambda", "Azure Functions", "Cloud Run")
            period: Time period for metrics (e.g., "7d", "30d", "90d")
            
        Returns:
            Dictionary containing serverless cost metrics
        """
        query = """
        query GetServerlessCostMetrics($functionType: String, $period: String) {
            serverlessCostMetrics(functionType: $functionType, period: $period) {
                id
                name
                value
                unit
                functionType
                invocationCount
                executionTime
                memoryUsage
                coldStarts
                costPerInvocation
                costPerGBSecond
                recommendations {
                    id
                    description
                    potentialSavings
                    confidence
                    implementationComplexity
                }
            }
        }
        """
        
        variables = {"period": period}
        if function_type:
            variables["functionType"] = function_type
            
        try:
            result = self.execute_graphql(query, variables)
            return result.get("serverlessCostMetrics", [])
        except Exception as e:
            logger.error(f"Error getting serverless cost metrics: {str(e)}")
            raise