###
# © 2025 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
# This AWS Content is provided subject to the terms of the AWS Customer Agreement
# available at http://aws.amazon.com/agreement or other written agreement between
# Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.
###

import os


def get_env(key, default=None, required=False):
    value = os.getenv(key, default)
    if required and value is None:
        raise RuntimeError(f"Environment variable '{key}' is required!")
    return value
