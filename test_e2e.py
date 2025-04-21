import unittest
import requests
import os
import json
import re
from unittest import mock
from dotenv import load_dotenv
from app import app
from grafana_api import GrafanaAPI

# Load environment variables
load_dotenv()

class GrafanaCostDashboardE2ETests(unittest.TestCase):
    """End-to-end tests for the Grafana Cost Dashboard application"""
    
    @classmethod
    def setUpClass(cls):
        """Set up the test environment once before all tests"""
        # Configure the Flask application for testing
        app.config['TESTING'] = True
        cls.client = app.test_client()
        
        # Get configuration from environment
        cls.grafana_url = os.environ.get('GRAFANA_URL')
        cls.grafana_token = os.environ.get('GRAFANA_SERVICE_TOKEN')
        cls.dashboard_id = os.environ.get('GRAFANA_COST_DASHBOARD_ID')
        
        # Validate that required environment variables are set
        if not all([cls.grafana_url, cls.grafana_token, cls.dashboard_id]):
            raise ValueError("Missing required environment variables. Please check your .env file.")
        
        # Set up headers for Grafana API requests
        cls.grafana_headers = {
            'Authorization': f'Bearer {cls.grafana_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        # Initialize the API client
        cls.grafana_api = GrafanaAPI()
    
    def test_homepage_loads(self):
        """Test that the homepage loads successfully"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Cost Dashboard', response.data)
    
    def test_default_dashboard_redirect(self):
        """Test that the default dashboard redirect works"""
        response = self.client.get('/default-cost-dashboard', follow_redirects=False)
        self.assertEqual(response.status_code, 302)  # 302 is redirect
        self.assertIn(f'/dashboard/{self.dashboard_id}', response.location)
    
    def test_dashboard_page_loads(self):
        """Test that the dashboard page loads successfully"""
        response = self.client.get(f'/dashboard/{self.dashboard_id}')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'iframe', response.data)  # Check that the iframe is present
    
    def test_api_cost_dashboards(self):
        """Test the API endpoint for cost dashboards"""
        response = self.client.get('/api/dashboards/cost')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIsInstance(data, list)  # Should return a list of dashboards
    
    def test_direct_grafana_api_access(self):
        """Test direct access to Grafana API to validate credentials"""
        url = f"{self.grafana_url}/api/dashboards/uid/{self.dashboard_id}"
        response = requests.get(url, headers=self.grafana_headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('dashboard', data)
        self.assertIn('meta', data)
    
    def test_grafana_token_permissions(self):
        """Test that the Grafana token has the necessary permissions"""
        # Test access to search API
        search_url = f"{self.grafana_url}/api/search?type=dash-db"
        response = requests.get(search_url, headers=self.grafana_headers)
        self.assertEqual(response.status_code, 200)
        
        # Test access to dashboard by UID
        dashboard_url = f"{self.grafana_url}/api/dashboards/uid/{self.dashboard_id}"
        response = requests.get(dashboard_url, headers=self.grafana_headers)
        self.assertEqual(response.status_code, 200)
    
    def test_grafana_dashboard_content(self):
        """Test that the Grafana dashboard contains expected content"""
        url = f"{self.grafana_url}/api/dashboards/uid/{self.dashboard_id}"
        response = requests.get(url, headers=self.grafana_headers)
        self.assertEqual(response.status_code, 200)
        
        dashboard_data = response.json().get('dashboard', {})
        
        # Verify dashboard has panels
        self.assertIn('panels', dashboard_data)
        self.assertTrue(len(dashboard_data['panels']) > 0)
        
        # Check if dashboard has cost-related content
        dashboard_json = json.dumps(dashboard_data).lower()
        cost_terms = ['cost', 'expense', 'billing', 'budget', 'finance']
        self.assertTrue(any(term in dashboard_json for term in cost_terms), 
                        "Dashboard doesn't contain any cost-related terms")
    
    def test_dashboard_embed_url_generation(self):
        """Test that the dashboard embed URL is correctly generated"""
        response = self.client.get(f'/dashboard/{self.dashboard_id}')
        self.assertEqual(response.status_code, 200)
        
        # Extract the iframe src URL from the response
        iframe_src_match = re.search(rb'<iframe[^>]*src="([^"]*)"', response.data)
        self.assertIsNotNone(iframe_src_match, "No iframe found in dashboard page")
        
        embed_url = iframe_src_match.group(1).decode('utf-8')
        
        # Verify embed URL parameters
        self.assertIn(f'd/{self.dashboard_id}', embed_url)
        self.assertIn('orgId=', embed_url)
        self.assertIn('theme=', embed_url)
        self.assertIn('from=', embed_url)
        self.assertIn('to=', embed_url)
        self.assertIn('kiosk', embed_url)
    
    def test_dashboard_with_custom_time_range(self):
        """Test that custom time ranges are correctly applied to the dashboard"""
        custom_from = 'now-30d'
        custom_to = 'now'
        
        response = self.client.get(
            f'/dashboard/{self.dashboard_id}?from={custom_from}&to={custom_to}'
        )
        self.assertEqual(response.status_code, 200)
        
        # Check that the custom time range is included in the iframe URL
        self.assertIn(f'from={custom_from}'.encode(), response.data)
        self.assertIn(f'to={custom_to}'.encode(), response.data)
    
    def test_dashboard_with_custom_theme(self):
        """Test that custom theme is correctly applied to the dashboard"""
        custom_theme = 'dark'
        
        response = self.client.get(
            f'/dashboard/{self.dashboard_id}?theme={custom_theme}'
        )
        self.assertEqual(response.status_code, 200)
        
        # Check that the custom theme is included in the iframe URL
        self.assertIn(f'theme={custom_theme}'.encode(), response.data)
    
    def test_dashboard_panels_api_access(self):
        """Test that we can access panels via API and validate their structure"""
        panels = self.grafana_api.get_dashboard_panels(self.dashboard_id)
        
        # Verify panels structure and content
        self.assertIsInstance(panels, list)
        if panels:  # Only check if there are panels
            sample_panel = panels[0]
            # Check for common panel attributes
            self.assertIn('id', sample_panel)
            self.assertIn('title', sample_panel)
            self.assertIn('type', sample_panel)
    
    def test_dashboard_metrics_data_structure(self):
        """Test that dashboard metrics data has the expected structure"""
        dashboard_data = self.grafana_api.get_dashboard(self.dashboard_id)
        
        self.assertIn('dashboard', dashboard_data)
        dashboard = dashboard_data['dashboard']
        
        required_props = ['id', 'uid', 'title', 'panels', 'time', 'timezone', 'schemaVersion']
        for prop in required_props:
            self.assertIn(prop, dashboard, f"Dashboard is missing '{prop}' property")
        
        self.assertIn('from', dashboard['time'])
        self.assertIn('to', dashboard['time'])
        
        if len(dashboard['panels']) > 0:
            cost_related_panels = 0
            for panel in dashboard['panels']:
                panel_json = json.dumps(panel).lower()
                if any(term in panel_json for term in ['cost', 'expense', 'billing', 'budget', 'finance']):
                    cost_related_panels += 1
                    
                self.assertIn('id', panel)
                self.assertIn('title', panel)
            
            self.assertGreater(cost_related_panels, 0, "No cost-related panels found in the dashboard")
    
    def test_error_handling_invalid_dashboard(self):
        """Test application's handling of invalid dashboard ID"""
        invalid_id = 'non-existent-dashboard-id'
        
        response = self.client.get(f'/dashboard/{invalid_id}')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'error', response.data.lower())
    
    def test_api_error_handling(self):
        """Test API endpoint error handling"""
        with mock.patch.object(GrafanaAPI, 'get_cost_dashboards', side_effect=Exception('API Error')):
            response = self.client.get('/api/dashboards/cost')
            self.assertEqual(response.status_code, 500)
            data = json.loads(response.data)
            self.assertIn('error', data)
            self.assertEqual(data['error'], 'API Error')
    
    def test_dashboard_with_all_parameters(self):
        """Test dashboard with all possible URL parameters"""
        # Test with supported custom parameters
        custom_params = {
            'from': 'now-60d',
            'to': 'now',
            'theme': 'dark'
        }
        
        query_string = '&'.join([f"{k}={v}" for k, v in custom_params.items()])
        response = self.client.get(f'/dashboard/{self.dashboard_id}?{query_string}')
        
        self.assertEqual(response.status_code, 200)
        
        # Check that all custom parameters are included in the iframe URL
        for param, value in custom_params.items():
            self.assertIn(f'{param}={value}'.encode(), response.data)
    
    def test_dashboard_response_headers(self):
        """Test that appropriate response headers are set"""
        response = self.client.get(f'/dashboard/{self.dashboard_id}')
        self.assertEqual(response.content_type, 'text/html; charset=utf-8')
        
        # Security headers recommendation
        security_headers = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'SAMEORIGIN'
        }
        
        # Flask's response.headers is a Headers object which contains key-value pairs
        # We need to convert the keys to lowercase for case-insensitive comparison
        response_header_keys = [key.lower() for key in response.headers.keys()]
        
        for header, value in security_headers.items():
            if header.lower() not in response_header_keys:
                print(f"Security recommendation: Add '{header}: {value}' header")
    
    def test_dashboard_html_structure(self):
        """Test the structure of the dashboard HTML page"""
        response = self.client.get(f'/dashboard/{self.dashboard_id}')
        
        self.assertTrue(re.search(rb'<!DOCTYPE html>', response.data), "Missing DOCTYPE declaration")
        self.assertTrue(re.search(rb'<html[^>]*>', response.data), "Missing HTML tag")
        self.assertTrue(re.search(rb'<head>', response.data), "Missing HEAD tag")
        self.assertTrue(re.search(rb'<title>[^<]*</title>', response.data), "Missing TITLE tag")
        self.assertTrue(re.search(rb'<body[^>]*>', response.data), "Missing BODY tag")
        self.assertTrue(re.search(rb'<iframe[^>]*src="[^"]*"[^>]*>', response.data), "Missing iframe for dashboard")
        self.assertTrue(re.search(rb'<meta[^>]*viewport[^>]*>', response.data), "Missing viewport meta tag")
    
    def test_dashboard_content_with_date_range(self):
        """Test dashboard with specific date range (not relative)"""
        specific_date_params = {
            'from': '2023-01-01T00:00:00.000Z',
            'to': '2023-01-31T23:59:59.999Z'
        }
        
        query_string = '&'.join([f"{k}={v}" for k, v in specific_date_params.items()])
        response = self.client.get(f'/dashboard/{self.dashboard_id}?{query_string}')
        self.assertEqual(response.status_code, 200)
        
        for param, value in specific_date_params.items():
            date_part = value.split('T')[0]
            self.assertIn(date_part.encode(), response.data)
    
    def test_api_response_structure(self):
        """Test the structure of API responses"""
        response = self.client.get('/api/dashboards/cost')
        self.assertEqual(response.status_code, 200)
        
        dashboards = json.loads(response.data)
        self.assertIsInstance(dashboards, list)
        
        if dashboards:
            dashboard = dashboards[0]
            required_props = ['id', 'uid', 'title', 'url']
            for prop in required_props:
                self.assertIn(prop, dashboard, f"API response dashboard missing '{prop}' property")
    
    def test_okta_templates_if_available(self):
        """Test Okta-specific templates if they exist"""
        okta_template_used = False
        
        response = self.client.get(f'/dashboard/{self.dashboard_id}')
        
        if b'okta' in response.data.lower() or b'oauth' in response.data.lower():
            okta_template_used = True
            print("Okta integration detected in templates")
            self.assertIn(b'login', response.data.lower() or b'sign in', response.data.lower())
        
        if not okta_template_used:
            print("Okta templates don't appear to be in use. Skipping Okta-specific assertions.")
            pass


class GrafanaAPIIntegrationTests(unittest.TestCase):
    """Tests specifically for the Grafana API integration"""
    
    @classmethod
    def setUpClass(cls):
        """Set up the test environment once before all tests"""
        load_dotenv()
        
        cls.grafana_url = os.environ.get('GRAFANA_URL')
        cls.grafana_token = os.environ.get('GRAFANA_SERVICE_TOKEN')
        cls.dashboard_id = os.environ.get('GRAFANA_COST_DASHBOARD_ID')
        
        if not all([cls.grafana_url, cls.grafana_token, cls.dashboard_id]):
            raise ValueError("Missing required environment variables. Please check your .env file.")
        
        cls.api = GrafanaAPI(
            base_url=cls.grafana_url,
            service_token=cls.grafana_token
        )
    
    def test_api_initialization(self):
        """Test that the GrafanaAPI is initialized correctly"""
        self.assertEqual(self.api.base_url, self.grafana_url)
        self.assertEqual(self.api.headers['Authorization'], f'Bearer {self.grafana_token}')
        
    def test_get_all_dashboards(self):
        """Test retrieving all dashboards"""
        dashboards = self.api.get_all_dashboards()
        
        self.assertIsInstance(dashboards, list)
        self.assertTrue(len(dashboards) > 0, "No dashboards returned from the API")
        
        if dashboards:
            dashboard = dashboards[0]
            required_props = ['id', 'uid', 'title']
            for prop in required_props:
                self.assertIn(prop, dashboard)
    
    def test_get_dashboard(self):
        """Test retrieving a specific dashboard"""
        dashboard = self.api.get_dashboard(self.dashboard_id)
        
        self.assertIn('dashboard', dashboard)
        self.assertIn('meta', dashboard)
        
        dashboard_data = dashboard['dashboard']
        self.assertEqual(dashboard_data['uid'], self.dashboard_id)
        self.assertIn('panels', dashboard_data)
    
    def test_get_dashboard_panels(self):
        """Test retrieving panels from a dashboard"""
        panels = self.api.get_dashboard_panels(self.dashboard_id)
        
        self.assertIsInstance(panels, list)
        self.assertTrue(len(panels) > 0, "No panels found in dashboard")
        
        if panels:
            panel = panels[0]
            required_props = ['id', 'type', 'title']
            for prop in required_props:
                self.assertIn(prop, panel)
    
    def test_get_cost_dashboards(self):
        """Test filtering for cost-related dashboards"""
        cost_dashboards = self.api.get_cost_dashboards()
        
        self.assertIsInstance(cost_dashboards, list)
        
        for dashboard in cost_dashboards:
            required_props = ['id', 'uid', 'title']
            for prop in required_props:
                self.assertIn(prop, dashboard)
    
    def test_generate_dashboard_embed_url(self):
        """Test URL generation for dashboard embedding"""
        url = self.api.generate_dashboard_embed_url(self.dashboard_id)
        
        self.assertIn(self.grafana_url, url)
        self.assertIn(f'/d/{self.dashboard_id}', url)
        self.assertIn('orgId=', url)
        self.assertIn('from=', url)
        self.assertIn('to=', url)
        self.assertIn('theme=', url)
        self.assertIn('kiosk', url)
        
        custom_url = self.api.generate_dashboard_embed_url(
            self.dashboard_id,
            theme='dark',
            from_time='2023-01-01',
            to_time='2023-12-31'
        )
        
        self.assertIn('theme=dark', custom_url)
        self.assertIn('from=2023-01-01', custom_url)
        self.assertIn('to=2023-12-31', custom_url)


if __name__ == '__main__':
    print("Running end-to-end tests for Grafana Cost Dashboard...")
    print(f"Grafana URL: {os.environ.get('GRAFANA_URL', 'Not set')}")
    print(f"Dashboard ID: {os.environ.get('GRAFANA_COST_DASHBOARD_ID', 'Not set')}")
    
    unittest.main()