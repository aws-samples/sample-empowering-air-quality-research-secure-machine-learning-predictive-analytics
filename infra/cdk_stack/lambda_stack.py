from aws_cdk import (
    NestedStack,
    aws_ec2 as ec2,
    aws_rds as rds,
    aws_s3 as s3,
    aws_lambda as _lambda,
    aws_iam as iam,
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

        # Create a role for the make_inference Lambda
        self.inference_role = iam.Role(
            self,
            f"{project_prefix}InferenceRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            description="IAM role for the inference Lambda function",
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
            self.inference_role,
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

        # Add specific S3 permissions to the inference role
        self.inference_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    # Read permissions for retrieved_from_db prefix
                    "s3:GetObject", 
                    "s3:ListBucket",
                    # Write permissions for predicted_values_output prefix
                    "s3:PutObject",
                    "s3:PutObjectAcl"
                ],
                resources=[
                    # Read resources
                    source_bucket.bucket_arn,
                    f"{source_bucket.bucket_arn}/retrieved_from_db/*",
                    # Write resources
                    f"{source_bucket.bucket_arn}/predicted_values_output/*"
                ]
            )
        )

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

        # Add sagemaker permissions to the inference role
        self.inference_role.add_to_policy(
            iam.PolicyStatement(
                actions=["sagemaker:InvokeEndpoint"],
                resources=[
                    f"arn:aws:sagemaker:{self.region}:{self.account}:endpoint/{config.get('canvas_model_endpoint_name')}"
                ],
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
            f"{project_prefix}InferenceRoleName",
            value=self.inference_role.role_name,
            export_name=f"{project_prefix}InferenceRoleName",
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
            Duration.seconds(30),
            256,
            self.reader_role,  # Use reader role for querying
        )

        self.make_inference_lambda = self.create_lambda_function(
            "MakeInference",
            "make_inference",
            vpc,
            [lambda_sg],
            [lambda_power_tool_layer, pandas_layer],
            self.get_inference_env_variables(config, aurora, source_bucket),
            Duration.minutes(1),
            512,
            self.inference_role,  # Use the inference role
        )

        self.write_results_function = self.create_lambda_function(
            "WriteResultsInDB",
            "write_results_in_db",
            vpc,
            [lambda_sg],
            [common_shared_layer],
            self.get_writer_env_variables(config, aurora, source_bucket),
            Duration.seconds(30),
            256,
            self.writer_role,  # Use writer role for writing results
        )

        # Outputs
        CfnOutput(self, f"{project_prefix}DBInitLambdaName", value=self.db_init_lambda.function_name)
        CfnOutput(self, f"{project_prefix}QueryLambdaName", value=self.query_function.function_name)
        CfnOutput(
            self, f"{project_prefix}InferenceLambdaName", value=self.make_inference_lambda.function_name
        )
        CfnOutput(
            self, f"{project_prefix}WriterLambdaName", value=self.write_results_function.function_name
        )

        # Add CDK nag suppressions for this stack
        # Suppress IAM4 for managed policies
        for role in [
            self.init_role,
            self.reader_role,
            self.writer_role,
            self.inference_role,
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

        NagSuppressions.add_resource_suppressions_by_path(
            self,
            f"/{self.node.path}/{project_prefix}InferenceRole/DefaultPolicy/Resource",
            [
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "Wildcard permissions are required for the application functionality and are scoped to specific resources",
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
            self.make_inference_lambda,
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
                "LOG_LEVEL": config.get("lambda_logs_level", "INFO").upper(),
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
                "LOG_LEVEL": str(config.get("lambda_logs_level", "INFO")).upper(),
                "SERVICE_NAME": "query_lambda",
                "RETRIEVAL_PREFIX": "retrieved_from_db",
                "DB_USERNAME": "reader_user",
                "READER_ROLE_NAME": self.reader_role.role_name,
                "AWS_ACCOUNT_ID": self.account,
            }
        )
        return env_vars

    def get_inference_env_variables(self, config, aurora, source_bucket):
        env_vars = self.get_common_env_variables(config, aurora, source_bucket)
        env_vars.update(
            {
                "LOG_LEVEL": str(config.get("lambda_logs_level", "INFO")).upper(),
                "SERVICE_NAME": "make_inference_lambda",
                "PREDICTED_PREFIX": "predicted_values_output",
                "CANVAS_MODEL_ENDPOINT_NAME": str(config.get("canvas_model_endpoint_name", "")),
            }
        )
        return env_vars

    def get_writer_env_variables(self, config, aurora, source_bucket):
        env_vars = self.get_common_env_variables(config, aurora, source_bucket)
        env_vars.update(
            {
                "LOG_LEVEL": str(config.get("lambda_logs_level", "INFO")).upper(),
                "SERVICE_NAME": "writer_lambda",
                "PREDICTED_PREFIX": "predicted_values_output",
                "DB_USERNAME": "writer_user",
                "WRITER_ROLE_NAME": self.writer_role.role_name,
                "AWS_ACCOUNT_ID": self.account,
            }
        )
        return env_vars
