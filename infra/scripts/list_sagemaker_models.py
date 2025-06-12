#!/usr/bin/env python3
"""
Script to list all SageMaker models in the current AWS account.
This helps identify Canvas model IDs for configuration.
"""

import boto3
import json
from datetime import datetime
from botocore.exceptions import ClientError, NoCredentialsError
import argparse
import sys

def get_aws_region():
    """Get the current AWS region from various sources"""
    try:
        # Try to get from session
        session = boto3.Session()
        region = session.region_name
        if region:
            return region
    except:
        pass
    
    # Default to us-east-1 if not found
    return 'us-east-1'

def list_sagemaker_models(region=None, filter_canvas=False, verbose=False):
    """
    List all SageMaker models in the account
    
    Args:
        region (str): AWS region to query (default: current session region)
        filter_canvas (bool): Only show Canvas models (names containing 'canvas')
        verbose (bool): Show detailed model information
    
    Returns:
        list: List of model information dictionaries
    """
    if not region:
        region = get_aws_region()
    
    try:
        # Create SageMaker client
        sagemaker_client = boto3.client('sagemaker', region_name=region)
        
        print(f"🔍 Searching for SageMaker models in region: {region}")
        print("=" * 60)
        
        # List all models
        paginator = sagemaker_client.get_paginator('list_models')
        models = []
        
        for page in paginator.paginate():
            models.extend(page['Models'])
        
        if not models:
            print("❌ No SageMaker models found in this account/region.")
            return []
        
        # Filter Canvas models if requested
        if filter_canvas:
            models = [model for model in models if 'canvas' in model['ModelName'].lower()]
            if not models:
                print("❌ No Canvas models found in this account/region.")
                return []
        
        print(f"✅ Found {len(models)} model(s)")
        print()
        
        # Sort by creation time (newest first)
        models.sort(key=lambda x: x['CreationTime'], reverse=True)
        
        model_info = []
        
        for i, model in enumerate(models, 1):
            model_name = model['ModelName']
            creation_time = model['CreationTime'].strftime('%Y-%m-%d %H:%M:%S UTC')
            
            print(f"📋 Model {i}:")
            print(f"   Name: {model_name}")
            print(f"   Created: {creation_time}")
            
            if verbose:
                try:
                    # Get detailed model information
                    model_details = sagemaker_client.describe_model(ModelName=model_name)
                    
                    print(f"   ARN: {model_details.get('ModelArn', 'N/A')}")
                    print(f"   Execution Role: {model_details.get('ExecutionRoleArn', 'N/A')}")
                    
                    # Show primary container info if available
                    if 'PrimaryContainer' in model_details:
                        container = model_details['PrimaryContainer']
                        print(f"   Image: {container.get('Image', 'N/A')}")
                        if 'ModelDataUrl' in container:
                            print(f"   Model Data: {container['ModelDataUrl']}")
                    
                    # Show containers info if available
                    if 'Containers' in model_details:
                        print(f"   Containers: {len(model_details['Containers'])} container(s)")
                
                except ClientError as e:
                    print(f"   ⚠️  Could not get detailed info: {e.response['Error']['Message']}")
            
            print()
            
            # Store model info
            model_info.append({
                'name': model_name,
                'creation_time': creation_time,
                'is_canvas': 'canvas' in model_name.lower()
            })
        
        return model_info
        
    except NoCredentialsError:
        print("❌ AWS credentials not found. Please configure your AWS credentials.")
        print("   Run: aws configure")
        return []
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        print(f"❌ AWS Error ({error_code}): {error_message}")
        return []
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return []

def list_canvas_endpoints(region=None):
    """
    List Canvas model endpoints
    
    Args:
        region (str): AWS region to query
    
    Returns:
        list: List of endpoint information
    """
    if not region:
        region = get_aws_region()
    
    try:
        sagemaker_client = boto3.client('sagemaker', region_name=region)
        
        print(f"🔍 Searching for SageMaker endpoints in region: {region}")
        print("=" * 60)
        
        # List all endpoints
        paginator = sagemaker_client.get_paginator('list_endpoints')
        endpoints = []
        
        for page in paginator.paginate():
            endpoints.extend(page['Endpoints'])
        
        if not endpoints:
            print("❌ No SageMaker endpoints found in this account/region.")
            return []
        
        # Filter Canvas endpoints
        canvas_endpoints = [ep for ep in endpoints if 'canvas' in ep['EndpointName'].lower()]
        
        if not canvas_endpoints:
            print("❌ No Canvas endpoints found in this account/region.")
            return []
        
        print(f"✅ Found {len(canvas_endpoints)} Canvas endpoint(s)")
        print()
        
        # Sort by creation time (newest first)
        canvas_endpoints.sort(key=lambda x: x['CreationTime'], reverse=True)
        
        endpoint_info = []
        
        for i, endpoint in enumerate(canvas_endpoints, 1):
            endpoint_name = endpoint['EndpointName']
            status = endpoint['EndpointStatus']
            creation_time = endpoint['CreationTime'].strftime('%Y-%m-%d %H:%M:%S UTC')
            
            print(f"🎯 Endpoint {i}:")
            print(f"   Name: {endpoint_name}")
            print(f"   Status: {status}")
            print(f"   Created: {creation_time}")
            print()
            
            endpoint_info.append({
                'name': endpoint_name,
                'status': status,
                'creation_time': creation_time
            })
        
        return endpoint_info
        
    except Exception as e:
        print(f"❌ Error listing endpoints: {str(e)}")
        return []

def main():
    parser = argparse.ArgumentParser(
        description="List SageMaker models and endpoints in your AWS account",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 list_sagemaker_models.py                    # List all models
  python3 list_sagemaker_models.py --canvas-only      # List only Canvas models
  python3 list_sagemaker_models.py --verbose          # Show detailed information
  python3 list_sagemaker_models.py --endpoints        # List Canvas endpoints
  python3 list_sagemaker_models.py --region us-west-2 # Specify region
        """
    )
    
    parser.add_argument(
        '--region', 
        help='AWS region to query (default: current session region)',
        default=None
    )
    
    parser.add_argument(
        '--canvas-only', 
        action='store_true',
        help='Only show Canvas models (names containing "canvas")'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show detailed model information'
    )
    
    parser.add_argument(
        '--endpoints', '-e',
        action='store_true',
        help='List Canvas endpoints instead of models'
    )
    
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results in JSON format'
    )
    
    args = parser.parse_args()
    
    # Determine region
    region = args.region or get_aws_region()
    
    print("🚀 SageMaker Model Discovery Tool")
    print(f"📍 Region: {region}")
    print(f"🕐 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    if args.endpoints:
        # List endpoints
        results = list_canvas_endpoints(region)
        
        if args.json and results:
            print("\n📄 JSON Output:")
            print(json.dumps(results, indent=2))
    else:
        # List models
        results = list_sagemaker_models(
            region=region,
            filter_canvas=args.canvas_only,
            verbose=args.verbose
        )
        
        if args.json and results:
            print("\n📄 JSON Output:")
            print(json.dumps(results, indent=2))
    
    # Provide helpful guidance
    if results:
        print("💡 Usage Tips:")
        if not args.endpoints:
            print("   • Copy the model name for your Canvas model configuration")
            print("   • Canvas models typically have names like 'canvas-aq-model-1234567890123'")
        else:
            print("   • Copy the endpoint name for your Canvas endpoint configuration")
        print("   • Use --verbose flag for more detailed information")
        print("   • Use --json flag to get machine-readable output")
    else:
        print("💡 Next Steps:")
        print("   • Make sure you have trained and deployed a Canvas model")
        print("   • Check if you're looking in the correct AWS region")
        print("   • Verify your AWS credentials have SageMaker permissions")
    
    return 0 if results else 1

if __name__ == "__main__":
    sys.exit(main())
