#!/usr/bin/env python3
import os
import aws_cdk as cdk
from cdk_stack.air_quality_stack import AirQualityStack
from cdk_nag import AwsSolutionsChecks

app = cdk.App()
AirQualityStack(
    app,
    "AirQualityStack-Dev",
    env=cdk.Environment(
        account=os.getenv("CDK_DEFAULT_ACCOUNT"), region=os.getenv("CDK_DEFAULT_REGION")
    ),
)
# cdk.Aspects.of(app).add(AwsSolutionsChecks())
app.synth()
