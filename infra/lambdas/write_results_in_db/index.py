from common import SecretsHelper, RDSHelper, PredictionsHelper, get_env, get_logger
import json

SECRET_NAME = get_env("SECRET_NAME")
REGION = get_env("AWS_REGION", "us-east-1")
SOURCE_BUCKET = get_env("SOURCE_BUCKET")
DB_TABLE = get_env("DB_TABLE")
SECRET_NAME = get_env("SECRET_NAME")
LOG_LEVEL = get_env("LOG_LEVEL", "DEBUG")
SERVICE_NAME = get_env("SERVICE_NAME", "air_quality_query_lambda")
logger = get_logger(service=SERVICE_NAME, level=LOG_LEVEL)


# Usage in your lambda handler
def lambda_handler(event, context):
    logger.info("Starting lambda execution")
    try:
        # Get the file name from the event
        event_body = event["Payload"]["body"]
        if isinstance(event_body, str):
            event_body = json.loads(event_body)
        file_name = event_body["key"]
        if not file_name:
            return {"statusCode": 400, "body": "File name not provided in the event"}
        records = event_body["records"]

        if records == 0:
            return {
                "statusCode": 200,
                "body": "Nothing to update. No predictions found",
            }
        # Parse predictions
        predictions = PredictionsHelper.parse_predictions_from_s3(
            SOURCE_BUCKET, file_name, REGION
        )

        if not predictions:
            return {
                "statusCode": 500,
                "body": "Failed to parse predictions or no predictions found",
            }

        # Get database connection
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

        conn = RDSHelper.get_connection_with_password(rds_config=rds_config)

        # Process predictions
        successful_updates = 0
        for pred in predictions:
            try:
                query = (
                    "UPDATE {} SET value = %s, predicted_label= TRUE WHERE id = %s"
                ).format(DB_TABLE)
                db_params = (pred["predicted_value"], pred["id"])

                # Execute query
                result = RDSHelper.execute_update_query_with_params_and_result(
                    conn, query, db_params
                )

                if result:
                    successful_updates += 1

            except Exception as e:
                logger.error(f"Error updating prediction for id {pred['id']}: {str(e)}")
                continue

        return {
            "statusCode": 200,
            "body": {
                "message": "Predictions complete!",
                "total_records": len(predictions),
                "update_records": successful_updates,
            },
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": {"message": f"Error in lambda execution: {str(e)}"},
        }
