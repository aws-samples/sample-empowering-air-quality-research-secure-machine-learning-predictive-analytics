#!/usr/bin/env python3
import os
import configparser
import aws_cdk as cdk
from cdk_stack.main_stack import MainStack
from cdk_nag import AwsSolutionsChecks

app = cdk.App()

# Determine the project root directory
# This assumes the script is being run from the project root or from within the project structure
def find_project_root():
    current_dir = os.getcwd()
    while current_dir != '/':
        if os.path.isdir(os.path.join(current_dir, 'infra')) and os.path.isdir(os.path.join(current_dir, 'bin')):
            return current_dir
        current_dir = os.path.dirname(current_dir)
    return None

project_root = find_project_root()
if not project_root:
    print("Warning: Could not locate project root directory. Using current directory.")
    project_root = os.getcwd()

# Load the pre-deployment configuration
config = configparser.ConfigParser()
config_path = os.path.join(project_root, "infra", "scripts", "pre-deployment-config.ini")

# Default project prefix if config file doesn't exist or doesn't contain the value
default_project_prefix = "demoapp"
project_prefix = default_project_prefix

# Try to read the project_prefix from the config file
if os.path.exists(config_path):
    config.read(config_path)
    if "defaults" in config and "project_prefix" in config["defaults"]:
        project_prefix = config["defaults"]["project_prefix"]
    else:
        print(f"Warning: project_prefix not found in {config_path}, using default: {default_project_prefix}")
else:
    print(f"Warning: Config file {config_path} not found, using default project prefix: {default_project_prefix}")

# Create the stack name using the project prefix
stack_name = f"{project_prefix.capitalize()}Stack"
print(f"Deploying stack: {stack_name}")

MainStack(
    app,
    stack_name,
    env=cdk.Environment(
        account=os.getenv("CDK_DEFAULT_ACCOUNT"), region=os.getenv("CDK_DEFAULT_REGION")
    ),
)

cdk.Aspects.of(app).add(AwsSolutionsChecks())
app.synth()
