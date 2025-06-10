from datetime import datetime
import pandas as pd
import json
import time
import uuid
from sagemaker_helper import SageMakerHelper
from utils_helper import get_env, get_logger
from s3_helper import S3Helper

# Environment variables
REGION = get_env("AWS_REGION", "us-east-1")
LOG_LEVEL = get_env("LOG_LEVEL", "DEBUG")
SERVICE_NAME = get_env("SERVICE_NAME", "inference_lambda")
CANVAS_MODEL_ID = get_env("CANVAS_MODEL_ID", "canvas-aq-model-1748983530549")
CANVAS_MODEL_ENDPOINT_NAME = get_env("CANVAS_MODEL_ENDPOINT_NAME", "canvas-aq-model-endpoint-serverless")
PREDICTED_PREFIX = get_env("PREDICTED_PREFIX", "predicted_values_output")
SOURCE_BUCKET = get_env("SOURCE_BUCKET")
#BATCH_PREDICTION_TIMEOUT = int(get_env("BATCH_PREDICTION_TIMEOUT", "900"))  # 30 minutes default
#BATCH_PREDICTION_POLL_INTERVAL = int(get_env("BATCH_PREDICTION_POLL_INTERVAL", "30"))  # 30 seconds default

logger = get_logger(service=SERVICE_NAME, level=LOG_LEVEL)


def lambda_handler(event, context):

    model_id=CANVAS_MODEL_ID

    file_key = event["Payload"]["body"]["file_name"]
    if not file_key:
        return {"statusCode": 400, "body": {"message": "No file key provided"}}

    records_ct = event["Payload"]["body"]["records"]
    if records_ct == 0:
        return {
            "statusCode": 200,
            "body": {"message": "No records found", "records": 0, "key": file_key},
        }

    # Read the input data
    df = S3Helper.read_csv_from_s3(SOURCE_BUCKET, file_key)
    
    # Prepare data for batch prediction
    # Select only the columns needed for prediction
    required_columns = [
        'timestamp', 
        'parameter', 
        'sensor_type', 
        'sensor_id', 
        'location_id', 
        'latitude', 
        'longitude', 
        'deployment_date'
    ]

    # Check if all required columns exist
    missing_columns = set(required_columns) - set(df.columns)
    if missing_columns:
        error_message = f"Missing required columns in input data: {missing_columns}"
        logger.error(error_message)
        return {"statusCode": 400, "body": {"message": error_message}}

    # Create input dataframe with only the required columns
    input_df = df[required_columns]
    logger.debug(f"Using {len(required_columns)} columns for prediction: {required_columns}")
    
    # Generate a unique ID for this batch prediction job
    batch_job_id = str(uuid.uuid4())
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save the prepared data to S3 for batch prediction
    input_batch_prefix = f"input_batch"
    output_batch_prefix = f"output_batch"
    S3Helper.save_csv_to_s3(input_df, SOURCE_BUCKET, f"{input_batch_prefix}/{batch_job_id}_{timestamp}.csv", include_header=False)
    
    logger.debug(f"Prepared input data saved to s3://{SOURCE_BUCKET}/{input_batch_prefix}")

    # Run batch prediction using the serverless endpoint
    try:
    
        logger.debug(f"Starting batch prediction for model: {model_id}")
        
        # Check if model exists
        if not SageMakerHelper.check_model_exists(model_id):
            return {
                'statusCode': 404,
                'body': {
                    'message': f'Model {model_id} not found. Please provide a valid SageMaker model name.'
                }
            }

        batch_job = SageMakerHelper.run_batch_prediction(
            model_id=CANVAS_MODEL_ID,
            input_location=f"s3://{SOURCE_BUCKET}/{input_batch_prefix}/{batch_job_id}_{timestamp}.csv",
            output_location=f"s3://{SOURCE_BUCKET}/{output_batch_prefix}"
        )
    
        batch_job_name = batch_job["TransformJobName"]
        logger.debug(f"Started batch prediction job: {batch_job_id}")

        # Wait for batch prediction job to complete
        job_status = SageMakerHelper.wait_for_batch_job(batch_job_name)
        
        if job_status.upper() != "COMPLETED":
            return {
                "statusCode": 500,
                "body": {"message": f"Batch prediction job failed with status: {job_status}"}
            }
            
        # Process the results
        result_df = SageMakerHelper.process_batch_results(batch_job_name, input_df, output_batch_prefix, output_file_name=f"{batch_job_id}_{timestamp}.csv.out", source_bucket=SOURCE_BUCKET)
        
        # Save the final results
        final_output_key = f"{PREDICTED_PREFIX}/output_results_{timestamp}.csv"
        S3Helper.save_csv_to_s3(result_df, SOURCE_BUCKET, final_output_key)
        
        return {
            "statusCode": 200,
            "body": {
                "message": "Batch prediction process completed!",
                "records": len(result_df),
                "bucket": SOURCE_BUCKET,
                "key": final_output_key,
            },
        }
    
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return {
            'statusCode': 500,
            'body': {
                'message': f'Error during batch prediction: {str(e)}'
            }
        }
