from aws_cdk import (
    NestedStack,
    aws_ec2 as ec2,
    aws_rds as rds,
    RemovalPolicy,
    Duration,
    CfnOutput,
)
from constructs import Construct
from cdk_nag import NagSuppressions

class DatabaseStack(NestedStack):

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc: ec2.IVpc,
        db_security_group: ec2.ISecurityGroup,
        config: dict,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Get database configuration from config
        rds_db_port = int(config.get("rds_db_port", 5432))
        # Get the project prefix from config
        project_prefix = config.get("project_prefix", "demoapp")

        # Create RDS cluster with IAM authentication enabled
        self.aurora = rds.DatabaseCluster(
            self,
            f"{project_prefix}Cluster",
            engine=rds.DatabaseClusterEngine.aurora_postgres(
                version=rds.AuroraPostgresEngineVersion.VER_16_4
            ),
            cluster_identifier=f"{project_prefix}-cluster",
            instances=2,
            instance_props=rds.InstanceProps(
                instance_type=ec2.InstanceType.of(
                    ec2.InstanceClass.T4G, ec2.InstanceSize.MEDIUM
                ),
                vpc_subnets=ec2.SubnetSelection(
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
                ),
                vpc=vpc,
            ),
            security_groups=[db_security_group],
            removal_policy=RemovalPolicy.DESTROY,
            backup=rds.BackupProps(
                retention=Duration.days(7),
                preferred_window="03:00-04:00",  # Adjust this time window as needed
            ),
            credentials=rds.Credentials.from_generated_secret(
                config.get("rds_db_username")
            ),
            default_database_name=config.get("rds_db_name"),
            port=rds_db_port,
            deletion_protection=False, # Set this to True for production workloads
            storage_encrypted=True,
            storage_encryption_key=None,  # This will use the default AWS managed key
            iam_authentication=True,  # Enable IAM authentication
        )

        # Output important information with prefix
        CfnOutput(
            self,
            f"{project_prefix}DatabaseEndpoint",
            value=self.aurora.cluster_endpoint.hostname,
            description="Database endpoint",
        )

        CfnOutput(
            self,
            f"{project_prefix}DatabasePort",
            value=str(self.aurora.cluster_endpoint.port),
            description="Database port",
        )

        # Add CDK nag suppressions for this stack
        NagSuppressions.add_resource_suppressions_by_path(
            self,
            f"/{self.node.path}/{project_prefix}Cluster/Secret/Resource",
            [
                {
                    "id": "AwsSolutions-SMG4",
                    "reason": "Secret rotation is not required for this demo application",
                }
            ],
        )
        
        # Add suppression for RDS deletion protection warning
        NagSuppressions.add_resource_suppressions(
            self.aurora,
            [
                {
                    "id": "AwsSolutions-RDS10",
                    "reason": "Deletion protection is disabled for this demo application to allow easy cleanup",
                }
            ],
        )
