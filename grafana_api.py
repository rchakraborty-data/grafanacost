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