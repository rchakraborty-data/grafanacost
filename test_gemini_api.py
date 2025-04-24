import unittest
from unittest.mock import patch, MagicMock
import os
import sys
import requests

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import get_insights_from_gemini, set_gemini_testing_mode
from config import GEMINI_API_URL, GEMINI_API_ENDPOINT  # Import URL variables but not the key

class TestGeminiAPI(unittest.TestCase):

    def setUp(self):
        """Set up for test methods."""
        # Ensure testing mode is off by default for these tests
        set_gemini_testing_mode(enable=False)
        
        # Save any existing API key
        self.original_api_key = os.environ.get('GEMINI_API_KEY')
        # Set test API key consistently
        os.environ['GEMINI_API_KEY'] = 'test_api_key'
        
        # Ensure we're using the correct API endpoint format (matching app.py implementation)
        self.model_name = "gemini-2.0-flash-thinking-exp"
        
        # Mimic the same logic used in app.py to construct the endpoint
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
                
        self.api_endpoint_base = api_base
        self.expected_api_endpoint = f"{self.api_endpoint_base}/models/{self.model_name}:generateContent"

    def tearDown(self):
        """Clean up after test methods."""
        # Restore original API key
        if self.original_api_key:
            os.environ['GEMINI_API_KEY'] = self.original_api_key
        else:
            if 'GEMINI_API_KEY' in os.environ:
                del os.environ['GEMINI_API_KEY']
        # Reset testing mode
        set_gemini_testing_mode(enable=False)

    @patch('app.GEMINI_API_KEY', 'test_api_key')  # Mock the imported API key directly
    @patch('app.requests.post')
    def test_gemini_api_call_success(self, mock_post):
        """Test successful Gemini API call with dashboard data."""
        # Mock the requests.post response
        mock_response = MagicMock()
        mock_response.status_code = 200
        # Updated mock response structure for v1beta
        mock_response.json.return_value = {
            'candidates': [{
                'content': {
                    'parts': [{
                        'text': 'Successful analysis based on dashboard.'
                    }],
                    'role': 'model'
                }
            }]
        }
        mock_post.return_value = mock_response

        dashboard_data = {'title': 'Test Dashboard', 'panels': []}
        insights = get_insights_from_gemini(dashboard_data)

        # Verify requests.post was called correctly
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        
        # Check that the URL contains the expected endpoint path (more flexible check)
        self.assertIn(f"models/{self.model_name}:generateContent", args[0])
        self.assertIn(f"v1beta", args[0])
        self.assertIn(f"key=test_api_key", args[0])
        
        # Check the payload structure
        self.assertIn('contents', kwargs['json'])
        self.assertIn('generationConfig', kwargs['json'])
        self.assertEqual(kwargs['json']['contents'][0]['parts'][0]['text'], 
                         'Analyze this Grafana dashboard structure and provide specific cost optimization recommendations for Databricks usage. Focus on query efficiency, resource utilization, and storage optimization.\n\nDashboard: {\n  "title": "Test Dashboard",\n  "panels": []\n}')

        # Verify the result
        self.assertEqual(insights, 'Successful analysis based on dashboard.')

    @patch('app.GEMINI_API_KEY', 'test_api_key')  # Mock the imported API key directly
    @patch('app.requests.post')
    def test_gemini_api_call_failure(self, mock_post):
        """Test Gemini API call failure."""
        # Mock the requests.post response for failure
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = 'Internal Server Error'
        mock_post.return_value = mock_response

        dashboard_data = {'title': 'Test Dashboard', 'panels': []}
        insights = get_insights_from_gemini(dashboard_data)

        # Verify requests.post was called
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        
        # Check that the URL contains the expected endpoint path (more flexible check)
        self.assertIn(f"models/{self.model_name}:generateContent", args[0])
        self.assertIn(f"v1beta", args[0])

        # Verify the error message
        self.assertIn("Error calling Gemini API:", insights)
        self.assertIn("500", insights)
    
    @patch('app.GEMINI_API_KEY', None)  # Force API key to be None
    def test_gemini_api_no_key(self):
        """Test Gemini API call when API key is missing."""
        # Make sure no API calls happen when key is None
        
        dashboard_data = {'title': 'Test Dashboard', 'panels': []}
        insights = get_insights_from_gemini(dashboard_data)
        
        # Verify the error message
        self.assertEqual(insights, "Error: Gemini API Key not configured.")

    def test_gemini_testing_mode(self):
        """Test that testing mode returns the mock response."""
        mock_text = "This is the mock testing response."
        set_gemini_testing_mode(enable=True, mock_response=mock_text)
        
        dashboard_data = {'title': 'Test Dashboard', 'panels': []}
        insights = get_insights_from_gemini(dashboard_data)
        
        # Verify the mock response is returned
        self.assertEqual(insights, mock_text)
        
        # Disable testing mode again for subsequent tests
        set_gemini_testing_mode(enable=False)

if __name__ == '__main__':
    unittest.main()
