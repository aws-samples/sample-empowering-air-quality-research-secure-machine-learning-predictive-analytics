from aws_cdk import (
    NestedStack,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as sfn_tasks,
    aws_iam as iam,
    aws_lambda as _lambda,
    aws_logs as logs,
    Duration,
    CfnOutput,
)
from constructs import Construct
from cdk_nag import NagSuppressions

class StepFunctionsStack(NestedStack):
    """
    Step Functions stack for orchestrating the air quality prediction workflow.
    
    Architecture Note:
    - The batch_transform_callback_function is NOT part of the Step Functions workflow
    - It's triggered by EventBridge when SageMaker batch transform jobs complete
    - The Step Functions workflow uses WAIT_FOR_TASK_TOKEN pattern to wait for callbacks
    - The callback function sends success/failure notifications back to Step Functions
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        query_function: _lambda.IFunction,
        initiate_batch_transform_function: _lambda.IFunction,
        write_results_function: _lambda.IFunction,
        config: dict,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Get the project prefix from config
        project_prefix = config.get("project_prefix", "demoapp")

        # Create state machine role
        self.state_machine_role = iam.Role(
            self,
            f"{project_prefix}StateMachineRole",
            assumed_by=iam.ServicePrincipal("states.amazonaws.com"),
        )

        # Create the state machine
        self.state_machine = self.create_state_machine(
            query_function,
            initiate_batch_transform_function,
            write_results_function,
            self.state_machine_role,
            project_prefix,
        )

        # Add permissions to the state machine role
        self.state_machine_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaRole")
        )

        # Add CloudWatch Logs permissions
        self.state_machine_role.add_to_policy(
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
        )

        # Add permissions to invoke Lambda functions
        self.state_machine_role.add_to_policy(
            iam.PolicyStatement(
                actions=["lambda:InvokeFunction"],
                resources=[
                    query_function.function_arn,
                    initiate_batch_transform_function.function_arn,
                    write_results_function.function_arn,
                ],
            )
        )

        # Add X-Ray permissions
        self.state_machine_role.add_to_policy(
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

        self.state_machine_role.add_to_policy(
            iam.PolicyStatement(actions=["iam:PassRole"], resources=["*"])
        )

        # Output with prefix
        CfnOutput(
            self,
            f"{project_prefix}StateMachineArn",
            value=self.state_machine.state_machine_arn,
            description="State Machine ARN",
        )

        # Add CDK nag suppressions for this stack
        NagSuppressions.add_resource_suppressions(
            self.state_machine_role,
            [
                {
                    "id": "AwsSolutions-IAM4",
                    "reason": "Using AWS managed policies is acceptable for this demo application",
                }
            ],
        )

        NagSuppressions.add_resource_suppressions(
            self.state_machine,
            [
                {
                    "id": "AwsSolutions-SF1",
                    "reason": "Step Function logging is configured with appropriate level for this demo application",
                }
            ],
        )

        NagSuppressions.add_resource_suppressions_by_path(
            self,
            f"/{self.node.path}/{project_prefix}StateMachineRole/DefaultPolicy/Resource",
            [
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "Wildcard permissions are required for the application functionality and are scoped to specific resources",
                }
            ],
        )

    def create_state_machine(
        self,
        query_function,
        initiate_batch_transform_function,
        write_results_function,
        state_machine_role,
        project_prefix,
    ):
        # Create Lambda task for query function
        query_task = sfn_tasks.LambdaInvoke(
            self,
            "Query DB",
            lambda_function=query_function,
            payload=sfn.TaskInput.from_json_path_at("$"),
            retry_on_service_exceptions=False,  # Handle errors explicitly
            result_path="$.QueryResult",
            task_timeout=sfn.Timeout.duration(Duration.hours(1)),  # 1 hour timeout
        )

        # Create Lambda task for batch transform initiation with callback
        batch_transform_task = sfn_tasks.LambdaInvoke(
            self,
            "Initiate Batch Transform",
            lambda_function=initiate_batch_transform_function,
            payload=sfn.TaskInput.from_object({
                "TaskToken": sfn.JsonPath.task_token,
                "QueryResult": sfn.JsonPath.string_at("$.QueryResult.Payload")
            }),
            retry_on_service_exceptions=False,  # Handle errors explicitly
            integration_pattern=sfn.IntegrationPattern.WAIT_FOR_TASK_TOKEN,
            payload_response_only=False,
            task_timeout=sfn.Timeout.duration(Duration.hours(1)),  # 1 hour timeout
        )

        # Create Lambda task for writing to DB
        write_results_task = sfn_tasks.LambdaInvoke(
            self,
            "Write Results in DB",
            lambda_function=write_results_function,
            payload=sfn.TaskInput.from_json_path_at("$"),
            retry_on_service_exceptions=False,  # Handle errors explicitly
            task_timeout=sfn.Timeout.duration(Duration.hours(1)),  # 1 hour timeout
        )

        # Create terminal states
        no_records_found = sfn.Succeed(self, "No Records Found")
        query_failed = sfn.Fail(self, "Query Failed", 
                               cause="Database query failed",
                               error="QueryError")
        batch_transform_failed = sfn.Fail(self, "Batch Transform Failed",
                                         cause="Batch transform initiation failed", 
                                         error="BatchTransformError")
        write_results_failed = sfn.Fail(self, "Write Results Failed",
                                       cause="Writing results to database failed",
                                       error="WriteResultsError")
        query_timeout = sfn.Fail(self, "Query Timeout",
                                cause="Database query timed out after 1 hour",
                                error="QueryTimeout")
        batch_transform_timeout = sfn.Fail(self, "Batch Transform Timeout",
                                          cause="Batch transform timed out after 1 hour",
                                          error="BatchTransformTimeout")
        write_results_timeout = sfn.Fail(self, "Write Results Timeout",
                                        cause="Writing results timed out after 1 hour",
                                        error="WriteResultsTimeout")
        batch_transform_completed = sfn.Succeed(self, "Batch Transform Completed Successfully")

        # Add error handling and timeout handling for each task
        query_task.add_catch(query_failed, errors=["States.ALL"], result_path="$.Error")
        query_task.add_catch(query_timeout, errors=["States.Timeout"], result_path="$.Error")
        
        batch_transform_task.add_catch(batch_transform_failed, errors=["States.ALL"], result_path="$.Error")
        batch_transform_task.add_catch(batch_transform_timeout, errors=["States.Timeout"], result_path="$.Error")
        
        write_results_task.add_catch(write_results_failed, errors=["States.ALL"], result_path="$.Error")
        write_results_task.add_catch(write_results_timeout, errors=["States.Timeout"], result_path="$.Error")

        definition = query_task.next(
            sfn.Choice(self, "IsRecordsAvailable")
            .when(
                # Check for 204 status code (No Content)
                sfn.Condition.number_equals("$.QueryResult.Payload.statusCode", 204),
                no_records_found
            )
            .when(
                # Check for error status codes (>= 400)
                sfn.Condition.number_greater_than_equals("$.QueryResult.Payload.statusCode", 400),
                query_failed
            )
            .otherwise(
                batch_transform_task.next(
                    sfn.Choice(self, "HasBatchTransformCompleted")
                    .when(
                        # Check for successful batch transform completion
                        sfn.Condition.number_equals("$.statusCode", 200),
                        write_results_task.next(batch_transform_completed)
                    )
                    .when(
                        # Check for batch transform error status codes (>= 400)
                        sfn.Condition.number_greater_than_equals("$.statusCode", 400),
                        batch_transform_failed
                    )
                    .otherwise(batch_transform_failed)
                )
            )
        )

        # Create the state machine
        log_group = logs.LogGroup(
            self, f"{project_prefix}StateMachineLogGroup", retention=logs.RetentionDays.ONE_WEEK
        )

        return sfn.StateMachine(
            self,
            f"{project_prefix}StateMachine",
            definition_body=sfn.DefinitionBody.from_chainable(definition),
            role=state_machine_role,
            tracing_enabled=True,
            timeout=Duration.hours(2),  # Overall state machine timeout of 2 hours
            logs=sfn.LogOptions(
                destination=log_group,
                level=sfn.LogLevel.ALL,
                include_execution_data=True,
            ),
        )
