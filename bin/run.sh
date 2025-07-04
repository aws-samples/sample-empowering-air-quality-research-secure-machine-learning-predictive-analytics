#!/bin/bash

# Simple Air Quality ML Setup Script
# This script handles the complete setup process with minimal user input

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Configuration variables to store parameters dynamically
CONFIG_KEYS=()
CONFIG_VALUES=()

# Parse command line arguments
USE_DEFAULTS=false
DEPLOY=false
HELP=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --use-defaults|-ud)
            USE_DEFAULTS=true
            shift
            ;;
        --deploy|-d)
            DEPLOY=true
            shift
            ;;
        --help|-h)
            HELP=true
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Show help
if [ "$HELP" = true ]; then
    echo -e "${BLUE}🚀 Air Quality ML System - Setup${NC}"
    echo "=============================================="
    echo
    echo -e "${GREEN}Usage:${NC}"
    echo "  ./bin/setup.sh [OPTIONS]"
    echo
    echo -e "${GREEN}Options:${NC}"
    echo "  --use-defaults, -ud    Use all default values (non-interactive)"
    echo "  --deploy, -d           Deploy the CDK stack after setup (default: only synth)"
    echo "  --help, -h             Show this help message"
    echo
    echo -e "${GREEN}Prerequisites:${NC}"
    echo "  1. Configuration files must be present:"
    echo "     • infra/scripts/config.ini"
    echo "     • infra/scripts/config.ini"
    echo "  2. Place your data file at: infra/data/[filename].csv"
    echo
    echo -e "${GREEN}Configuration:${NC}"
    echo "  Values are read from the provided configuration files"
    echo
    echo -e "${GREEN}Examples:${NC}"
    echo "  ./bin/setup.sh                     # Interactive setup (synth only)"
    echo "  ./bin/setup.sh --use-defaults      # Use all defaults (synth only)"
    echo "  ./bin/setup.sh -ud                 # Same as above (short form)"
    echo "  ./bin/setup.sh --deploy            # Interactive setup + deploy"
    echo "  ./bin/setup.sh -ud -d              # Use defaults + deploy"
    echo
    exit 0
fi

echo -e "${BLUE}🚀 Air Quality ML System - Simple Setup${NC}"
echo "=============================================="
echo

if [ "$USE_DEFAULTS" = true ]; then
    echo -e "${GREEN}🤖 Running in non-interactive mode with default values${NC}"
    echo
else
    echo -e "${YELLOW}📝 Running in interactive mode${NC}"
    echo -e "${BLUE}💡 For non-interactive setup, use: $0 --use-defaults${NC}"
    echo
fi

# Helper function to get value by key from arrays
get_config_value() {
    local key="$1"
    
    for i in "${!CONFIG_KEYS[@]}"; do
        if [ "${CONFIG_KEYS[$i]}" = "$key" ]; then
            echo "${CONFIG_VALUES[$i]}"
            return 0
        fi
    done
    echo ""
}

# Function to read all parameters from config file dynamically
read_default_config() {
    local config_file="$PROJECT_ROOT/infra/scripts/config.ini"
    local default_config_file="$PROJECT_ROOT/infra/scripts/config.ini.default"
    
    # Create config.ini from default if it doesn't exist
    if [[ ! -f "$config_file" ]]; then
        if [[ -f "$default_config_file" ]]; then
            echo "Creating config.ini from default template..."
            cp "$default_config_file" "$config_file"
        else
            echo -e "${RED}❌ Default configuration file not found!${NC}"
            echo -e "  • ${BLUE}$default_config_file${NC}"
            exit 1
        fi
    fi
    
    # Clear existing configurations
    CONFIG_KEYS=()
    CONFIG_VALUES=()
    
    # Read config file
    if [ "$USE_DEFAULTS" = false ]; then
        echo "Reading configuration from: $config_file" >&2
    fi
    while IFS='=' read -r key value; do
        # Skip empty lines and comments
        [[ -z "$key" || "$key" =~ ^[[:space:]]*# ]] && continue
        # Skip section headers like [defaults]
        [[ "$key" =~ ^\[.*\]$ ]] && continue
        
        # Clean up key and value (remove leading/trailing whitespace)
        key=$(echo "$key" | xargs)
        value=$(echo "$value" | xargs)
        
        if [ -n "$key" ]; then
            CONFIG_KEYS+=("$key")
            CONFIG_VALUES+=("$value")
            if [ "$USE_DEFAULTS" = false ]; then
                echo "  $key = $value" >&2
            fi
        fi
    done < "$config_file"
    
    if [ "$USE_DEFAULTS" = false ]; then
        echo "Total parameters loaded: ${#CONFIG_KEYS[@]}" >&2
    fi
}

# Function to display configuration and ask for confirmation
show_config_and_confirm() {
    echo -e "${GREEN}📋 Configuration Parameters${NC}"
    echo "=============================================="
    
    # Display all parameters
    if [ ${#CONFIG_KEYS[@]} -gt 0 ]; then
        echo -e "${BLUE}Configuration:${NC}"
        for i in "${!CONFIG_KEYS[@]}"; do
            echo -e "  ${CONFIG_KEYS[$i]}: ${BLUE}${CONFIG_VALUES[$i]}${NC}"
        done
        echo
    fi
    
    if [ ${#CONFIG_KEYS[@]} -eq 0 ]; then
        echo -e "${RED}❌ No configuration parameters found!${NC}"
        echo -e "${YELLOW}Please ensure the configuration file exists and contains valid parameters.${NC}"
        return 1
    fi
    
    echo -e "${YELLOW}These are the parameters that will be used for your deployment.${NC}"
    echo
    echo -e "${BLUE}💡 To modify these parameters:${NC}"
    echo -e "   1. Edit the configuration file:"
    echo -e "      • ${YELLOW}infra/scripts/config.ini${NC}"
    echo -e "   2. Re-run the script: ${YELLOW}./bin/run.sh${NC}"
    echo
    
    if [ "$USE_DEFAULTS" = true ]; then
        echo -e "${GREEN}✅ Using default configuration (non-interactive mode)${NC}"
        return 0
    fi
    
    read -p "Do you want to continue with these parameters? (Y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        echo
        echo -e "${YELLOW}Setup cancelled.${NC}"
        echo -e "${BLUE}To modify the parameters:${NC}"
        echo -e "   1. Edit the configuration file:"
        echo -e "      • ${YELLOW}infra/scripts/config.ini${NC}"
        echo -e "   2. Re-run: ${YELLOW}./bin/run.sh${NC}"
        echo
        exit 1
    fi
    
    echo -e "${GREEN}✅ Proceeding with default configuration${NC}"
    return 0
}

# Read default configuration from file
if [ "$USE_DEFAULTS" = false ]; then
    echo "Loading configuration from default files..."
fi
read_default_config

echo -e "${GREEN}📋 Step 1: Configuration Review${NC}"
show_config_and_confirm

# Extract commonly used values for backward compatibility
# These can be accessed by other parts of the script that expect specific variable names
PROJECT_PREFIX=$(get_config_value "project_prefix")
PROJECT_PREFIX=${PROJECT_PREFIX:-demoapp}

DATA_FILE=$(get_config_value "initial_data_file")
DATA_FILE=${DATA_FILE:-init_data.csv}

AQ_PARAMETER=$(get_config_value "aq_parameter_prediction")
AQ_PARAMETER=${AQ_PARAMETER:-"PM 2.5"}

CANVAS_MODEL_ID=$(get_config_value "aq_canvas_model_id")
CANVAS_MODEL_ID=${CANVAS_MODEL_ID:-canvas-model-placeholder-update-after-training}

# Convert project prefix to lowercase
PROJECT_PREFIX=$(echo "$PROJECT_PREFIX" | tr '[:upper:]' '[:lower:]')

echo
echo -e "${GREEN}🔧 Step 2: Environment Setup${NC}"
echo "Setting up Python environment and dependencies..."

# Navigate to project root
echo "Project root: $PROJECT_ROOT"
cd "$PROJECT_ROOT"

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating Python virtual environment at: $(pwd)/.venv"
    python3 -m venv .venv
else
    echo "Virtual environment already exists at: $(pwd)/.venv"
fi

# Activate virtual environment
echo "Activating virtual environment..."
# shellcheck source=/dev/null
source .venv/bin/activate

# Install dependencies
echo "Installing Python dependencies from: $(pwd)/infra/requirements.txt"
if [ -f "infra/requirements.txt" ]; then
    pip install -q --upgrade pip
    pip install -q -r infra/requirements.txt
    echo "✅ Dependencies installed successfully"
else
    echo "❌ Error: requirements.txt not found at $(pwd)/infra/requirements.txt"
    exit 1
fi

echo
echo -e "${GREEN}📦 Step 2: Building Lambda Packages${NC}"
echo "Preparing Lambda layer packages..."

# Build Lambda layer packages
echo "Building Lambda layers..."

# Create common layer directory
mkdir -p lambda_layer/common
cd lambda_layer/common

# Clean existing python directory
if [ -d ./python ]; then
    rm -rf ./python
fi

# Create python directory and copy common files
mkdir -p ./python/common
cp ../../infra/lambdas/requirements.txt ./python/
cp ../../infra/lambdas/common/*.py ./python/common/

# Install dependencies
echo "Installing Lambda dependencies..."
pip3 install \
  -t ./python \
  --implementation cp \
  --python-version 3.10 \
  --platform manylinux2014_aarch64 \
  --only-binary=:all: --upgrade \
  --no-cache-dir \
  -r ./python/requirements.txt

# Create zip file
if [ -f common_layer.zip ]; then
    rm -f common_layer.zip
fi

zip -rq common_layer.zip python -x "./**/__pycache__/*"
echo "✅ Common layer package created"

# Return to project root
cd "$PROJECT_ROOT"

echo "✅ Lambda packages built successfully"

echo
echo -e "${GREEN}📝 Step 3: Validating Configuration Files${NC}"

# Check if config file exists and is readable
CONFIG_FILE="$PROJECT_ROOT/infra/scripts/config.ini"

if [[ -f "$CONFIG_FILE" ]]; then
    echo "✅ Configuration file found:"
    echo "  • config.ini"
    echo
    echo "Using configuration from this file."
else
    echo -e "${RED}❌ Configuration file missing!${NC}"
    echo "This should not happen as it was created earlier."
    exit 1
fi

# Ensure data directory exists
echo
echo -e "${BLUE}📁 Preparing data directory...${NC}"
mkdir -p "$PROJECT_ROOT/infra/data"
echo "✅ Data directory ready: infra/data/"

# Check if data file exists and provide guidance
if [ -f "$PROJECT_ROOT/infra/data/$DATA_FILE" ]; then
    echo -e "${GREEN}✅ Data file found: infra/data/$DATA_FILE${NC}"
else
    echo -e "${YELLOW}ℹ️  Data file not found: infra/data/$DATA_FILE${NC}"
    echo "   This is normal - you'll need to add your air quality dataset"
fi

echo
echo -e "${GREEN}🏗️  Step 4: CDK Setup${NC}"
if [ "$DEPLOY" = true ]; then
    echo "Preparing AWS CDK and deploying stack..."
else
    echo "Preparing AWS CDK for deployment (synthesis only)..."
fi

# Bootstrap CDK if needed
echo "Checking CDK bootstrap status..."
if ! aws sts get-caller-identity &>/dev/null; then
    echo -e "${RED}❌ AWS credentials not configured${NC}"
    echo "Please run: aws configure"
    exit 1
fi

# Get AWS account and region
AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=$(aws configure get region || echo "us-east-1")

echo "AWS Account: $AWS_ACCOUNT"
echo "AWS Region: $AWS_REGION"

# Navigate to infra directory for CDK commands
echo "Navigating to infra directory for CDK operations..."
cd "$PROJECT_ROOT/infra"
echo "Current directory: $(pwd)"
echo "CDK config file exists: $([ -f "cdk.json" ] && echo "YES" || echo "NO")"

# Bootstrap CDK
echo "Bootstrapping CDK..."
cdk bootstrap "aws://$AWS_ACCOUNT/$AWS_REGION"

# Synthesize CDK
echo "Synthesizing CDK stack..."
cdk synth

# Deploy if requested
if [ "$DEPLOY" = true ]; then
    echo
    echo -e "${YELLOW}🚀 Deploying CDK stack...${NC}"
    echo "This may take several minutes..."
    cdk deploy --require-approval never
    echo -e "${GREEN}✅ Deployment completed!${NC}"
fi

# Return to project root
cd "$PROJECT_ROOT"

echo
if [ "$DEPLOY" = true ]; then
    echo -e "${GREEN}🎉 Setup and Deployment Complete!${NC}"
else
    echo -e "${GREEN}🎉 Setup Complete!${NC}"
fi
echo "=============================================="
echo

# Check if data file exists and show appropriate message
if [ -f "infra/data/$DATA_FILE" ]; then
    echo -e "${GREEN}✅ Data File Ready${NC}"
    echo "=============================================="
    echo -e "${GREEN}Your data file is properly configured and ready for deployment.${NC}"
else
    echo -e "${YELLOW}📋 Data File Setup Required${NC}"
    echo "=============================================="
    echo -e "${BLUE}Choose one of the following approaches to provide your data:${NC}"
fi
echo

echo -e "${BLUE}1. Data File Location:${NC}"
echo -e "   Copy your CSV file to: ${YELLOW}infra/data/$DATA_FILE${NC}"
echo

echo -e "${BLUE}2. Required CSV Fields (order flexible):${NC}"
echo "   timestamp,value,parameter,device_id,chip_id,sensor_type,sensor_id,location_id,location,street_name,city,country,latitude,longitude,deployment_date"
echo

echo -e "${BLUE}3. Example Data Record:${NC}"
echo "   2023-07-15 09:22:31.456 +0200,25.4,PM 2.5,24,esp8266-87654322,2,38,43,City Center,Oak Avenue,Springfield,United States,38.7823456,-92.1245678,2022-05-12 08:45:22.310 +0200"
echo

echo -e "${BLUE}4. Important Notes:${NC}"
echo -e "   • Column order is flexible - headers will be used to identify fields"
echo -e "   • Parameter field can contain any measurement type (not limited to PM values)"
echo -e "   • Your configured parameter ($AQ_PARAMETER) will be used for predictions"
echo

echo -e "${BLUE}5. Detailed Format Guide:${NC}"
echo -e "   See: ${YELLOW}infra/data/README.md${NC} for complete field descriptions"
echo

echo -e "${BLUE}6. Check Data File:${NC}"
if [ -f "infra/data/$DATA_FILE" ]; then
    echo -e "   ${GREEN}✅ Data file found: infra/data/$DATA_FILE${NC}"
    echo -e "   ${GREEN}   You can proceed with deployment${NC}"
else
    echo -e "   ${RED}❌ Data file NOT found: infra/data/$DATA_FILE${NC}"
    echo -e "   ${YELLOW}   Two options available (see Next Steps below)${NC}"
fi
echo
echo -e "${GREEN}Next Steps:${NC}"
echo "=============================================="
if [ "$DEPLOY" = true ]; then
    if [ -f "infra/data/$DATA_FILE" ]; then
        echo -e "${GREEN}✅ Infrastructure deployed and ready:${NC}"
        echo "   1. Initialize database using the Lambda function in AWS Console"
        echo "   2. Your system will be ready to process air quality data!"
    else
        echo -e "${YELLOW}📋 Infrastructure deployed - Data file options:${NC}"
        echo
        echo -e "${BLUE}Option 1: Local file approach${NC}"
        echo -e "   1. Add your data file to: ${YELLOW}infra/data/$DATA_FILE${NC}"
        echo "   2. Run the database initialization Lambda function in AWS Console"
        echo
        echo -e "${BLUE}Option 2: S3 upload approach${NC}"
        echo -e "   1. Upload your data file to S3 bucket location: ${YELLOW}initial_dataset/${NC}"
        echo "   2. Run the database initialization Lambda function in AWS Console"
        echo "   3. The Lambda will process the file from S3 and populate the database"
        echo
        echo -e "${GREEN}💡 Both approaches work - choose based on your preference${NC}"
    fi
else
    if [ -f "infra/data/$DATA_FILE" ]; then
        echo -e "${GREEN}✅ Ready for deployment:${NC}"
        echo -e "   1. ${YELLOW}source .venv/bin/activate${NC}"
        echo -e "   2. ${YELLOW}cd infra && cdk deploy${NC}"
        echo "   3. Initialize database using the Lambda function in AWS Console"
        echo "   4. Your system will be ready to process air quality data!"
    else
        echo -e "${YELLOW}📋 Data file options - Choose one approach:${NC}"
        echo
        echo -e "${BLUE}Option 1: Local file approach${NC}"
        echo -e "   1. Add your data file to: ${YELLOW}infra/data/$DATA_FILE${NC}"
        echo "   2. Verify the CSV format matches the required schema"
        echo -e "   3. Activate environment: ${YELLOW}source .venv/bin/activate${NC}"
        echo -e "   4. Deploy: ${YELLOW}cd infra && cdk deploy${NC}"
        echo "   5. Run the database initialization Lambda function in AWS Console"
        echo
        echo -e "${BLUE}Option 2: S3 upload approach${NC}"
        echo -e "   1. Activate environment: ${YELLOW}source .venv/bin/activate${NC}"
        echo -e "   2. Deploy infrastructure first: ${YELLOW}cd infra && cdk deploy${NC}"
        echo -e "   3. Upload your data file to S3 bucket location: ${YELLOW}initial_dataset/${NC}"
        echo "   4. Run the database initialization Lambda function in AWS Console"
        echo "   5. The Lambda will process the file from S3 and populate the database"
        echo
        echo -e "${GREEN}💡 Recommendation:${NC} Use Option 2 if you have large data files or prefer S3 storage"
    fi
fi
echo
echo -e "${GREEN}Configuration saved to:${NC}"
echo "  • $PROJECT_ROOT/infra/scripts/config.ini"
echo
echo -e "${GREEN}Lambda packages built in:${NC}"
echo "  • lambda_layer/common/common_layer.zip"
echo "  • lambda_layer/pandas/pandas_layer.zip"
echo
echo -e "${BLUE}💡 Tips:${NC}"
echo "  • Your data file should contain air quality sensor readings"
echo "  • Make sure timestamps include timezone information"
echo "  • Check AWS costs before deploying (RDS, Lambda, SageMaker endpoints)"
echo "  • Use 'cdk destroy' to clean up resources when done"
echo "  • The database init Lambda will process your data file automatically"
echo
if [[ "$CANVAS_MODEL_ID" == *"placeholder"* ]]; then
    echo -e "${YELLOW}📋 Next Steps - Canvas Model Setup:${NC}"
    echo "  1. Activate environment: source .venv/bin/activate"
    echo "  2. Deploy this infrastructure first: cd infra && cdk deploy"
    echo "  2. Follow the blog post to create and deploy your Canvas model:"
    echo "     • See the detailed Canvas setup instructions in the blog post"
    echo "     • This covers data preparation, model training, and deployment"
    echo "  4. Update configuration with your model ID:"
    echo "     • Run: ./bin/run.sh (to update model ID)"
    echo "     • Activate environment: source .venv/bin/activate"
    echo "     • Re-deploy: cd infra && cdk deploy"
    echo
fi
echo -e "${GREEN}Happy ML modeling! 🤖${NC}"
