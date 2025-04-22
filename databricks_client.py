import pandas as pd
from databricks import sql as databricks_sql
from config import DATABRICKS_SERVER_HOSTNAME, DATABRICKS_HTTP_PATH, DATABRICKS_ACCESS_TOKEN
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def execute_databricks_query(query: str) -> pd.DataFrame | str:
    """
    Connects to Databricks SQL Warehouse and executes the given query.

    Args:
        query: The SQL query string to execute.

    Returns:
        A pandas DataFrame containing the query results if successful,
        or an error message string if an error occurs.
    """
    if not all([DATABRICKS_SERVER_HOSTNAME, DATABRICKS_HTTP_PATH, DATABRICKS_ACCESS_TOKEN]):
        error_msg = "Error: Databricks connection details not fully configured in .env file."
        logger.error(error_msg)
        return error_msg

    try:
        logger.info(f"Attempting to connect to Databricks host: {DATABRICKS_SERVER_HOSTNAME}")
        with databricks_sql.connect(
            server_hostname=DATABRICKS_SERVER_HOSTNAME,
            http_path=DATABRICKS_HTTP_PATH,
            access_token=DATABRICKS_ACCESS_TOKEN
        ) as connection:
            logger.info("Successfully connected to Databricks.")
            with connection.cursor() as cursor:
                logger.info(f"Executing query: {query[:100]}...") # Log first 100 chars
                # --- Add detailed logging of the full query --- 
                logger.info(f"[databricks_client] Full query before execution:\n{query}")
                # --- End detailed logging ---
                cursor.execute(query)
                
                # --- New: Fetch results using standard fetchall and create DataFrame --- 
                result = cursor.fetchall()
                if result:
                    columns = [desc[0] for desc in cursor.description]
                    df = pd.DataFrame(result, columns=columns)
                    logger.info(f"Query executed successfully, fetched {len(df)} rows.")
                else:
                    # If no results, create an empty DataFrame with correct columns
                    columns = [desc[0] for desc in cursor.description]
                    df = pd.DataFrame(columns=columns)
                    logger.info("Query executed successfully, but returned no rows.")
                # --- End New ---
                return df
    except databricks_sql.exc.Error as e:
        error_msg = f"Databricks SQL Error: {e}"
        logger.error(error_msg, exc_info=True)
        return error_msg
    except Exception as e:
        error_msg = f"An unexpected error occurred during Databricks query execution: {e}"
        logger.error(error_msg, exc_info=True)
        return error_msg

# Example usage (for testing purposes, can be removed later)
if __name__ == '__main__':
    # Replace with a simple test query relevant to your Databricks data
    test_query = "SELECT 1" 
    result = execute_databricks_query(test_query)
    if isinstance(result, pd.DataFrame):
        print("Successfully executed query. Result preview:")
        print(result.head())
    else:
        print(f"Failed to execute query: {result}")
