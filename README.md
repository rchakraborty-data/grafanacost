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

## System Architecture

The Grafana Cost Analyzer follows a modular architecture designed for flexibility, scalability, and maintainability. The system is composed of several key components that work together to provide comprehensive cost analysis and recommendations.

```
┌───────────────────────────────────────────────────────────────────────────┐
│                        Grafana Cost Analyzer Architecture                  │
└───────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌───────────────────┐  HTTP    ┌───────────────────┐  API    ┌───────────────┐
│    Web Browser    │◄────────►│    Flask App      │◄───────►│ Grafana API   │
│                   │          │    (app.py)       │         │               │
└───────────────────┘          └────────┬──────────┘         └───────────────┘
                                        │  
                                        │ Query  
                  ┌─────────────────────┼─────────────────────┐
                  │                     │                     │
                  ▼                     ▼                     ▼
┌───────────────────┐  ┌───────────────────┐  ┌───────────────────────────────┐
│  Databricks SQL   │  │   AI Analysis     │  │  Report Generation            │
│  (Query Execution)│  │   (Gemini API)    │  │  (PDF & Interactive HTML)     │
└───────────────────┘  └───────────────────┘  └───────────────────────────────┘
                               │
                  ┌────────────┴────────────┐
                  │                         │
                  ▼                         ▼
┌─────────────────────────┐    ┌─────────────────────────┐
│ Direct Gemini API Mode  │    │ Model Context Protocol  │
│ (Synchronous Analysis)  │    │ (MCP) Mode              │
└─────────────────────────┘    └─────────────────────────┘
```

### Core Components

1. **Flask Web Application** (app.py)
   - Core component that handles HTTP requests, manages sessions, and coordinates data flow
   - Renders HTML templates and serves static assets
   - Manages asynchronous analysis tasks and state management
   - Implements error handling and logging

2. **Grafana API Interface** (grafana_api.py)
   - Provides a client for Grafana's REST API
   - Retrieves dashboard definitions, panel configurations, and query details
   - Handles authentication and error management
   - Supports both HTTP and GraphQL API interactions

3. **Databricks Client** (databricks_client.py)
   - Executes SQL queries against Databricks SQL warehouses
   - Manages connections and error handling
   - Processes query results into Pandas DataFrames for analysis
   - Handles connection pooling and query timeout management

4. **AI Analysis Engines**
   - **Direct Gemini API Integration**
     - Sends data directly to Google's Gemini API
     - Processes responses and formats them for display
   - **Model Context Protocol (MCP)**
     - Structured approach to AI reasoning with discrete actions
     - Background MCP server for enhanced multi-step analysis
     - Parallel processing capabilities for complex analyses

5. **Report Generation System**
   - **HTML Report Generator**
     - Converts Markdown recommendations to HTML
     - Applies syntax highlighting for code blocks
   - **PDF Report Generator**
     - Transforms HTML content to professionally formatted PDFs
     - Implements advanced styling with ReportLab
     - Supports tables, lists, metadata blocks, and section formatting

## Data Flow Diagram

The following diagram illustrates the flow of data through the system when analyzing a dashboard:

```
┌─────────────┐         ┌─────────────┐         ┌────────────────┐
│  User Input │         │  Grafana    │         │   Databricks   │
│  Dashboard  │─────────►   API       │◄────────┤   SQL Engine   │
│     URL     │         │             │         │                │
└─────┬───────┘         └──────┬──────┘         └───────┬────────┘
      │                        │                        │
      │                        │                        │
      ▼                        ▼                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│                      Flask Application                          │
│                                                                 │
│   ┌───────────┐     ┌───────────┐      ┌──────────────────┐    │
│   │ Dashboard │     │  Query    │      │ Results Analysis │    │
│   │ Retrieval │────►│ Execution │─────►│ & Recommendations│    │
│   └───────────┘     └───────────┘      └──────────┬───────┘    │
│                                                   │            │
└───────────────────────────────────────────────────┼────────────┘
                                                    │
                    ┌─────────────────────┐         │
                    │                     │         │
                    ▼                     ▼         │
            ┌──────────────┐     ┌──────────────┐   │
            │              │     │              │   │
            │ Direct API   │     │ MCP Server   │   │
            │ (Gemini)     │     │ Protocol     │   │
            │              │     │              │   │
            └──────┬───────┘     └──────┬───────┘   │
                   │                    │           │
                   └────────────┬───────┘           │
                                │                   │
                                ▼                   │
                      ┌────────────────┐            │
                      │                │            │
                      │  AI Analysis   │◄───────────┘
                      │  Generation    │
                      │                │
                      └───────┬────────┘
                              │
                              ▼
                    ┌───────────────────┐          ┌───────────────────┐
                    │                   │          │                   │
                    │  HTML Response    │────────► │  PDF Generation   │
                    │                   │          │                   │
                    └───────────────────┘          └───────────────────┘
```

## PDF Generation System

The PDF generation system converts HTML analysis into professionally formatted PDF reports with enhanced readability and visual appeal.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PDF Generation Architecture                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────┐            ┌─────────────────┐            ┌─────────────────┐
│                 │            │                 │            │                 │
│  HTML Content   │────────────►  HTML Parser    │────────────►  Content        │
│  from Analysis  │            │  & Extractor    │            │  Structuring    │
│                 │            │                 │            │                 │
└─────────────────┘            └─────────────────┘            └────────┬────────┘
                                                                       │
                                                                       │
┌─────────────────┐            ┌─────────────────┐            ┌────────▼────────┐
│                 │            │                 │            │                 │
│  PDF Document   │◄───────────┤  Style          │◄───────────┤  Content        │
│  Generation     │            │  Application    │            │  Organization   │
│                 │            │                 │            │                 │
└─────────────────┘            └─────────────────┘            └─────────────────┘
```

### PDF Generation Features

The PDF generator creates visually appealing reports with:

1. **Professional Formatting**
   - Clean hierarchical structure with consistent styling
   - Color-coded sections based on priority and importance
   - Proper page breaks and content flow management
   - Embedded metadata with visual emphasis for key metrics

2. **Content Organization**
   - Title page with dashboard information and generation date
   - Table of contents with hyperlinks to sections
   - Properly formatted code blocks with syntax highlighting
   - Structured recommendations with implementation steps

3. **Visual Elements**
   - Color-coded priority indicators
   - Styled metadata blocks for better information hierarchy
   - Properly formatted tables with alternating row colors
   - Bulleted and numbered lists with correct indentation

4. **Technical Implementation**
   - HTML parsing to extract structured content
   - ReportLab library for PDF generation
   - Custom paragraph styles for different content types
   - Advanced table formatting with cell styling

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

## Query Processing System

The Query Processing System is responsible for handling Grafana dashboard queries, interpolating variables, and executing them against Databricks SQL:

```
┌────────────────────────────────────────────────────────────────────┐
│                   Query Processing Workflow                         │
└────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌───────────────────┐    ┌─────────────────┐    ┌───────────────────┐
│                   │    │                 │    │                   │
│  Extract SQL      │───►│ Parse Template  │───►│ Process Time      │
│  from Dashboard   │    │ Variables       │    │ Range Variables   │
│                   │    │                 │    │                   │
└───────────────────┘    └─────────────────┘    └─────────┬─────────┘
                                                          │
                                                          ▼
┌───────────────────┐    ┌─────────────────┐    ┌───────────────────┐
│                   │    │                 │    │                   │
│  Execute Query    │◄───┤ Replace Special │◄───┤ Handle Multi-     │
│  Against          │    │ Variables       │    │ Value Variables   │
│  Databricks SQL   │    │                 │    │                   │
└─────────┬─────────┘    └─────────────────┘    └───────────────────┘
          │
          ▼
┌───────────────────┐
│                   │
│  Process Query    │
│  Results          │
│                   │
└───────────────────┘
```

Key components of the query processing system:

1. **Variable Interpolation Engine**
   - Handles Grafana's complex template variable syntax
   - Supports multi-value variables and special values like `$__all`
   - Processes time range variables with absolute and relative formats

2. **Query Transformation Pipeline**
   - Parses and extracts SQL from dashboard panels
   - Handles complex SQL transformations with variable substitution
   - Manages SQL query validation and error handling

3. **Result Processing**
   - Converts query results to structured data formats
   - Generates statistical summaries for numerical columns
   - Prepares data for AI analysis and visualization

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
- `USE_MCP`: Enable Model Context Protocol (True/False)
- `MCP_HOST`: Host for MCP server (default: localhost)
- `MCP_PORT`: Port for MCP server (default: 8080)
- `START_MCP_SERVER`: Auto-start MCP server (True/False)

## Detailed Project Structure

```
grafanacost/
├── app.py                  # Main Flask application
├── config.py               # Configuration handling
├── databricks_client.py    # Databricks SQL connection
├── grafana_api.py          # Grafana API interaction
├── grafana_graphql.py      # GraphQL API support for Grafana
├── grafana_mcp_server.py   # MCP server implementation
├── mcp_client.py           # Client for MCP interactions
├── requirements.txt        # Python dependencies
├── run_app.sh              # Application startup script
├── run_tests.sh            # Test runner script
│
├── tests/
│   ├── test_e2e.py         # End-to-end tests
│   ├── test_gemini_api.py  # Tests for Gemini API integration
│   └── test_pdf_generation.py # Tests for PDF generation
│
├── static/                 # Static assets
│   ├── style.css           # CSS styles
│   └── downloads/          # Folder for generated PDFs
│
└── templates/              # HTML templates
    ├── base.html           # Base template
    ├── dashboard.html      # Dashboard analysis page
    ├── dashboard_okta.html # Okta integration for dashboards
    ├── error.html          # Error page
    ├── index.html          # Home page
    └── index_okta.html     # Okta integration for home page
```

## Component Interactions

The following diagram shows how the key components interact during the dashboard analysis process:

```
┌─────────────────────┐     ┌─────────────────────┐
│                     │     │                     │
│  Web Browser        │◄───►│  Flask App (app.py) │
│                     │     │                     │
└─────────────────────┘     └──────────┬──────────┘
                                       │
                 ┌─────────────────────┼─────────────────────┐
                 │                     │                     │
                 ▼                     ▼                     ▼
    ┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐
    │                     │ │                     │ │                     │
    │  Grafana API        │ │  Databricks Client  │ │  Gemini API         │
    │  (grafana_api.py)   │ │  (databricks_       │ │  Integration        │
    │                     │ │   client.py)        │ │                     │
    └─────────────────────┘ └─────────────────────┘ └─────────────────────┘
              │                       │                        │
              └───────────────────────┼────────────────────────┘
                                     │
                                     ▼
                          ┌─────────────────────┐
                          │                     │
                          │  MCP Server/Client  │
                          │  (Optional)         │
                          │                     │
                          └─────────────────────┘
```

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
- ReportLab for the PDF generation library

## Contact

For questions or support, please reach out to the repository owner.