###
# © 2025 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
# This AWS Content is provided subject to the terms of the AWS Customer Agreement
# available at http://aws.amazon.com/agreement or other written agreement between
# Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.
###

import csv
import io
import boto3
import pandas as pd
from io import StringIO
from aws_helper import AwsHelper
from utils_helper import get_logger

logger = get_logger(service="common_s3_helper", level="debug")


class S3Helper:

    @staticmethod
    def read_csv_from_s3(bucket_name, file_key, aws_region=None):
        """
        Read CSV file from S3 bucket
        """
        s3_client = AwsHelper.get_client("s3", aws_region)
        response = s3_client.get_object(Bucket=bucket_name, Key=file_key)
        csv_content = response["Body"].read().decode("utf-8")
        df = pd.read_csv(StringIO(csv_content))
        return df

    @staticmethod
    def save_csv_to_s3(df, bucket_name, file_key, aws_region=None):
        """
        Save DataFrame as CSV to S3 bucket
        """
        csv_buffer = StringIO()
        df.to_csv(csv_buffer, index=False)
        s3_client = AwsHelper.get_client("s3", aws_region)
        s3_client.put_object(
            Bucket=bucket_name, Key=file_key, Body=csv_buffer.getvalue()
        )
        logger.info(f"Successfully saved to s3://{bucket_name}/{file_key}")
