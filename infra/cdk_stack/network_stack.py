from aws_cdk import (
    NestedStack,
    aws_ec2 as ec2,
    CfnOutput,
)
from constructs import Construct
from cdk_nag import NagSuppressions

class NetworkStack(NestedStack):

    def __init__(
        self, scope: Construct, construct_id: str, config: dict, **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Get the project prefix from config
        project_prefix = config.get("project_prefix", "demoapp")

        # Create VPC with custom CIDR
        self.vpc = ec2.Vpc(
            self,
            f"{project_prefix}CustomVPC",
            ip_addresses=ec2.IpAddresses.cidr("10.0.0.0/16"),
            max_azs=2,  # Using 2 Availability Zones for high availability
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Private1",
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    cidr_mask=24,
                ),
                ec2.SubnetConfiguration(
                    name="Private2",
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    cidr_mask=24,
                ),
            ],
            nat_gateways=0,  # Explicitly set to 0 to ensure no NAT Gateways are created
            enable_dns_hostnames=True,
            enable_dns_support=True,
        )

        # Add S3 VPC Gateway Endpoint
        self.s3_endpoint = self.vpc.add_gateway_endpoint(
            "S3Endpoint",
            service=ec2.GatewayVpcEndpointAwsService.S3,
            subnets=[ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED)],
        )

        # Create security groups
        self.db_security_group = ec2.SecurityGroup(
            self,
            f"{project_prefix}DatabaseSecurityGroup",
            vpc=self.vpc,
            description="Security group for RDS",
            allow_all_outbound=False,
        )

        self.lambda_sg = ec2.SecurityGroup(
            self,
            f"{project_prefix}LambdaSecurityGroup",
            vpc=self.vpc,
            description="Security group for Lambda functions",
            allow_all_outbound=True,
        )

        self.sagemaker_security_group = ec2.SecurityGroup(
            self,
            f"{project_prefix}SageMakerSecurityGroup",
            vpc=self.vpc,
            description="Security group for SageMaker",
            allow_all_outbound=True,
        )

        self.secrets_manager_sg = ec2.SecurityGroup(
            self,
            f"{project_prefix}SecretsManagerEndpointSecurityGroup",
            vpc=self.vpc,
            description="Security group for Secrets Manager VPC Endpoint",
            allow_all_outbound=False,
        )

        # Create VPC Endpoints
        self.sagemaker_api_endpoint = self.vpc.add_interface_endpoint(
            f"{project_prefix}SageMakerAPIEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.SAGEMAKER_API,
            private_dns_enabled=True,
            subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            security_groups=[self.sagemaker_security_group, self.lambda_sg],
        )

        self.sagemaker_runtime_endpoint = self.vpc.add_interface_endpoint(
            f"{project_prefix}SageMakerRuntimeEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.SAGEMAKER_RUNTIME,
            private_dns_enabled=True,
            subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            security_groups=[self.sagemaker_security_group, self.lambda_sg],
        )
      
        self.secrets_manager_endpoint = ec2.InterfaceVpcEndpoint(
            self,
            f"{project_prefix}SecretsManagerEndpoint",
            vpc=self.vpc,
            service=ec2.InterfaceVpcEndpointAwsService.SECRETS_MANAGER,
            private_dns_enabled=True,
            subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            security_groups=[self.secrets_manager_sg],
        )

        # Add SSM VPC Endpoint for Parameter Store access
        self.ssm_endpoint = self.vpc.add_interface_endpoint(
            f"{project_prefix}SSMEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.SSM,
            private_dns_enabled=True,
            subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            security_groups=[self.lambda_sg],
        )

        # Add Step Functions VPC Endpoint for task callbacks
        self.step_functions_endpoint = self.vpc.add_interface_endpoint(
            f"{project_prefix}StepFunctionsEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.STEP_FUNCTIONS,
            private_dns_enabled=True,
            subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            security_groups=[self.lambda_sg],
        )

        # Get database configuration from config
        rds_db_port = int(config.get("rds_db_port", 5432))

        # Create Security Group Rules
        self.db_security_group.add_ingress_rule(
            peer=self.lambda_sg,
            connection=ec2.Port.tcp(rds_db_port),
            description="Allow Lambda to access PostgreSQL",
        )

        self.secrets_manager_sg.add_ingress_rule(
            peer=self.lambda_sg,
            connection=ec2.Port.tcp(443),
            description="Allow HTTPS inbound from Lambda",
        )

        self.sagemaker_security_group.add_ingress_rule(
            self.lambda_sg, ec2.Port.tcp(443), "Allow HTTPS inbound from Lambda"
        )

        # Add outputs with prefix
        CfnOutput(
            self, 
            f"{project_prefix}VpcId", 
            value=self.vpc.vpc_id, 
            description="VPC ID"
        )

        # Fix: Use isolated_subnets instead of private_subnets
        CfnOutput(
            self,
            f"{project_prefix}PrivateSubnets",
            value=",".join([subnet.subnet_id for subnet in self.vpc.isolated_subnets]),
            description="Isolated Subnets",
        )

        # Add CDK nag suppressions for this stack
        NagSuppressions.add_resource_suppressions(
            self.vpc,
            [
                {
                    "id": "AwsSolutions-VPC7",
                    "reason": "VPC Flow logs are not required for this demo application",
                }
            ],
        )

        NagSuppressions.add_resource_suppressions(
            self.lambda_sg,
            [
                {
                    "id": "AwsSolutions-EC23",
                    "reason": "Security group rules are using intrinsic functions which is causing validation errors",
                }
            ],
        )

        NagSuppressions.add_resource_suppressions(
            self.sagemaker_security_group,
            [
                {
                    "id": "AwsSolutions-EC23",
                    "reason": "Security group rules are using intrinsic functions which is causing validation errors",
                }
            ],
        )

        NagSuppressions.add_resource_suppressions(
            self.secrets_manager_sg,
            [
                {
                    "id": "AwsSolutions-EC23",
                    "reason": "Security group rules are using intrinsic functions which is causing validation errors",
                }
            ],
        )
