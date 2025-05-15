###
# © 2025 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
# This AWS Content is provided subject to the terms of the AWS Customer Agreement
# available at http://aws.amazon.com/agreement or other written agreement between
# Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.
###

import csv
import io
import boto3

from .aws_helper import AwsHelper
from .logging import get_logger

logger = get_logger(service="common_s3_helper", level="debug")


class S3Helper:
    @staticmethod
    def read_csv_from_s3(bucket_name, file_key, aws_region=None):
        s3 = AwsHelper.get_resource("s3", aws_region)
        csv_content = s3.Object(bucket_name, file_key)
        return csv_content

    @staticmethod
    def read_from_s3(bucket_name, s3_file_name, aws_region=None):
        s3 = AwsHelper.get_resource("s3", aws_region)
        obj = s3.Object(bucket_name, s3_file_name)
        return obj.get()["Body"].read().decode("utf-8")

    @staticmethod
    def get_s3_bucket_region(bucket_name):
        client = boto3.client("s3")
        response = client.get_bucket_location(Bucket=bucket_name)
        aws_region = response["LocationConstraint"]
        return aws_region

    @staticmethod
    def write_to_s3(content, bucket_name, s3_file_name, aws_region=None):
        s3 = AwsHelper.get_resource("s3", aws_region)
        object = s3.Object(bucket_name, s3_file_name)
        object.put(Body=content)

    @staticmethod
    def write_csv(csv_data, bucket_name, s3_file_name, upload_to_s3):
        csv_buffer = io.StringIO()
        chunk_size = 1000
        offset = 0
        record_count = 0
        # Create CSV buffer
        csv_writer = None
        # Process results in chunks
        while True:
            chunk = csv_data[offset : offset + chunk_size]
            if not chunk:
                break

            if not csv_writer:
                csv_writer = csv.DictWriter(csv_buffer, fieldnames=chunk[0].keys())
                csv_writer.writeheader()

            csv_writer.writerows(chunk)
            record_count += len(chunk)
            offset += chunk_size
            if offset >= len(csv_data):
                break
        if upload_to_s3:
            S3Helper.write_to_s3(csv_buffer.getvalue(), bucket_name, s3_file_name)
        return record_count
