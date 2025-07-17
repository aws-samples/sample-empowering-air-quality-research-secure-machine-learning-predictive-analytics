from datetime import datetime
import json
import boto3
from sagemaker_helper import SageMakerHelper
from utils_helper import get_env, get_logger
from s3_helper import S3Helper

# Environment variables
REGION = get_env("AWS_REGION", "us-east-1")
LOG_LEVEL = get_env("LOG_LEVEL", "DEBUG")
SERVICE_NAME = get_env("SERVICE_NAME", "batch_transform_callback_lambda")
SOURCE_BUCKET = get_env("SOURCE_BUCKET")
PREDICTED_PREFIX = get_env("PREDICTED_PREFIX", "predicted_values_output")

logger = get_logger(service=SERVICE_NAME, level=LOG_LEVEL)


def lambda_handler(event, context):
    """
    Handles SageMaker batch transform job completion events from EventBridge
    and sends callbacks to Step Functions
    """
    logger.info("Batch transform callback handler started")
    logger.debug(f"Received event: {json.dumps(event, default=str)}")
    
    try:
        # Extract job information from EventBridge event
        if 'detail' in event:
            # EventBridge event from SageMaker
            detail = event['detail']
            batch_job_name = detail.get('TransformJobName')
            job_status = detail.get('TransformJobStatus')
        else:
            # Direct invocation for testing
            batch_job_name = event.get('batch_job_name')
            job_status = event.get('job_status', 'Unknown')
        
        if not batch_job_name:
            logger.error("No batch job name found in event")
            return {
                'statusCode': 400,
                'body': {'message': 'No batch job name provided'}
            }
        
        logger.info(f"Processing callback for job: {batch_job_name}, status: {job_status}")
        
        # Retrieve job metadata from Parameter Store
        ssm = boto3.client('ssm')
        try:
            response = ssm.get_parameter(Name=f'/batch-transform/{batch_job_name}/metadata')
            job_metadata = json.loads(response['Parameter']['Value'])
        except Exception as e:
            logger.error(f"Failed to retrieve job metadata: {str(e)}")
            return {
                'statusCode': 500,
                'body': {'message': f'Failed to retrieve job metadata: {str(e)}'}
            }
        
        task_token = job_metadata.get('task_token')
        if not task_token:
            logger.error("No task token found in job metadata")
            return {
                'statusCode': 500,
                'body': {'message': 'No task token found in job metadata'}
            }
        
        stepfunctions_client = boto3.client('stepfunctions')
        
        if job_status == 'Completed':
            logger.info(f"Job {batch_job_name} completed successfully")
            
            # Process the batch transform results
            try:
                result_data = process_batch_results(job_metadata)
                
                # Send success callback to Step Functions
                stepfunctions_client.send_task_success(
                    taskToken=task_token,
                    output=json.dumps({
                        "statusCode": 200,
                        "body": {
                            "message": "Batch transform completed successfully",
                            "batch_job_name": batch_job_name,
                            "records": result_data.get('records_processed', 0),
                            "key": result_data.get('output_file'),
                            "status": "COMPLETED"
                        }
                    })
                )
                
                logger.info("Sent success callback to Step Functions")
                
            except Exception as e:
                logger.error(f"Error processing batch results: {str(e)}")
                # Send failure callback
                stepfunctions_client.send_task_failure(
                    taskToken=task_token,
                    error='BatchResultProcessingFailed',
                    cause=f'Failed to process batch transform results: {str(e)}'
                )
                
        else:
            logger.error(f"Job {batch_job_name} failed with status: {job_status}")
            # Send failure callback to Step Functions
            stepfunctions_client.send_task_failure(
                taskToken=task_token,
                error='BatchTransformFailed',
                cause=f'Batch transform job failed with status: {job_status}'
            )
            
            logger.info("Sent failure callback to Step Functions")
        
        # Clean up Parameter Store entry
        try:
            ssm.delete_parameter(Name=f'/batch-transform/{batch_job_name}/metadata')
            logger.info("Cleaned up job metadata from Parameter Store")
        except Exception as e:
            logger.warning(f"Failed to clean up job metadata: {str(e)}")
        
        return {
            'statusCode': 200,
            'body': {
                'message': f'Callback processed for job {batch_job_name}',
                'job_status': job_status
            }
        }
        
    except Exception as e:
        logger.error(f"Error in callback handler: {str(e)}")
        return {
            'statusCode': 500,
            'body': {'message': f'Error processing callback: {str(e)}'}
        }


def process_batch_results(job_metadata):
    """
    Process the batch transform results and prepare output file
    """
    batch_job_name = job_metadata['batch_job_name']
    output_batch_prefix = job_metadata['output_batch_prefix']
    batch_job_id = job_metadata['batch_job_id']
    timestamp = job_metadata['timestamp']
    original_file_key = job_metadata.get('original_file_key')
    
    logger.info(f"Processing results for job: {batch_job_name}")
    
    # Get the original input data
    original_df = S3Helper.read_csv_from_s3(SOURCE_BUCKET, original_file_key, REGION)
    
    if original_df is None or original_df.empty:
        raise Exception("Failed to read original input data")
    
    # Process the batch transform results
    result_df = SageMakerHelper.process_batch_results(
        job_name=batch_job_name,
        original_df=original_df,
        output_prefix=output_batch_prefix,
        output_file_name=f"{batch_job_id}_{timestamp}.csv.out",
        source_bucket=SOURCE_BUCKET
    )

    # Get original_data_columns from job_metadata with a default empty list if not present
    original_data_columns = job_metadata.get('original_data_columns', [])
    
    # Ensure all original columns are preserved
    if original_data_columns:
        missing_cols = set(original_data_columns) - set(result_df.columns)
        if missing_cols:
            logger.warning(f"Missing columns in result: {missing_cols}")
        # Reorder columns to match original order plus predictions
        available_original_cols = [col for col in original_data_columns if col in result_df.columns]
        prediction_cols = [col for col in result_df.columns if col not in original_data_columns]
        result_df = result_df[available_original_cols + prediction_cols]
    
    if result_df is None or result_df.empty:
        raise Exception("Failed to process batch transform results")
    
    # Save the final results with predictions
    final_output_key = f"{PREDICTED_PREFIX}/output_results_{timestamp}.csv"
    S3Helper.save_csv_to_s3(result_df, SOURCE_BUCKET, final_output_key)
    
    logger.info(f"Saved final results to: s3://{SOURCE_BUCKET}/{final_output_key}")
    
    return {
        'records_processed': len(result_df),
        'output_file': final_output_key
    }
