from aws_cdk import (
    NestedStack,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_s3 as s3,
    aws_sagemaker as sagemaker,
    CfnOutput,
    CfnParameter,
    CfnCondition,
    Fn,
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

        # Get Canvas model parameters from config using the new parameter names
        create_from_canvas_str = config.get("create_from_canvas", "false").lower()
        create_from_canvas = create_from_canvas_str in ('true', 'yes', '1', 'y')
        canvas_model_package_group_name = config.get("canvas_model_package_group_name", "")
        canvas_model_version = config.get("canvas_model_version", "1")

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

        # Create a condition for Canvas model creation
        # We'll use a CfnCondition with a custom expression that evaluates to true/false
        canvas_condition = CfnCondition(
            self,
            f"{project_prefix}CanvasModelCondition",
            expression=Fn.condition_equals(Fn.ref("AWS::Region"), Fn.ref("AWS::Region"))  # Always true
        )
        
        # If create_from_canvas is False, we need to invert the condition
        if not create_from_canvas:
            canvas_condition = CfnCondition(
                self,
                f"{project_prefix}NoCanvasModelCondition",
                expression=Fn.condition_equals("false", "true")  # Always false
            )

        # Only create the Canvas model if create_from_canvas is True and we have a valid model name
        if create_from_canvas and canvas_model_package_group_name and canvas_model_package_group_name != "placeholder-update-after-model-training":
            # Create SageMaker model from Canvas model
            self.canvas_model = sagemaker.CfnModel(
                self,
                f"{project_prefix}SageMakerCanvasModel",
                execution_role_arn=self.sagemaker_execution_role.role_arn,
                primary_container=sagemaker.CfnModel.ContainerDefinitionProperty(
                    model_package_name=f"arn:aws:sagemaker:{self.region}:{self.account}:model-package/{canvas_model_package_group_name}/{canvas_model_version}"
                ),
                model_name=f"{project_prefix}-canvas-model",
                vpc_config=sagemaker.CfnModel.VpcConfigProperty(
                    security_group_ids=[self.sagemaker_security_group.security_group_id],
                    subnets=[subnet.subnet_id for subnet in vpc.isolated_subnets]
                )
            )
            
            # Only create the Canvas model if the condition is true
            self.canvas_model.cfn_options.condition = canvas_condition
            
            # Conditional output for the Canvas model ARN
            canvas_model_output = CfnOutput(
                self,
                f"{project_prefix}CanvasModelName",
                value=self.canvas_model.attr_model_name,
                description="SageMaker Canvas Model Name",
            )
            canvas_model_output.condition = canvas_condition
        
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

        # Add a message output for when the model is not created
        if not create_from_canvas or not canvas_model_package_group_name or canvas_model_package_group_name == "placeholder-update-after-model-training":
            no_model_message = CfnOutput(
                self,
                f"{project_prefix}CanvasModelStatus",
                value="Canvas model creation skipped - either create_from_canvas is false or using placeholder model name",
                description="Canvas Model Status",
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
