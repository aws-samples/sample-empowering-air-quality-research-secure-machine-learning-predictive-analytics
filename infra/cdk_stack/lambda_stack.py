from aws_cdk import (
    NestedStack,
    aws_ec2 as ec2,
    aws_rds as rds,
    aws_s3 as s3,
    aws_lambda as _lambda,
    aws_iam as iam,
    aws_events as events,
    aws_events_targets as events_targets,
    Duration,
    CfnOutput,
)
from constructs import Construct
from cdk_nag import NagSuppressions


class LambdaStack(NestedStack):

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc: ec2.IVpc,
        lambda_sg: ec2.ISecurityGroup,
        aurora: rds.IDatabaseCluster,
        source_bucket: s3.IBucket,
        config: dict,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        project_prefix = config.get("project_prefix", "")
        # Create the DB reader role
        self.init_role = iam.Role(
            self,
            f"{project_prefix}DBInitRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            description="IAM role for initial access to the database",
        )

        # Create the DB reader role
        self.reader_role = iam.Role(
            self,
            f"{project_prefix}DBReaderRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            description="IAM role for read-only access to the database",
        )

        # Create the DB writer role
        self.writer_role = iam.Role(
            self,
            f"{project_prefix}DBWriterRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            description="IAM role for read-write access to the database",
        )

        # Create separate roles for batch transform functions following least privilege principle
        
        # Role for InitiateBatchTransform Lambda
        self.batch_initiate_role = iam.Role(
            self,
            f"{project_prefix}BatchInitiateRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
        )

        # Role for BatchTransformCallback Lambda
        self.batch_callback_role = iam.Role(
            self,
            f"{project_prefix}BatchCallbackRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
        )

        # Add permissions to the DB reader role
        self.reader_role.add_to_policy(
            iam.PolicyStatement(
                actions=["rds-db:connect"],
                resources=[
                    f"arn:aws:rds-db:{self.region}:{self.account}:dbuser:{aurora.cluster_resource_identifier}/reader_user"
                ],
            )
        )

        # Add permissions to the DB writer role
        self.writer_role.add_to_policy(
            iam.PolicyStatement(
                actions=["rds-db:connect"],
                resources=[
                    f"arn:aws:rds-db:{self.region}:{self.account}:dbuser:{aurora.cluster_resource_identifier}/writer_user"
                ],
            )
        )

        # Add common permissions for all lambda roles
        for role in [
            self.init_role,
            self.reader_role,
            self.writer_role,
            self.batch_initiate_role,
            self.batch_callback_role,
        ]:
            role.add_managed_policy(
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaVPCAccessExecutionRole"
                )
            )

        # Add secretsmanager permissions to the DB init role
        self.init_role.add_to_policy(
            iam.PolicyStatement(
                actions=["secretsmanager:GetSecretValue"],
                resources=[aurora.secret.secret_arn],
            )
        )

        # Add specific S3 permissions to the DB init role for initial_dataset prefix
        self.init_role.add_to_policy(
            iam.PolicyStatement(
                actions=["s3:GetObject", "s3:ListBucket"],
                resources=[
                    source_bucket.bucket_arn,
                    f"{source_bucket.bucket_arn}/initial_dataset/*"
                ]
            )   
        )

        # Add specific S3 permissions to the reader role for retrieved_from_db prefix
        self.reader_role.add_to_policy(
            iam.PolicyStatement(
                actions=["s3:PutObject", "s3:PutObjectAcl"],
                resources=[
                    f"{source_bucket.bucket_arn}/retrieved_from_db/*"
                ]
            )
        )

        # Permissions for InitiateBatchTransform Lambda
        # S3 read permissions for reading input data
        self.batch_initiate_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "s3:GetObject",
                    "s3:ListBucket"
                ],
                resources=[
                    source_bucket.bucket_arn,
                    f"{source_bucket.bucket_arn}/retrieved_from_db/*"  # Read input data
                ]
            )
        )

        # S3 write permissions for writing batch input files
        self.batch_initiate_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "s3:GetObject",
                    "s3:ListBucket",
                    "s3:PutObject",
                    "s3:PutObjectAcl"
                ],
                resources=[
                    source_bucket.bucket_arn,
                    f"{source_bucket.bucket_arn}/input_batch/*"       # Write batch input
                ]
            )
        )

        # SageMaker permissions for batch transform job creation and model access
        self.batch_initiate_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "sagemaker:DescribeModel",
                    "sagemaker:InvokeEndpoint",
                    "sagemaker:CreateTransformJob",
                    "sagemaker:DescribeTransformJob",
                    "sagemaker:StopTransformJob",
                    "sagemaker:ListTags",
                    "sagemaker:AddTags"
                ],
                resources=[
                    f"arn:aws:sagemaker:{self.region}:{self.account}:model/{project_prefix}-canvas-model",
                    f"arn:aws:sagemaker:{self.region}:{self.account}:model/{project_prefix}-batch-transform-model",
                    f"arn:aws:sagemaker:{self.region}:{self.account}:transform-job/*"
                ]
            )
        )

        # Step Functions permissions for task callbacks
        self.batch_initiate_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "states:SendTaskSuccess",
                    "states:SendTaskFailure"
                ],
                resources=["*"]  # Step Functions requires wildcard for task tokens
            )
        )

        # Parameter Store permissions for storing job metadata
        self.batch_initiate_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "ssm:PutParameter"
                ],
                resources=[
                    f"arn:aws:ssm:{self.region}:{self.account}:parameter/batch-transform/*"
                ]
            )
        )

        # Permissions for BatchTransformCallback Lambda
        # S3 read permissions for reading batch results and original input
        self.batch_callback_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "s3:GetObject",
                    "s3:ListBucket"
                ],
                resources=[
                    source_bucket.bucket_arn,
                    f"{source_bucket.bucket_arn}/retrieved_from_db/*",  # Read original input data
                    f"{source_bucket.bucket_arn}/output_batch/*"          # Read batch results
                ]
            )
        )

        # S3 write permissions for writing final output
        self.batch_callback_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "s3:GetObject",
                    "s3:ListBucket",
                    "s3:PutObject",
                    "s3:PutObjectAcl"
                ],
                resources=[
                    source_bucket.bucket_arn,
                    f"{source_bucket.bucket_arn}/predicted_values_output/*" # Write final output
                ]
            )
        )

        # Step Functions permissions for task callbacks
        self.batch_callback_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "states:SendTaskSuccess",
                    "states:SendTaskFailure"
                ],
                resources=["*"]  # Step Functions requires wildcard for task tokens
            )
        )

        # Parameter Store permissions for reading and cleaning up job metadata
        self.batch_callback_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "ssm:GetParameter",
                    "ssm:DeleteParameter"
                ],
                resources=[
                    f"arn:aws:ssm:{self.region}:{self.account}:parameter/batch-transform/*"
                ]
            )
        )

        # Remove the old inference role permissions (keep the role for backward compatibility but update its usage)

        # Add specific S3 permissions to the writer role for predicted_values_output prefix
        self.writer_role.add_to_policy(
            iam.PolicyStatement(
                actions=["s3:GetObject", "s3:ListBucket"],
                resources=[
                    source_bucket.bucket_arn,
                    f"{source_bucket.bucket_arn}/predicted_values_output/*"
                ]
            )
        )

        # Output the role names and ARNs
        CfnOutput(
            self,
            f"{project_prefix}DBInitRoleName",
            value=self.init_role.role_name,
            export_name=f"{project_prefix}DBInitRoleName",
        )
        CfnOutput(
            self,
            f"{project_prefix}ReaderRoleName",
            value=self.reader_role.role_name,
            export_name=f"{project_prefix}DBReaderRoleName",
        )
        CfnOutput(
            self,
            f"{project_prefix}WriterRoleName",
            value=self.writer_role.role_name,
            export_name=f"{project_prefix}DBWriterRoleName",
        )
        CfnOutput(
            self,
            f"{project_prefix}BatchInitiateRoleName",
            value=self.batch_initiate_role.role_name,
            export_name=f"{project_prefix}BatchInitiateRoleName",
        )
        CfnOutput(
            self,
            f"{project_prefix}BatchCallbackRoleName",
            value=self.batch_callback_role.role_name,
            export_name=f"{project_prefix}BatchCallbackRoleName",
        )

        # Create Lambda layers
        common_shared_layer = self._create_dummy_layer(
            "common_shared_layer", "../lambda_layer/common/common_layer.zip"
        )
        pandas_layer = self.create_pandas_layer()
        lambda_power_tool_layer = self.create_lambda_powertools_layer()

        # Create Lambda functions
        self.db_init_lambda = self.create_lambda_function(
            "DBInitialization",
            "db_init",
            vpc,
            [lambda_sg],
            [common_shared_layer],
            self.get_db_init_env_variables(config, aurora, source_bucket),
            Duration.minutes(2),
            256,
            self.init_role,  # Use writer role for DB initialization
        )

        self.query_function = self.create_lambda_function(
            "Query",
            "get_records_from_db",
            vpc,
            [lambda_sg],
            [common_shared_layer],
            self.get_query_env_variables(config, aurora, source_bucket),
            Duration.minutes(2),
            256,
            self.reader_role,  # Use reader role for querying
        )



        self.write_results_function = self.create_lambda_function(
            "WriteResultsInDB",
            "write_results_in_db",
            vpc,
            [lambda_sg],
            [common_shared_layer],
            self.get_writer_env_variables(config, aurora, source_bucket),
            Duration.minutes(2),
            256,
            self.writer_role,  # Use writer role for writing results
        )

        # New batch transform Lambda functions with separate roles
        self.initiate_batch_transform_lambda = self.create_lambda_function(
            "InitiateBatchTransform",
            "initiate_batch_transform",
            vpc,
            [lambda_sg],
            [lambda_power_tool_layer, pandas_layer],
            self.get_batch_transform_env_variables(config, aurora, source_bucket),
            Duration.minutes(15),
            512,
            self.batch_initiate_role,  # Use dedicated batch initiate role
        )

        self.batch_transform_callback_lambda = self.create_lambda_function(
            "BatchTransformCallback",
            "batch_transform_callback",
            vpc,
            [lambda_sg],
            [lambda_power_tool_layer, pandas_layer],
            self.get_batch_callback_env_variables(config, aurora, source_bucket),
            Duration.minutes(2),
            512,
            self.batch_callback_role,  # Use dedicated batch callback role
        )

        # Create EventBridge rule to trigger callback Lambda when SageMaker batch transform jobs complete
        batch_transform_rule = events.Rule(
            self,
            f"{project_prefix}BatchTransformCompletionRule",
            event_pattern=events.EventPattern(
                source=["aws.sagemaker"],
                detail_type=["SageMaker Transform Job State Change"],
                detail={
                    "TransformJobStatus": ["Completed", "Failed", "Stopped"]
                }
            ),
            description="Triggers callback Lambda when SageMaker batch transform jobs complete"
        )

        # Add the callback Lambda as a target for the EventBridge rule
        batch_transform_rule.add_target(
            events_targets.LambdaFunction(self.batch_transform_callback_lambda)
        )

        # Grant EventBridge permission to invoke the callback Lambda
        self.batch_transform_callback_lambda.add_permission(
            f"{project_prefix}EventBridgeInvokePermission",
            principal=iam.ServicePrincipal("events.amazonaws.com"),
            action="lambda:InvokeFunction",
            source_arn=batch_transform_rule.rule_arn
        )

        # Outputs
        CfnOutput(self, f"{project_prefix}DBInitLambdaName", value=self.db_init_lambda.function_name)
        CfnOutput(self, f"{project_prefix}QueryLambdaName", value=self.query_function.function_name)

        CfnOutput(
            self, f"{project_prefix}WriterLambdaName", value=self.write_results_function.function_name
        )
        CfnOutput(
            self, f"{project_prefix}InitiateBatchTransformLambdaName", value=self.initiate_batch_transform_lambda.function_name
        )
        CfnOutput(
            self, f"{project_prefix}BatchTransformCallbackLambdaName", value=self.batch_transform_callback_lambda.function_name
        )

        # Add CDK nag suppressions for this stack
        # Suppress IAM4 for managed policies
        for role in [
            self.init_role,
            self.reader_role,
            self.writer_role,
            self.batch_initiate_role,
            self.batch_callback_role,
        ]:
            NagSuppressions.add_resource_suppressions(
                role,
                [
                    {
                        "id": "AwsSolutions-IAM4",
                        "reason": "Using AWS managed policies is acceptable for this demo application",
                    }
                ],
            )

        # Suppress IAM5 for wildcard permissions in policies
        NagSuppressions.add_resource_suppressions_by_path(
            self,
            f"/{self.node.path}/{project_prefix}DBInitRole/DefaultPolicy/Resource",
            [
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "Wildcard permissions are required for the application functionality and are scoped to specific resources",
                }
            ],
        )

        NagSuppressions.add_resource_suppressions_by_path(
            self,
            f"/{self.node.path}/{project_prefix}DBReaderRole/DefaultPolicy/Resource",
            [
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "Wildcard permissions are required for the application functionality and are scoped to specific resources",
                }
            ],
        )

        NagSuppressions.add_resource_suppressions_by_path(
            self,
            f"/{self.node.path}/{project_prefix}DBWriterRole/DefaultPolicy/Resource",
            [
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "Wildcard permissions are required for the application functionality and are scoped to specific resources",
                }
            ],
        )

        # Add NAG suppressions for the new separate batch roles
        NagSuppressions.add_resource_suppressions_by_path(
            self,
            f"/{self.node.path}/{project_prefix}BatchInitiateRole/DefaultPolicy/Resource",
            [
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "Wildcard permissions are required for Step Functions task tokens and SageMaker transform jobs. Canvas model access is restricted to 'canvas-*' pattern for security.",
                }
            ],
        )

        NagSuppressions.add_resource_suppressions_by_path(
            self,
            f"/{self.node.path}/{project_prefix}BatchCallbackRole/DefaultPolicy/Resource",
            [
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "Wildcard permissions are required for Step Functions task tokens",
                }
            ],
        )

        # Suppress L1 for Lambda runtime versions
        NagSuppressions.add_resource_suppressions(
            self.db_init_lambda,
            [
                {
                    "id": "AwsSolutions-L1",
                    "reason": "Lambda runtime versions are managed through the application lifecycle",
                }
            ],
        )

        NagSuppressions.add_resource_suppressions(
            self.query_function,
            [
                {
                    "id": "AwsSolutions-L1",
                    "reason": "Lambda runtime versions are managed through the application lifecycle",
                }
            ],
        )

        NagSuppressions.add_resource_suppressions(
            self.write_results_function,
            [
                {
                    "id": "AwsSolutions-L1",
                    "reason": "Lambda runtime versions are managed through the application lifecycle",
                }
            ],
        )

        NagSuppressions.add_resource_suppressions(
            self.initiate_batch_transform_lambda,
            [
                {
                    "id": "AwsSolutions-L1",
                    "reason": "Lambda runtime versions are managed through the application lifecycle",
                }
            ],
        )

        NagSuppressions.add_resource_suppressions(
            self.batch_transform_callback_lambda,
            [
                {
                    "id": "AwsSolutions-L1",
                    "reason": "Lambda runtime versions are managed through the application lifecycle",
                }
            ],
        )

    def create_lambda_function(
        self,
        name,
        folder,
        vpc,
        security_groups,
        layers,
        env_vars,
        timeout,
        memory_size,
        role,
    ):
        return _lambda.Function(
            self,
            f"{name}Function",
            runtime=_lambda.Runtime.PYTHON_3_10,
            handler="index.lambda_handler",
            code=_lambda.Code.from_asset(f"lambdas/{folder}"),
            vpc=vpc,
            security_groups=security_groups,
            timeout=timeout,
            memory_size=memory_size,
            layers=layers,
            environment=env_vars,
            role=role,
        )

    def _create_dummy_layer(self, id, asset_path):
        return _lambda.LayerVersion(
            self,
            id,
            code=_lambda.Code.from_asset(asset_path),
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_10],
        )

    def create_pandas_layer(self):
        return _lambda.LayerVersion.from_layer_version_arn(
            self,
            "pandas_layer",
            f"arn:aws:lambda:{self.region}:336392948345:layer:AWSSDKPandas-Python310:23",
        )

    def create_lambda_powertools_layer(self):
        return _lambda.LayerVersion.from_layer_version_arn(
            self,
            "lambda_power_tool_layer",
            f"arn:aws:lambda:{self.region}:017000801446:layer:AWSLambdaPowertoolsPythonV2:78",
        )

    def get_common_env_variables(self, config, aurora, source_bucket):
        return {
            "DB_HOST": aurora.cluster_endpoint.hostname,
            "DB_PORT": str(config.get("rds_db_port")),  # Convert to string
            "DB_NAME": config.get("rds_db_name"),
            "DB_TABLE": config.get("rds_db_table"),
            "SOURCE_BUCKET": source_bucket.bucket_name,
        }

    def get_db_init_env_variables(self, config, aurora, source_bucket):
        env_vars = self.get_common_env_variables(config, aurora, source_bucket)
        # Use initial_data_file from config or provide a default value if it's None
        db_dump_file = config.get("initial_data_file", "init_data.csv")
        # Ensure it's a string
        if db_dump_file is None:
            db_dump_file = "init_data.csv"

        env_vars.update(
            {
                "LOG_LEVEL": config.get("log_level", "INFO").upper(),
                "DB_DUMP_PREFIX": "initial_dataset",
                "DB_DUMP_FILE": db_dump_file,
                "SERVICE_NAME": "db_init_lambda",
                "PROCESS_LOCAL": "true",
                "DB_SECRET_NAME": aurora.secret.secret_name,
                "DB_USERNAME": "postgres",
                "READER_ROLE_NAME": self.reader_role.role_name,
                "WRITER_ROLE_NAME": self.writer_role.role_name,
                "AWS_ACCOUNT_ID": self.account,
            }
        )
        return env_vars

    def get_query_env_variables(self, config, aurora, source_bucket):
        env_vars = self.get_common_env_variables(config, aurora, source_bucket)
        env_vars.update(
            {
                "LOG_LEVEL": str(config.get("log_level", "INFO")).upper(),
                "SERVICE_NAME": "query_lambda",
                "RETRIEVAL_PREFIX": "retrieved_from_db",
                "DB_USERNAME": "reader_user",
                "READER_ROLE_NAME": self.reader_role.role_name,
                "AWS_ACCOUNT_ID": self.account,
                "AQ_PARAMETER_PREDICTION": str(config.get("aq_parameter_prediction", "PM 2.5")),
                "MISSING_VALUE_PATTERN_MATCH": str(config.get("missing_value_pattern_match", "[65535]")),
            }
        )
        return env_vars

    def get_writer_env_variables(self, config, aurora, source_bucket):
        env_vars = self.get_common_env_variables(config, aurora, source_bucket)
        env_vars.update(
            {
                "LOG_LEVEL": str(config.get("log_level", "INFO")).upper(),
                "SERVICE_NAME": "writer_lambda",
                "PREDICTED_PREFIX": "predicted_values_output",
                "DB_USERNAME": "writer_user",
                "WRITER_ROLE_NAME": self.writer_role.role_name,
                "AWS_ACCOUNT_ID": self.account,
            }
        )
        return env_vars

    def get_batch_transform_env_variables(self, config, aurora, source_bucket):
        env_vars = self.get_common_env_variables(config, aurora, source_bucket)
        env_vars.update(
            {
                "LOG_LEVEL": str(config.get("log_level", "INFO")).upper(),
                "SERVICE_NAME": "initiate_batch_transform_lambda",
                "PREDICTED_PREFIX": "predicted_values_output",
                "SAGEMAKER_MODEL_ID": f"{config.get('project_prefix', 'demoapp')}-canvas-model",
                "BATCH_CALLBACK_FUNCTION_NAME": f"{config.get('project_prefix', 'demoapp')}-BatchTransformCallback",
                
                # New configurable batch transform parameters
                "ATTRIBUTES_FOR_PREDICTION": str(config.get("columns_of_impact", "['timestamp', 'parameter', 'sensor_type', 'sensor_id', 'longitude', 'latitude', 'deployment_date']")),
                "BATCH_TRANSFORM_INSTANCE_TYPE": str(config.get("batch_transform_instance_type", "ml.m5.xlarge")),
                "BATCH_TRANSFORM_INSTANCE_COUNT": str(config.get("batch_transform_instance_count", "1")),
                "BATCH_TRANSFORM_MAX_WAIT_TIME_IN_SECONDS": str(config.get("batch_transform_max_wait_time_in_seconds", "900")),
                "BATCH_TRANSFORM_CHECK_INTERVAL_IN_SECONDS": str(config.get("batch_transform_check_interval_in_seconds", "10")),
            }
        )
        return env_vars

    def get_batch_callback_env_variables(self, config, aurora, source_bucket):
        env_vars = self.get_common_env_variables(config, aurora, source_bucket)
        env_vars.update(
            {
                "LOG_LEVEL": str(config.get("log_level", "INFO")).upper(),
                "SERVICE_NAME": "batch_transform_callback_lambda",
                "PREDICTED_PREFIX": "predicted_values_output",
                
                # Add the same batch transform configuration parameters for consistency
                "ATTRIBUTES_FOR_PREDICTION": str(config.get("columns_of_impact", "['timestamp', 'parameter', 'sensor_type', 'sensor_id', 'longitude', 'latitude', 'deployment_date']")),
                "BATCH_TRANSFORM_INSTANCE_TYPE": str(config.get("batch_transform_instance_type", "ml.m5.xlarge")),
                "BATCH_TRANSFORM_INSTANCE_COUNT": str(config.get("batch_transform_instance_count", "1")),
                "BATCH_TRANSFORM_MAX_WAIT_TIME_IN_SECONDS": str(config.get("batch_transform_max_wait_time_in_seconds", "900")),
                "BATCH_TRANSFORM_CHECK_INTERVAL_IN_SECONDS": str(config.get("batch_transform_check_interval_in_seconds", "10")),
            }
        )
        return env_vars
