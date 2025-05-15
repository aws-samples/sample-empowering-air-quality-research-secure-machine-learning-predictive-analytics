from aws_cdk import (
    NestedStack,
    aws_iam as iam,
    aws_scheduler as scheduler,
    aws_stepfunctions as sfn,
    CfnOutput,
)
from constructs import Construct
import json
import random
import string

class EventBridgeSchedulerStack(NestedStack):

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        state_machine: sfn.IStateMachine,
        config: dict,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        project_prefix = config.get("project_prefix", "demoapp")

        # EventBridge Scheduler role
        self.scheduler_role = iam.Role(
            self,
            f"{project_prefix}SchedulerRole",
            assumed_by=iam.ServicePrincipal("scheduler.amazonaws.com"),
        )

        # Add permission to invoke Step Function
        self.scheduler_role.add_to_policy(
            iam.PolicyStatement(
                actions=["states:StartExecution"],
                resources=[state_machine.state_machine_arn],
            )
        )

        # Schedule
        self.schedule = scheduler.CfnSchedule(
            self,
            f"{project_prefix}DailySchedule",
            flexible_time_window=scheduler.CfnSchedule.FlexibleTimeWindowProperty(
                mode="FLEXIBLE", maximum_window_in_minutes=60
            ),
            schedule_expression="cron(0 0 * * ? *)",  # Run at midnight UTC every day
            target=scheduler.CfnSchedule.TargetProperty(
                arn=state_machine.state_machine_arn,
                role_arn=self.scheduler_role.role_arn,
                input=json.dumps(
                    {
                        "timestamp": "$.time",
                        "metadata": {
                            "source": "EventBridge Scheduler",
                            "service": "demo_workflow",
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
            name=f"{project_prefix}-scheduler",
            description="Invokes step functions workflow daily",
            state="ENABLED",
        )

        # Output
        CfnOutput(
            self,
            f"{project_prefix}ScheduleName",
            value=self.schedule.name,
            description="EventBridge Scheduler Schedule Name",
        )
