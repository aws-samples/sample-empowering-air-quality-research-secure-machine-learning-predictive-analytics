from aws_cdk import (
    NestedStack,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
    RemovalPolicy,
    Duration,
    CfnOutput,
)
from constructs import Construct
from cdk_nag import NagSuppressions
import os

class StorageStack(NestedStack):

    def __init__(
        self, scope: Construct, construct_id: str, config: dict, **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Get the project prefix from config
        project_prefix = config.get("project_prefix", "demoapp")

        # Create Standard Output S3 bucket
        self.source_bucket = s3.Bucket(
            self,
            f"{project_prefix}DatasetsStore",
            removal_policy=RemovalPolicy.DESTROY,  # Change to RETAIN for production
            auto_delete_objects=True,  # Set to False for production
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            public_read_access=False,
            lifecycle_rules=[
                s3.LifecycleRule(
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.GLACIER,
                            transition_after=Duration.days(90),
                        )
                    ],
                    expiration=Duration.days(365),
                )
            ],
            # Add CORS configuration for SageMaker Canvas
            cors=[
                s3.CorsRule(
                    allowed_headers=["*"],
                    allowed_methods=[
                        s3.HttpMethods.POST,
                        s3.HttpMethods.PUT,
                        s3.HttpMethods.GET,
                        s3.HttpMethods.HEAD,
                        s3.HttpMethods.DELETE
                    ],
                    allowed_origins=["agemaker.aws"],
                    exposed_headers=[
                        "ETag",
                        "x-amz-delete-marker",
                        "x-amz-id-2",
                        "x-amz-request-id",
                        "x-amz-server-side-encryption",
                        "x-amz-version-id"
                    ]
                )
            ]
        )

        # Create initial_dataset prefix explicitly
        self.initial_dataset_prefix = "initial_dataset"

        # Get the initial data file name and path from config
        initial_data_file = config.get("initial_data_file", "")
        initial_data_path = config.get("initial_data_path", "data")  # Default to "data" if not specified
        
        # Construct the full path to the data directory
        data_dir = os.path.join(os.path.dirname(__file__), "..", initial_data_path)
        
        # Deploy the initial data file to S3
        file_deployment = s3deploy.BucketDeployment(
            self,
            f"{project_prefix}InitialDataFileDeployment",
            sources=[s3deploy.Source.asset(data_dir, exclude=["*", f"!{initial_data_file}"])],
            destination_bucket=self.source_bucket,
            destination_key_prefix=self.initial_dataset_prefix,
            retain_on_delete=False,
        )
                 
        # Add bucket output with prefix
        CfnOutput(
            self,
            f"{project_prefix}OutputBucketName",
            value=self.source_bucket.bucket_name,
            description="Output S3 Bucket",
        )

        # Add initial dataset prefix output with prefix
        CfnOutput(
            self,
            f"{project_prefix}InitialDatasetPrefix",
            value=self.initial_dataset_prefix,
            description="Initial Dataset Prefix in S3",
        )

        # Add CDK nag suppressions for this stack
        NagSuppressions.add_resource_suppressions(
            self.source_bucket,
            [
                {
                    "id": "AwsSolutions-S1",
                    "reason": "S3 server access logs are not required for this demo application",
                }
            ],
        )

        # Add suppressions for the BucketDeployment construct
        # This needs to be applied at the stack level to catch all generated resources
        NagSuppressions.add_stack_suppressions(
            self,
            [
                {
                    "id": "AwsSolutions-IAM4",
                    "reason": "BucketDeployment uses AWS managed policies by design for Lambda execution",
                    "applies_to": ["Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"]
                },
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "BucketDeployment requires S3 permissions with wildcards to copy files",
                    "applies_to": [
                        "Action::s3:GetBucket*",
                        "Action::s3:GetObject*",
                        "Action::s3:List*",
                        "Action::s3:Abort*",
                        "Action::s3:DeleteObject*",
                        "Resource::arn:aws:s3:::cdk-*/*",
                        "Resource::*/*"
                    ]
                },
                {
                    "id": "AwsSolutions-L1",
                    "reason": "BucketDeployment Lambda runtime is managed by CDK",
                }
            ]
        )
