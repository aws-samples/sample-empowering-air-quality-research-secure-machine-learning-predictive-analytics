###
# © 2025 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
# This AWS Content is provided subject to the terms of the AWS Customer Agreement
# available at http://aws.amazon.com/agreement or other written agreement between
# Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.
###

import boto3
import uuid
import time
import json
import pandas as pd
import io
import ast
from utils_helper import get_env, get_logger
from botocore.exceptions import ClientError

logger = get_logger(service="sagemaker_helper", level="debug")
sagemaker_client = boto3.client("sagemaker")
runtime_client = boto3.client("runtime.sagemaker")

# Configuration parameters from environment variables
BATCH_TRANSFORM_INSTANCE_TYPE = get_env("BATCH_TRANSFORM_INSTANCE_TYPE", "ml.m5.xlarge")
BATCH_TRANSFORM_INSTANCE_COUNT = int(get_env("BATCH_TRANSFORM_INSTANCE_COUNT", "1"))
BATCH_TRANSFORM_MAX_WAIT_TIME = int(get_env("BATCH_TRANSFORM_MAX_WAIT_TIME_IN_SECONDS", "900"))
BATCH_TRANSFORM_CHECK_INTERVAL = int(get_env("BATCH_TRANSFORM_CHECK_INTERVAL_IN_SECONDS", "10"))
ATTRIBUTES_FOR_PREDICTION = get_env("ATTRIBUTES_FOR_PREDICTION", "['timestamp', 'parameter', 'device_id', 'location_id', 'deployment_date']")

class SageMakerHelper:
    
    @staticmethod
    def get_inference(body, endpoint_name):
        """
        Get real-time inference from a SageMaker endpoint
        """
        response = runtime_client.invoke_endpoint(
            EndpointName=endpoint_name,
            ContentType="text/csv",
            Body=body,
            Accept="application/json",
        )
        return response
    
    @staticmethod
    def run_batch_prediction(model_id, input_location, output_location, instance_type=None, instance_count=None):
        """
        Run batch predictions using a SageMaker model
        
        Args:
            model_id (str): The SageMaker model name
            input_location (str): S3 location of input data (s3://bucket/prefix/file.csv)
            output_location (str): S3 location for output data (s3://bucket/prefix)
            instance_type (str, optional): Instance type for batch transform. If None, uses environment variable.
            instance_count (int, optional): Number of instances. If None, uses environment variable.
            
        Returns:
            dict: Response containing batch transform job details
        """
        start_time = time.time()
        logger.debug(f"Starting batch prediction for model: {model_id}")
        logger.debug(f"Input location: {input_location}")
        logger.debug(f"Output location: {output_location}")
        
        # Use environment variables if parameters not provided
        final_instance_type = instance_type or BATCH_TRANSFORM_INSTANCE_TYPE
        final_instance_count = instance_count or BATCH_TRANSFORM_INSTANCE_COUNT
        
        logger.info(f"Using instance type: {final_instance_type}, instance count: {final_instance_count}")
        
        try:
            # Generate a unique job name
            job_name = f"batch-{uuid.uuid4().hex[:8]}"
            logger.debug(f"Generated job name: {job_name}")
            
            # Create batch transform job directly using the model
            response = sagemaker_client.create_transform_job(
                TransformJobName=job_name,
                ModelName=model_id,
                TransformInput={
                    'DataSource': {
                        'S3DataSource': {
                            'S3DataType': 'S3Prefix',
                            'S3Uri': input_location
                        }
                    },
                    'ContentType': 'text/csv',
                    'SplitType': 'Line'
                },
                TransformOutput={
                    'S3OutputPath': output_location,
                    'Accept': 'text/csv',
                    'AssembleWith': 'None'
                },
                TransformResources={
                    'InstanceType': final_instance_type,
                    'InstanceCount': final_instance_count
                }
            )
            
            logger.debug(f"Batch transform job created successfully: {job_name}")
            
            result = {
                'TransformJobName': job_name,
                'ModelName': model_id,
                'TransformJobArn': response.get('TransformJobArn'),
                'InstanceType': final_instance_type,
                'InstanceCount': final_instance_count,
                'ExecutionTime': time.time() - start_time
            }
            
            logger.debug(f"Returning result: {json.dumps(result, default=str)}")
            return result
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"Error after {elapsed:.2f} seconds: {str(e)}")
            raise
    
    @staticmethod
    def get_batch_prediction_status(transform_job_name):
        """
        Get the status of a batch transform job
        
        Args:
            transform_job_name (str): The name of the transform job
            
        Returns:
            dict: Status information
        """
        try:
            response = sagemaker_client.describe_transform_job(
                TransformJobName=transform_job_name
            )
            
            return {
                'TransformJobName': transform_job_name,
                'Status': response['TransformJobStatus'],
                'CreationTime': response['CreationTime'],
                'TransformStartTime': response.get('TransformStartTime'),
                'TransformEndTime': response.get('TransformEndTime'),
                'FailureReason': response.get('FailureReason'),
                'OutputLocation': response['TransformOutput']['S3OutputPath']
            }
        except Exception as e:
            logger.error(f"Error getting transform job status: {str(e)}")
            return {
                'TransformJobName': transform_job_name,
                'Status': 'Unknown',
                'Error': str(e)
            }
    
    @staticmethod
    def list_batch_jobs(max_results=10):
        """
        List recent batch transform jobs
        
        Args:
            max_results (int, optional): Maximum number of results to return. Defaults to 10.
            
        Returns:
            list: List of transform jobs
        """
        try:
            response = sagemaker_client.list_transform_jobs(
                SortBy='CreationTime',
                SortOrder='Descending',
                MaxResults=max_results
            )
            
            return response.get('TransformJobSummaries', [])
        except Exception as e:
            logger.error(f"Error listing transform jobs: {str(e)}")
            return []
    
    @staticmethod
    def check_model_exists(model_name):
        """
        Check if a SageMaker model exists
        
        Args:
            model_name (str): The name of the model to check
            
        Returns:
            bool: True if model exists, False otherwise
        """
        try:
            sagemaker_client.describe_model(ModelName=model_name)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'ValidationException':
                return False
            else:
                logger.error(f"Error checking model existence: {str(e)}")
                raise
    @staticmethod
    def wait_for_batch_job(job_name, max_wait_time=None, check_interval=None):
        """
        Wait for a batch transform job to complete
        
        Args:
            job_name (str): Name of the batch transform job
            max_wait_time (int, optional): Maximum time to wait in seconds. If None, uses environment variable.
            check_interval (int, optional): Time between status checks in seconds. If None, uses environment variable.
            
        Returns:
            str: Final job status
        """
        # Use environment variables if parameters not provided
        final_max_wait_time = max_wait_time or BATCH_TRANSFORM_MAX_WAIT_TIME
        final_check_interval = check_interval or BATCH_TRANSFORM_CHECK_INTERVAL
        
        logger.info(f"Waiting for job {job_name} with max_wait_time={final_max_wait_time}s, check_interval={final_check_interval}s")
        
        start_time = time.time()
        elapsed_time = 0
        
        while elapsed_time < final_max_wait_time:
            job_info = SageMakerHelper.get_batch_prediction_status(job_name)
            status = job_info.get('Status')
            
            if status.upper() in ['COMPLETED', 'FAILED', 'STOPPED']:
                logger.info(f"Job {job_name} completed with status: {status}")
                return status
                
            logger.debug(f"Job status: {status}, waiting {final_check_interval} seconds...")
            time.sleep(final_check_interval)
            elapsed_time = time.time() - start_time
        
        logger.warning(f"Job {job_name} did not complete within {final_max_wait_time} seconds")
        return "TIMED_OUT"
        
    @staticmethod
    def get_prediction_attributes():
        """
        Get the list of attributes to use for prediction from environment variable
        
        Returns:
            list: List of attribute names for prediction
        """
        try:
            if isinstance(ATTRIBUTES_FOR_PREDICTION, str):
                attributes = ast.literal_eval(ATTRIBUTES_FOR_PREDICTION)
            else:
                attributes = ATTRIBUTES_FOR_PREDICTION
            logger.debug(f"Using prediction attributes from config: {attributes}")
            return attributes
        except (ValueError, SyntaxError) as e:
            logger.warning(f"Failed to parse ATTRIBUTES_FOR_PREDICTION: {e}. Using default.")
            default_attributes = ['timestamp', 'parameter', 'device_id', 'location_id', 'deployment_date']
            return default_attributes
    
    @staticmethod
    def prepare_prediction_data(df):
        """
        Prepare data for prediction using configured attributes from environment variable
        
        Args:
            df (DataFrame): Input dataframe
            
        Returns:
            DataFrame: Prepared dataframe with only prediction attributes
        """
        required_columns = SageMakerHelper.get_prediction_attributes()
        
        # Check if all required columns exist
        missing_columns = set(required_columns) - set(df.columns)
        if missing_columns:
            error_message = f"Missing required columns in input data: {missing_columns}"
            logger.error(error_message)
            raise Exception(error_message)

        # Create input dataframe with only the required columns
        input_df = df[required_columns]
        logger.info(f"Using {len(required_columns)} columns for prediction: {required_columns}")
        
        return input_df
        
    @staticmethod
    def process_batch_results(job_name, original_df, output_prefix, output_file_name, source_bucket):
        """
        Process batch transform results and combine with original data
        
        Args:
            job_name (str): Name of the batch transform job
            original_df (DataFrame): Original input dataframe
            output_prefix (str): S3 prefix where batch results are stored
            output_file_name (str): Name of the output file to process
            source_bucket (str): S3 bucket name where results are stored
            
        Returns:
            DataFrame: Combined results dataframe
        """

        
        # Set up S3 client
        s3_client = boto3.client('s3')
        
        # Check if the file exists in S3
        try:
            logger.debug(f"Checking if file exists: s3://{source_bucket}/{output_prefix}/{output_file_name}")
            s3_client.head_object(Bucket=source_bucket, Key=f"{output_prefix}/{output_file_name}")
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                # The file does not exist
                error_msg = f"Output file not found: s3://{source_bucket}/{output_prefix}/{output_file_name}"
                logger.error(error_msg)
                
                # Try to list files in the output prefix to provide more context
                try:
                    response = s3_client.list_objects_v2(
                        Bucket=source_bucket,
                        Prefix=output_prefix,
                        MaxKeys=10
                    )
                    
                    if 'Contents' in response and len(response['Contents']) > 0:
                        available_files = [item['Key'] for item in response['Contents']]
                        logger.info(f"Available files in prefix: {available_files}")
                        raise Exception(f"{error_msg}. Available files in prefix: {available_files}")
                    else:
                        raise Exception(f"{error_msg}. No files found in prefix: {output_prefix}")
                except Exception as list_error:
                    # If we can't list files, just raise the original error
                    raise Exception(error_msg)
            else:
                # Something else went wrong
                raise Exception(f"Error checking file existence: {str(e)}")
        
        logger.debug(f"File exists, reading: {output_file_name}")
        
        # Read the predictions directly from S3 using boto3
        try:
            s3_response = s3_client.get_object(Bucket=source_bucket, Key=f"{output_prefix}/{output_file_name}")
            file_content = s3_response['Body'].read()
            
            # Parse CSV content
            predictions_df = pd.read_csv(io.BytesIO(file_content), header=None)
            logger.debug(f"Successfully read predictions file with {len(predictions_df)} rows and columns: {predictions_df.columns.tolist()}")
        except Exception as e:
            logger.error(f"Error reading predictions file: {str(e)}")
            raise
        
        # Check if we have the right number of predictions
        if len(predictions_df) != len(original_df):
            logger.error(f"Prediction count ({len(predictions_df)}) doesn't match input count ({len(original_df)})")
            logger.error(f"Original data shape: {original_df.shape}")
            logger.error(f"Predictions shape: {predictions_df.shape}")
            
            # If predictions have more rows, take only the first N rows to match original data
            if len(predictions_df) > len(original_df):
                logger.warning(f"Truncating predictions from {len(predictions_df)} to {len(original_df)} rows")
                predictions_df = predictions_df.head(len(original_df))
            else:
                # If predictions have fewer rows, this is a more serious issue
                raise Exception(f"Insufficient predictions: got {len(predictions_df)}, expected {len(original_df)}")
        
        # Determine the prediction column name
        if len(predictions_df.columns) == 0:
            raise Exception("Prediction file has no columns")
            
        prediction_column = predictions_df.columns[0]
        logger.debug(f"Using prediction column: {prediction_column}")
        
        # Create a copy of the original dataframe
        result_df = original_df.copy()
        
        # Reset indices to ensure alignment
        predictions_df = predictions_df.reset_index(drop=True)
        result_df = result_df.reset_index(drop=True)
        
        # Add the predictions with proper alignment
        try:
            result_df['predicted_value'] = predictions_df[prediction_column].values
            logger.debug(f"Successfully added {len(predictions_df)} predictions to {len(result_df)} rows")
        except Exception as e:
            logger.error(f"Error adding predictions: {str(e)}")
            logger.error(f"Predictions shape: {predictions_df[prediction_column].values.shape}")
            logger.error(f"Result dataframe shape: {result_df.shape}")
            raise Exception(f"Failed to align predictions with original data: {str(e)}")
        
        # Add predicted_label column with TRUE value for all rows
        result_df['predicted_label'] = 'TRUE'
        
        logger.info(f"Successfully processed batch results: {len(result_df)} rows with predictions")
        return result_df
