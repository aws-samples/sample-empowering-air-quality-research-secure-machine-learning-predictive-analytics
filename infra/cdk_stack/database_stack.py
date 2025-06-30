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

        # Get PostgreSQL version from config or use default
        pg_version_config = config.get("rds_aurora_pg_version", "").strip()
        if pg_version_config:
            # Map version strings to CDK version objects
            version_mapping = {
                "16.4": rds.AuroraPostgresEngineVersion.VER_16_4,
                "16.3": rds.AuroraPostgresEngineVersion.VER_16_3,
                "16.2": rds.AuroraPostgresEngineVersion.VER_16_2,
                "16.1": rds.AuroraPostgresEngineVersion.VER_16_1,
                "15.8": rds.AuroraPostgresEngineVersion.VER_15_8,
                "15.7": rds.AuroraPostgresEngineVersion.VER_15_7,
                "15.6": rds.AuroraPostgresEngineVersion.VER_15_6,
                "15.5": rds.AuroraPostgresEngineVersion.VER_15_5,
                "15.4": rds.AuroraPostgresEngineVersion.VER_15_4,
                "14.13": rds.AuroraPostgresEngineVersion.VER_14_13,
                "14.12": rds.AuroraPostgresEngineVersion.VER_14_12,
                "14.11": rds.AuroraPostgresEngineVersion.VER_14_11,
                "14.10": rds.AuroraPostgresEngineVersion.VER_14_10,
                "14.9": rds.AuroraPostgresEngineVersion.VER_14_9,
            }
            postgres_version = version_mapping.get(pg_version_config, rds.AuroraPostgresEngineVersion.VER_16_4)
            if pg_version_config not in version_mapping:
                print(f"Warning: PostgreSQL version '{pg_version_config}' not found in mapping. Using default 16.4")
        else:
            # Use default version if not specified
            postgres_version = rds.AuroraPostgresEngineVersion.VER_16_4

        # Create RDS cluster with IAM authentication enabled
        self.aurora = rds.DatabaseCluster(
            self,
            f"{project_prefix}Cluster",
            engine=rds.DatabaseClusterEngine.aurora_postgres(
                version=postgres_version
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
