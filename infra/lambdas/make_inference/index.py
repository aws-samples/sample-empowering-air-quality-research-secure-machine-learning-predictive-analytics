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
CANVAS_MODEL_ID = get_env("CANVAS_MODEL_ID", "model-123456789012")
PREDICTED_PREFIX = get_env("PREDICTED_PREFIX", "predicted_values_output")
SOURCE_BUCKET = get_env("SOURCE_BUCKET")
BATCH_PREDICTION_TIMEOUT = int(get_env("BATCH_PREDICTION_TIMEOUT", "300"))  # 30 minutes default
BATCH_PREDICTION_POLL_INTERVAL = int(get_env("BATCH_PREDICTION_POLL_INTERVAL", "30"))  # 30 seconds default

logger = get_logger(service=SERVICE_NAME, level=LOG_LEVEL)


def lambda_handler(event, context):
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
    # Remove columns that shouldn't be used for prediction
    rows_to_remove = ["id", "value", "predicted_label"]
    input_df = df.drop([col for col in rows_to_remove if col in df.columns], axis=1)
    
    # Generate a unique ID for this batch prediction job
    batch_job_id = str(uuid.uuid4())
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save the prepared data to S3 for batch prediction
    input_file_key = f"batch_input/input_{batch_job_id}_{timestamp}.csv"
    S3Helper.save_csv_to_s3(input_df, SOURCE_BUCKET, input_file_key)
    
    logger.debug(f"Prepared input data saved to s3://{SOURCE_BUCKET}/{input_file_key}")
    
    # Start batch prediction job
    output_prefix = f"batch_output/{batch_job_id}_{timestamp}"
    batch_job = SageMakerHelper.start_batch_prediction(
        model_id=CANVAS_MODEL_ID,
        input_location=f"s3://{SOURCE_BUCKET}/{input_file_key}",
        output_location=f"s3://{SOURCE_BUCKET}/{output_prefix}"
    )
    
    batch_job_id = batch_job["BatchPredictionJobId"]
    logger.debug(f"Started batch prediction job: {batch_job_id}")
    
    # Wait for batch prediction job to complete
    start_time = time.time()
    while True:
        status = SageMakerHelper.get_batch_prediction_status(batch_job_id)
        logger.debug(f"Batch prediction job status: {status}")
        
        if status == "COMPLETED":
            logger.debug("Batch prediction job completed successfully")
            break
        elif status in ["FAILED", "STOPPED"]:
            error_message = f"Batch prediction job {status.lower()}"
            logger.error(error_message)
            return {"statusCode": 500, "body": {"message": error_message}}
        
        # Check if we've exceeded the timeout
        if time.time() - start_time > BATCH_PREDICTION_TIMEOUT:
            error_message = "Batch prediction job timed out"
            logger.error(error_message)
            return {"statusCode": 500, "body": {"message": error_message}}
        
        # Wait before checking again
        time.sleep(BATCH_PREDICTION_POLL_INTERVAL)
    
    # Get the results from the batch prediction job
    output_file_key = f"{output_prefix}/predictions.csv"
    try:
        predictions_df = S3Helper.read_csv_from_s3(SOURCE_BUCKET, output_file_key)
        logger.debug(f"Retrieved batch prediction results from s3://{SOURCE_BUCKET}/{output_file_key}")
    except Exception as e:
        error_message = f"Failed to retrieve batch prediction results: {str(e)}"
        logger.error(error_message)
        return {"statusCode": 500, "body": {"message": error_message}}
    
    # Merge predictions with original data
    # The format of predictions_df will depend on Canvas output format
    # Assuming it has a column with predictions that we need to extract
    
    # Create a copy of the original dataframe to store results
    results_df = df.copy()
    
    # Add predictions to results dataframe
    # Adjust this based on the actual format of Canvas batch prediction output
    if "prediction" in predictions_df.columns:
        results_df["predicted_value"] = predictions_df["prediction"]
    elif "score" in predictions_df.columns:
        results_df["predicted_value"] = predictions_df["score"]
    else:
        # If the column name is different, you may need to adjust this
        # This assumes the first column after index contains the predictions
        prediction_column = predictions_df.columns[0]
        results_df["predicted_value"] = predictions_df[prediction_column]
    
    # Add predicted_label column with TRUE value for all rows
    results_df["predicted_label"] = "TRUE"
    
    # Save final results to output bucket
    final_output_file_key = f"{PREDICTED_PREFIX}/predictions_output_{timestamp}.csv"
    S3Helper.save_csv_to_s3(results_df, SOURCE_BUCKET, final_output_file_key)
    
    logger.debug("\nPredictions complete!")
    logger.debug(f"Processed {len(df)} rows")
    logger.debug(f"Results saved to s3://{SOURCE_BUCKET}/{final_output_file_key}")
    logger.debug(f"Added 'predicted_label' column with value 'TRUE' to all rows")
    
    # Return success response
    return {
        "statusCode": 200,
        "body": {
            "message": "Batch prediction process completed!",
            "records": len(df),
            "bucket": SOURCE_BUCKET,
            "key": final_output_file_key,
        },
    }
