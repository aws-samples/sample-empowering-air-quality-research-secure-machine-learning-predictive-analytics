from datetime import datetime
from botocore.exceptions import ClientError
from common import SecretsHelper, RDSHelper, S3Helper, get_env, get_logger


SECRET_NAME = get_env("SECRET_NAME")
REGION = get_env("AWS_REGION", "us-east-1")
SOURCE_BUCKET = get_env("SOURCE_BUCKET")
DB_TABLE = get_env("DB_TABLE")
SECRET_NAME = get_env("SECRET_NAME")
LOG_LEVEL = get_env("LOG_LEVEL", "DEBUG")
SERVICE_NAME = get_env("SERVICE_NAME", "air_quality_query_lambda")
RETRIEVAL_PREFIX = get_env("RETRIEVAL_PREFIX", "retrieved_from_db")
logger = get_logger(service=SERVICE_NAME, level=LOG_LEVEL)


def lambda_handler(event, context):
    logger.info("Starting lambda execution")
    try:
        # Get credentials from Secrets Manager
        secret = SecretsHelper.get_secret(SECRET_NAME)
        if not secret:
            return {"statusCode": 500, "body": "Failed to retrieve secret"}
        rds_config = {
            "host": get_env("DB_HOST"),
            "database": get_env("DB_NAME"),
            "username": secret["username"],
            "password": secret["password"],
            "port": get_env("RDS_DB_PORT", 5432),
            "region": REGION,
        }
        logger.info("Successfully retrieved secret")

        # Establish connection
        conn = RDSHelper.get_connection_with_password(rds_config=rds_config)
        query = (
            # "SELECT * FROM {} WHERE value = %s AND predicted_label = false AND timestamp >= NOW() - INTERVAL '24 hours'"
            "SELECT * FROM {} WHERE value = %s AND predicted_label = false"
            # "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'aqdataset'"
        ).format(DB_TABLE)
        db_params = (65535,)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"{RETRIEVAL_PREFIX}/query_results_{timestamp}.csv"
        records = RDSHelper.execute_query_with_result_and_close(conn, query, db_params)
        logger.info("Successfully executed query")
        if not records:
            return {
                "statusCode": 200,
                "body": {
                    "message": "No records found",
                    "records": len(records),
                    "file_name": None,
                },
            }
        else:
            try:
                S3Helper.write_csv(records, SOURCE_BUCKET, file_name, REGION)
            except ClientError as e:
                return {
                    "statusCode": 500,
                    "body": {"message": f"Error uploading to S3: {str(e)}"},
                }

            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": {
                    "message": "Query executed successfully",
                    "records": len(records),
                    "file_name": file_name,
                },
            }

    except ClientError as e:
        return {
            "statusCode": 500,
            "body": {"message": f"Error fetching data: {str(e)}"},
        }
    except Exception as e:
        return {"statusCode": 500, "body": {"message": f"Unexpected error: {str(e)}"}}
