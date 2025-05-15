#!/bin/bash

###
# © 2025 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
# This AWS Content is provided subject to the terms of the AWS Customer Agreement
# available at http://aws.amazon.com/agreement or other written agreement between
# Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.
###

set -e  # Exit immediately if a command exits with a non-zero status

# Silence Node.js version warning
export JSII_SILENCE_WARNING_UNTESTED_NODE_VERSION=1

# Function to find the project root directory
find_project_root() {
    local current_path="$PWD"
    
    # Navigate up the directory tree until we find the project root
    # Project root is identified by having both 'infra' and 'bin' directories
    while [[ "$current_path" != "/" ]]; do
        if [[ -d "$current_path/infra" && -d "$current_path/bin" ]]; then
            echo "$current_path"
            return 0
        fi
        current_path="$(dirname "$current_path")"
    done
    
    echo "Error: Could not locate project root directory." >&2
    echo "Please run this script from within the project directory structure." >&2
    return 1
}

# Find project root and navigate to it
PROJECT_ROOT=$(find_project_root)
if [[ $? -ne 0 ]]; then
    exit 1
fi

echo "Project root identified at: $PROJECT_ROOT"
cd "$PROJECT_ROOT"

# Create and activate virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment"
    python3 -m venv .venv
fi
source .venv/bin/activate

# Install requirements
echo "Installing dependencies"
pip install -r infra/requirements.txt

# Prepare Lambda layers
echo "Preparing Lambda layers"
sh ./bin/prepare_layer_packages.sh

# Run pre-deployment configuration
echo "Running pre-deployment configuration"
pushd infra/scripts
python3 config.py --pre
if [ $? -ne 0 ]; then
    echo "Error: pre-deployment config.py failed"
    exit 1
fi

# Run post-deployment configuration
echo "Running post-deployment configuration"
python3 config.py --post
if [ $? -ne 0 ]; then
    echo "Error: post-deployment config.py failed"
    exit 1
fi
popd

# Determine stack name from pre-deployment-config.ini
CONFIG_FILE="$PROJECT_ROOT/infra/scripts/pre-deployment-config.ini"
DEFAULT_STACK_NAME="DemoappStack"

if [ -f "$CONFIG_FILE" ]; then
    # Extract project_prefix from config file using Python
    PROJECT_PREFIX=$(python3 -c "
import configparser
config = configparser.ConfigParser()
config.read('$CONFIG_FILE')
prefix = config['defaults']['project_prefix'] if 'defaults' in config and 'project_prefix' in config['defaults'] else 'demoapp'
print(prefix.capitalize() + 'Stack')
" 2>/dev/null)
    
    # Check if we got a valid stack name
    if [ -z "$PROJECT_PREFIX" ]; then
        echo "Could not extract stack name from config, using default: $DEFAULT_STACK_NAME"
        STACK_NAME="$DEFAULT_STACK_NAME"
    else
        STACK_NAME="$PROJECT_PREFIX"
        echo "Using stack name from config: $STACK_NAME"
    fi
else
    echo "Config file not found at $CONFIG_FILE, using default stack name: $DEFAULT_STACK_NAME"
    STACK_NAME="$DEFAULT_STACK_NAME"
fi

# CDK operations
echo "Bootstrapping CDK"
pushd infra
cdk bootstrap

echo "Synthesizing CDK stack: $STACK_NAME"
cdk synth "$STACK_NAME"

# Uncomment to deploy the stack
# echo "Deploying CDK stack: $STACK_NAME"
# cdk deploy "$STACK_NAME" --require-approval=never
popd

echo "Script completed successfully"
