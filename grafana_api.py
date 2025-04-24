import requests
import json
from config import GRAFANA_URL, GRAFANA_SERVICE_TOKEN, GRAFANA_ORG_ID

class GrafanaAPI:
    def __init__(self, base_url=GRAFANA_URL, service_token=GRAFANA_SERVICE_TOKEN, org_id=GRAFANA_ORG_ID):
        self.base_url = base_url
        self.headers = {
            'Authorization': f'Bearer {service_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        self.org_id = org_id

    def get_dashboard(self, dashboard_uid):
        """Get dashboard by UID"""
        url = f"{self.base_url}/api/dashboards/uid/{dashboard_uid}"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return response.json()
        else:
            response.raise_for_status()
    
    def get_dashboard_by_id(self, dashboard_id):
        """Get dashboard by numeric ID"""
        url = f"{self.base_url}/api/dashboards/id/{dashboard_id}"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return response.json()
        else:
            response.raise_for_status()
    
    def get_dashboard_panels(self, dashboard_uid):
        """Get panels from a dashboard"""
        dashboard = self.get_dashboard(dashboard_uid)
        return dashboard.get('dashboard', {}).get('panels', [])
    
    def get_all_dashboards(self):
        """Get all dashboards"""
        url = f"{self.base_url}/api/search?type=dash-db"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return response.json()
        else:
            response.raise_for_status()
    
    def get_cost_dashboards(self):
        """Get dashboards related to costs (based on title or tags)"""
        all_dashboards = self.get_all_dashboards()
        cost_dashboards = [
            d for d in all_dashboards 
            if any(cost_term in d.get('title', '').lower() 
                  for cost_term in ['cost', 'expense', 'billing', 'finance', 'budget'])
            or any(tag in d.get('tags', []) 
                  for tag in ['cost', 'expense', 'billing', 'finance', 'budget'])
        ]
        return cost_dashboards
    
    def generate_dashboard_embed_url(self, dashboard_uid, theme='light', from_time='now-7d', to_time='now'):
        """Generate URL for embedding a dashboard"""
        return f"{self.base_url}/d/{dashboard_uid}?orgId={self.org_id}&theme={theme}&from={from_time}&to={to_time}&kiosk"
    
    def get_current_time_iso(self):
        """Get current time in ISO format"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def get_cost_metrics(self, dashboard_uid, period=None):
        """Get cost metrics from a dashboard
        
        Args:
            dashboard_uid: The UID of the dashboard
            period: Time period for metrics (e.g., 'last-30-days', 'last-7-days')
            
        Returns:
            A list of cost metrics with name, value, unit, timestamp, and source
        """
        # Get dashboard panels to extract cost metrics
        panels = self.get_dashboard_panels(dashboard_uid)
        
        # Filter for panels that contain cost data
        cost_panels = [p for p in panels if any(
            term in p.get('title', '').lower() for term in 
            ['cost', 'expense', 'spend', 'budget', 'billing']
        )]
        
        # Extract metrics from panels
        metrics = []
        for panel in cost_panels:
            # In a real implementation, this would query panel data using Grafana API
            # For this example, we'll create sample metrics based on panel metadata
            panel_id = panel.get('id')
            panel_title = panel.get('title', 'Unknown')
            
            # Sample metric (in a real implementation, this would be actual panel data)
            metrics.append({
                'name': f"{panel_title}",
                'value': 100 + (panel_id * 10),  # Sample value
                'unit': 'USD',
                'timestamp': self.get_current_time_iso(),
                'source': f"panel-{panel_id}"
            })
        
        # Add total cost metric if we have cost metrics
        if metrics:
            total = sum(metric['value'] for metric in metrics)
            metrics.append({
                'name': 'Total Cost',
                'value': total,
                'unit': 'USD',
                'timestamp': self.get_current_time_iso(),
                'source': 'calculated'
            })
            
        return metrics
    
    def generate_cost_recommendations(self, dashboard_uid, metrics):
        """Generate cost optimization recommendations based on metrics
        
        Args:
            dashboard_uid: The UID of the dashboard
            metrics: List of cost metrics
            
        Returns:
            A list of cost optimization recommendations
        """
        recommendations = []
        
        # In a real implementation, this would analyze metrics and generate
        # intelligent recommendations based on cost patterns
        
        # Sample recommendations
        if metrics:
            total_cost = sum(metric.get('value', 0) for metric in metrics)
            
            if total_cost > 1000:
                recommendations.append(
                    "Consider implementing reserved instances to reduce overall cloud costs."
                )
            
            if len(metrics) > 3:
                recommendations.append(
                    "Analyze resource utilization patterns to identify idle resources that can be terminated."
                )
                
            recommendations.append(
                "Implement tagging strategy to better track and allocate costs to specific teams or projects."
            )
        
        return recommendations
    
    def get_cost_trend(self, dashboard_uid, period=None):
        """Get cost trend analysis for a dashboard
        
        Args:
            dashboard_uid: The UID of the dashboard
            period: Time period for trend analysis
            
        Returns:
            Dictionary with trend analysis data including previous and current totals,
            change percentage, breakdown by category, and cost forecast
        """
        # In a real implementation, this would query historical data and calculate trends
        
        # Get current metrics
        current_metrics = self.get_cost_metrics(dashboard_uid, period)
        current_total = sum(metric.get('value', 0) for metric in current_metrics)
        
        # For demo purposes, create sample trend data
        # In a real implementation, this would query historical data
        previous_total = current_total * 0.85  # Sample: 15% increase from previous period
        
        # Calculate change percentage
        if previous_total > 0:
            change_percentage = ((current_total - previous_total) / previous_total) * 100
        else:
            change_percentage = 0
            
        # Sample breakdown by service category
        breakdown = [
            {"category": "Compute", "value": current_total * 0.45, "percentage": 45},
            {"category": "Storage", "value": current_total * 0.30, "percentage": 30},
            {"category": "Network", "value": current_total * 0.15, "percentage": 15},
            {"category": "Other", "value": current_total * 0.10, "percentage": 10}
        ]
        
        # Sample forecast for next period
        forecast = current_total * 1.05  # Sample: 5% projected increase
        
        return {
            "previous_total": previous_total,
            "current_total": current_total,
            "change_percentage": change_percentage,
            "breakdown": breakdown,
            "forecast": forecast
        }
    
    def get_compute_cost_metrics(self, dashboard_uid, period=None):
        """Get compute-specific cost metrics from a dashboard
        
        Args:
            dashboard_uid: The UID of the dashboard
            period: Time period for metrics (e.g., 'last-30-days', 'last-7-days')
            
        Returns:
            A list of compute-specific cost metrics
        """
        # Get dashboard panels to extract compute cost metrics
        panels = self.get_dashboard_panels(dashboard_uid)
        
        # Filter for panels that contain compute cost data
        compute_panels = [p for p in panels if any(
            term in p.get('title', '').lower() for term in 
            ['compute', 'cpu', 'instance', 'vm', 'ec2', 'server']
        )]
        
        # Extract metrics from panels
        metrics = []
        for panel in compute_panels:
            panel_id = panel.get('id')
            panel_title = panel.get('title', 'Unknown')
            
            # Sample metric (in a real implementation, this would be actual panel data)
            metrics.append({
                'name': f"{panel_title}",
                'value': 75 + (panel_id * 8),  # Sample value
                'unit': 'USD',
                'timestamp': self.get_current_time_iso(),
                'cpu_usage': 65 + (panel_id % 20),  # Sample CPU usage percentage
                'memory_usage': 70 + (panel_id % 15),  # Sample memory usage percentage
                'instance_type': f"t3.{'small' if panel_id % 3 == 0 else 'medium' if panel_id % 3 == 1 else 'large'}",
                'region': f"{'us' if panel_id % 2 == 0 else 'eu'}-{'east' if panel_id % 2 == 0 else 'west'}-{1 + (panel_id % 3)}"
            })
            
        return metrics
    
    def get_storage_cost_metrics(self, dashboard_uid, period=None):
        """Get storage-specific cost metrics from a dashboard
        
        Args:
            dashboard_uid: The UID of the dashboard
            period: Time period for metrics (e.g., 'last-30-days', 'last-7-days')
            
        Returns:
            A list of storage-specific cost metrics
        """
        # Get dashboard panels to extract storage cost metrics
        panels = self.get_dashboard_panels(dashboard_uid)
        
        # Filter for panels that contain storage cost data
        storage_panels = [p for p in panels if any(
            term in p.get('title', '').lower() for term in 
            ['storage', 'disk', 's3', 'ebs', 'volume', 'blob']
        )]
        
        # Extract metrics from panels
        metrics = []
        for panel in storage_panels:
            panel_id = panel.get('id')
            panel_title = panel.get('title', 'Unknown')
            
            # Sample metric (in a real implementation, this would be actual panel data)
            metrics.append({
                'name': f"{panel_title}",
                'value': 50 + (panel_id * 5),  # Sample value
                'unit': 'USD',
                'timestamp': self.get_current_time_iso(),
                'storage_type': f"{'Standard' if panel_id % 3 == 0 else 'SSD' if panel_id % 3 == 1 else 'Archive'}",
                'volume_size': 100 + (panel_id * 50),  # Sample volume size in GB
                'read_ops': 5000 + (panel_id * 1000),  # Sample read operations
                'write_ops': 2000 + (panel_id * 500)   # Sample write operations
            })
            
        return metrics
    
    def get_network_cost_metrics(self, dashboard_uid, period=None):
        """Get network-specific cost metrics from a dashboard
        
        Args:
            dashboard_uid: The UID of the dashboard
            period: Time period for metrics (e.g., 'last-30-days', 'last-7-days')
            
        Returns:
            A list of network-specific cost metrics
        """
        # Get dashboard panels to extract network cost metrics
        panels = self.get_dashboard_panels(dashboard_uid)
        
        # Filter for panels that contain network cost data
        network_panels = [p for p in panels if any(
            term in p.get('title', '').lower() for term in 
            ['network', 'bandwidth', 'transfer', 'egress', 'ingress', 'traffic']
        )]
        
        # Extract metrics from panels
        metrics = []
        for panel in network_panels:
            panel_id = panel.get('id')
            panel_title = panel.get('title', 'Unknown')
            
            # Sample metric (in a real implementation, this would be actual panel data)
            metrics.append({
                'name': f"{panel_title}",
                'value': 30 + (panel_id * 3),  # Sample value
                'unit': 'USD',
                'timestamp': self.get_current_time_iso(),
                'data_transfer_in': 200 + (panel_id * 100),  # Sample inbound data in GB
                'data_transfer_out': 400 + (panel_id * 200),  # Sample outbound data in GB
                'region': f"{'us' if panel_id % 2 == 0 else 'eu'}-{'east' if panel_id % 2 == 0 else 'west'}-{1 + (panel_id % 3)}"
            })
            
        return metrics
    
    def get_database_cost_metrics(self, dashboard_uid, period=None):
        """Get database-specific cost metrics from a dashboard
        
        Args:
            dashboard_uid: The UID of the dashboard
            period: Time period for metrics (e.g., 'last-30-days', 'last-7-days')
            
        Returns:
            A list of database cost metrics with name, value, unit, timestamp, and source
        """
        # Get dashboard panels to extract cost metrics
        panels = self.get_dashboard_panels(dashboard_uid)
        
        # Filter for panels that contain database cost data
        db_cost_panels = [p for p in panels if any(
            term in p.get('title', '').lower() for term in 
            ['database', 'db', 'rds', 'sql', 'nosql', 'dynamo', 'cosmos', 'mongo']
        )]
        
        # Extract metrics from panels
        metrics = []
        for panel in db_cost_panels:
            # In a real implementation, this would query panel data using Grafana API
            panel_id = panel.get('id')
            panel_title = panel.get('title', 'Unknown')
            
            # Sample metric (in a real implementation, this would be actual panel data)
            metrics.append({
                'name': f"{panel_title}",
                'value': 75 + (panel_id * 5),  # Sample value
                'unit': 'USD',
                'timestamp': self.get_current_time_iso(),
                'source': f"panel-{panel_id}",
                'database_type': self._determine_database_type(panel_title),
                'database_instance_count': self._determine_database_instances(panel_id)
            })
        
        # Add total database cost metric if we have cost metrics
        if metrics:
            total = sum(metric['value'] for metric in metrics)
            metrics.append({
                'name': 'Total Database Cost',
                'value': total,
                'unit': 'USD',
                'timestamp': self.get_current_time_iso(),
                'source': 'calculated',
                'database_type': 'all',
                'database_instance_count': sum(m.get('database_instance_count', 1) for m in metrics)
            })
            
        return metrics
    
    def _determine_database_type(self, panel_title):
        """Helper method to determine database type from panel title"""
        panel_title_lower = panel_title.lower()
        if 'mysql' in panel_title_lower or 'maria' in panel_title_lower:
            return 'MySQL/MariaDB'
        elif 'postgres' in panel_title_lower:
            return 'PostgreSQL'
        elif 'sql server' in panel_title_lower or 'mssql' in panel_title_lower:
            return 'SQL Server'
        elif 'oracle' in panel_title_lower:
            return 'Oracle'
        elif 'dynamo' in panel_title_lower:
            return 'DynamoDB'
        elif 'cosmos' in panel_title_lower:
            return 'CosmosDB'
        elif 'mongo' in panel_title_lower:
            return 'MongoDB'
        elif 'redis' in panel_title_lower:
            return 'Redis'
        elif 'elastic' in panel_title_lower:
            return 'Elasticsearch'
        else:
            return 'Other'
    
    def _determine_database_instances(self, panel_id):
        """Helper method to determine database instance count (sample data)"""
        # In a real implementation, this would retrieve actual instance counts
        # For this example, we'll use the panel_id to generate a sample number
        return max(1, panel_id % 5)
    
    def get_serverless_cost_metrics(self, dashboard_uid, period=None):
        """Get serverless-specific cost metrics from a dashboard
        
        Args:
            dashboard_uid: The UID of the dashboard
            period: Time period for metrics (e.g., 'last-30-days', 'last-7-days')
            
        Returns:
            A list of serverless cost metrics with name, value, unit, timestamp, and source
        """
        # Get dashboard panels to extract cost metrics
        panels = self.get_dashboard_panels(dashboard_uid)
        
        # Filter for panels that contain serverless cost data
        serverless_cost_panels = [p for p in panels if any(
            term in p.get('title', '').lower() for term in 
            ['serverless', 'lambda', 'function', 'azure function', 'cloud function', 'fargate']
        )]
        
        # Extract metrics from panels
        metrics = []
        for panel in serverless_cost_panels:
            # In a real implementation, this would query panel data using Grafana API
            panel_id = panel.get('id')
            panel_title = panel.get('title', 'Unknown')
            
            # Sample metric (in a real implementation, this would be actual panel data)
            metrics.append({
                'name': f"{panel_title}",
                'value': 50 + (panel_id * 3),  # Sample value
                'unit': 'USD',
                'timestamp': self.get_current_time_iso(),
                'source': f"panel-{panel_id}",
                'function_type': self._determine_serverless_type(panel_title),
                'invocation_count': self._determine_serverless_invocations(panel_id),
                'avg_execution_time_ms': self._determine_serverless_execution_time(panel_id)
            })
        
        # Add total serverless cost metric if we have cost metrics
        if metrics:
            total = sum(metric['value'] for metric in metrics)
            metrics.append({
                'name': 'Total Serverless Cost',
                'value': total,
                'unit': 'USD',
                'timestamp': self.get_current_time_iso(),
                'source': 'calculated',
                'function_type': 'all',
                'invocation_count': sum(m.get('invocation_count', 0) for m in metrics),
                'avg_execution_time_ms': sum(m.get('avg_execution_time_ms', 0) * m.get('invocation_count', 0) 
                                           for m in metrics) / max(1, sum(m.get('invocation_count', 0) for m in metrics))
            })
            
        return metrics
    
    def _determine_serverless_type(self, panel_title):
        """Helper method to determine serverless function type from panel title"""
        panel_title_lower = panel_title.lower()
        if 'lambda' in panel_title_lower:
            return 'AWS Lambda'
        elif 'azure function' in panel_title_lower:
            return 'Azure Function'
        elif 'cloud function' in panel_title_lower:
            return 'Google Cloud Function'
        elif 'fargate' in panel_title_lower:
            return 'AWS Fargate'
        else:
            return 'Other Serverless'
    
    def _determine_serverless_invocations(self, panel_id):
        """Helper method to determine serverless function invocation count (sample data)"""
        # In a real implementation, this would retrieve actual invocation counts
        # For this example, we'll use the panel_id to generate a sample number
        return panel_id * 1000
    
    def _determine_serverless_execution_time(self, panel_id):
        """Helper method to determine serverless function execution time in ms (sample data)"""
        # In a real implementation, this would retrieve actual execution time
        # For this example, we'll use the panel_id to generate a sample number
        return 200 + (panel_id * 10)