from common import RDSHelper, PredictionsHelper, get_env, get_logger
import json
import psycopg2

# Centralized environment variables
REGION = get_env("AWS_REGION", "us-east-1")
SOURCE_BUCKET = get_env("SOURCE_BUCKET")
DB_TABLE = get_env("DB_TABLE")
DB_USERNAME = get_env("DB_USERNAME")
RDS_DB_PORT = int(get_env("RDS_DB_PORT", "5432"))
DB_HOST = get_env("DB_HOST")
DB_NAME = get_env("DB_NAME")
LOG_LEVEL = get_env("LOG_LEVEL", "DEBUG")
SERVICE_NAME = get_env("SERVICE_NAME", "writer_lambda")
logger = get_logger(service=SERVICE_NAME, level=LOG_LEVEL)

def lambda_handler(event, context):
    logger.info("Starting lambda execution")
    try:
        # Get the file name from the event
        logger.debug(f"Received event: {json.dumps(event)}")
        
        # Handle different event structures from Step Functions
        event_body = None
        if "input" in event and "body" in event["input"]:
            # Step Functions passes data in "input" field
            event_body = event["input"]["body"]
        elif "Payload" in event and "body" in event["Payload"]:
            # Legacy format
            event_body = event["Payload"]["body"]
        elif "body" in event:
            # Direct format
            event_body = event["body"]
        else:
            logger.error(f"Could not find event body in event structure: {list(event.keys())}")
            return {"statusCode": 400, "body": "Invalid event structure"}
        
        if isinstance(event_body, str):
            event_body = json.loads(event_body)
        
        # Check if we have the expected keys
        if not isinstance(event_body, dict):
            logger.error(f"Unexpected event body format: {event_body}")
            return {"statusCode": 400, "body": "Invalid event format"}
            
        file_name = event_body.get("key")
        if not file_name:
            logger.error("No file name provided in event")
            return {"statusCode": 400, "body": "File name not provided in the event"}
            
        records = event_body.get("records", 0)
        logger.info(f"Processing file: {file_name} with {records} records")

        if records == 0:
            return {
                "statusCode": 200,
                "body": "Nothing to update. No predictions found",
            }
            
        # Parse predictions
        logger.debug(f"Parsing predictions from S3: {SOURCE_BUCKET}/{file_name}")
        predictions = PredictionsHelper.parse_predictions_from_s3(
            SOURCE_BUCKET, file_name, REGION
        )

        if not predictions:
            logger.error("No predictions found or parsing failed")
            return {
                "statusCode": 500,
                "body": "Failed to parse predictions or no predictions found",
            }
            
        logger.info(f"Found {len(predictions)} predictions to process")
        # Log a sample prediction to verify structure
        if predictions:
            logger.debug(f"Sample prediction: {predictions[0]}")

        # Set up RDS configuration for IAM authentication
        rds_config = {
            "host": DB_HOST,
            "database": DB_NAME,
            "username": DB_USERNAME,
            "port": RDS_DB_PORT,
            "region": REGION,
        }
        
        logger.debug(f"Connecting to database: {DB_HOST}/{DB_NAME}")
        # Establish connection using IAM authentication
        conn = RDSHelper.get_connection_with_iam(rds_config)
        logger.info("Successfully established connection using IAM authentication")

        # Process predictions
        successful_updates = 0
        for pred in predictions:
            try:
                # Check if required fields exist
                if "id" not in pred or "predicted_value" not in pred:
                    logger.warning(f"Missing required fields in prediction: {pred}")
                    continue
                    
                # Log the update we're about to perform
                logger.debug(f"Updating record with ID {pred['id']} to value {pred['predicted_value']}")
                
                # Use parameterized query with table name as a parameter
                query = "UPDATE %s SET value = %s, predicted_label = TRUE WHERE id = %s RETURNING id"
                db_params = (psycopg2.extensions.AsIs(DB_TABLE), pred["predicted_value"], pred["id"])

                # Execute query
                result = RDSHelper.execute_update_query_with_params_and_result(
                    conn, query, db_params
                )

                if result:
                    successful_updates += 1
                    logger.debug(f"Successfully updated record with ID {pred['id']}")
                else:
                    logger.warning(f"No record found with ID {pred['id']}")

            except Exception as e:
                logger.error(f"Error updating prediction for id {pred.get('id', 'unknown')}: {str(e)}")
                continue

        # Commit the transaction if not auto-committed
        try:
            conn.commit()
            logger.info("Transaction committed")
        except Exception as e:
            logger.warning(f"Commit operation failed or not needed: {str(e)}")
            
        # Close the connection
        try:
            conn.close()
            logger.info("Database connection closed")
        except Exception as e:
            logger.warning(f"Error closing connection: {str(e)}")

        logger.info(f"Update complete. {successful_updates} of {len(predictions)} records updated.")
        return {
            "statusCode": 200,
            "body": {
                "message": "Predictions complete!",
                "total_records": len(predictions),
                "update_records": successful_updates,
            },
        }

    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
        return {
            "statusCode": 500,
            "body": {"message": f"Error in lambda execution: {str(e)}"},
        }
