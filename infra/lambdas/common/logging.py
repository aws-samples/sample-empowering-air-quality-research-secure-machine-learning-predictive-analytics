###
# © 2025 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
# This AWS Content is provided subject to the terms of the AWS Customer Agreement
# available at http://aws.amazon.com/agreement or other written agreement between
# Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.
###

from aws_lambda_powertools import Logger, Tracer

DEFAULT_SERVICE_NAME = "demoapp"
DEFAULT_LOGGING_LEVEL = "DEBUG"


def get_logger(
    service: str = DEFAULT_SERVICE_NAME, level: str = DEFAULT_LOGGING_LEVEL, child=False
):
    return Logger(service, level, child)


def get_tracer(service: str = DEFAULT_SERVICE_NAME):
    return Tracer(service)
