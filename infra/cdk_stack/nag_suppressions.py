from aws_cdk import Stack
from cdk_nag import NagSuppressions


def add_nag_suppressions(stack: Stack) -> None:
    NagSuppressions.add_stack_suppressions(
        stack,
        [
            {
                "id": "AwsSolutions-VPC7",
                "reason": "VPC Flow logs are not required for this demo application",
            },
            {
                "id": "AwsSolutions-EC23",
                "reason": "Security group rules are using intrinsic functions which is causing validation errors",
            },
            {
                "id": "AwsSolutions-SMG4",
                "reason": "Secret rotation is not required for this demo application",
            },
            {
                "id": "AwsSolutions-S1",
                "reason": "S3 server access logs are not required for this demo application",
            },
            {
                "id": "AwsSolutions-IAM4",
                "reason": "Using AWS managed policies is acceptable for this demo application",
            },
            {
                "id": "AwsSolutions-IAM5",
                "reason": "Wildcard permissions are required for the application functionality and are scoped to specific resources",
            },
            {
                "id": "AwsSolutions-L1",
                "reason": "Lambda runtime versions are managed through the application lifecycle",
            },
        ],
    )
