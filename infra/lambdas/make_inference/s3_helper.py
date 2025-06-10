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
    def save_csv_to_s3(df, bucket_name, file_key, include_header=True, aws_region=None, date_format=None):
        """
        Save DataFrame as CSV to S3 bucket
        include_header (bool): Whether to include column headers
        """
        csv_buffer = StringIO()
        df.to_csv(csv_buffer, index=False, header=include_header, date_format=date_format)
        csv_buffer.seek(0)
        s3_client = AwsHelper.get_client("s3", aws_region)
        s3_client.put_object(
            Bucket=bucket_name, Key=file_key, Body=csv_buffer.getvalue()
        )
        
        logger.info(f"Successfully saved to s3://{bucket_name}/{file_key}")

    @staticmethod
    def list_s3_files(bucket, prefix):
        """List files in an S3 bucket with the given prefix"""
        s3_client = boto3.client('s3')
        response = s3_client.list_objects_v2(
            Bucket=bucket,
            Prefix=prefix
        )
        
        files = []
        for item in response.get('Contents', []):
            files.append(item['Key'])
        
        return files