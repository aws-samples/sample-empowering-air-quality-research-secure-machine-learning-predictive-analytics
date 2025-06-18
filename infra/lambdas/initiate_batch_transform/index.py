from datetime import datetime
import pandas as pd
import json
import uuid
from sagemaker_helper import SageMakerHelper
from utils_helper import get_env, get_logger
from s3_helper import S3Helper
import boto3

# Environment variables
REGION = get_env("AWS_REGION", "us-east-1")
LOG_LEVEL = get_env("LOG_LEVEL", "DEBUG")
SERVICE_NAME = get_env("SERVICE_NAME", "initiate_batch_transform_lambda")
CANVAS_MODEL_ID = get_env("CANVAS_MODEL_ID", "")
SOURCE_BUCKET = get_env("SOURCE_BUCKET")

logger = get_logger(service=SERVICE_NAME, level=LOG_LEVEL)


def lambda_handler(event, context):
    """
    Initiates a SageMaker batch transform job and stores task token for callback
    """
    logger.info("Starting batch transform initiation")
    logger.debug(f"Received event: {json.dumps(event, default=str)}")
    
    # Extract task token from Step Functions context
    task_token = event.get('TaskToken')
    if not task_token:
        logger.error("No task token provided in event")
        error_response = {"statusCode": 400, "body": {"message": "No task token provided"}}
        # Send failure callback to Step Functions
        try:
            stepfunctions_client = boto3.client('stepfunctions')
            stepfunctions_client.send_task_failure(
                taskToken=task_token,
                error="MissingTaskToken",
                cause="No task token provided in event"
            )
        except Exception as callback_error:
            logger.error(f"Failed to send failure callback: {str(callback_error)}")
        return error_response

    # Validate Canvas model ID is configured
    model_id = CANVAS_MODEL_ID
    if not model_id:
        logger.error("Canvas model ID not configured")
        error_response = {"statusCode": 500, "body": {"message": "Canvas model ID not configured. Please run post-deployment configuration."}}
        # Send failure callback to Step Functions
        try:
            stepfunctions_client = boto3.client('stepfunctions')
            stepfunctions_client.send_task_failure(
                taskToken=task_token,
                error="MissingCanvasModelId",
                cause="Canvas model ID not configured in environment variables"
            )
        except Exception as callback_error:
            logger.error(f"Failed to send failure callback: {str(callback_error)}")
        return error_response

    # Parse the query result from the new payload structure
    try:
        query_result_str = event.get('QueryResult')
        if not query_result_str:
            raise ValueError("No QueryResult provided in event")
        
        # Parse the JSON string if it's a string, otherwise use directly
        if isinstance(query_result_str, str):
            query_result = json.loads(query_result_str)
        else:
            query_result = query_result_str
            
        logger.debug(f"Parsed query result: {json.dumps(query_result, default=str)}")
        
    except (json.JSONDecodeError, ValueError) as parse_error:
        logger.error(f"Failed to parse QueryResult: {str(parse_error)}")
        error_response = {"statusCode": 400, "body": {"message": f"Invalid QueryResult format: {str(parse_error)}"}}
        # Send failure callback to Step Functions
        try:
            stepfunctions_client = boto3.client('stepfunctions')
            stepfunctions_client.send_task_failure(
                taskToken=task_token,
                error="InvalidQueryResult",
                cause=f"Failed to parse QueryResult: {str(parse_error)}"
            )
        except Exception as callback_error:
            logger.error(f"Failed to send failure callback: {str(callback_error)}")
        return error_response

    # Extract file information from query result
    file_key = query_result.get("body", {}).get("file_name")
    if not file_key:
        logger.error("No file key provided in query result")
        error_response = {"statusCode": 400, "body": {"message": "No file key provided"}}
        # Send failure callback to Step Functions
        try:
            stepfunctions_client = boto3.client('stepfunctions')
            stepfunctions_client.send_task_failure(
                taskToken=task_token,
                error="MissingFileKey",
                cause="No file key provided in query result"
            )
        except Exception as callback_error:
            logger.error(f"Failed to send failure callback: {str(callback_error)}")
        return error_response

    records_ct = query_result.get("body", {}).get("records", 0)
    if records_ct == 0:
        logger.info("No records to process, sending success callback")
        # Send success callback immediately for no records case
        try:
            stepfunctions_client = boto3.client('stepfunctions')
            stepfunctions_client.send_task_success(
                taskToken=task_token,
                output=json.dumps({
                    "statusCode": 200,
                    "body": {"message": "No records found", "records": 0, "key": file_key}
                })
            )
        except Exception as callback_error:
            logger.error(f"Failed to send no-records callback: {str(callback_error)}")
        
        return {
            "statusCode": 200,
            "body": {"message": "No records found", "records": 0, "key": file_key},
        }

    try:
        # Read the input data
        logger.info(f"Reading input data from s3://{SOURCE_BUCKET}/{file_key}")
        df = S3Helper.read_csv_from_s3(SOURCE_BUCKET, file_key)
        
        if df is None or df.empty:
            raise Exception("Failed to read input data or data is empty")
        
        logger.info(f"Successfully read {len(df)} records from input file")
        
        # Prepare data for batch prediction using configured attributes
        input_df = SageMakerHelper.prepare_prediction_data(df)
        
        # Generate a unique ID for this batch prediction job
        batch_job_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save the prepared data to S3 for batch prediction
        input_batch_prefix = f"input_batch"
        output_batch_prefix = f"output_batch"
        input_s3_key = f"{input_batch_prefix}/{batch_job_id}_{timestamp}.csv"
        S3Helper.save_csv_to_s3(input_df, SOURCE_BUCKET, input_s3_key, include_header=False)
        
        logger.info(f"Prepared input data saved to s3://{SOURCE_BUCKET}/{input_s3_key}")

        # Check if model exists
        if not SageMakerHelper.check_model_exists(model_id):
            error_message = f'Model {model_id} not found. Please provide a valid SageMaker model name.'
            logger.error(error_message)
            raise Exception(error_message)

        # Start batch transform job
        logger.info(f"Starting batch transform job with model: {model_id}")
        batch_job = SageMakerHelper.run_batch_prediction(
            model_id=model_id,
            input_location=f"s3://{SOURCE_BUCKET}/{input_s3_key}",
            output_location=f"s3://{SOURCE_BUCKET}/{output_batch_prefix}"
        )
    
        batch_job_name = batch_job["TransformJobName"]
        logger.info(f"Started batch transform job: {batch_job_name}")

        # Store job metadata for the callback function
        job_metadata = {
            "batch_job_name": batch_job_name,
            "batch_job_id": batch_job_id,
            "timestamp": timestamp,
            "task_token": task_token,
            "input_s3_key": input_s3_key,
            "output_batch_prefix": output_batch_prefix,
            "source_bucket": SOURCE_BUCKET,
            "original_file_key": file_key,
            "records_count": len(input_df),
            "model_id": model_id,
            "original_data_columns": list(df.columns)
        }
        
        # Store in Parameter Store for callback Lambda to retrieve
        ssm = boto3.client('ssm')
        ssm.put_parameter(
            Name=f'/batch-transform/{batch_job_name}/metadata',
            Value=json.dumps(job_metadata),
            Type='String',
            Overwrite=True
        )
        
        logger.info(f"Job metadata stored in Parameter Store: /batch-transform/{batch_job_name}/metadata")

        # The job is now running asynchronously
        # The callback Lambda will be triggered by EventBridge when job completes
        # and will use the stored task token to notify Step Functions
        
        logger.info(f"Batch transform job {batch_job_name} started successfully. Waiting for callback...")
        
        # Return success - the Step Function will wait for callback
        # Don't call send_task_success here - that's the callback Lambda's job
        return {
            "statusCode": 202,  # Accepted - processing started
            "body": {
                "message": "Batch transform job initiated successfully",
                "batch_job_name": batch_job_name,
                "batch_job_id": batch_job_id,
                "status": "IN_PROGRESS"
            }
        }
    
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        
        # Send failure callback to Step Functions
        try:
            stepfunctions_client = boto3.client('stepfunctions')
            stepfunctions_client.send_task_failure(
                taskToken=task_token,
                error='BatchTransformInitiationFailed',
                cause=str(e)
            )
            logger.info("Sent failure callback to Step Functions")
        except Exception as callback_error:
            logger.error(f"Failed to send failure callback: {str(callback_error)}")
        
        return {
            'statusCode': 500,
            'body': {
                'message': f'Error during batch transform initiation: {str(e)}'
            }
        }
        # Don't fail the main function for monitoring setup issues
