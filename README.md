# ANYCompany_blog_code

This project implements an air quality monitoring and prediction system using AWS services. It includes a data processing pipeline, machine learning inference, and a database for storing air quality sensor data.


> [!WARNING]
>**_This example is for experimental purposes only and is not production ready. The deployment of this sample **can incur costs**. Please ensure to remove infrastructure via the provided instructions at the end when not needed anymore._**


## Prerequisites

- Python 3.10 or later
- AWS CLI configured with appropriate credentials
- AWS CDK CLI

## Getting Started

To set up the project, follow these steps:

1. Clone the repository:
   ```
   $ git clone https://github.com/aws-samples/sample-empowering-air-quality-research-serverless-machine-learning-predictive-analytics.git
   $ cd sample-empowering-air-quality-research-serverless-machine-learning-predictive-analytics
   ```

2. Run the setup script:
   ```
   $ ./bin/setup.sh
   ```

   This script will:
   - Create and activate a virtual environment
   - Install required dependencies
   - Prepare Lambda layer packages
   - Configure the project using default values
   - Bootstrap the AWS CDK stack
   - Synthesize the AWS CDK stack

3. Activate virtual environment:
   ```
   $ source .venv/bin/activate
   ```


## Configuration

To customize the project configuration:

1. Navigate to the `infra/scripts` directory:
   ```
   $ cd infra/scripts
   ```

2. Run the configuration script:
   ```
   $ python3 config.py --interactive
   ```

   This will prompt you for various configuration options, including:
   - Environment (e.g., DEV, PROD)
   - Lambda log levels
   - Database settings
   - S3 bucket prefixes
   - And more

   You can also use `--use-defaults` to use default values without interaction.

## Project Structure

- `infra/`: Contains the CDK stack definition and Lambda functions
- `bin/`: Contains setup and utility scripts
- `infra/lambdas/`: Contains Lambda function code
- `infra/cdk_stack/`: Contains the main CDK stack definition

## Usage

After setting up and configuring the project:

1. To deploy the stack:
   ```
   $ cd infra
   $ cdk deploy
   ```

2. To make changes to the stack:
   - Modify the relevant files in the `infra/` directory
   - Run `cdk synth` to see the changes
   - Run `cdk deploy` to apply the changes

## NOTES
Make sure your database has a predicted_label column:
ALTER TABLE table_name \
ADD COLUMN predicted_label BOOLEAN DEFAULT false;

How to connect to the pgsql instance:

psql -h airqualitystack-aurorapostgresae2c8b71-skzjptoh0fsm.c6mrfjdjcek2.us-east-1.rds.amazonaws.com p 5432 -U postgres -d aqdata

## References and License

This project is provided as an experimental example and is not intended for production use. It is designed to demonstrate air quality monitoring and prediction using AWS services.

The code in this repository is provided "as-is" without any explicit license. Users are encouraged to review any accompanying documentation or contact the project maintainers for specific licensing information.

Please note that this project may use various AWS services and third-party libraries, each of which may have its own licensing terms. Users are responsible for ensuring compliance with all applicable licenses and terms of service when using or deploying this project.

For the most up-to-date information on licensing and usage rights, please refer to the project's official documentation or contact the project maintainers.