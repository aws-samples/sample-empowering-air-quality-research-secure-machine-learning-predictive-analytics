###
# © 2025 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
# This AWS Content is provided subject to the terms of the AWS Customer Agreement
# available at http://aws.amazon.com/agreement or other written agreement between
# Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.
###

from datetime import datetime, timezone
from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_rds as rds,
    aws_iam as iam,
    aws_s3 as s3,
    aws_secretsmanager as secretsmanager,
    aws_lambda as _lambda,
    CfnOutput,
    RemovalPolicy,
    Duration,
    CustomResource,
    custom_resources as cr,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as sfn_tasks,
    aws_scheduler as scheduler,
)
from constructs import Construct
import json
from .config_reader import ConfigReader


class AirQualityStack(Stack):

    # Step function construct
    def create_state_machine(
        self,
        query_function,
        make_inference_function,
        write_results_function,
        state_machine_role,
    ):

        # Create Lambda task for query function
        query_task = sfn_tasks.LambdaInvoke(
            self,
            "Query Function",
            lambda_function=query_function,
            payload=sfn.TaskInput.from_json_path_at("$"),
            retry_on_service_exceptions=True,
        )

        # Create Lambda task for inference
        inference_task = sfn_tasks.LambdaInvoke(
            self,
            "Inference Lambda function",
            lambda_function=make_inference_function,
            payload=sfn.TaskInput.from_json_path_at("$"),
            retry_on_service_exceptions=True,
        )

        # Create Lambda task for writing to DB
        write_db_task = sfn_tasks.LambdaInvoke(
            self,
            "Write Data in DB",
            lambda_function=write_results_function,
            payload=sfn.TaskInput.from_json_path_at("$"),
            retry_on_service_exceptions=True,
        )

        # Create Success states
        success_state = sfn.Succeed(self, "No Records Found")
        success_state_1 = sfn.Succeed(self, "Inference Completed Without Data")

        definition = query_task.next(
            sfn.Choice(self, "IsRecordsAvailable")
            .when(
                sfn.Condition.number_greater_than("$.Payload.statusCode", 200),
                success_state,
            )
            .otherwise(
                inference_task.next(
                    sfn.Choice(self, "HasInferenceCompleted")
                    .when(
                        sfn.Condition.number_greater_than("$.Payload.statusCode", 200),
                        success_state_1,
                    )
                    .otherwise(write_db_task)
                )
            )
        )

        # Create the state machine
        state_machine = sfn.StateMachine(
            self,
            "AirQualityStateMachine",
            definition=definition,
            role=state_machine_role,
            tracing_enabled=True,
        )

        return state_machine

    # Lambda function construct
    def create_lambda_function(
        self,
        name,
        lambda_folder,
        vpc,
        security_groups,
        database_secret,
        source_bucket,
        layers,
        environment_variables,
        memory_size=None,
        timeout=None,
        python_version=None,
        allow_s3_read=False,
        allow_s3_write=False,
        allow_secret_read=False,
        allow_sagemaker_inference=False,
    ):
        """
        Creates and returns the Lambda function with necessary configurations
        """
        lambda_function = _lambda.Function(
            self,
            f"{name}Function",
            runtime=(
                _lambda.Runtime.PYTHON_3_10
                if python_version is None
                else python_version
            ),
            handler="index.lambda_handler",
            code=_lambda.Code.from_asset(f"lambdas/{lambda_folder}"),
            vpc=vpc,
            memory_size=256 if memory_size is None else memory_size,
            security_groups=security_groups,
            timeout=Duration.minutes(1) if timeout is None else timeout,
            layers=layers,
            environment=environment_variables,
            allow_public_subnet=True,
        )

        # Grant necessary permissions to Lambda
        lambda_function.role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "service-role/AWSLambdaVPCAccessExecutionRole"
            )
        )

        if allow_s3_read:
            source_bucket.grant_read(lambda_function)
        if allow_s3_write:
            source_bucket.grant_write(lambda_function)
        if allow_secret_read:
            database_secret.grant_read(lambda_function)
        if allow_sagemaker_inference:
            lambda_function.role.add_to_policy(
                iam.PolicyStatement(
                    actions=[
                        "sagemaker:InvokeEndpoint",
                        "sagemaker:ListEndpoints",
                        "sagemaker:DescribeEndpoint",
                    ],
                    resources=[
                        f"arn:aws:sagemaker:{self.region}:{self.account}:endpoint/canvas-AQDeployment"
                    ],
                )
            )
        return lambda_function

    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        config_reader = ConfigReader()
        config = config_reader.get_stack_config()
        environment = config.get("environment")
        project = config.get("project")
        company = config.get("company")
        secret_name = f"{project}-{config.get('rds_config_secret_name')}-{environment}"

        common_tags = {
            "Environment": environment,
            "Project": project,
            "Company": company,
            "ManagedBy": "CDK",
            "auto-delete": "no",
        }
        # cast rds db port into integer
        rds_db_port = int(config.get("rds_db_port", 5432))

        for key, value in common_tags.items():
            self.tags.set_tag(key, value)

        # Createing VPC with custom CIDR
        vpc = ec2.Vpc(
            self,
            "CustomVPC",
            ip_addresses=ec2.IpAddresses.cidr("10.0.0.0/16"),
            max_azs=2,  # Using 2 Availability Zones for high availability
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public", subnet_type=ec2.SubnetType.PUBLIC, cidr_mask=24
                ),
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24,
                ),
                ec2.SubnetConfiguration(
                    name="Isolated",
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    cidr_mask=24,
                ),
            ],
            nat_gateways=1,  # Adding a NAT Gateway for private subnets
            enable_dns_hostnames=True,
            enable_dns_support=True,
        )

        # Create VPC Endpoints for Session Manager
        ec2.InterfaceVpcEndpoint(
            self,
            "SSMEndpoint",
            vpc=vpc,
            service=ec2.InterfaceVpcEndpointAwsService.SSM,
            private_dns_enabled=True,
        )

        ec2.InterfaceVpcEndpoint(
            self,
            "SSMMessagesEndpoint",
            vpc=vpc,
            service=ec2.InterfaceVpcEndpointAwsService.SSM_MESSAGES,
            private_dns_enabled=True,
        )

        ec2.InterfaceVpcEndpoint(
            self,
            "EC2MessagesEndpoint",
            vpc=vpc,
            service=ec2.InterfaceVpcEndpointAwsService.EC2_MESSAGES,
            private_dns_enabled=True,
        )

        # Create Security Group for RDS
        db_security_group = ec2.SecurityGroup(
            self,
            "DatabaseSecurityGroup",
            vpc=vpc,
            description="Security group for Aurora PostgreSQL",
            allow_all_outbound=True,
        )

        # Create Security Group for EC2 Bastion
        bastion_security_group = ec2.SecurityGroup(
            self,
            "BastionSecurityGroup",
            vpc=vpc,
            description="Security group for Bastion Host",
            allow_all_outbound=True,
        )

        # Allow the bastion to connect to RDS
        db_security_group.add_ingress_rule(
            peer=bastion_security_group,
            connection=ec2.Port.tcp(rds_db_port),
            description="Allow PostgreSQL access from Bastion",
        )
        # Optional Create the Bastion EC2 Instance
        # if config.get("create_bastion_instance", "N").lower() == "y":
        #     # Create EC2 Instance Role
        #     bastion_role = iam.Role(
        #         self,
        #         "BastionRole",
        #         assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
        #     )

        #     # Add SSM policy to allow Session Manager access
        #     bastion_role.add_managed_policy(
        #         iam.ManagedPolicy.from_aws_managed_policy_name(
        #             "AmazonSSMManagedInstanceCore"
        #         )
        #     )

        #     bastion_host = ec2.Instance(
        #         self,
        #         "BastionHost",
        #         vpc=vpc,
        #         vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
        #         instance_type=ec2.InstanceType.of(
        #             ec2.InstanceClass.T3, ec2.InstanceSize.MICRO
        #         ),
        #         machine_image=ec2.AmazonLinuxImage(
        #             generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2
        #         ),
        #         security_group=bastion_security_group,
        #         role=bastion_role,
        #         disable_api_termination=False,
        #     )

        #     # Add output for Bastion Instance ID
        #     CfnOutput(
        #         self,
        #         "BastionInstanceId",
        #         value=bastion_host.instance_id,
        #         description="Bastion Host Instance ID for SSM Session Manager",
        #     )

        # Allow inbound from VPC CIDR to PostgreSQL port
        db_security_group.add_ingress_rule(
            peer=ec2.Peer.ipv4(vpc.vpc_cidr_block),
            connection=ec2.Port.tcp(rds_db_port),
            description="Allow PostgreSQL access from VPC",
        )

        # Create a secret for database credentials
        database_secret = secretsmanager.Secret(
            self,
            "DatabaseSecret",
            secret_name=secret_name,
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template=json.dumps(
                    {"username": config.get("rds_db_username")}
                ),
                generate_string_key="password",
                exclude_punctuation=True,
                include_space=False,
                password_length=16,
            ),
        )

        # TODO: if rds_db_host is provided then find the rds db instance and create the object
        if config.get("rds_db_host"):
            rds_db_host = config.get("rds_db_host")
            aurora = rds.DatabaseInstance.from_database_instance_attributes(
                self,
                "RDSInstance",
                instance_endpoint_address=rds_db_host,
                instance_identifier=config.get("rds_db_instance_id"),
                port=rds_db_port,
                security_groups=[db_security_group],
            )
        else:
            # aurora = rds.DatabaseInstance(
            #     self,
            #     "AuroraPostgres",
            #     engine=rds.DatabaseInstanceEngine.postgres(
            #         version=rds.PostgresEngineVersion.VER_14
            #     ),
            #     instance_type=ec2.InstanceType.of(
            #         ec2.InstanceClass.T4G, ec2.InstanceSize.MICRO
            #     ),
            #     vpc=vpc,
            #     vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            #     security_groups=[db_security_group],
            #     removal_policy=RemovalPolicy.RETAIN,
            #     delete_automated_backups=False,
            #     credentials=rds.Credentials.from_secret(database_secret),
            #     database_name=config.get("rds_db_name"),
            #     port=rds_db_port,
            #     deletion_protection=True,
            #     multi_az=True,
            # )

            aurora = rds.DatabaseCluster(
                self,
                "AuroraPostgresCluster",
                engine=rds.DatabaseClusterEngine.aurora_postgres(
                    version=rds.AuroraPostgresEngineVersion.VER_16_4
                ),
                cluster_identifier=f"{config.get('project_name')}-aurora-cluster",
                instances=2,
                instance_props=rds.InstanceProps(
                    instance_type=ec2.InstanceType.of(
                        ec2.InstanceClass.T4G, ec2.InstanceSize.MEDIUM
                    ),
                    vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
                    vpc=vpc,
                ),
                # vpc=vpc,
                security_groups=[db_security_group],
                removal_policy=RemovalPolicy.RETAIN,
                backup=rds.BackupProps(
                    retention=Duration.days(7),
                    preferred_window="03:00-04:00"  # Adjust this time window as needed
                ),
                credentials=rds.Credentials.from_secret(database_secret),
                default_database_name=config.get("rds_db_name"),
                port=rds_db_port,
                deletion_protection=True,
                storage_encrypted=True,
                storage_encryption_key=None,  # This will use the default AWS managed key
            )
        
        # cluster_endpoint = aurora.cluster_endpoint.hostname

        # Create IAM Role for Session Manager Access
        session_manager_role = iam.Role(
            self,
            "SessionManagerRole",
            assumed_by=iam.ServicePrincipal("ssm.amazonaws.com"),
        )

        # Add required policies for Session Manager
        session_manager_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "AmazonSSMManagedInstanceCore"
            )
        )

        # Add custom policy for port forwarding
        session_manager_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "ssm:StartSession",
                    "ssm:TerminateSession",
                    "ssm:ResumeSession",
                ],
                resources=["*"],
            )
        )

        # Create Standard Output S3 bucket
        source_bucket = s3.Bucket(
            self,
            "OutputBucket",
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
        )

        # Create Lambda Security Group
        lambda_sg = ec2.SecurityGroup(
            self,
            "LambdaSecurityGroup",
            vpc=vpc,
            description="Security group for Lambda function",
            allow_all_outbound=True,
        )

        # Allow Lambda to access RDS
        aurora.connections.allow_default_port_from(lambda_sg)

        # Allow Lambda to access RDS
        db_security_group.add_ingress_rule(
            peer=lambda_sg,
            connection=ec2.Port.tcp(rds_db_port),
            description="Allow Lambda to access PostgreSQL",
        )

        secrets_manager_endpoint = ec2.InterfaceVpcEndpoint(
            self,
            "SecretsManagerEndpoint",
            vpc=vpc,
            service=ec2.InterfaceVpcEndpointAwsService.SECRETS_MANAGER,
            private_dns_enabled=True,
            subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PUBLIC  # Match your Lambda subnet type
            ),
            security_groups=[
                lambda_sg
            ],  # Allow Lambda security group to access the endpoint
        )

        # Create S3 Gateway Endpoint
        s3_endpoint = ec2.GatewayVpcEndpoint(
            self, "S3Endpoint", vpc=vpc, service=ec2.GatewayVpcEndpointAwsService.S3
        )

        # Modify Lambda security group to allow HTTPS outbound to the VPC endpoint
        lambda_sg.add_egress_rule(
            peer=ec2.Peer.ipv4(vpc.vpc_cidr_block),
            connection=ec2.Port.tcp(443),
            description="Allow HTTPS outbound to Secrets Manager VPC Endpoint",
        )

        common_shared_layer_zip_path = "../lambda_layer/common/common_layer.zip"
        python_version = _lambda.Runtime.PYTHON_3_10

        common_shared_layer = _lambda.LayerVersion(
            self,
            "sensorafrica_common",
            code=_lambda.Code.from_asset(common_shared_layer_zip_path),
            compatible_runtimes=[python_version],
        )

        pandas_layer_arn = (
            f"arn:aws:lambda:{self.region}:336392948345:layer:AWSSDKPandas-Python310:23"
        )
        pandas_layer = _lambda.LayerVersion.from_layer_version_arn(
            self, "pandas_layer", pandas_layer_arn
        )

        lambda_power_tool_layer_arn = f"arn:aws:lambda:{self.region}:017000801446:layer:AWSLambdaPowertoolsPythonV2:78"
        lambda_power_tool_layer = _lambda.LayerVersion.from_layer_version_arn(
            self, "lambda_power_tool_layer", lambda_power_tool_layer_arn
        )

        vpc.add_interface_endpoint(
            "SageMakerAPIEndpoint",
            service=ec2.InterfaceVpcEndpointService(
                f"com.amazonaws.{self.region}.sagemaker.api"
            ),
            private_dns_enabled=True,
            subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PUBLIC  # Match your Lambda subnet type
            ),
            security_groups=[
                lambda_sg
            ],  # Allow Lambda security group to access the endpoint
        )

        vpc.add_interface_endpoint(
            "SageMakerRuntimeEndpoint",
            service=ec2.InterfaceVpcEndpointService(
                f"com.amazonaws.{self.region}.sagemaker.runtime"
            ),
            private_dns_enabled=True,
            subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PUBLIC  # Match your Lambda subnet type
            ),
            security_groups=[
                lambda_sg
            ],  # Allow Lambda security group to access the endpoint
        )

        # Create Lambda function
        common_env_variables = {
            "DB_HOST": aurora.cluster_endpoint.hostname,
            "DB_PORT": config.get("rds_db_port"),
            "DB_NAME": config.get("rds_db_name"),
            "DB_USERNAME": config.get("rds_db_username"),
            "DB_TABLE": config.get("rds_db_table"),
            "SOURCE_BUCKET": source_bucket.bucket_name,
            "SECRET_NAME": database_secret.secret_name,
        }

        # Step0: Optional Lambda function to Initial DB Dump
        if config.get("create_db_init_lambda").lower() == "y":
            db_init_function_env_variables = {
                "LOG_LEVEL": config.get("lambda_logs_level").upper(),
                "DB_DUMP_PREFIX": config.get("db_dump_prefix"),
                "DB_DUMP_FILE": config.get("db_dump_s3_key"),
                "SERVICE_NAME": "air_quality_db_init_lambda",
                "PROCESS_LOCAL": "true",
            }
            db_init_function_env_variables.update(common_env_variables)
            db_init_lambda_function = self.create_lambda_function(
                name="DBInitialization",
                lambda_folder="db_init",
                vpc=vpc,
                security_groups=[lambda_sg],
                database_secret=database_secret,
                source_bucket=source_bucket,
                layers=[common_shared_layer],
                environment_variables=db_init_function_env_variables,
                timeout=Duration.minutes(2),
                memory_size=256,
                python_version=_lambda.Runtime.PYTHON_3_10,
                allow_s3_read=True,
                allow_s3_write=False,
                allow_secret_read=True,
                allow_sagemaker_inference=False,
            )
            if config.get("run_db_init_on_deployment").lower() == "y":
                provider = cr.Provider(
                    self,
                    "DBInitializationProvider",
                    on_event_handler=db_init_lambda_function,
                )

                CustomResource(
                    self,
                    "DBInitializationResource",
                    service_token=provider.service_token,
                    properties={
                        "timestamp": datetime.now(
                            timezone.utc
                        ).isoformat()  # Force update on each deployment
                    },
                )

        # Step1: First Lambda function to Query DB
        query_function_env_variables = {
            "LOG_LEVEL": config.get("lambda_logs_level").upper(),
            "SERVICE_NAME": "air_quality_query_lambda",
            "RETRIEVAL_PREFIX": config.get("retrival_prefix"),
        }

        query_function_env_variables.update(common_env_variables)

        query_function = self.create_lambda_function(
            name="Query",
            lambda_folder="get_records_from_db",
            vpc=vpc,
            security_groups=[lambda_sg],
            database_secret=database_secret,
            source_bucket=source_bucket,
            layers=[common_shared_layer],
            environment_variables=query_function_env_variables,
            timeout=Duration.seconds(30),
            memory_size=256,
            python_version=_lambda.Runtime.PYTHON_3_10,
            allow_s3_read=True,
            allow_s3_write=True,
            allow_secret_read=True,
            allow_sagemaker_inference=False,
        )

        # Step2: Second Lambda function to Predict
        predict_function_env_variables = {
            "LOG_LEVEL": config.get("lambda_logs_level").upper(),
            "SERVICE_NAME": "air_quality_make_inference_lambda",
            "PREDICTED_PREFIX": config.get("predicted_prefix"),
            "CANVAS_MODEL_ENDPOINT_NAME": config.get("canvas_model_endpoint_name"),
        }
        predict_function_env_variables.update(common_env_variables)
        make_inference_lambda = self.create_lambda_function(
            name="MakeInference",
            lambda_folder="make_inference",
            vpc=vpc,
            security_groups=[lambda_sg],
            database_secret=database_secret,
            source_bucket=source_bucket,
            layers=[lambda_power_tool_layer, pandas_layer],
            environment_variables=predict_function_env_variables,
            timeout=Duration.minutes(1),
            memory_size=512,
            python_version=_lambda.Runtime.PYTHON_3_10,
            allow_s3_read=True,
            allow_s3_write=True,
            allow_secret_read=False,
            allow_sagemaker_inference=True,
        )

        # Step3: Lambda function to read data from inference s3 and Update DB
        writer_function_env_variables = {
            "LOG_LEVEL": config.get("lambda_logs_level").upper(),
            "SERVICE_NAME": "air_quality_writer_lambda",
            "RETRIEVAL_PREFIX": config.get("retrival_prefix"),
        }

        writer_function_env_variables.update(common_env_variables)

        write_results_in_db_function = self.create_lambda_function(
            name="WriteResultsInDB",
            lambda_folder="write_results_in_db",
            vpc=vpc,
            security_groups=[lambda_sg],
            database_secret=database_secret,
            source_bucket=source_bucket,
            layers=[common_shared_layer],
            environment_variables=writer_function_env_variables,
            timeout=Duration.seconds(30),
            memory_size=256,
            python_version=_lambda.Runtime.PYTHON_3_10,
            allow_s3_read=True,
            allow_s3_write=True,
            allow_secret_read=True,
            allow_sagemaker_inference=False,
        )

        # Create state machin role
        state_machine_role = iam.Role(
            self,
            "AirQualityStateMachineRole",
            assumed_by=iam.ServicePrincipal("states.amazonaws.com"),
        )
        # Add permissions to the state machine role
        state_machine_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaRole")
        )

        sfn_cloudwatch_logs_delivery_policy = iam.ManagedPolicy(
            self,
            "CloudWatchLogsDeliveryFullAccessPolicy",
            managed_policy_name=f"CloudWatchLogsDeliveryFullAccess-{environment}",
            statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "logs:CreateLogDelivery",
                        "logs:GetLogDelivery",
                        "logs:UpdateLogDelivery",
                        "logs:DeleteLogDelivery",
                        "logs:ListLogDeliveries",
                        "logs:PutResourcePolicy",
                        "logs:DescribeResourcePolicies",
                        "logs:DescribeLogGroups",
                    ],
                    resources=["*"],
                )
            ],
        )

        # Attach the necessary IAM policies to the role
        state_machine_role.add_managed_policy(sfn_cloudwatch_logs_delivery_policy)

        # Add permissions for EventBridge Scheduler
        state_machine_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "scheduler:CreateSchedule",
                    "scheduler:DeleteSchedule",
                    "scheduler:GetSchedule",
                    "scheduler:UpdateSchedule",
                ],
                resources=["*"],
            )
        )

        # Add permissions to invoke Lambda functions
        state_machine_role.add_to_policy(
            iam.PolicyStatement(
                actions=["lambda:InvokeFunction"],
                resources=[
                    query_function.function_arn,
                    make_inference_lambda.function_arn,
                    write_results_in_db_function.function_arn,
                ],
            )
        )

        # Add X-Ray permissions
        state_machine_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "xray:PutTraceSegments",
                    "xray:PutTelemetryRecords",
                    "xray:GetSamplingRules",
                    "xray:GetSamplingTargets",
                ],
                resources=["*"],
            )
        )

        state_machine_role.add_to_policy(
            iam.PolicyStatement(actions=["iam:PassRole"], resources=["*"])
        )

        # Create the state machine
        state_machine = self.create_state_machine(
            query_function=query_function,
            make_inference_function=make_inference_lambda,
            write_results_function=write_results_in_db_function,
            state_machine_role=state_machine_role,
        )

        # EventBridge Scheduler role
        scheduler_role = iam.Role(
            self,
            "SchedulerRole",
            assumed_by=iam.ServicePrincipal("scheduler.amazonaws.com"),
        )
        # Add permission to invoke Step Function
        scheduler_role.add_to_policy(
            iam.PolicyStatement(
                actions=["states:StartExecution"],
                resources=[state_machine.state_machine_arn],
            )
        )

        # schedule
        schedule = scheduler.CfnSchedule(
            self,
            "DailySchedule",
            flexible_time_window=scheduler.CfnSchedule.FlexibleTimeWindowProperty(
                mode="FLEXIBLE", maximum_window_in_minutes=60
            ),
            schedule_expression="cron(0 0 * * ? *)",  # Run at midnight UTC every day
            target=scheduler.CfnSchedule.TargetProperty(
                arn=state_machine.state_machine_arn,
                role_arn=scheduler_role.role_arn,
                input=json.dumps(
                    {
                        "timestamp": "$.time",
                        "metadata": {
                            "source": "EventBridge Scheduler",
                            "environment": config.get("environment"),
                            "project": project,
                            "service": "air_quality_workflow",
                        },
                        "parameters": {
                            "duration_hours": 24,
                        },
                    }
                ),
                retry_policy=scheduler.CfnSchedule.RetryPolicyProperty(
                    maximum_retry_attempts=3,
                    maximum_event_age_in_seconds=3600,  # 1 hour
                ),
            ),
            name=f"AirQualityDailySchedule-{environment}",
            description="Triggers Air Quality processing workflow daily",
            state="ENABLED",
        )

        # Add these at the end of your stack
        CfnOutput(self, "VpcId", value=vpc.vpc_id, description="VPC ID")

        CfnOutput(
            self,
            "PublicSubnets",
            value=",".join([subnet.subnet_id for subnet in vpc.public_subnets]),
            description="Public Subnets",
        )

        CfnOutput(
            self,
            "PrivateSubnets",
            value=",".join([subnet.subnet_id for subnet in vpc.private_subnets]),
            description="Private Subnets",
        )

        CfnOutput(
            self,
            "IsolatedSubnets",
            value=",".join([subnet.subnet_id for subnet in vpc.isolated_subnets]),
            description="Isolated Subnets",
        )

        # Add output for State Machine ARN
        CfnOutput(
            self,
            "StateMachineArn",
            value=state_machine.state_machine_arn,
            description="State Machine ARN",
        )

        # Output Lambda function name
        CfnOutput(
            self,
            "ReaderLambdaFunctionName",
            value=query_function.function_name,
            description="Query Lambda function name",
        )

        CfnOutput(
            self,
            "WriterLambdaFunctionName",
            value=write_results_in_db_function.function_name,
            description="Write Inference results in DB Lambda function name",
        )

        # Add bucket output
        CfnOutput(
            self,
            "OutputBucketName",
            value=source_bucket.bucket_name,
            description="Output S3 Bucket",
        )

        # Output important information
        CfnOutput(
            self,
            "DatabaseEndpoint",
            value=aurora.cluster_endpoint.hostname,
            description="Database endpoint",
        )

        CfnOutput(
            self,
            "DatabasePort",
            value=str(aurora.cluster_endpoint.port),
            description="Database port",
        )

        CfnOutput(
            self,
            "SecretName",
            value=database_secret.secret_name,
            description="Name of the secret in Secrets Manager",
        )
