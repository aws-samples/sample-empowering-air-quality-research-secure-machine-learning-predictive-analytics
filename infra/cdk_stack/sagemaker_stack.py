from aws_cdk import (
    NestedStack,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_s3 as s3,
    aws_sagemaker as sagemaker,
    CfnOutput,
)
from constructs import Construct
from cdk_nag import NagSuppressions

class SageMakerStack(NestedStack):

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc: ec2.IVpc,
        sagemaker_security_group: ec2.ISecurityGroup,
        source_bucket: s3.IBucket,
        config: dict,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Get the project prefix from config
        project_prefix = config.get("project_prefix", "demoapp")

        # Create SageMaker execution role
        self.sagemaker_execution_role = iam.Role(
            self,
            f"{project_prefix}SageMakerExecutionRole",
            assumed_by=iam.ServicePrincipal("sagemaker.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSageMakerFullAccess"),
                # Add Canvas-specific managed policy
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSageMakerCanvasFullAccess"),
            ],
        )

        # Add specific S3 permissions to the sagemaker execution role
        self.sagemaker_execution_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:DeleteObject",
                    "s3:ListBucket",
                    "s3:GetBucketLocation"
                ],
                resources=[
                    source_bucket.bucket_arn,
                    f"{source_bucket.bucket_arn}/*"  # Grant access to all objects in the bucket
                ]
            )   
        )

        # Create space execution role
        self.space_execution_role = iam.Role(
            self,
            f"{project_prefix}SpaceExecutionRole",
            assumed_by=iam.ServicePrincipal("sagemaker.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonSageMakerFullAccess"
                )
            ],
        )

        # # Use the passed security group
        self.sagemaker_security_group = sagemaker_security_group

        # Create SageMaker domain
        self.sagemaker_domain = sagemaker.CfnDomain(
            self,
            f"{project_prefix}SageMakerDomain",
            auth_mode="IAM",
            default_user_settings=sagemaker.CfnDomain.UserSettingsProperty(
                execution_role=self.sagemaker_execution_role.role_arn,
                security_groups=[self.sagemaker_security_group.security_group_id],
            ),
            default_space_settings=sagemaker.CfnDomain.DefaultSpaceSettingsProperty(
                execution_role=self.space_execution_role.role_arn,
                security_groups=[self.sagemaker_security_group.security_group_id],  # Add security groups to space settings too
            ),
            domain_name=f"{project_prefix}-domain",
            subnet_ids=[subnet.subnet_id for subnet in vpc.isolated_subnets],
            vpc_id=vpc.vpc_id,
            app_network_access_type="VpcOnly",
        )

        # Create sagemaker domain user profile
        self.user_profile = sagemaker.CfnUserProfile(
            self,
            f"{project_prefix}SageMakerUserProfile",
            domain_id=self.sagemaker_domain.attr_domain_id,
            user_profile_name=f"{project_prefix}-user",
            user_settings=sagemaker.CfnUserProfile.UserSettingsProperty(
                execution_role=self.sagemaker_execution_role.role_arn,
            ),
        )

        # Outputs with prefix
        CfnOutput(
            self,
            f"{project_prefix}SageMakerDomainId",
            value=self.sagemaker_domain.attr_domain_id,
            description="SageMaker Domain ID",
        )

        CfnOutput(
            self,
            f"{project_prefix}SageMakerUserProfileName",
            value=self.user_profile.user_profile_name,
            description="SageMaker User Profile Name",
        )

        CfnOutput(
            self,
            f"{project_prefix}SageMakerExecutionRoleArn",
            value=self.sagemaker_execution_role.role_arn,
            description="SageMaker Execution Role ARN",
        )

        CfnOutput(
            self,
            f"{project_prefix}SpaceExecutionRoleArn",
            value=self.space_execution_role.role_arn,
            description="Space Execution Role ARN",
        )

        # Add CDK nag suppressions for this stack
        NagSuppressions.add_resource_suppressions(
            self.sagemaker_execution_role,
            [
                {
                    "id": "AwsSolutions-IAM4",
                    "reason": "Using AWS managed policies is acceptable for this demo application",
                }
            ],
        )

        NagSuppressions.add_resource_suppressions(
            self.space_execution_role,
            [
                {
                    "id": "AwsSolutions-IAM4",
                    "reason": "Using AWS managed policies is acceptable for this demo application",
                }
            ],
        )

        # Add the suppression AFTER creating the role and its policies
        NagSuppressions.add_resource_suppressions(
            self.sagemaker_execution_role,
            suppressions=[
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "SageMaker execution role requires access to all files in the initial_dataset directory to load training data and models. Access is limited to only this specific directory path.",
                }
            ],
            apply_to_children=True  # Important to apply to the default policy resource
        )
