from datetime import datetime
import pandas as pd
import json
from sagemaker_helper import SageMakerHelper
from utils_helper import get_env, get_logger
from s3_helper import S3Helper
from botocore.client import Config as ClientConfig

REGION = get_env("AWS_REGION", "us-east-1")
DEFAULT_MAX_RETRY_ATTEMPTS = get_env("MAX_RETRY_ATTEMPTS", 2)
REGION = get_env("AWS_REGION", "us-east-1")
LOG_LEVEL = get_env("LOG_LEVEL", "DEBUG")
SERVICE_NAME = get_env("SERVICE_NAME", "air_quality_inference_lambda")
CANVAS_MODEL_ENDPOINT_NAME = get_env(
    "CANVAS_MODEL_ENDPOINT_NAME", "canvas-AQDeployment"
)
PREDICTED_PREFIX = get_env("PREDICTED_PREFIX", "predicted_values_output")
logger = get_logger(service=SERVICE_NAME, level=LOG_LEVEL)

# Get bucket names from environment variables
source_bucket = get_env("SOURCE_BUCKET")
DEFAULT_CONFIG = ClientConfig(
    region_name=REGION, retries=dict(max_attempts=DEFAULT_MAX_RETRY_ATTEMPTS)
)


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

    df = S3Helper.read_csv_from_s3(source_bucket, file_key)

    # Create a copy of the dataframe to store predictions
    results_df = df.copy()

    # Process each row
    predictions = []
    for index, row in df.iterrows():
        # Create a single row DataFrame
        row_df = pd.DataFrame([row])
        rows_to_remove = ["id", "value", "predicted_label"]
        # check if columns exist in the rows if yes, then drop from df
        row_df = row_df.drop(
            [col for col in rows_to_remove if col in row_df.columns], axis=1
        )

        # Convert to CSV format
        body = row_df.to_csv(header=False, index=False).encode("utf-8")

        # Get prediction
        response = SageMakerHelper.get_inference(body, CANVAS_MODEL_ENDPOINT_NAME)

        # Parse response
        response_body = response["Body"].read().decode("utf-8")
        prediction_data = json.loads(response_body)
        predicted_value = prediction_data["predictions"][0]["score"]
        predictions.append(predicted_value)

        # log progress
        logger.debug(
            f"Processed row {index + 1}/{len(df)}: {row['timestamp']} - {row['parameter']} = {predicted_value:.2f}"
        )

    # Add predictions to results dataframe
    results_df["predicted_value"] = predictions

    # Save results to output bucket
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file_key = f"{PREDICTED_PREFIX}/predictions_output_{timestamp}.csv"
    S3Helper.save_csv_to_s3(results_df, source_bucket, output_file_key)

    logger.debug("\nPredictions complete!")
    logger.debug(f"Processed {len(df)} rows")
    logger.debug(f"Results saved to s3://{source_bucket}/{output_file_key}")

    # add a return statement
    return {
        "statusCode": 200,
        "body": {
            "message": "Process completed!",
            "records": len(df),
            "bucket": source_bucket,
            "key": output_file_key,
        },
    }
