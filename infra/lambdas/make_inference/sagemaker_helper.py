###
# © 2025 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
# This AWS Content is provided subject to the terms of the AWS Customer Agreement
# available at http://aws.amazon.com/agreement or other written agreement between
# Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.
###

import boto3

from utils_helper import get_logger

logger = get_logger(service="rds_helper", level="debug")
client = boto3.client("runtime.sagemaker")


class SageMakerHelper:

    @staticmethod
    def get_inference(body, endpoint_name):
        response = client.invoke_endpoint(
            EndpointName=endpoint_name,
            ContentType="text/csv",
            Body=body,
            Accept="application/json",
        )
        return response
