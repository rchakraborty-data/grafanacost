# Grafana Cost Analyzer

A powerful AI-powered tool that analyzes Grafana dashboards to provide cost optimization recommendations for Databricks workloads.

![Grafana Cost Analyzer](https://via.placeholder.com/800x400?text=Grafana+Cost+Analyzer)

## Overview

Grafana Cost Analyzer is a web application that helps data engineering and DevOps teams optimize their Databricks costs by analyzing Grafana dashboards. The tool:

- Parses and analyzes Grafana dashboard structures
- Executes Databricks SQL queries to retrieve actual usage and cost data
- Leverages Google's Gemini AI to generate cost optimization insights
- Provides professional reports with specific recommendations
- Offers PDF export functionality for sharing analysis results

## Features

- **Dashboard Analysis**: Analyze any Grafana dashboard by URL
- **Smart Variable Handling**: Automatically handles Grafana template variables in SQL queries
- **AI-Powered Insights**: Uses Gemini AI to generate cost optimization recommendations
- **Interactive UI**: Modern, responsive interface with intuitive visualization
- **PDF Reports**: Export analysis results as professional PDF reports
- **Categorized Recommendations**: Recommendations are automatically prioritized and categorized
- **Model Context Protocol (MCP)**: Enhanced AI reasoning through structured action chains

## Model Context Protocol (MCP) Integration

The Grafana Cost Analyzer leverages the Model Context Protocol (MCP) to provide more structured and sophisticated AI analysis capabilities. MCP enables AI models to reason more effectively by breaking down complex tasks into discrete actions with specific contexts.

```
┌─────────────────────────────────┐      ┌─────────────────────────────────┐
│    Grafana Cost Web App         │      │     Model Context Protocol      │
│                                 │      │                                 │
│  ┌─────────┐     ┌─────────┐    │      │  ┌─────────┐     ┌─────────┐    │
│  │ Request │     │ Response│    │      │  │ Action  │     │ Action  │    │
│  │ Handler ├────►│ Builder │◄───┼──────┼──┤ Results │◄────┤ Handler │    │
│  └─────────┘     └─────────┘    │      │  └─────────┘     └─────────┘    │
│        │                        │      │        ▲               ▲        │
└────────┼────────────────────────┘      └────────┼───────────────┼────────┘
         │                                         │               │
         │                                         │               │
         ▼                                         │               │
┌─────────────────┐                     ┌──────────┴───────┐      │
│  MCP Client     │                     │                  │      │
│                 │                     │   AI Analysis    │      │
│  ┌──────────┐   │   ┌──────────────┐  │    Engine       │      │
│  │Dashboard ├───┼──►│get_dashboard │──┼─────────────────┼──────┘
│  │ Analysis │   │   └──────────────┘  │  ┌────────────┐ │
│  └──────────┘   │                     │  │   Gemini   │ │
│                 │   ┌──────────────┐  │  │    API     │ │
│  ┌──────────┐   │   │execute_query │──┼─►│            │ │
│  │  Query   ├───┼──►│              │  │  │            │ │
│  │ Analysis │   │   └──────────────┘  │  └────────────┘ │
│  └──────────┘   │                     │                  │
│                 │   ┌──────────────┐  │  ┌────────────┐  │
│  ┌──────────┐   │   │analyze_cost_ │  │  │Recommendations│
│  │Cost Data ├───┼──►│   patterns   │──┼─►│  Generator  │  │
│  │ Analysis │   │   └──────────────┘  │  └────────────┘  │
│  └──────────┘   │                     │                  │
└─────────────────┘                     └──────────────────┘
```

### How MCP Works in Grafana Cost Analyzer

1. **Structured Actions**: The MCP server provides distinct actions like:
   - `get_dashboard`: Fetches dashboard structure
   - `execute_query`: Runs SQL queries against Databricks
   - `analyze_cost_patterns`: Analyzes cost data for patterns
   - `generate_recommendations`: Creates tailored recommendations

2. **Enhanced Context Management**: MCP maintains context throughout the analysis chain:
   - Dashboard structure is analyzed to understand query relationships
   - Query results are analyzed in the context of overall usage patterns
   - Recommendations are generated with knowledge of both dashboard structure and query results

3. **Multithreaded Operation**: The MCP server runs in a background thread, allowing asynchronous AI processing without blocking the main application.

4. **Graceful Fallback**: If MCP encounters issues, the system automatically falls back to direct Gemini API calls.

5. **UI Integration**: The user interface displays an MCP badge when analysis is being performed through the Model Context Protocol.

### Benefits of MCP

- **More Sophisticated Analysis**: Breaking down analysis into discrete actions enables more complex reasoning
- **Better Error Handling**: Each action has specific error handling, improving reliability
- **Enhanced Performance**: Parallel processing of actions improves response time
- **Extensibility**: New actions can be easily added to enhance capabilities
- **Multi-Model Support**: The architecture can work with different AI models beyond just Gemini

## Installation

### Prerequisites

- Python 3.10+
- Access to Grafana dashboards
- Databricks workspace with SQL warehouse
- Google Gemini API key

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/rchakraborty-data/grafanacost.git
   cd grafanacost
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure your environment by creating a `.env` file in the project root:
   ```
   GRAFANA_API_KEY=your_grafana_api_key
   GRAFANA_URL=your_grafana_url
   DATABRICKS_HOST=your_databricks_host
   DATABRICKS_TOKEN=your_databricks_token
   DATABRICKS_HTTP_PATH=your_databricks_http_path
   GEMINI_API_KEY=your_gemini_api_key
   SECRET_KEY=your_flask_secret_key
   ```

## Usage

### Starting the Application

Run the application using the provided script:

```bash
chmod +x run_app.sh
./run_app.sh
```

This will start the Flask server on http://localhost:5000.

### Analyzing a Dashboard

1. Open the application in your browser
2. Enter a Grafana dashboard URL in the input field
3. Wait for the analysis to complete (a progress bar will show the status)
4. Review the generated insights and recommendations
5. Optionally download a PDF report of the analysis

## Configuration

The application can be configured through environment variables or the `config.py` file:

- `GRAFANA_API_KEY`: Your Grafana API key
- `GRAFANA_URL`: The base URL of your Grafana instance
- `DATABRICKS_HOST`: Your Databricks workspace host
- `DATABRICKS_TOKEN`: Authentication token for Databricks
- `DATABRICKS_HTTP_PATH`: HTTP path for Databricks SQL warehouse
- `GEMINI_API_KEY`: Google Gemini API key
- `GEMINI_API_ENDPOINT`: Endpoint for the Gemini API
- `DEBUG`: Enable/disable debug mode (True/False)

## Project Structure

```
grafanacost/
├── app.py                  # Main Flask application
├── config.py               # Configuration handling
├── databricks_client.py    # Databricks SQL connection
├── grafana_api.py          # Grafana API interaction
├── requirements.txt        # Python dependencies
├── run_app.sh              # Application startup script
├── run_tests.sh            # Test runner script
├── test_e2e.py             # End-to-end tests
├── static/                 # Static assets
│   └── style.css           # CSS styles
└── templates/              # HTML templates
    ├── base.html           # Base template
    ├── dashboard.html      # Dashboard analysis page
    ├── dashboard_okta.html # Okta integration for dashboards
    ├── error.html          # Error page
    ├── index.html          # Home page
    └── index_okta.html     # Okta integration for home page
```

## How It Works

1. **Dashboard Retrieval**: The application fetches the dashboard JSON from Grafana using the API
2. **Query Extraction**: SQL queries are extracted from dashboard panels
3. **Variable Interpolation**: Grafana template variables are processed and interpolated
4. **Data Retrieval**: Queries are executed against Databricks SQL warehouse
5. **AI Analysis**: Results are sent to Google's Gemini API for analysis
6. **Visualization**: Insights and recommendations are displayed with intuitive formatting
7. **Report Generation**: Analysis can be exported as a PDF report

## Development

### Running Tests

```bash
chmod +x run_tests.sh
./run_tests.sh
```

### Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -am 'Add my feature'`
4. Push to the branch: `git push origin feature/my-feature`
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Grafana for their excellent dashboarding platform
- Databricks for their SQL warehouse capabilities
- Google Gemini for the AI analysis capabilities

## Contact

For questions or support, please reach out to the repository owner.