#!/usr/bin/env python3
import subprocess
import os
import re

def get_latest_version(package_name):
    try:
        result = subprocess.run(
            ["pip", "index", "versions", package_name],
            capture_output=True,
            text=True,
            check=True
        )
        output = result.stdout
        
        # Extract the latest version
        match = re.search(r"Available versions: ([\d\.]+)", output)
        if match:
            return match.group(1)
        return None
    except subprocess.CalledProcessError:
        print(f"Error getting latest version for {package_name}")
        return None

def update_requirements_file(file_path):
    print(f"Updating {file_path}...")
    with open(file_path, 'r') as f:
        requirements = f.readlines()
    
    updated_requirements = []
    for req in requirements:
        req = req.strip()
        if not req or req.startswith('#'):
            updated_requirements.append(req)
            continue
        
        # Handle complex requirements with version specifiers
        if '>=' in req and '<' in req:
            # For constructs>=10.0.0,<11.0.0 type of requirements
            package_name = req.split('>=')[0].strip()
            version_constraint = req.split('>=')[1].strip()
            updated_requirements.append(f"{package_name}>={version_constraint}")
            continue
            
        # Handle simple requirements with version pins
        if '==' in req:
            package_name = req.split('==')[0].strip()
            latest_version = get_latest_version(package_name)
            if latest_version:
                updated_requirements.append(f"{package_name}=={latest_version}")
            else:
                updated_requirements.append(req)
        else:
            updated_requirements.append(req)
    
    # Write updated requirements back to file
    with open(file_path, 'w') as f:
        f.write('\n'.join(updated_requirements) + '\n')
    
    print(f"Updated {file_path}")

# List of requirements files to update
requirements_files = [
    "./infra/requirements.txt",
    "./infra/lambdas/requirements.txt",
    "./infra/lambdas/common/requirements.txt",
    "./lambda_layer/common/python/requirements.txt"
]

for req_file in requirements_files:
    if os.path.exists(req_file):
        update_requirements_file(req_file)
    else:
        print(f"File not found: {req_file}")
