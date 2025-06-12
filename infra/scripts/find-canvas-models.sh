#!/bin/bash

# Simple wrapper script to find Canvas models and endpoints
# Usage: ./find-canvas-models.sh [options]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/list_sagemaker_models.py"

echo "🎯 Canvas Model Discovery Tool"
echo "=============================="
echo

# Check if Python script exists
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "❌ Error: Python script not found at $PYTHON_SCRIPT"
    exit 1
fi

# Default to showing Canvas models only
if [ $# -eq 0 ]; then
    echo "🔍 Finding Canvas models in your AWS account..."
    echo
    python3 "$PYTHON_SCRIPT" --canvas-only
    echo
    echo "🎯 Finding Canvas endpoints in your AWS account..."
    echo
    python3 "$PYTHON_SCRIPT" --endpoints
else
    # Pass all arguments to the Python script
    python3 "$PYTHON_SCRIPT" "$@"
fi

echo
echo "💡 Quick Commands:"
echo "   ./find-canvas-models.sh                    # Find Canvas models and endpoints"
echo "   ./find-canvas-models.sh --verbose          # Show detailed information"
echo "   ./find-canvas-models.sh --region us-west-2 # Search in specific region"
echo "   ./find-canvas-models.sh --json             # JSON output"
