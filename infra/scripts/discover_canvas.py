#!/usr/bin/env python3
"""
Simple Canvas model and endpoint discovery script
Used by setup.sh for auto-discovery
"""

import boto3
import sys
from datetime import datetime

def discover_canvas_models():
    """Find Canvas models and return the most recent one"""
    try:
        sagemaker = boto3.client('sagemaker')
        
        # List all models
        paginator = sagemaker.get_paginator('list_models')
        models = []
        
        for page in paginator.paginate():
            models.extend(page['Models'])
        
        # Filter Canvas models
        canvas_models = [
            model for model in models 
            if 'canvas' in model['ModelName'].lower()
        ]
        
        if not canvas_models:
            return None
        
        # Sort by creation time (newest first)
        canvas_models.sort(key=lambda x: x['CreationTime'], reverse=True)
        
        # Return the most recent model name
        return canvas_models[0]['ModelName']
        
    except Exception:
        return None

def discover_canvas_endpoints():
    """Find Canvas endpoints and return the first one"""
    try:
        sagemaker = boto3.client('sagemaker')
        
        # List all endpoints
        paginator = sagemaker.get_paginator('list_endpoints')
        endpoints = []
        
        for page in paginator.paginate():
            endpoints.extend(page['Endpoints'])
        
        # Filter Canvas endpoints
        canvas_endpoints = [
            endpoint for endpoint in endpoints 
            if 'canvas' in endpoint['EndpointName'].lower()
        ]
        
        if not canvas_endpoints:
            return None
        
        # Sort by creation time (newest first)
        canvas_endpoints.sort(key=lambda x: x['CreationTime'], reverse=True)
        
        # Return the most recent endpoint name
        return canvas_endpoints[0]['EndpointName']
        
    except Exception:
        return None

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 discover_canvas.py [models|endpoints]")
        sys.exit(1)
    
    discovery_type = sys.argv[1]
    
    if discovery_type == "models":
        result = discover_canvas_models()
    elif discovery_type == "endpoints":
        result = discover_canvas_endpoints()
    else:
        print("Invalid type. Use 'models' or 'endpoints'")
        sys.exit(1)
    
    if result:
        print(result)
    else:
        sys.exit(1)  # No results found

if __name__ == "__main__":
    main()
