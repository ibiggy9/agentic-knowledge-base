
"""
###############################################################################
#                          BIG QUERY MCP Server                               #
###############################################################################
Generic Google BigQuery MCP Server

This MCP server provides a generic interface for querying Google BigQuery datasets.
It handles authentication via service account credentials and exposes tools for:
- Running SQL queries against BigQuery tables
- Fetching table metadata and schema information 
- Managing dataset and table permissions
- Monitoring query costs and usage

The server uses the google-cloud-bigquery library and requires proper GCP credentials
to be configured via environment variables or service account key files.
"""

import os
from typing import Any, Dict, List, Optional
from mcp.server.fastmcp import FastMCP, Context
import asyncio
import logging
from google.cloud import bigquery
from google.cloud.exceptions import NotFound
from google.oauth2 import service_account

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("gbq-mcp-server")

mcp = FastMCP("gbq")

PROJECT_ID = os.environ.get("GBQ_PROJECT_ID")
CREDENTIALS_PATH = os.environ.get("GBQ_CREDENTIALS_PATH")
LOCATION = os.environ.get("GBQ_LOCATION", "US")
DEFAULT_DATASET = os.environ.get("GBQ_DEFAULT_DATASET")

MAX_CONNECTIONS = int(os.environ.get("MAX_BQ_CONNECTIONS", "10"))

class BigQueryPool:
    def __init__(self, max_connections=10):
        self.max_connections = max_connections
        self.clients = asyncio.Queue(maxsize=max_connections)
        self.active_clients = 0
        self.lock = asyncio.Lock()
        self.credentials = None
        if CREDENTIALS_PATH and os.path.exists(CREDENTIALS_PATH):
            self.credentials = service_account.Credentials.from_service_account_file(CREDENTIALS_PATH)
        logger.info(f"Initializing BigQuery client pool with max {max_connections} clients")

    async def initialize(self):
        logger.info("Initializing BigQuery client pool")
        for _ in range(self.max_connections):
            if self.credentials:
                client = bigquery.Client(project=PROJECT_ID, credentials=self.credentials, location=LOCATION)
            else:
                client = bigquery.Client(project=PROJECT_ID, location=LOCATION)
            await self.clients.put(client)
        
    async def get_client(self):
        async with self.lock:
            if self.clients.empty() and self.active_clients < self.max_connections:
                if self.credentials:
                    client = bigquery.Client(project=PROJECT_ID, credentials=self.credentials, location=LOCATION)
                else:
                    client = bigquery.Client(project=PROJECT_ID, location=LOCATION)
                self.active_clients += 1
                logger.debug(f"Created new client, active: {self.active_clients}")
                return client
        
        try:
            client = await asyncio.wait_for(self.clients.get(), timeout=5.0)
            return client
        except asyncio.TimeoutError:
            logger.warning("Timeout waiting for BigQuery client")
            raise Exception("BigQuery client timeout - server is too busy")

    async def release_client(self, client):    
        try:
            await self.clients.put(client)
            logger.debug("Released client back to pool")
        except asyncio.QueueFull:
            client.close()
            async with self.lock:
                self.active_clients -= 1
            logger.debug(f"Closed client, active: {self.active_clients}")

    async def close_all(self):
        logger.info("Closing all BigQuery clients")
        while not self.clients.empty():
            client = await self.clients.get()
            client.close()
        logger.info("All clients closed")

pool = BigQueryPool(MAX_CONNECTIONS)

class BigQueryConnection:
    def __init__(self):
        self.client = None
        
    async def __aenter__(self):
        self.client = await pool.get_client()
        return self.client
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await pool.release_client(self.client)

def run_query_async(query_job):
    async def _async_query():
        return query_job.result()
    return _async_query()

@mcp.tool()
async def describe_table(table_name: str, dataset_name: str = DEFAULT_DATASET):
    """Get detailed information about a table's structure.
    
    Args:
        table_name: Name of the table to describe
        dataset_name: Name of the dataset containing the table (defaults to configured dataset)
    
    Returns:
        Column information including name, type, mode, and description
    """
    if not dataset_name:
        return {"error": True, "message": "Dataset name is required"}
    
    async with BigQueryConnection() as client:
        try:
            full_table_id = f"{PROJECT_ID}.{dataset_name}.{table_name}"
            
            table = client.get_table(full_table_id)
            
            column_info = []
            for field in table.schema:
                column_info.append({
                    "name": field.name,
                    "type": field.field_type,
                    "mode": field.mode,
                    "description": field.description,
                    "fields": [{"name": f.name, "type": f.field_type, "mode": f.mode} 
                              for f in field.fields] if field.fields else None
                })
            
            return column_info
        except NotFound:
            return {"error": True, "message": f"Table {full_table_id} not found"}
        except Exception as e:
            logger.error(f"Error describing table {table_name}: {str(e)}")
            return {"error": True, "message": f"Error describing table: {str(e)}"}
        
@mcp.tool()
async def list_datasets():
    """List all available datasets in the project.
    
    Returns:
        List of dataset names
    """
    async with BigQueryConnection() as client:
        try:
            datasets = list(client.list_datasets())
            dataset_list = [dataset.dataset_id for dataset in datasets]
            return dataset_list
        except Exception as e:
            logger.error(f"Error listing datasets: {str(e)}")
            return {"error": True, "message": f"Error listing datasets: {str(e)}"}

@mcp.tool()
async def list_tables(dataset_name: str = DEFAULT_DATASET):
    """List all available tables in a dataset.
    
    Args:
        dataset_name: Name of the dataset to list tables from (defaults to configured dataset)
    
    Returns:
        List of table names
    """
    if not dataset_name:
        return {"error": True, "message": "Dataset name is required"}
    
    async with BigQueryConnection() as client:
        try:
            tables = list(client.list_tables(dataset_name))
            table_list = [table.table_id for table in tables]
            return table_list
        except NotFound:
            return {"error": True, "message": f"Dataset {dataset_name} not found"}
        except Exception as e:
            logger.error(f"Error listing tables: {str(e)}")
            return {"error": True, "message": f"Error listing tables: {str(e)}"}

@mcp.tool()
async def read_query(query: str, maximum_bytes_billed: Optional[int] = None):
    """Execute a read-only SQL query against BigQuery.
    
    Args:
        query: SQL query to execute (must be a SELECT statement)
        maximum_bytes_billed: Optional maximum bytes to be billed for this query
    
    Returns:
        Query results as a list of records
    """
    if not query.strip().upper().startswith("SELECT"):
        logger.warning(f"Non-SELECT query attempted: {query}")
        raise ValueError("Only SELECT queries are allowed for read_query")
    
    async with BigQueryConnection() as client:
        try:
            job_config = bigquery.QueryJobConfig()
            
            if maximum_bytes_billed:
                job_config.maximum_bytes_billed = maximum_bytes_billed
            
            query_job = client.query(query, job_config=job_config)
            
            results = await run_query_async(query_job)
            
            return [dict(row.items()) for row in results]
        except Exception as e:
            logger.error(f"Error executing query: {str(e)}, Query: {query}")
            return {"error": True, "message": f"Error executing query: {str(e)}"}

@mcp.tool()
async def calculate_correlation(table_name: str, column1: str, column2: str, dataset_name: str = DEFAULT_DATASET):
    """Calculate the correlation coefficient between two numeric columns.
    
    Args:
        table_name: Name of the table containing the columns
        column1: First column to correlate
        column2: Second column to correlate
        dataset_name: Name of the dataset containing the table (defaults to configured dataset)
    
    Returns:
        Correlation statistics including coefficient, relationship strength, direction, and sample size
    """
    if not dataset_name:
        return {"error": True, "message": "Dataset name is required"}
    
    columns = await describe_table(table_name, dataset_name)
    if isinstance(columns, dict) and columns.get("error"):
        return columns
        
    column_names = [col["name"] for col in columns]
    
    if column1 not in column_names or column2 not in column_names:
        return {
            "error": True,
            "message": f"One or both columns not found in table '{table_name}'"
        }
    
    async with BigQueryConnection() as client:
        try:
            query = f"""
            SELECT 
                CORR({column1}, {column2}) AS correlation,
                COUNT(*) as count
            FROM `{PROJECT_ID}.{dataset_name}.{table_name}`
            WHERE {column1} IS NOT NULL AND {column2} IS NOT NULL
            """
            
            query_job = client.query(query)
            
            result_rows = await run_query_async(query_job)
            
            result = list(result_rows)[0]
            correlation = result.correlation
            row_count = result.count
            
            if row_count < 2:
                return {
                    "error": True,
                    "message": "Insufficient data for correlation calculation"
                }
                
            correlation_abs = abs(correlation) if correlation is not None else 0
            if correlation is None or correlation_abs < 0.1:
                strength = "No correlation"
            elif correlation_abs < 0.3:
                strength = "Weak correlation"
            elif correlation_abs < 0.5:
                strength = "Moderate correlation"
            elif correlation_abs < 0.7:
                strength = "Strong correlation"
            else:
                strength = "Very strong correlation"
            
            direction = "positive" if correlation and correlation > 0 else "negative"
            
            return {
                "correlation_coefficient": correlation,
                "relationship_strength": strength,
                "direction": direction,
                "sample_size": row_count
            }
            
        except Exception as e:
            logger.error(f"Error calculating correlation: {str(e)}")
            return {
                "error": True,
                "message": f"Error calculating correlation: {str(e)}"
            }

@mcp.tool()
async def find_correlations(table_name: str, target_column: str = None, 
                          threshold: float = 0.3, dataset_name: str = DEFAULT_DATASET):
    """Find significant correlations between numeric columns in a table.
    
    Args:
        table_name: Name of the table to analyze
        target_column: Optional specific column to correlate against all others
        threshold: Minimum correlation coefficient magnitude to include (default: 0.3)
        dataset_name: Name of the dataset containing the table (defaults to configured dataset)
    
    Returns:
        List of correlations sorted by strength
    """
    if not dataset_name:
        return {"error": True, "message": "Dataset name is required"}
    
    columns = await describe_table(table_name, dataset_name)
    if isinstance(columns, dict) and columns.get("error"):
        return columns
    numeric_columns = [col["name"] for col in columns 
                       if col["type"] in ("INTEGER", "FLOAT", "NUMERIC")]
    
    if not numeric_columns:
        return {
            "error": True,
            "message": f"No numeric columns found in table '{table_name}'"
        }
    
    if target_column and target_column not in numeric_columns:
        return {
            "error": True,
            "message": f"Target column '{target_column}' not found or is not numeric"
        }
    
    correlations = []
    
    if target_column:
        for column in numeric_columns:
            if column == target_column:
                continue
                
            result = await calculate_correlation(table_name, target_column, column, dataset_name)
            if not result.get("error") and abs(result.get("correlation_coefficient", 0)) >= threshold:
                correlations.append({
                    "column1": target_column,
                    "column2": column,
                    **result
                })
    else:
        pairs = []
        for i, col1 in enumerate(numeric_columns):
            for col2 in numeric_columns[i+1:]:
                pairs.append((col1, col2))
        
        if pairs:
            correlations_query = "SELECT\n"
            for i, (col1, col2) in enumerate(pairs):
                if i > 0:
                    correlations_query += ",\n"
                correlations_query += f"  CORR({col1}, {col2}) AS corr_{i},\n"
                correlations_query += f"  '{col1}' AS col1_{i},\n"
                correlations_query += f"  '{col2}' AS col2_{i}"
            
            correlations_query += f"\nFROM `{PROJECT_ID}.{dataset_name}.{table_name}`"
            
            async with BigQueryConnection() as client:
                try:
                    query_job = client.query(correlations_query)
                    result_rows = await run_query_async(query_job)
                    
                    row = list(result_rows)[0]
                    
                    for i, (col1, col2) in enumerate(pairs):
                        corr_val = getattr(row, f"corr_{i}")
                        if corr_val and abs(corr_val) >= threshold:
                            corr_abs = abs(corr_val)
                            
                            if corr_abs < 0.1:
                                strength = "No correlation"
                            elif corr_abs < 0.3:
                                strength = "Weak correlation"
                            elif corr_abs < 0.5:
                                strength = "Moderate correlation"
                            elif corr_abs < 0.7:
                                strength = "Strong correlation"
                            else:
                                strength = "Very strong correlation"
                                
                            direction = "positive" if corr_val > 0 else "negative"
                            
                            correlations.append({
                                "column1": col1,
                                "column2": col2,
                                "correlation_coefficient": corr_val,
                                "relationship_strength": strength,
                                "direction": direction
                            })
                except Exception as e:
                    logger.warning(f"Combined correlation query failed: {str(e)}, falling back to individual queries")
                    for col1, col2 in pairs:
                        result = await calculate_correlation(table_name, col1, col2, dataset_name)
                        if not result.get("error") and abs(result.get("correlation_coefficient", 0)) >= threshold:
                            correlations.append({
                                "column1": col1,
                                "column2": col2,
                                **result
                            })
    
    
    correlations.sort(key=lambda x: abs(x.get("correlation_coefficient", 0)), reverse=True)
    
    return correlations

@mcp.tool()
async def get_monthly_statistics(table_name: str, date_column: str, metric_column: str = None, 
                               start_date: str = None, end_date: str = None, 
                               dataset_name: str = DEFAULT_DATASET):
    """Get monthly statistics for a selected metric.
    
    Args:
        table_name: Name of the table to analyze
        date_column: Column containing date information
        metric_column: Optional column to aggregate (if not provided, will count rows)
        start_date: Optional start date in YYYY-MM-DD format
        end_date: Optional end date in YYYY-MM-DD format
        dataset_name: Name of the dataset containing the table (defaults to configured dataset)
    
    Returns:
        Monthly statistics for the selected metric
    """
    if not dataset_name:
        return {"error": True, "message": "Dataset name is required"}
    
    async with BigQueryConnection() as client:
        try:
            date_filter = ""
            if start_date:
                date_filter += f" AND {date_column} >= '{start_date}'"
            if end_date:
                date_filter += f" AND {date_column} <= '{end_date}'"
            
            if metric_column:
                query = f"""
                SELECT 
                    FORMAT_TIMESTAMP('%Y-%m', {date_column}) as month,
                    SUM({metric_column}) as metric_value
                FROM `{PROJECT_ID}.{dataset_name}.{table_name}`
                WHERE {date_column} IS NOT NULL{date_filter}
                GROUP BY month
                ORDER BY month
                """
            else:
                query = f"""
                SELECT 
                    FORMAT_TIMESTAMP('%Y-%m', {date_column}) as month,
                    COUNT(*) as count
                FROM `{PROJECT_ID}.{dataset_name}.{table_name}`
                WHERE {date_column} IS NOT NULL{date_filter}
                GROUP BY month
                ORDER BY month
                """
            
            query_job = client.query(query)
            result_rows = await run_query_async(query_job)
            
            return [dict(row.items()) for row in result_rows]
        except Exception as e:
            logger.error(f"Error getting monthly statistics: {str(e)}")
            return {
                "error": True,
                "message": f"Error getting monthly statistics: {str(e)}"
            }

@mcp.tool()
async def estimate_query_cost(query: str):
    """Estimate the cost of running a query without executing it.
    
    Args:
        query: SQL query to analyze
    
    Returns:
        Estimated bytes processed and approximate cost
    """
    async with BigQueryConnection() as client:
        try:
            job_config = bigquery.QueryJobConfig(dry_run=True)
            query_job = client.query(query, job_config=job_config)
            
            bytes_processed = query_job.total_bytes_processed
            
            tb_processed = bytes_processed / (1024**4)
            estimated_cost = tb_processed * 5
            
            return {
                "bytes_processed": bytes_processed,
                "terabytes_processed": tb_processed,
                "estimated_cost_usd": estimated_cost,
                "note": "Cost estimate based on standard pricing, not accounting for free tier or discounts"
            }
        except Exception as e:
            logger.error(f"Error estimating query cost: {str(e)}")
            return {
                "error": True,
                "message": f"Error estimating query cost: {str(e)}"
            }

@mcp.tool()
async def list_schema(dataset_name: str = DEFAULT_DATASET):
    """Get a comprehensive overview of the dataset schema.
    
    Args:
        dataset_name: Name of the dataset to describe (defaults to configured dataset)
    
    Returns:
        A dictionary mapping table names to their column structures
    """
    if not dataset_name:
        return {"error": True, "message": "Dataset name is required"}
    
    schema = {}
    async with BigQueryConnection() as client:
        try:
            tables = list(client.list_tables(dataset_name))
            
            for table in tables:
                full_table = client.get_table(f"{dataset_name}.{table.table_id}")
                
                column_info = []
                for field in full_table.schema:
                    column_info.append({
                        "name": field.name,
                        "type": field.field_type,
                        "mode": field.mode,
                        "description": field.description
                    })
                
                schema[table.table_id] = {
                    "columns": column_info,
                    "num_rows": full_table.num_rows,
                    "size_bytes": full_table.num_bytes,
                    "created": full_table.created.isoformat() if full_table.created else None,
                    "modified": full_table.modified.isoformat() if full_table.modified else None,
                    "description": full_table.description
                }
            
            return schema
        except Exception as e:
            logger.error(f"Error listing schema: {str(e)}")
            return {"error": True, "message": f"Error listing schema: {str(e)}"}

@mcp.tool()
async def run_query_with_parameters(query: str, parameters: List[Dict[str, Any]]):
    """Execute a parameterized SQL query against BigQuery.
    
    Args:
        query: SQL query with parameter placeholders (e.g., @param_name)
        parameters: List of parameter objects, each with name, type, and value
    
    Returns:
        Query results as a list of records
    """
    async with BigQueryConnection() as client:
        try:
            
            job_config = bigquery.QueryJobConfig()
            query_params = []
            
            for param in parameters:
                param_name = param.get("name")
                param_type = param.get("type", "STRING").upper()
                param_value = param.get("value")
                
                if param_type == "STRING":
                    query_params.append(bigquery.ScalarQueryParameter(param_name, "STRING", param_value))
                elif param_type == "INT64" or param_type == "INTEGER":
                    query_params.append(bigquery.ScalarQueryParameter(param_name, "INT64", int(param_value)))
                elif param_type == "FLOAT" or param_type == "NUMERIC":
                    query_params.append(bigquery.ScalarQueryParameter(param_name, "FLOAT64", float(param_value)))
                elif param_type == "BOOL" or param_type == "BOOLEAN":
                    query_params.append(bigquery.ScalarQueryParameter(param_name, "BOOL", bool(param_value)))
                elif param_type == "DATE":
                    query_params.append(bigquery.ScalarQueryParameter(param_name, "DATE", param_value))
                elif param_type == "TIMESTAMP":
                    query_params.append(bigquery.ScalarQueryParameter(param_name, "TIMESTAMP", param_value))
                else:
                    return {
                        "error": True,
                        "message": f"Unsupported parameter type: {param_type}"
                    }
            
            job_config.query_parameters = query_params
            
            query_job = client.query(query, job_config=job_config)
            
            results = await run_query_async(query_job)
            return [dict(row.items()) for row in results]
        except Exception as e:
            logger.error(f"Error executing parameterized query: {str(e)}")
            return {"error": True, "message": f"Error executing query: {str(e)}"}

async def initialize_server():
    logger.info("Initializing BigQuery MCP server...")
    if not PROJECT_ID:
        logger.warning("GBQ_PROJECT_ID environment variable not set")
    
    await pool.initialize()
    logger.info("BigQuery client pool initialized.")
    return True

async def shutdown_server():
    logger.info("Shutting down BigQuery MCP server...")
    
    await pool.close_all()
    
    logger.info("Server shutdown complete.")

if __name__ == "__main__":
    print("Starting BigQuery MCP server...")
    
    loop = asyncio.get_event_loop()
    
    try:
        loop.run_until_complete(initialize_server())
        
        mcp.run(transport='stdio')
    except Exception as e:
        logger.error(f"Error starting server: {e}")
        print(f"Error starting server: {e}")
    finally:
        try:
            loop.run_until_complete(shutdown_server())
        except Exception as e:
            logger.error(f"Error during server shutdown: {e}")