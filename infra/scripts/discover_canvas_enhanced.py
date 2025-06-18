#!/usr/bin/env python3
"""
Enhanced Canvas model and model package discovery script
Finds both regular SageMaker models and model packages
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
            if 'canvas' in model['ModelName'].lower() or 'aq' in model['ModelName'].lower()
        ]
        
        if not canvas_models:
            return None
        
        # Sort by creation time (newest first)
        canvas_models.sort(key=lambda x: x['CreationTime'], reverse=True)
        
        # Return the most recent model name
        return canvas_models[0]['ModelName']
        
    except Exception:
        return None

def discover_canvas_model_packages():
    """Find Canvas model packages and return information about them"""
    try:
        sagemaker = boto3.client('sagemaker')
        
        # List all model package groups
        response = sagemaker.list_model_package_groups()
        model_packages = []
        
        for group in response['ModelPackageGroupSummaryList']:
            group_name = group['ModelPackageGroupName']
            
            # Check if it's a Canvas-related group
            if any(keyword in group_name.lower() for keyword in ['canvas', 'aq', 'air', 'quality']):
                # Get model packages in this group
                packages_response = sagemaker.list_model_packages(
                    ModelPackageGroupName=group_name
                )
                
                for package in packages_response['ModelPackageSummaryList']:
                    model_packages.append({
                        'GroupName': group_name,
                        'Version': package['ModelPackageVersion'],
                        'Arn': package['ModelPackageArn'],
                        'CreationTime': package['CreationTime'],
                        'Status': package['ModelPackageStatus']
                    })
        
        if not model_packages:
            return None
        
        # Sort by creation time (newest first)
        model_packages.sort(key=lambda x: x['CreationTime'], reverse=True)
        
        return model_packages
        
    except Exception:
        return None

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 discover_canvas_enhanced.py [models|packages|all]")
        sys.exit(1)
    
    discovery_type = sys.argv[1]
    
    if discovery_type == "models":
        result = discover_canvas_models()
        if result:
            print(result)
        else:
            sys.exit(1)
    
    elif discovery_type == "packages":
        result = discover_canvas_model_packages()
        if result:
            # Print the most recent package ARN
            print(result[0]['Arn'])
        else:
            sys.exit(1)
    
    elif discovery_type == "all":
        print("=== Canvas Models ===")
        models = discover_canvas_models()
        if models:
            print(f"Most recent model: {models}")
        else:
            print("No Canvas models found")
        
        print("\n=== Canvas Model Packages ===")
        packages = discover_canvas_model_packages()
        if packages:
            for pkg in packages:
                print(f"Group: {pkg['GroupName']}, Version: {pkg['Version']}")
                print(f"ARN: {pkg['Arn']}")
                print(f"Created: {pkg['CreationTime']}")
                print(f"Status: {pkg['Status']}")
                print("-" * 50)
        else:
            print("No Canvas model packages found")
    
    else:
        print("Invalid type. Use 'models', 'packages', or 'all'")
        sys.exit(1)

if __name__ == "__main__":
    main()
