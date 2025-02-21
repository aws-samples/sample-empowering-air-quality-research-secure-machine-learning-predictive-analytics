###
# © 2025 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
# This AWS Content is provided subject to the terms of the AWS Customer Agreement
# available at http://aws.amazon.com/agreement or other written agreement between
# Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.
###

from dataclasses import fields


def from_dict(class_name, dict: dict):
    set = {f.name for f in fields(class_name) if f.init}
    filtered = {k: v for k, v in dict.items() if k in set}
    return class_name(**filtered)
