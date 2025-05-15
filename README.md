```markdown
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
The solution utilizes the following AWS services:
- Amazon SageMaker AI for machine learning operations
- AWS Step Functions for workflow orchestration
- AWS Lambda for serverless computing
- Amazon S3 for data storage
- Amazon RDS Aurora PostgreSQL for relational database management
- Amazon CloudWatch for monitoring
- AWS CloudFormation for infrastructure deployment
- AWS IAM for security management
- Amazon EventBridge for event handling
- AWS Secrets Manager for secure credentials management
- Amazon VPC for network isolation

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
   
   $ git clone https://gitlab.aws.dev/airquality-hackathon-2023-banyantree/sensorsafrica_blog_code.git
   $ cd sensorsafrica_blog_code


2. Run the setup script from the project's root folder:

   $ ./bin/setup.sh


   This script will:
   - Create and activate a virtual environment
   - Install required dependencies
   - Create pre and post configs with default values
   - Prepare Lambda layer packages
   - Bootstrap the AWS CDK stack
   - Synthesize the AWS CDK stack

3. Activate virtual environment:

   $ source .venv/bin/activate


## Copy Initial Air Quality Dataset

1. Navigate to the `infra/data` directory:

   $ cd infra/data


2. Copy your initial air quality dataset in the CSV format to upload to S3 bucket provided by our sample solution as part of the CDK deployment.

3. Return to project's root folder.

   $ cd ../..


## Pre-Deployment Configuration

1. Navigate to the `infra/scripts` directory:

   $ cd infra/scripts


2. Run the pre-deployment configuration script:

   $ python3 config.py --pre --interactive


   This will prompt you for below pre-deployment configuration options:
   - Project prefix name
   - Filename of your air quality dataset csv

3. Return to project's root folder.

   $ cd ../..


## Infrastructure Installation

1. Deploy the infrastructure:

   $ cd infra
   $ cdk deploy

   This will install AWS resources required for our solution.

2. Return to project's root folder.

   $ cd ..


## Air Quality Database Initialization

1. Access AWS Console
2. Navigate to Lambda
2. Execute DB Initialization funtion

## SageMaker Canvas Configuration

Refer to our AWS Blog to complete below steps.
1. Configure Canvas App in SageMaker Domain
2. Train and deploy model
3. Record model endpoint name

## Post-Deployment Configuration

1. Navigate to the `infra/scripts` directory:

   $ cd infra/scripts


2. Run the post-deployment configuration script:

   $ python3 config.py --post --interactive


   This will prompt you for below post-deployment configuration options:
   - Canvas model endpoint name

3. Return to project's root folder.

   $ cd ../..


## Infrastructure Update

1. Deploy the updated infrastructure:

   $ cd infra
   $ cdk deploy


2. Return to project's root folder.

   $ cd ../..



## Cleanup

To prevent ongoing charges, refer to our AWS Blog to complete Cleanup steps.
