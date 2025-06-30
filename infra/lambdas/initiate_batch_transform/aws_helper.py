###
# © 2025 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
# This AWS Content is provided subject to the terms of the AWS Customer Agreement
# available at http://aws.amazon.com/agreement or other written agreement between
# Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.
###

import boto3
from botocore.client import Config as ClientConfig

from utils_helper import get_env

REGION = get_env("AWS_REGION", "us-east-1")
DEFAULT_MAX_RETRY_ATTEMPTS = get_env("MAX_RETRY_ATTEMPTS", 2)
DEFAULT_CONFIG = ClientConfig(
    region_name=REGION, retries=dict(max_attempts=DEFAULT_MAX_RETRY_ATTEMPTS)
)


class AwsHelper:
    @staticmethod
    def get_session():
        return boto3.Session()

    @staticmethod
    def get_client(name, aws_region=None):
        if aws_region is not None:
            return boto3.client(name, region_name=aws_region, config=DEFAULT_CONFIG)
        else:
            return boto3.client(name, config=DEFAULT_CONFIG)

    @staticmethod
    def get_resource(name, aws_region=None):
        if aws_region:
            return boto3.resource(name, region_name=aws_region, config=DEFAULT_CONFIG)
        else:
            return boto3.resource(name, config=DEFAULT_CONFIG)
