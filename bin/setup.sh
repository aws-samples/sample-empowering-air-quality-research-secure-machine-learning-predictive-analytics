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

# Default values
DEFAULT_PROJECT_PREFIX="demoapp"
DEFAULT_DATA_FILE="init_data.csv"
DEFAULT_AQ_PARAMETER="PM 2.5"

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

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
    echo -e "${GREEN}Default Values:${NC}"
    echo "  Project Prefix:        $DEFAULT_PROJECT_PREFIX"
    echo "  Data File:             $DEFAULT_DATA_FILE"
    echo "  AQ Parameter:          $DEFAULT_AQ_PARAMETER"
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

# Function to prompt for input with default
prompt_with_default() {
    local prompt="$1"
    local default="$2"
    local result
    
    if [ "$USE_DEFAULTS" = true ]; then
        # Non-interactive: clean output to stderr, return clean value
        echo -e "${GREEN}✓ $prompt: $default${NC}" >&2
        echo "$default"
        return
    fi
    
    # Interactive: detailed prompts to stderr, return clean value
    echo >&2
    echo -e "${YELLOW}$prompt${NC}" >&2
    echo -e "${BLUE}Default value: ${GREEN}$default${NC}" >&2
    echo -e "${BLUE}Instructions: Type your value and press Enter, or just press Enter to use the default${NC}" >&2
    echo -n "> " >&2
    read -r result
    
    if [ -z "$result" ]; then
        echo -e "${GREEN}Using default: $default${NC}" >&2
        echo "$default"
    else
        echo -e "${GREEN}Using: $result${NC}" >&2
        echo "$result"
    fi
}

# Function to discover Canvas models
discover_canvas_models() {
    if [ "$USE_DEFAULTS" = false ]; then
        echo -e "${BLUE}🔍 Discovering your Canvas models...${NC}" >&2
    fi
    
    # Try to use Python discovery script
    local discovered_model
    discovered_model=$(python3 "$PROJECT_ROOT/infra/scripts/discover_canvas.py" models 2>/dev/null || echo "")
    
    if [ -n "$discovered_model" ]; then
        if [ "$USE_DEFAULTS" = false ]; then
            echo -e "${GREEN}✅ Found Canvas model: $discovered_model${NC}" >&2
        fi
        echo "$discovered_model"
        return 0
    fi
    
    if [ "$USE_DEFAULTS" = false ]; then
        echo -e "${YELLOW}⚠️  No Canvas models found${NC}" >&2
        echo -e "${YELLOW}📋 Canvas Model Setup Required:${NC}" >&2
        echo "   1. Complete this infrastructure deployment first" >&2
        echo "   2. Follow the blog post to create and deploy your Canvas model:" >&2
        echo "      • See the detailed Canvas setup instructions in the blog post" >&2
        echo "      • This includes data preparation, model training, and deployment" >&2
        echo "   3. Re-run this setup script to configure the model ID" >&2
        echo "   4. Re-deploy the infrastructure with: cd infra && cdk deploy" >&2
        echo >&2
        echo -e "${BLUE}💡 For now, we'll use a placeholder model ID${NC}" >&2
        echo >&2
    fi
    echo "canvas-model-placeholder-update-after-training"  # Placeholder that's clearly identifiable
}

echo -e "${GREEN}📋 Step 1: Basic Configuration${NC}"
if [ "$USE_DEFAULTS" = true ]; then
    echo "Using default values for basic configuration."
else
    echo "Let's configure your air quality ML system with some basic settings."
    echo -e "${BLUE}💡 Tip: You can press Enter to use default values, or use --use-defaults flag for non-interactive setup${NC}"
fi
echo

# Get basic configuration
PROJECT_PREFIX=$(prompt_with_default "Enter project prefix (used for resource naming):" "$DEFAULT_PROJECT_PREFIX")
PROJECT_PREFIX=$(echo "$PROJECT_PREFIX" | tr '[:upper:]' '[:lower:]')  # Convert to lowercase

DATA_FILE=$(prompt_with_default "Enter your initial data filename:" "$DEFAULT_DATA_FILE")

if [ "$USE_DEFAULTS" = false ]; then
    echo
    echo -e "${BLUE}Available air quality parameters (common examples):${NC}"
    echo "  • PM 10   - Particulate matter 10 micrometers"
    echo "  • PM 1    - Particulate matter 1 micrometer" 
    echo "  • PM 2.5  - Particulate matter 2.5 micrometers"
    echo "  • Temperature, Humidity, CO2, etc. - Any measurement type"
    echo
fi
AQ_PARAMETER=$(prompt_with_default "Enter the parameter for ML prediction (can be any measurement type):" "$DEFAULT_AQ_PARAMETER")

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
echo -e "${GREEN}📋 Step 3: Canvas Model Discovery${NC}"
if [ "$USE_DEFAULTS" = true ]; then
    echo "Auto-discovering Canvas models..."
else
    echo "Now let's find your SageMaker Canvas model."
    echo -e "${BLUE}💡 Note: Canvas model creation is a separate manual step${NC}"
fi
echo

# Auto-discover Canvas models (now with proper Python environment)
DISCOVERED_MODEL=$(discover_canvas_models)

echo
CANVAS_MODEL_ID=$(prompt_with_default "Enter your Canvas Model ID:" "$DISCOVERED_MODEL")

echo
echo -e "${GREEN}📋 Step 4: Configuration Summary${NC}"
echo "=============================================="
echo -e "Project Prefix:     ${BLUE}$PROJECT_PREFIX${NC}"
echo -e "Data File:          ${BLUE}$DATA_FILE${NC}"
echo -e "AQ Parameter:       ${BLUE}$AQ_PARAMETER${NC}"
echo -e "Canvas Model ID:    ${BLUE}$CANVAS_MODEL_ID${NC}"
echo

if [ "$USE_DEFAULTS" = false ]; then
    read -p "Continue with this configuration? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Setup cancelled.${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✅ Using configuration above (non-interactive mode)${NC}"
fi

echo
echo -e "${GREEN}📦 Step 5: Building Lambda Packages${NC}"
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
echo -e "${GREEN}📝 Step 6: Creating Configuration Files${NC}"

# Create pre-deployment config
cat > "$PROJECT_ROOT/infra/scripts/pre-deployment-config.ini" << EOF
[defaults]
initial_data_file = $DATA_FILE
project_prefix = $PROJECT_PREFIX
aq_parameter_prediction = $AQ_PARAMETER
EOF

# Create post-deployment config
cat > "$PROJECT_ROOT/infra/scripts/post-deployment-config.ini" << EOF
[defaults]
canvas_model_id = $CANVAS_MODEL_ID
EOF

echo "✅ Configuration files created"

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
echo -e "${GREEN}🏗️  Step 6: CDK Setup${NC}"
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
echo -e "${RED}⚠️  IMPORTANT: Data File Required${NC}"
echo "=============================================="
echo -e "${YELLOW}Before deployment, you MUST provide your air quality dataset:${NC}"
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
    echo -e "   ${YELLOW}   You MUST add this file before deployment${NC}"
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
        echo -e "${YELLOW}📋 Infrastructure deployed but data file missing:${NC}"
        echo -e "   1. ${RED}Add your data file to: infra/data/$DATA_FILE${NC}"
        echo "   2. Initialize database using the Lambda function in AWS Console"
        echo "   3. Your system will be ready to process air quality data!"
    fi
else
    if [ -f "infra/data/$DATA_FILE" ]; then
        echo -e "${GREEN}✅ Ready for deployment:${NC}"
        echo -e "   1. ${YELLOW}cd infra && cdk deploy${NC}"
        echo "   2. Initialize database using the Lambda function in AWS Console"
        echo "   3. Your system will be ready to process air quality data!"
    else
        echo -e "${YELLOW}📋 Before deployment:${NC}"
        echo -e "   1. ${RED}Add your data file to: infra/data/$DATA_FILE${NC}"
        echo "   2. Verify the CSV format matches the required schema"
        echo -e "   3. Then deploy: ${YELLOW}cd infra && cdk deploy${NC}"
        echo "   4. Initialize database using the Lambda function in AWS Console"
        echo
        echo -e "${BLUE}💡 Alternative approach:${NC}"
        echo -e "   • Deploy infrastructure first: ${YELLOW}cd infra && cdk deploy${NC}"
        echo -e "   • Add data file later: ${YELLOW}infra/data/$DATA_FILE${NC}"
        echo "   • Then run the database initialization Lambda function"
    fi
fi
echo
echo -e "${GREEN}Configuration saved to:${NC}"
echo "  • $PROJECT_ROOT/infra/scripts/pre-deployment-config.ini"
echo "  • $PROJECT_ROOT/infra/scripts/post-deployment-config.ini"
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
    echo "  1. Deploy this infrastructure first: cd infra && cdk deploy"
    echo "  2. Follow the blog post to create and deploy your Canvas model:"
    echo "     • See the detailed Canvas setup instructions in the blog post"
    echo "     • This covers data preparation, model training, and deployment"
    echo "  3. Update configuration with your model ID:"
    echo "     • Run: ./bin/setup.sh (to update model ID)"
    echo "     • Re-deploy: cd infra && cdk deploy"
    echo
fi
echo -e "${GREEN}Happy ML modeling! 🤖${NC}"
