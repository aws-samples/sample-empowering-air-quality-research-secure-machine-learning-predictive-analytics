from aws_cdk import (
    NestedStack,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as sfn_tasks,
    aws_iam as iam,
    aws_lambda as _lambda,
    aws_logs as logs,
    CfnOutput,
)
from constructs import Construct
from cdk_nag import NagSuppressions

class StepFunctionsStack(NestedStack):

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        query_function: _lambda.IFunction,
        make_inference_function: _lambda.IFunction,
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
            make_inference_function,
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
                    make_inference_function.function_arn,
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
        make_inference_function,
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
            retry_on_service_exceptions=True,
        )

        # Create Lambda task for inference
        inference_task = sfn_tasks.LambdaInvoke(
            self,
            "Make Inference",
            lambda_function=make_inference_function,
            payload=sfn.TaskInput.from_json_path_at("$"),
            retry_on_service_exceptions=True,
        )

        # Create Lambda task for writing to DB
        write_results_task = sfn_tasks.LambdaInvoke(
            self,
            "Write Results in DB",
            lambda_function=write_results_function,
            payload=sfn.TaskInput.from_json_path_at("$"),
            retry_on_service_exceptions=True,
        )

        # Create Success states
        no_records_found = sfn.Succeed(self, "No Records Found")
        error_state = sfn.Succeed(self, "Error Occurred")
        success_state = sfn.Succeed(self, "Inference Completed Without Data")

        definition = query_task.next(
            sfn.Choice(self, "IsRecordsAvailable")
            .when(
                # Check for 204 status code (No Content)
                sfn.Condition.number_equals("$.Payload.statusCode", 204),
                no_records_found
            )
            .when(
                # Check for error status codes (>= 400)
                sfn.Condition.number_greater_than_equals("$.Payload.statusCode", 400),
                error_state
            )
            .otherwise(
                inference_task.next(
                    sfn.Choice(self, "HasInferenceCompleted")
                    .when(
                        sfn.Condition.number_greater_than_equals("$.Payload.statusCode", 400),
                        success_state
                    )
                    .otherwise(write_results_task)
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
            definition=definition,
            role=state_machine_role,
            tracing_enabled=True,
            logs=sfn.LogOptions(
                destination=log_group,
                level=sfn.LogLevel.ALL,
                include_execution_data=True,
            ),
        )
