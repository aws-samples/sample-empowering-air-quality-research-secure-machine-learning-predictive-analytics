#!/bin/bash

###
# © 2025 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
# This AWS Content is provided subject to the terms of the AWS Customer Agreement
# available at http://aws.amazon.com/agreement or other written agreement between
# Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.
###

set -e  # Exit immediately if a command exits with a non-zero status

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🧹 Starting comprehensive cleanup process...${NC}"

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
PROJECT_ROOT=$(find_project_root) || exit 1

echo -e "${GREEN}Project root identified at: $PROJECT_ROOT${NC}"
cd "$PROJECT_ROOT"

# Function to safely remove files/directories
safe_remove() {
    local path="$1"
    local description="$2"
    
    if [ -e "$path" ]; then
        echo -e "${YELLOW}  Removing: $description${NC}"
        rm -rf "$path"
    fi
}

# Function to find and remove files by pattern
find_and_remove() {
    local pattern="$1"
    local description="$2"
    local type="${3:-f}"  # Default to files
    
    local count=$(find . -type "$type" -name "$pattern" 2>/dev/null | wc -l)
    if [ "$count" -gt 0 ]; then
        echo -e "${YELLOW}  Removing $count $description${NC}"
        find . -type "$type" -name "$pattern" -exec rm -rf {} + 2>/dev/null || true
    fi
}

# Clean Python cache files
echo -e "${GREEN}🐍 Cleaning Python cache files...${NC}"
find_and_remove "__pycache__" "Python cache directories" "d"
find_and_remove "*.pyc" "Python compiled files"
find_and_remove "*.pyo" "Python optimized files"
find_and_remove "*.pyd" "Python extension modules"
find_and_remove ".coverage" "coverage files"
find_and_remove ".pytest_cache" "pytest cache directories" "d"
find_and_remove ".mypy_cache" "mypy cache directories" "d"
find_and_remove "*.egg-info" "Python egg info directories" "d"

# Clean CDK generated files
echo -e "${GREEN}☁️  Cleaning CDK generated files...${NC}"
safe_remove "./infra/cdk.out" "CDK output directory"
safe_remove "./cdk.out" "CDK output directory (root)"
find_and_remove "cdk.context.json" "CDK context files"
find_and_remove "*.js.map" "JavaScript source maps"
find_and_remove "*.d.ts" "TypeScript declaration files"

# Clean Lambda layer packages
echo -e "${GREEN}📦 Cleaning Lambda layer packages...${NC}"
if [ -d "./lambda_layer" ]; then
    echo -e "${YELLOW}  Found lambda_layer directory${NC}"
    
    # Show what's in the directory
    echo -e "${BLUE}  Contents of lambda_layer:${NC}"
    ls -la ./lambda_layer/ 2>/dev/null || true
    
    # Remove the entire lambda_layer directory
    echo -e "${YELLOW}  Removing entire lambda_layer directory and all contents${NC}"
    rm -rf ./lambda_layer
    
    # Verify removal
    if [ ! -d "./lambda_layer" ]; then
        echo -e "${GREEN}  ✅ Lambda layer directory completely removed${NC}"
    else
        echo -e "${RED}  ❌ Failed to remove lambda_layer directory${NC}"
    fi
else
    echo -e "${BLUE}  No lambda_layer directory found${NC}"
fi

# Clean build and distribution directories
echo -e "${GREEN}🏗️  Cleaning build directories...${NC}"
find_and_remove "build" "build directories" "d"
find_and_remove "dist" "distribution directories" "d"
find_and_remove ".tox" "tox directories" "d"
find_and_remove ".nox" "nox directories" "d"

# Clean Node.js files (if any)
echo -e "${GREEN}📦 Cleaning Node.js files...${NC}"
find_and_remove "node_modules" "Node.js modules directories" "d"
find_and_remove "package-lock.json" "npm lock files"
find_and_remove "yarn.lock" "yarn lock files"
find_and_remove ".npm" "npm cache directories" "d"

# Clean configuration files (with user confirmation)
echo -e "${GREEN}⚙️  Cleaning configuration files...${NC}"
config_files=(
    "./infra/scripts/pre-deployment-config.ini"
    "./infra/scripts/post-deployment-config.ini"
)

for config_file in "${config_files[@]}"; do
    if [ -f "$config_file" ]; then
        echo -e "${YELLOW}Found configuration file: $config_file${NC}"
        read -p "Do you want to remove this config file? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm "$config_file"
            echo -e "${GREEN}  Removed: $config_file${NC}"
        else
            echo -e "${BLUE}  Kept: $config_file${NC}"
        fi
    fi
done

# Clean log files
echo -e "${GREEN}📝 Cleaning log files...${NC}"
find_and_remove "*.log" "log files"
find_and_remove "*.out" "output files"
find_and_remove "*.err" "error files"

# Clean temporary files
echo -e "${GREEN}🗑️  Cleaning temporary files...${NC}"
find_and_remove "*.tmp" "temporary files"
find_and_remove "*.temp" "temp files"
find_and_remove "*.bak" "backup files"
find_and_remove "*.swp" "vim swap files"
find_and_remove "*.swo" "vim swap files"
find_and_remove "*~" "editor backup files"
find_and_remove ".DS_Store" "macOS metadata files"
find_and_remove "Thumbs.db" "Windows thumbnail files"
find_and_remove "desktop.ini" "Windows desktop files"

# Clean IDE and editor files
echo -e "${GREEN}💻 Cleaning IDE and editor files...${NC}"
find_and_remove ".vscode" "VS Code directories" "d"
find_and_remove ".idea" "IntelliJ IDEA directories" "d"
find_and_remove "*.sublime-*" "Sublime Text files"
find_and_remove ".project" "Eclipse project files"
find_and_remove ".classpath" "Eclipse classpath files"

# Clean AWS and deployment artifacts
echo -e "${GREEN}☁️  Cleaning AWS deployment artifacts...${NC}"
find_and_remove ".aws-sam" "AWS SAM directories" "d"
find_and_remove "samconfig.toml" "SAM configuration files"
find_and_remove ".serverless" "Serverless framework directories" "d"

# Clean test artifacts
echo -e "${GREEN}🧪 Cleaning test artifacts...${NC}"
find_and_remove ".coverage.*" "coverage data files"
find_and_remove "htmlcov" "HTML coverage directories" "d"
find_and_remove ".tox" "tox test directories" "d"
find_and_remove "junit.xml" "JUnit test result files"
find_and_remove "test-results" "test result directories" "d"

# Clean documentation build files
echo -e "${GREEN}📚 Cleaning documentation files...${NC}"
find_and_remove "_build" "Sphinx build directories" "d"
find_and_remove "docs/_build" "documentation build directories" "d"
find_and_remove ".doctrees" "Sphinx doctree directories" "d"

# Optional: Clean virtual environment (with user confirmation)
echo -e "${GREEN}🐍 Virtual environment cleanup...${NC}"
if [ -d "./.venv" ]; then
    echo -e "${YELLOW}Found Python virtual environment: .venv${NC}"
    read -p "Do you want to remove the virtual environment? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf ./.venv
        echo -e "${GREEN}  Removed: .venv${NC}"
    else
        echo -e "${BLUE}  Kept: .venv (recommended for development)${NC}"
    fi
fi

# Optional: Clean data files (with user confirmation)
echo -e "${GREEN}📊 Data files cleanup...${NC}"
if [ -d "./infra/data" ] && [ "$(ls -A ./infra/data 2>/dev/null)" ]; then
    echo -e "${YELLOW}Found data files in: ./infra/data${NC}"
    ls -la ./infra/data
    echo
    read -p "Do you want to remove data files? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        find ./infra/data -type f -name "*.csv" -delete 2>/dev/null || true
        find ./infra/data -type f -name "*.json" -delete 2>/dev/null || true
        echo -e "${GREEN}  Removed data files${NC}"
    else
        echo -e "${BLUE}  Kept data files${NC}"
    fi
fi

# Summary
echo
echo -e "${GREEN}🎉 Cleanup complete!${NC}"
echo -e "${BLUE}Summary of what was cleaned:${NC}"
echo "  • Python cache files and compiled bytecode"
echo "  • CDK generated files and build artifacts"
echo "  • Lambda layer packages and zip files"
echo "  • Build and distribution directories"
echo "  • Node.js modules and lock files"
echo "  • Log files and temporary files"
echo "  • IDE and editor configuration files"
echo "  • AWS deployment artifacts"
echo "  • Test artifacts and coverage files"
echo "  • Documentation build files"
echo
echo -e "${YELLOW}Note: Configuration files and virtual environment were preserved by default.${NC}"
echo -e "${YELLOW}Run with user confirmation to selectively remove them.${NC}"
echo
echo -e "${GREEN}Your project is now clean and ready for fresh deployment! 🚀${NC}"
