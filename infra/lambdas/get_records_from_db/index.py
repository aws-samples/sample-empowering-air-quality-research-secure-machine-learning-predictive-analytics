from datetime import datetime, timedelta, timezone
from botocore.exceptions import ClientError
from common import RDSHelper, S3Helper, get_env, get_logger
import psycopg2

# Environment variables
REGION = get_env("AWS_REGION", "us-east-1")
SOURCE_BUCKET = get_env("SOURCE_BUCKET")
DB_TABLE = get_env("DB_TABLE")
DB_USERNAME = get_env("DB_USERNAME")
LOG_LEVEL = get_env("LOG_LEVEL", "DEBUG")
SERVICE_NAME = get_env("SERVICE_NAME", "query_lambda")
RETRIEVAL_PREFIX = get_env("RETRIEVAL_PREFIX", "retrieved_from_db")
READER_ROLE_NAME = get_env("READER_ROLE_NAME")
DB_HOST = get_env("DB_HOST")
DB_NAME = get_env("DB_NAME")
RDS_DB_PORT = int(get_env("RDS_DB_PORT", "5432"))

logger = get_logger(service=SERVICE_NAME, level=LOG_LEVEL)


def lambda_handler(event, context):
    logger.info("Starting lambda execution")
    try:
        # Set up RDS configuration for IAM authentication
        rds_config = {
            "host": DB_HOST,
            "database": DB_NAME,
            "username": DB_USERNAME,
            "port": RDS_DB_PORT,
            "region": REGION,
        }
        logger.info("RDS configuration set up")

        # Establish connection using IAM authentication
        conn = RDSHelper.get_connection_with_iam(rds_config)
        logger.info("Successfully established connection using IAM authentication")

        # Calculate timestamp for 24 hours ago in UTC
        # Using timezone-aware datetime
        twenty_four_hours_ago = datetime.now(timezone.utc) - timedelta(hours=24)
        
        # Format the timestamp for PostgreSQL with timezone information
        timestamp_str = twenty_four_hours_ago.strftime("%Y-%m-%d %H:%M:%S %z")
        logger.info(f"Filtering for records newer than: {timestamp_str}")
        
        # Use parameterized query with table name as a parameter
        # Look for timestamp or created_at column for time filtering
        # First, check if the table has a timestamp column
        check_column_query = """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = %s 
            AND column_name IN ('timestamp', 'created_at', 'time', 'date')
        """
        
        time_columns = RDSHelper.execute_query_with_result_and_close(
            RDSHelper.get_connection_with_iam(rds_config),
            check_column_query,
            (DB_TABLE,)
        )
       
        # Construct the query based on available time column
        if time_columns:
            time_column = time_columns[0]['column_name']
            logger.info(f"Found time column: {time_column}")
            
            # Use AT TIME ZONE to ensure proper timezone comparison
            query = f'''
                SELECT * FROM "{DB_TABLE}" 
                WHERE value = %s 
                AND predicted_label = false 
                AND {time_column} AT TIME ZONE 'UTC' >= %s::timestamptz
            '''
            db_params = (65535, timestamp_str)
        else:
            logger.info("No time column found, querying without time constraint")
            query = f'SELECT * FROM "{DB_TABLE}" WHERE value = %s AND predicted_label = false'
            db_params = (65535,)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"{RETRIEVAL_PREFIX}/query_results_{timestamp}.csv"
        
        # Execute the query
        conn = RDSHelper.get_connection_with_iam(rds_config)
        records = RDSHelper.execute_query_with_result_and_close(conn, query, db_params)
        logger.info(f"Successfully executed query, found {len(records) if records else 0} records")

        if not records:
            # Return status code 204 to indicate no content found
            # This will be used by the Step Function to exit early
            return {
                "statusCode": 204,  # Changed from 200 to 204 (No Content)
                "body": {
                    "message": "No records found in the last 24 hours with value 65535",
                    "records": 0,
                    "file_name": None,
                },
            }
        else:
            try:
                S3Helper.write_csv(records, SOURCE_BUCKET, file_name, REGION)
                logger.info(f"Successfully wrote {len(records)} records to S3: {file_name}")
            except ClientError as e:
                logger.error(f"Error uploading to S3: {str(e)}")
                return {
                    "statusCode": 500,
                    "body": {"message": f"Error uploading to S3: {str(e)}"},
                }

            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": {
                    "message": f"Query executed successfully. Found {len(records)} records from the last 24 hours with value 65535",
                    "records": len(records),
                    "file_name": file_name,
                },
            }

    except ClientError as e:
        logger.error(f"ClientError: {str(e)}")
        return {
            "statusCode": 500,
            "body": {"message": f"Error fetching data: {str(e)}"},
        }
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return {
            "statusCode": 500, "body": {
                "message": f"Unexpected error: {str(e)}"
            }
        }