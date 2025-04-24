"""
Grafana GraphQL MCP Implementation

This module provides an implementation of the MCP GraphQL interface for Grafana
based on the specification from https://github.com/grafana/mcp-grafana
"""
import graphene
from typing import Dict, Any, List, Optional
from grafana_api import GrafanaAPI
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# GraphQL Types for Grafana resources
class Panel(graphene.ObjectType):
    """Represents a Grafana dashboard panel"""
    id = graphene.ID()
    title = graphene.String()
    type = graphene.String()
    description = graphene.String()
    datasource = graphene.String()
    targets = graphene.List(lambda: graphene.JSONString)

class Dashboard(graphene.ObjectType):
    """Represents a Grafana dashboard"""
    uid = graphene.ID()
    id = graphene.Int()
    title = graphene.String()
    url = graphene.String()
    tags = graphene.List(graphene.String)
    panels = graphene.List(Panel)
    
    def resolve_panels(self, info):
        """Resolver for panels field"""
        panels_data = self.get('panels', [])
        return [Panel(
            id=panel.get('id'),
            title=panel.get('title'),
            type=panel.get('type'),
            description=panel.get('description', ''),
            datasource=panel.get('datasource', {}).get('uid', '') if isinstance(panel.get('datasource'), dict) else panel.get('datasource', ''),
            targets=panel.get('targets', [])
        ) for panel in panels_data]

class DashboardSearchResult(graphene.ObjectType):
    """Represents a dashboard in search results"""
    uid = graphene.ID()
    id = graphene.Int()
    title = graphene.String()
    url = graphene.String()
    type = graphene.String()
    tags = graphene.List(graphene.String)
    is_starred = graphene.Boolean()

class CostMetric(graphene.ObjectType):
    """Represents a cost metric from Grafana"""
    name = graphene.String()
    value = graphene.Float()
    unit = graphene.String()
    timestamp = graphene.String()
    source = graphene.String()
    
class ComputeCostMetric(graphene.ObjectType):
    """Represents a compute-specific cost metric"""
    name = graphene.String()
    value = graphene.Float()
    unit = graphene.String()
    timestamp = graphene.String()
    cpu_usage = graphene.Float()
    memory_usage = graphene.Float()
    instance_type = graphene.String()
    region = graphene.String()
    
class StorageCostMetric(graphene.ObjectType):
    """Represents a storage-specific cost metric"""
    name = graphene.String()
    value = graphene.Float()
    unit = graphene.String()
    timestamp = graphene.String()
    storage_type = graphene.String()
    volume_size = graphene.Float()
    read_ops = graphene.Int()
    write_ops = graphene.Int()
    
class NetworkCostMetric(graphene.ObjectType):
    """Represents a network-specific cost metric"""
    name = graphene.String()
    value = graphene.Float()
    unit = graphene.String()
    timestamp = graphene.String()
    data_transfer_in = graphene.Float()
    data_transfer_out = graphene.Float()
    region = graphene.String()
    
class DatabaseCostMetric(graphene.ObjectType):
    """Represents a database-specific cost metric"""
    name = graphene.String()
    value = graphene.Float()
    unit = graphene.String()
    timestamp = graphene.String()
    db_type = graphene.String()
    instance_size = graphene.String()
    storage_allocated = graphene.Float()
    io_operations = graphene.Int()
    backup_storage = graphene.Float()
    
class ServerlessCostMetric(graphene.ObjectType):
    """Represents a serverless-specific cost metric"""
    name = graphene.String()
    value = graphene.Float()
    unit = graphene.String()
    timestamp = graphene.String()
    invocations = graphene.Int()
    execution_duration = graphene.Float()
    memory_configured = graphene.Int()
    region = graphene.String()
    
class CostReport(graphene.ObjectType):
    """Represents a cost analysis report"""
    id = graphene.ID()
    title = graphene.String()
    dashboard_uid = graphene.String()
    creation_date = graphene.String()
    metrics = graphene.List(CostMetric)
    total_cost = graphene.Float()
    period = graphene.String()
    recommendations = graphene.String()
    
class CostTrend(graphene.ObjectType):
    """Represents a cost trend analysis"""
    period = graphene.String()
    previous_total = graphene.Float()
    current_total = graphene.Float() 
    change_percentage = graphene.Float()
    breakdown = graphene.List(graphene.JSONString)
    forecast = graphene.Float()

# Input types for mutations
class PanelInput(graphene.InputObjectType):
    """Input type for panel creation/updates"""
    title = graphene.String(required=True)
    type = graphene.String(required=True)
    description = graphene.String()
    datasource = graphene.String()
    targets = graphene.List(graphene.JSONString)

class DashboardInput(graphene.InputObjectType):
    """Input type for dashboard creation/updates"""
    title = graphene.String(required=True)
    tags = graphene.List(graphene.String)
    panels = graphene.List(PanelInput)

# Mutation response types
class DashboardMutationResponse(graphene.ObjectType):
    """Response for dashboard mutations"""
    success = graphene.Boolean()
    message = graphene.String()
    dashboard = graphene.Field(Dashboard)

class Query(graphene.ObjectType):
    """Root query object for Grafana GraphQL API"""
    dashboard = graphene.Field(
        Dashboard,
        uid=graphene.String(required=True),
        description="Get a dashboard by UID"
    )
    dashboards = graphene.List(
        DashboardSearchResult,
        query=graphene.String(),
        tag=graphene.String(),
        limit=graphene.Int(),
        description="Search for dashboards"
    )
    cost_dashboards = graphene.List(
        DashboardSearchResult,
        description="Get dashboards related to costs"
    )
    
    cost_report = graphene.Field(
        CostReport,
        dashboard_uid=graphene.String(required=True),
        period=graphene.String(),
        description="Get a cost analysis report for a dashboard"
    )
    
    cost_trend = graphene.Field(
        CostTrend,
        dashboard_uid=graphene.String(required=True),
        period=graphene.String(),
        description="Get cost trend analysis for a dashboard"
    )
    
    cost_metrics = graphene.List(
        CostMetric,
        dashboard_uid=graphene.String(required=True),
        period=graphene.String(),
        description="Get cost metrics for a dashboard"
    )
    
    compute_cost_metrics = graphene.List(
        ComputeCostMetric,
        dashboard_uid=graphene.String(required=True),
        period=graphene.String(),
        description="Get compute-specific cost metrics for a dashboard"
    )
    
    storage_cost_metrics = graphene.List(
        StorageCostMetric,
        dashboard_uid=graphene.String(required=True),
        period=graphene.String(),
        description="Get storage-specific cost metrics for a dashboard"
    )
    
    network_cost_metrics = graphene.List(
        NetworkCostMetric,
        dashboard_uid=graphene.String(required=True),
        period=graphene.String(),
        description="Get network-specific cost metrics for a dashboard"
    )
    
    database_cost_metrics = graphene.List(
        DatabaseCostMetric,
        dashboard_uid=graphene.String(required=True),
        period=graphene.String(),
        description="Get database-specific cost metrics for a dashboard"
    )
    
    serverless_cost_metrics = graphene.List(
        ServerlessCostMetric,
        dashboard_uid=graphene.String(required=True),
        period=graphene.String(),
        description="Get serverless-specific cost metrics for a dashboard"
    )
    
    cost_breakdown = graphene.Field(
        graphene.JSONString,
        dashboard_uid=graphene.String(required=True),
        period=graphene.String(),
        groupby=graphene.String(),
        description="Get cost breakdown by service, region, or resource type"
    )
    
    cost_anomalies = graphene.List(
        graphene.JSONString,
        dashboard_uid=graphene.String(required=True),
        period=graphene.String(),
        threshold=graphene.Float(),
        description="Get cost anomalies detected in the specified period"
    )

class Mutation(graphene.ObjectType):
    """Root mutation object for Grafana GraphQL API"""
    create_dashboard = graphene.Field(
        DashboardMutationResponse,
        input=DashboardInput(required=True),
        description="Create a new dashboard"
    )
    
    update_dashboard = graphene.Field(
        DashboardMutationResponse,
        uid=graphene.String(required=True),
        input=DashboardInput(required=True),
        description="Update an existing dashboard"
    )
    
    delete_dashboard = graphene.Field(
        DashboardMutationResponse,
        uid=graphene.String(required=True),
        description="Delete a dashboard"
    )
    
    def resolve_create_dashboard(self, info, input):
        """Resolver for creating a new dashboard"""
        api = GrafanaAPI()
        try:
            # Prepare dashboard data
            dashboard_data = {
                "title": input.title,
                "tags": input.tags or [],
                "panels": []
            }
            
            # Add panels if provided
            if input.panels:
                for i, panel_input in enumerate(input.panels):
                    panel = {
                        "id": i + 1,  # Simple ID assignment
                        "title": panel_input.title,
                        "type": panel_input.type,
                    }
                    
                    if panel_input.description:
                        panel["description"] = panel_input.description
                    
                    if panel_input.datasource:
                        panel["datasource"] = panel_input.datasource
                    
                    if panel_input.targets:
                        panel["targets"] = panel_input.targets
                    
                    dashboard_data["panels"].append(panel)
            
            # Create dashboard in Grafana
            result = api.create_dashboard(dashboard_data)
            
            # Get the created dashboard for the response
            dashboard = api.get_dashboard(result.get('uid'))
            dashboard_meta = dashboard.get('meta', {})
            dashboard_data = dashboard.get('dashboard', {})
            
            return DashboardMutationResponse(
                success=True,
                message="Dashboard created successfully",
                dashboard=Dashboard(
                    uid=result.get('uid'),
                    id=dashboard_meta.get('id'),
                    title=dashboard_data.get('title'),
                    url=dashboard_meta.get('url', ''),
                    tags=dashboard_data.get('tags', []),
                    panels=dashboard_data.get('panels', [])
                )
            )
        except Exception as e:
            logger.error(f"Error creating dashboard: {str(e)}")
            return DashboardMutationResponse(
                success=False,
                message=f"Failed to create dashboard: {str(e)}",
                dashboard=None
            )
    
    def resolve_update_dashboard(self, info, uid, input):
        """Resolver for updating a dashboard"""
        api = GrafanaAPI()
        try:
            # First, get the existing dashboard
            existing_dashboard = api.get_dashboard(uid)
            if not existing_dashboard:
                return DashboardMutationResponse(
                    success=False,
                    message=f"Dashboard with UID {uid} not found",
                    dashboard=None
                )
            
            # Prepare update data, preserving existing structure
            dashboard_data = existing_dashboard.get('dashboard', {})
            dashboard_data['title'] = input.title
            
            if input.tags is not None:
                dashboard_data['tags'] = input.tags
            
            if input.panels:
                # Replace panels if provided
                new_panels = []
                for i, panel_input in enumerate(input.panels):
                    panel = {
                        "id": i + 1,
                        "title": panel_input.title,
                        "type": panel_input.type,
                    }
                    
                    if panel_input.description:
                        panel["description"] = panel_input.description
                    
                    if panel_input.datasource:
                        panel["datasource"] = panel_input.datasource
                    
                    if panel_input.targets:
                        panel["targets"] = panel_input.targets
                    
                    new_panels.append(panel)
                
                dashboard_data["panels"] = new_panels
            
            # Update the dashboard
            result = api.update_dashboard(uid, dashboard_data)
            
            # Get the updated dashboard for the response
            updated_dashboard = api.get_dashboard(uid)
            dashboard_meta = updated_dashboard.get('meta', {})
            dashboard_data = updated_dashboard.get('dashboard', {})
            
            return DashboardMutationResponse(
                success=True,
                message="Dashboard updated successfully",
                dashboard=Dashboard(
                    uid=uid,
                    id=dashboard_meta.get('id'),
                    title=dashboard_data.get('title'),
                    url=dashboard_meta.get('url', ''),
                    tags=dashboard_data.get('tags', []),
                    panels=dashboard_data.get('panels', [])
                )
            )
        except Exception as e:
            logger.error(f"Error updating dashboard: {str(e)}")
            return DashboardMutationResponse(
                success=False,
                message=f"Failed to update dashboard: {str(e)}",
                dashboard=None
            )
    
    def resolve_delete_dashboard(self, info, uid):
        """Resolver for deleting a dashboard"""
        api = GrafanaAPI()
        try:
            # First, get the dashboard to return in the response
            dashboard_before_delete = api.get_dashboard(uid)
            if not dashboard_before_delete:
                return DashboardMutationResponse(
                    success=False,
                    message=f"Dashboard with UID {uid} not found",
                    dashboard=None
                )
            
            dashboard_meta = dashboard_before_delete.get('meta', {})
            dashboard_data = dashboard_before_delete.get('dashboard', {})
            
            # Delete the dashboard
            api.delete_dashboard(uid)
            
            return DashboardMutationResponse(
                success=True,
                message="Dashboard deleted successfully",
                dashboard=Dashboard(
                    uid=uid,
                    id=dashboard_meta.get('id'),
                    title=dashboard_data.get('title'),
                    url=dashboard_meta.get('url', ''),
                    tags=dashboard_data.get('tags', []),
                    panels=dashboard_data.get('panels', [])
                )
            )
        except Exception as e:
            logger.error(f"Error deleting dashboard: {str(e)}")
            return DashboardMutationResponse(
                success=False,
                message=f"Failed to delete dashboard: {str(e)}",
                dashboard=None
            )
    
    def resolve_database_cost_metrics(self, info, dashboard_uid, period="30d"):
        """Resolver for database_cost_metrics query"""
        api = info.context.get('grafana_api', self.grafana_api)
        try:
            # Get database cost metrics from Grafana API
            metrics = api.get_database_cost_metrics(dashboard_uid, period)
            
            # Convert to GraphQL type
            results = []
            for metric in metrics:
                results.append(DatabaseCostMetric(
                    name=metric.get('name'),
                    value=metric.get('value'),
                    unit=metric.get('unit'),
                    timestamp=metric.get('timestamp'),
                    db_type=metric.get('dbType'),
                    instance_size=metric.get('instanceSize'),
                    storage_allocated=metric.get('storageAllocated'),
                    io_operations=metric.get('ioOperations'),
                    backup_storage=metric.get('backupStorage')
                ))
            return results
        except Exception as e:
            logger.error(f"Error fetching database cost metrics for dashboard {dashboard_uid}: {str(e)}")
            return []
    
    def resolve_serverless_cost_metrics(self, info, dashboard_uid, period="30d"):
        """Resolver for serverless_cost_metrics query"""
        api = info.context.get('grafana_api', self.grafana_api)
        try:
            # Get serverless cost metrics from Grafana API
            metrics = api.get_serverless_cost_metrics(dashboard_uid, period)
            
            # Convert to GraphQL type
            results = []
            for metric in metrics:
                results.append(ServerlessCostMetric(
                    name=metric.get('name'),
                    value=metric.get('value'),
                    unit=metric.get('unit'),
                    timestamp=metric.get('timestamp'),
                    invocations=metric.get('invocations'),
                    execution_duration=metric.get('executionDuration'),
                    memory_configured=metric.get('memoryConfigured'),
                    region=metric.get('region')
                ))
            return results
        except Exception as e:
            logger.error(f"Error fetching serverless cost metrics for dashboard {dashboard_uid}: {str(e)}")
            return []

# Create the GraphQL schema with both Query and Mutation
grafana_schema = graphene.Schema(query=Query, mutation=Mutation)

class GrafanaMCPGraphQL:
    """Handles GraphQL operations for Grafana through MCP"""
    
    def __init__(self, grafana_api=None):
        """Initialize the GraphQL handler with an optional Grafana API instance"""
        self.grafana_api = grafana_api or GrafanaAPI()
    
    def execute_query(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a GraphQL query against the Grafana schema
        
        Args:
            query: The GraphQL query string
            variables: Optional variables for the query
            
        Returns:
            The query execution result
        """
        result = grafana_schema.execute(query, variable_values=variables or {})
        
        # Handle errors
        if result.errors:
            errors = [str(error) for error in result.errors]
            logger.error(f"GraphQL query execution errors: {errors}")
            return {
                "data": result.data,
                "errors": errors
            }
        
        return {"data": result.data}

    def get_dashboard_example(self, uid: str) -> str:
        """Example query to get a dashboard by UID
        
        Returns the GraphQL query string that can be used as an example
        """
        return """
        query GetDashboard($uid: String!) {
            dashboard(uid: $uid) {
                uid
                id
                title
                url
                tags
                panels {
                    id
                    title
                    type
                    description
                    datasource
                    targets
                }
            }
        }
        """
    
    def search_dashboards_example(self) -> str:
        """Example query to search for dashboards
        
        Returns the GraphQL query string that can be used as an example
        """
        return """
        query SearchDashboards($query: String, $tag: String, $limit: Int) {
            dashboards(query: $query, tag: $tag, limit: $limit) {
                uid
                id
                title
                url
                tags
                type
                is_starred
            }
        }
        """
    
    def create_dashboard_example(self) -> str:
        """Example mutation to create a dashboard
        
        Returns the GraphQL mutation string that can be used as an example
        """
        return """
        mutation CreateDashboard($input: DashboardInput!) {
            createDashboard(input: $input) {
                success
                message
                dashboard {
                    uid
                    id
                    title
                    url
                    tags
                }
            }
        }
        """
    
    def update_dashboard_example(self) -> str:
        """Example mutation to update a dashboard
        
        Returns the GraphQL mutation string that can be used as an example
        """
        return """
        mutation UpdateDashboard($uid: String!, $input: DashboardInput!) {
            updateDashboard(uid: $uid, input: $input) {
                success
                message
                dashboard {
                    uid
                    id
                    title
                    url
                    tags
                }
            }
        }
        """