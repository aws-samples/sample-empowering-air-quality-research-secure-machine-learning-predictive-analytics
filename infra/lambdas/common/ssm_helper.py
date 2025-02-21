###
# © 2025 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
# This AWS Content is provided subject to the terms of the AWS Customer Agreement
# available at http://aws.amazon.com/agreement or other written agreement between
# Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.
###

from typing import Dict, List

from .aws_helper import AwsHelper


class SsmHelper:
    @staticmethod
    def get_client() -> object:
        """
        get a client for SSM
        """
        return AwsHelper.get_client("ssm")

    @staticmethod
    def get_value(key) -> str:
        """
        get a value for given key in SSM ParameterStore
        """
        ssm = SsmHelper.get_client()
        return ssm.get_parameter(Name=key, WithDecryption=True)["Parameter"]["Value"]

    @staticmethod
    def get_values(keys: List[str]) -> Dict[str, str]:
        """
        get values for given keys in SSM ParameterStore
        """
        ssm = SsmHelper.get_client()

        parameters = ssm.get_parameters(Names=keys, WithDecryption=True)["Parameters"]
        return {param["Name"]: param["Value"] for param in parameters}

    @staticmethod
    def delete_parameter(key: str):
        """
        delete a value for given key in SSM ParameterStore
        """
        ssm = SsmHelper.get_client()
        ssm.delete_parameter(Name=key)

    @staticmethod
    def delete_values(keys: List[str]):
        """
        delete values for given keys in SSM ParameterStore
        """
        ssm = SsmHelper.get_client()
        ssm.delete_parameters(Names=keys)

    @staticmethod
    def update_parameter(key: str, value: str):
        """
        set a value for given name and value  in SSM ParameterStore
        """
        ssm = SsmHelper.get_client()
        ssm.put_parameter(Name=key, Value=value, Type="String", Overwrite=True)
