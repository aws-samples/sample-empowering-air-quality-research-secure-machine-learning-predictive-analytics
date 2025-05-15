#!/bin/bash

###
# © 2025 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
# This AWS Content is provided subject to the terms of the AWS Customer Agreement
# available at http://aws.amazon.com/agreement or other written agreement between
# Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.
###

set -e  # Exit immediately if a command exits with a non-zero status

echo "Starting cleanup process..."

# Function to find the project root directory
find_project_root() {
    local current_path="$PWD"
    
    # First check if we're already at the project root
    if [[ -d "$current_path/infra" && -d "$current_path/bin" ]]; then
        echo "$current_path"
        return 0
    fi
    
    # Navigate up the directory tree until we find the project root
    while [[ "$current_path" != "/" ]]; do
        current_path="$(dirname "$current_path")"
        if [[ -d "$current_path/infra" && -d "$current_path/bin" ]]; then
            echo "$current_path"
            return 0
        fi
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

# Clean Python cache files
echo "Cleaning Python cache files..."
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
find . -type f -name "*.pyo" -delete
find . -type f -name "*.pyd" -delete
find . -type f -name ".coverage" -delete
find . -type d -name ".pytest_cache" -exec rm -rf {} +
find . -type d -name ".mypy_cache" -exec rm -rf {} +

# Clean CDK generated files
echo "Cleaning CDK generated files..."
if [ -d "./infra/cdk.out" ]; then
    rm -rf ./infra/cdk.out
fi

# Clean Lambda layer packages
echo "Cleaning Lambda layer packages..."
if [ -d "./lambda_layer" ]; then
    find ./lambda_layer -name "*.zip" -delete
    find ./lambda_layer -type d -name "python" -exec rm -rf {} +
fi

# Clean build directories
echo "Cleaning build directories..."
find . -type d -name "build" -exec rm -rf {} +
find . -type d -name "dist" -exec rm -rf {} +
find . -type d -name "*.egg-info" -exec rm -rf {} +

# Clean logs
echo "Cleaning log files..."
find . -type f -name "*.log" -delete

# Clean temporary files
echo "Cleaning temporary files..."
find . -type f -name "*.tmp" -delete
find . -type f -name "*.bak" -delete
find . -type f -name "*.swp" -delete
find . -type f -name ".DS_Store" -delete

# Clean any generated config files (optional - uncomment if needed)
# echo "Cleaning generated config files..."
# if [ -f "./pre-deployment-config.ini" ]; then
#     echo "Keeping pre-deployment-config.ini as it contains your project settings"
#     # Uncomment the line below if you want to remove it anyway
#     # rm ./pre-deployment-config.ini
# fi

# Clean virtual environment (optional - uncomment if needed)
# echo "Cleaning virtual environment..."
# if [ -d "./.venv" ]; then
#     rm -rf ./.venv
# fi

echo "Cleanup complete!"
echo "Note: Virtual environment was preserved. To remove it, uncomment the relevant section in this script."
