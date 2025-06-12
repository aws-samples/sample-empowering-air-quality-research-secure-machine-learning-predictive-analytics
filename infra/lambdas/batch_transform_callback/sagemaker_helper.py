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
from utils_helper import get_env, get_logger
from botocore.exceptions import ClientError

logger = get_logger(service="sagemaker_helper", level="debug")
sagemaker_client = boto3.client("sagemaker")
runtime_client = boto3.client("runtime.sagemaker")

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
    def run_batch_prediction(model_id, input_location, output_location, instance_type="ml.m5.xlarge", instance_count=1):
        """
        Run batch predictions using a SageMaker model
        
        Args:
            model_id (str): The SageMaker model name
            input_location (str): S3 location of input data (s3://bucket/prefix/file.csv)
            output_location (str): S3 location for output data (s3://bucket/prefix)
            instance_type (str, optional): Instance type for batch transform. Defaults to "ml.m5.xlarge".
            instance_count (int, optional): Number of instances. Defaults to 1.
            
        Returns:
            dict: Response containing batch transform job details
        """
        start_time = time.time()
        logger.debug(f"Starting batch prediction for model: {model_id}")
        logger.debug(f"Input location: {input_location}")
        logger.debug(f"Output location: {output_location}")
        
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
                    'InstanceType': instance_type,
                    'InstanceCount': instance_count
                }
            )
            
            logger.debug(f"Batch transform job created successfully: {job_name}")
            
            result = {
                'TransformJobName': job_name,
                'ModelName': model_id,
                'TransformJobArn': response.get('TransformJobArn'),
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
    def wait_for_batch_job(job_name, max_wait_time=900, check_interval=10):
        """
        Wait for a batch transform job to complete
        
        Args:
            job_name (str): Name of the batch transform job
            max_wait_time (int): Maximum time to wait in seconds
            check_interval (int): Time between status checks in seconds
            
        Returns:
            str: Final job status
        """
        start_time = time.time()
        elapsed_time = 0
        
        while elapsed_time < max_wait_time:
            job_info = SageMakerHelper.get_batch_prediction_status(job_name)
            status = job_info.get('Status')
            
            if status.upper() in ['COMPLETED', 'FAILED', 'STOPPED']:
                return status
                
            logger.debug(f"Job status: {status}, waiting {check_interval} seconds...")
            time.sleep(check_interval)
            elapsed_time = time.time() - start_time
        
        logger.warning(f"Job {job_name} did not complete within {max_wait_time} seconds")
        return "TIMED_OUT"
        
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
            logger.warning(f"Prediction count ({len(predictions_df)}) doesn't match input count ({len(original_df)})")
        
        # Determine the prediction column name
        if len(predictions_df.columns) == 0:
            raise Exception("Prediction file has no columns")
            
        prediction_column = predictions_df.columns[0]
        logger.debug(f"Using prediction column: {prediction_column}")
        
        # Create a copy of the original dataframe
        result_df = original_df.copy()
        
        # Add the predictions
        result_df['predicted_value'] = predictions_df[prediction_column].values
        
        # Add predicted_label column with TRUE value for all rows
        result_df['predicted_label'] = 'TRUE'
        
        return result_df
