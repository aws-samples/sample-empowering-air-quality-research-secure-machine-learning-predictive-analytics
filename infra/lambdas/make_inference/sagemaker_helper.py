###
# © 2025 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
# This AWS Content is provided subject to the terms of the AWS Customer Agreement
# available at http://aws.amazon.com/agreement or other written agreement between
# Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.
###

import boto3

from utils_helper import get_env, get_logger

logger = get_logger(service="sagemaker_helper", level="debug")
runtime_client = boto3.client("runtime.sagemaker")
canvas_client = boto3.client("sagemaker-canvas")
sagemaker_client = boto3.client("sagemaker")


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
    def start_batch_prediction(model_id, input_location, output_location):
        """
        Start a SageMaker Canvas batch prediction job
        
        Args:
            model_id (str): The Canvas model ID
            input_location (str): S3 location of input data (s3://bucket/prefix/file.csv)
            output_location (str): S3 location for output data (s3://bucket/prefix)
            
        Returns:
            dict: Response from create_batch_prediction_job API
        """
        response = canvas_client.create_batch_prediction_job(
            ModelId=model_id,
            InputConfig={
                "S3InputLocation": input_location,
                "ContentType": "text/csv"
            },
            OutputConfig={
                "S3OutputLocation": output_location
            },
            JobName=f"canvas-batch-{model_id.split('-')[-1]}"
        )
        return response
    
    @staticmethod
    def get_batch_prediction_status(batch_prediction_job_id):
        """
        Get the status of a SageMaker Canvas batch prediction job
        
        Args:
            batch_prediction_job_id (str): The batch prediction job ID
            
        Returns:
            str: Status of the batch prediction job
        """
        response = canvas_client.describe_batch_prediction_job(
            BatchPredictionJobId=batch_prediction_job_id
        )
        return response["Status"]
