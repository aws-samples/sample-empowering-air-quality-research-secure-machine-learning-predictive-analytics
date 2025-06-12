# ANYCompany Air Quality Monitoring System

## Overview
This project implements a comprehensive air quality monitoring and prediction system leveraging AWS services. The solution includes:
- Data processing orchestration that runs every 24 hour
- Machine learning-based prediction system
- Scalable database architecture for sensor data management
- Automated deployment infrastructure

> [!IMPORTANT]
> **_This solution is intended for experimental purposes and should not be used in production environments. Deployment will incur AWS service costs. Please follow the cleanup instructions when the resources are no longer needed._**

## System Architecture

The solution implements a comprehensive serverless architecture for air quality monitoring and prediction. 

### Architecture Documentation
- **[Architecture Diagram](ARCHITECTURE_DIAGRAM.md)** - Comprehensive technical documentation with interactive Mermaid diagrams
- **[Flow Diagram](FlowDiagram.png)** - Visual workflow representation showing data flow and process steps
- **[Architecture Overview](architecture_diagram.md)** - Quick reference with system overview

![Flow Diagram](FlowDiagram.png)

### Core AWS Services:
- **Amazon SageMaker AI** for machine learning operations and Canvas model endpoints
- **AWS Step Functions** for workflow orchestration and data processing pipeline
- **AWS Lambda** for serverless computing and data processing functions
- **Amazon S3** for scalable data storage with organized prefixes for different data stages
- **Amazon RDS Aurora PostgreSQL** for relational database management and sensor data storage
- **Amazon EventBridge Scheduler** for automated 24-hour interval processing
- **Amazon CloudWatch** for comprehensive monitoring and logging
- **AWS CloudFormation/CDK** for infrastructure as code deployment
- **AWS IAM** for fine-grained security and access management
- **AWS Secrets Manager** for secure database credentials management
- **Amazon VPC** for network isolation and security
- **AWS Systems Manager Parameter Store** for job metadata and configuration

### Key Architectural Features:
- **Configurable Parameter Selection**: Choose between PM 2.5, PM 10, or PM 1 for targeted predictions
- **Serverless Design**: Scales automatically based on demand, cost-effective
- **Batch Processing**: Efficient handling of large datasets through SageMaker Batch Transform
- **Fault Tolerance**: Built-in retry logic and error handling via Step Functions
- **Security First**: All data encrypted at rest and in transit, least privilege access
- **Comprehensive Monitoring**: Full observability through CloudWatch logs and metrics

## Prerequisites

### AWS Requirements
- Active AWS account with administrative privileges
- Appropriate IAM permissions for service deployment
- Selected AWS region for deployment

### Local Development Environment
- AWS CLI (configured with appropriate credentials)
- Python 3.10+
- AWS CDK for Python
- Git

### Data Requirements
The system expects air quality data in CSV format with the following schema:

timestamp,value,parameter,device_id,chip_id,sensor_type,sensor_id,location_id,location,street_name,city,country,latitude,longitude,deployment_date

Example Record:

2023-07-15 09:22:31.456 +0200,42187,Temperature,23,esp8266-87654321,1,37,42,ABC University,Main Street,Springfield,United States,38.7812345,-92.1234567,2022-05-12 08:45:22.310 +0200


## Installation Guide

1. Clone the repository:
   
   ```bash
   git clone https://github.com/aws-samples/sample-empowering-air-quality-research-secure-machine-learning-predictive-analytics.git
   cd sample-empowering-air-quality-research-secure-machine-learning-predictive-analytics
   ```

2. Run the setup script from the project's root folder:

   ```bash
   ./bin/setup.sh
   ```

   This script will:
   - Create and activate a virtual environment
   - Install required dependencies
   - Create pre and post configs with default values
   - Prepare Lambda layer packages
   - Bootstrap the AWS CDK stack
   - Synthesize the AWS CDK stack

3. Activate virtual environment:

   ```bash
   source .venv/bin/activate
   ```

## Copy Initial Air Quality Dataset

1. Navigate to the `infra/data` directory:

   ```bash
   cd infra/data
   ```

2. Copy your initial air quality dataset in CSV format to this directory. The system expects data with the following schema:

   ```
   timestamp,value,parameter,device_id,chip_id,sensor_type,sensor_id,location_id,location,street_name,city,country,latitude,longitude,deployment_date
   ```

   Example record:
   ```
   2023-07-15 09:22:31.456 +0200,42187,Temperature,23,esp8266-87654321,1,37,42,ABC University,Main Street,Springfield,United States,38.7812345,-92.1234567,2022-05-12 08:45:22.310 +0200
   ```

   **Note**: The system uploads the file in CSV format to S3 bucket provided by our sample solution as part of the CDK deployment.

3. Return to project's root folder:

   ```bash
   cd ../..
   ```

## Pre-Deployment Configuration

1. Navigate to the `infra/scripts` directory:

   ```bash
   cd infra/scripts
   ```

2. Run the pre-deployment configuration script:

   ```bash
   python3 config.py --pre --interactive
   ```

   This will prompt you for the following pre-deployment configuration options:
   - **Project prefix name**: Used for resource naming (default: "demoapp")
   - **Initial data filename**: Name of your air quality dataset CSV file (default: "init_data.csv")
   - **Air quality parameter**: Choose from PM 10, PM 1, or PM 2.5 for targeted predictions (default: "PM 2.5")

3. Return to project's root folder:

   ```bash
   cd ../..
   ```

## Infrastructure Installation

1. Deploy the infrastructure:

   ```bash
   cd infra
   cdk deploy
   ```

   This will install AWS resources required for our solution.

2. Return to project's root folder.

   ```bash
   cd ..
   ```


## Air Quality Database Initialization

1. Access AWS Console
2. Navigate to Lambda
3. Execute DB Initialization function

## SageMaker Canvas Configuration

Refer to our AWS Blog to complete the following steps:
1. Configure Canvas App in SageMaker Domain
2. Train and deploy model
3. Record model endpoint name

### Finding Your Canvas Model Details

To help you find your Canvas model ID and endpoint name, use the provided discovery script:

```bash
cd infra/scripts
./find-canvas-models.sh
```

This script will:
- List all Canvas models in your AWS account
- Show Canvas endpoints and their status
- Display creation dates and other helpful information

**Alternative usage:**
```bash
# Show detailed information
./find-canvas-models.sh --verbose

# Search in a specific region
./find-canvas-models.sh --region us-west-2

# Get JSON output for automation
./find-canvas-models.sh --json

# Show all models (not just Canvas)
python3 list_sagemaker_models.py
```

## Post-Deployment Configuration

1. Navigate to the `infra/scripts` directory:

   ```bash
   cd infra/scripts
   ```

2. Run the post-deployment configuration script:

   ```bash
   python3 config.py --post --interactive
   ```

   This will prompt you for the following post-deployment configuration options:
   - **Canvas model endpoint name**: SageMaker Canvas Model Endpoint Name (default: "canvas-demo-deployment")
   - **Canvas model ID**: SageMaker Canvas Model ID (e.g., "canvas-aq-model-12345678901234")

3. Return to project's root folder.

   ```bash
   cd ../..
   ```

## Infrastructure Update

1. Deploy the updated infrastructure:

   ```bash
   cd infra
   cdk deploy
   ```

2. Return to project's root folder.

   ```bash
   cd ../..
   ```

## Cleanup

To prevent ongoing charges, refer to our AWS Blog to complete Cleanup steps.
