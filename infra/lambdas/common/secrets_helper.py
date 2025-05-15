###
# © 2025 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
# This AWS Content is provided subject to the terms of the AWS Customer Agreement
# available at http://aws.amazon.com/agreement or other written agreement between
# Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.
###

import json
from botocore.exceptions import ClientError

from .aws_helper import AwsHelper
from .logging import get_logger

logger = get_logger(service="common_secrets_helper", level="debug")


class SecretsHelper:
    @staticmethod
    def get_client() -> object:
        """
        get a client for SecretsManager
        """
        return AwsHelper.get_client("secretsmanager")

    @staticmethod
    def get_secret(secret_name):
        """
        get a secret from AWS Secrets Manager
        """
        secrets_manager = SecretsHelper.get_client()
        try:
            get_secret_value_response = secrets_manager.get_secret_value(
                SecretId=secret_name
            )
        except ClientError as e:
            logger.exception(
                "An error occurred during execution", e, stack_info=True, exc_info=True
            )
            raise e
        else:
            if "SecretString" in get_secret_value_response:
                return json.loads(get_secret_value_response["SecretString"])
