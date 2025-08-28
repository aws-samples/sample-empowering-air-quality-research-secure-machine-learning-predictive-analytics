# ANYCompany Air Quality ML-Driven Predictive Analytics

## Overview
This project implements a comprehensive air quality data imputation solution leveraging AWS services. The solution includes:
- Data imputation orchestration that runs every 24 hours
- Machine learning-based prediction system
- Scalable database architecture for sensor data management
- Automated deployment infrastructure

You can find the related blogpost to this repository here: [Empowering air quality research with secure, ML-driven predictive analytics](https://aws.amazon.com/blogs/machine-learning/empowering-air-quality-research-with-secure-ml-driven-predictive-analytics/)

> [!IMPORTANT]
> **_This solution is intended for experimental purposes and should not be used in production environments. Deployment will incur AWS service costs. Please follow the cleanup instructions when the resources are no longer needed._**

## System Architecture

The solution implements a comprehensive serverless architecture for air quality data imputation. 

### Architecture Documentation
- **[Architecture Overview](Architecture.png)** - Quick reference with system overview

![Architecture Overview](Architecture.png)


- **[Flow Diagram](FlowDiagram.png)** - Visual workflow representation showing data flow and process steps

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

## Prerequisites

### AWS Requirements
- Active AWS account with sufficient IAM permissions for solution deployment

### Local Development Environment
- AWS CLI (configured with appropriate credentials)
- Python 3.10+
- AWS CDK for Python
- Git

### Data Requirements
The system expects air quality dataset in CSV format with the following fields (order flexible):

```
timestamp,value,parameter,device_id,chip_id,sensor_type,sensor_id,location_id,location,street_name,city,country,latitude,longitude,deployment_date
```

**Important Notes:**
- Column order is flexible - headers are used to identify fields
- Parameter field contains air qualtiy metric (For example: PM 2.5, Temperature, Humidity, etc.)
- Timestamps must include timezone information
- GPS coordinates should be in decimal degrees format

Example Record:
```
2023-07-15 09:22:31.456 +0200,25.4,PM 2.5,24,esp8266-87654322,2,38,43,City Center,Oak Avenue,Springfield,United States,38.7823456,-92.1245678,2022-05-12 08:45:22.310 +0200
```

## Installation Guide

### Setup

**Step 1: Clone Repository**
```bash
# Clone the repository
git clone https://github.com/aws-samples/sample-empowering-air-quality-research-secure-machine-learning-predictive-analytics.git
cd sample-empowering-air-quality-research-secure-machine-learning-predictive-analytics
```

**Step 2: Setup Local Environment**
```bash
# Setup your python virtual environment and create initial config.ini
./bin/run.sh                    # Shows parameters and asks for confirmation
```

**Step 3: Add Your Data**
```bash
# You have an option to place your CSV file directly in this path (update filename in config.ini if different)
cp your-data.csv infra/data/init_data.csv
```

For large files you have an option to upload to S3 after initial deployment creates the bucket for you. Follow the instructions in the [Data File Setup](#data-file-setup).

**Step 4: Customize Configuration (Optional)**
The setup uses a configuration template that is provided with the stack:
- `infra/scripts/config.ini.default` (template with all settings)
- `infra/scripts/config.ini` (created from template on first run)

Edit the config.ini file as needed to customize your deployment.


**Note - since this is your initial cdk deploy make sure that `create_from_canvas = false` as you do not have the SageMaker Canvas model yet**

```bash
# Edit configuration settings (created from template on first run)
vim infra/scripts/config.ini
```

The run.sh script automatically:
- Sets up Python environment and dependencies
- Builds Lambda layer packages
- Bootstraps CDK and synthesizes templates
- Optionally deploys infrastructure (with `--deploy` flag)

**Step 5: Activate Python Virtual Environment**
```bash
# Ensure you are at the root directory
source .venv/bin/activate
```

**Step 6: Initial CDK Deploy**
```bash
cd infra && cdk deploy
```

### Data Upload

You have two options for providing your air quality dataset:

#### Option 1: Local File Approach
1. **Location**: Place your CSV file at `infra/data/init_data.csv` (or your configured filename)
2. **Format**: CSV with required headers (see Prerequisites section)
3. **Size**: Suitable for smaller files (<100MB)
4. **Encoding**: Use UTF-8 encoding
5. **Deploy**: Run `cdk deploy` with the file in place

#### Option 2: S3 Upload Approach (Recommended for Large Files)
1. **Deploy First**: Deploy infrastructure without local data file
2. **Upload to S3**: Upload your CSV file to the S3 bucket location `initial_dataset/`

### Initialize Database 
1. Access AWS Console → Lambda
2. Execute the DB Initialization function
3. Lambda will process the file from S3 and populate the database

### Model Setup for Batch Inference

After deploying your infrastructure and initializing the database, you need to create a SageMaker model for batch inference.

#### Create SageMaker Canvas Model

Follow the blog post instructions (Step 2) to create, train and register a SageMaker Canvas model.

#### Update SageMaker Model Configuration

In order to create a SageMaker model, you must complete the following steps. 

1. Obtain your SageMaker Model Package Group Name:
   ```bash
   aws sagemaker list-model-package-groups --query 'ModelPackageGroupSummaryList[*].ModelPackageGroupName'
   ```
2. Update infra/scripts/config.ini with SageMaker Model Configuration

```
# SageMaker Model Creation Parameters
create_from_canvas = true
canvas_model_package_group_name = <obtained-sagemaker-model-package-group-name>
canvas_model_version = <version>
```

#### Update remaining configuration (OPTIONAL)
At this time, review your remaining config.ini settings and adjust as needed before proceeding


### Re-deploy with Updated Configuration
   ```bash
   # Ensure you are at the root directory
   cd infra && cdk deploy
   ```

### Model Management Tips

- **Model Names**: Use descriptive names with dates (e.g., `air-quality-model-20241218`)
- **Model Lifecycle**: Models are free to keep, but you can delete old ones to keep things organized
- **Model Updates**: When you have a new model version, create a new SageMaker model and update the config
- **Testing**: You can test your model using the AWS Console or CLI before updating the configuration


## Cleanup

### Complete the following steps to clean up your resources

1. **SageMaker Canvas application cleanup:**
- On the go to the SageMaker AI console and select the domain that was created under Admin Configurations, and Domains
- Select the user created under User Profiles for that domain 
- On the User Details page, navigate to Spaces and Apps, and choose Delete to manually delete your Sagemaker AI canvas application and clean up resources 

2. **SageMaker Domain EFS storage cleanup:**
- Open Amazon EFS and in File systems, delete filesystem tagged as ManagedByAmazonSageMakerResource 
- Open VPC and under Security, navigate to Security groups 
- On Security groups, select `security-group-for-inbound-nfs-<your-sagemaker-domain-id>` and delete all Inbound rules associated with that group
- On Security groups, select `security-group-for-outbound-nfs-<your-sagemaker-domain-id>` and delete all associated Outbound rules
- Finally, delete both the security groups: `security-group-for-inbound-nfs-<your-sagemaker-domain-id>` and `security-group-for-outbound-nfs-<your-sagemaker-domain-id>`

3. **Use the AWS CDK to clean up the remaining AWS resources:**
- After the preceding steps are complete, return to your local desktop environment where the GitHub repo was cloned, and change to the project’s infra directory: `$ cd <BASE_PROJECT_FOLDER>/infra` 
- Destroy the resources created with AWS CloudFormation using the AWS CDK: `$ cdk destroy` 
- Monitor the AWS CDK process deleting resources created by the solution
- If there are any errors, troubleshoot using the CloudFormation console and then retry deletion

## Troubleshooting

### Common Issues

**run.sh Script Issues:**
- Configuration template must be present in `infra/scripts/` directory
- The script requires `config.ini.default` file and creates `config.ini` from it
- To modify parameters, edit the `config.ini` file and re-run the script
- Use `./bin/run.sh --use-defaults` for non-interactive setup

**CDK Deployment Errors:**
- Ensure AWS credentials are configured: `aws configure`
- Check you're in the correct directory: `cd infra`
- Verify CDK is bootstrapped in your region

**Data File Issues:**
- Verify file exists at `infra/data/init_data.csv`
- Check CSV format matches required headers
- Ensure UTF-8 encoding and timezone in timestamps

### Getting Help
- Check CloudWatch logs for Lambda function errors
- Review CDK synthesis output for configuration issues
- Use `./bin/run.sh --help` for setup options
