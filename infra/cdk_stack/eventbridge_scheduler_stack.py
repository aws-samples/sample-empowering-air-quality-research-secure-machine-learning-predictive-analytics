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

        # Get schedule configuration from config
        schedule_hours = int(config.get("batch_transform_schedule_in_hours", "24"))
        
        # Generate cron expression based on schedule hours
        if schedule_hours == 24:
            # Daily at midnight UTC
            schedule_expression = "cron(0 0 * * ? *)"
        elif schedule_hours == 12:
            # Every 12 hours (midnight and noon UTC)
            schedule_expression = "cron(0 0,12 * * ? *)"
        elif schedule_hours == 8:
            # Every 8 hours (midnight, 8am, 4pm UTC)
            schedule_expression = "cron(0 0,8,16 * * ? *)"
        elif schedule_hours == 6:
            # Every 6 hours (midnight, 6am, noon, 6pm UTC)
            schedule_expression = "cron(0 0,6,12,18 * * ? *)"
        elif schedule_hours == 4:
            # Every 4 hours
            schedule_expression = "cron(0 0,4,8,12,16,20 * * ? *)"
        elif schedule_hours == 2:
            # Every 2 hours
            schedule_expression = "cron(0 0,2,4,6,8,10,12,14,16,18,20,22 * * ? *)"
        elif schedule_hours == 1:
            # Every hour
            schedule_expression = "cron(0 * * * ? *)"
        else:
            # For other values, use rate expression
            schedule_expression = f"rate({schedule_hours} hours)"

        # Schedule
        self.schedule = scheduler.CfnSchedule(
            self,
            f"{project_prefix}DailySchedule",
            flexible_time_window=scheduler.CfnSchedule.FlexibleTimeWindowProperty(
                mode="FLEXIBLE", maximum_window_in_minutes=60
            ),
            schedule_expression=schedule_expression,
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
                            "duration_hours": schedule_hours,
                        },
                    }
                ),
                retry_policy=scheduler.CfnSchedule.RetryPolicyProperty(
                    maximum_retry_attempts=3,
                    maximum_event_age_in_seconds=3600,  # 1 hour
                ),
            ),
            name=f"{project_prefix}-scheduler",
            description=f"Invokes step functions workflow every {schedule_hours} hours",
            state="ENABLED",
        )

        # Output
        CfnOutput(
            self,
            f"{project_prefix}ScheduleName",
            value=self.schedule.name,
            description="EventBridge Scheduler Schedule Name",
        )
