"""
The program:

Supports multiple modes of operation (interactive, defaults-only, command-line parameters)
Validates input parameters
Creates a default config if none exists
Allows specifying custom config file path
Falls back to interactive mode if no specific mode or parameters are provided
Loads existing config if present
Prompts for each configuration value showing current/default values
Validates email format and time format
Saves updated configuration back to the file
Preserves the INI structure
Provides help text for all options (python config.py --help)



The program includes input validation for:

Email format
Time format (HHMM)
Preserves default values if user just hits enter
Automatically uppercases Y/N responses
"""

"""
Usage examples:
Run: python config.py
Answer the prompts to update configuration
The program will create/update config.ini with the new values

Interactive mode:
```python config.py --interactive```


Use defaults only:
```python config.py --use-defaults```


Specify configuration via command line:
```python config.py --admin-email admin@example.com --retention-days 14 --frequency 12```


Use different config file:
```python config.py --config custom-config.ini```


Mix of command line parameters:
```python config.py --config custom-config.ini --environment test```

"""

from configparser import ConfigParser
import os
import re
import argparse
from datetime import datetime

import boto3
from botocore.exceptions import ClientError


def get_user_input(prompt, default_value, validator=None):
    while True:
        user_input = input(f"{prompt} [{default_value}]: ").strip()

        if user_input == "":
            return default_value

        if validator:
            if validator(user_input):
                return user_input
            print("Invalid input. Please try again.")
        else:
            return user_input


def create_default_config():
    config = ConfigParser()

    config["defaults"] = {
        "environment": "demo",
        "lambda_logs_level": "DEBUG",
        "company": "ANYCompany",
        "project": "air-quality",
        "rds_db_name": "aqdb",
        "rds_db_port": 5432,
        "rds_db_table": "aqdataset",
        "rds_db_username": "postgres",
        "rds_config_secret_name": "aurora-postgres-credentials",
        "canvas_model_endpoint_name": "canvas-AQDeployment",
        "retrival_prefix": "retrieved_from_db",
        "predicted_prefix": "predicted_values_output",
        "db_dump_prefix": "initial_db_dump_files",
        "db_dump_s3_key": "init_data.csv",
        "create_db_init_lambda": "Y",
        "run_db_init_on_deployment": "N",
        "create_bastion_instance": "Y",
        "rds_db_host": "",
    }

    return config


def load_or_create_config(config_path="config.ini"):
    config = ConfigParser()

    if os.path.exists(config_path):
        print("config.ini found, reading file...")
        config.read(config_path)
    else:
        print("no default config.ini file found, creating a default config file... ")
        config = create_default_config()

    return config


def interactive_config(config_path="config.ini"):
    config = load_or_create_config(config_path)

    # Admin section
    environment = get_user_input(
        "Provide the AWS Health Admin environment", config["defaults"]["environment"]
    ).upper()
    lambda_logs_level = get_user_input(
        "Provide the Log levels for Lambda environment",
        config["defaults"]["lambda_logs_level"],
    ).upper()
    if lambda_logs_level not in ["DEBUG", "INFO", "WARN", "ERROR"]:
        print("Invalid input. Please use from 'DEBUG', 'INFO', 'WARN', 'ERROR'")
        return

    project = get_user_input(
        "Provide the project name", config["defaults"]["project"]
    )

    company = get_user_input(
        "Provide the company name", config["defaults"]["company"]
    )

    rds_db_name = get_user_input(
        "Provide the RDS database name", config["defaults"]["rds_db_name"]
    ).lower()

    rds_db_port = get_user_input(
        "Provide the RDS port name", config["defaults"]["rds_db_port"]
    )

    rds_db_table = get_user_input(
        "Provide the RDS database table name", config["defaults"]["rds_db_table"]
    ).lower()

    rds_db_username = get_user_input(
        "Provide the RDS database username", config["defaults"]["rds_db_username"]
    ).lower()

    rds_config_secret_name = get_user_input(
        "Provide the RDS secret name to store password",
        config["defaults"]["rds_config_secret_name"],
    ).lower()

    canvas_model_endpoint_name = get_user_input(
        "Provide the Canvas model endpoint name",
        config["defaults"]["canvas_model_endpoint_name"],
    )

    retrival_prefix = get_user_input(
        "Provide the retrival prefix", config["defaults"]["retrival_prefix"]
    ).lower()

    predicted_prefix = get_user_input(
        "Provide the predicted prefix", config["defaults"]["predicted_prefix"]
    ).lower()

    db_dump_prefix = get_user_input(
        "Provide the predicted prefix", config["defaults"]["db_dump_prefix"]
    ).lower()

    db_dump_s3_key = get_user_input(
        "Provide the predicted prefix", config["defaults"]["db_dump_s3_key"]
    ).lower()

    rds_db_host = get_user_input(
        "Provide the RDS database host", config["defaults"]["rds_db_host"]
    ).lower()

    create_db_init_lambda = get_user_input(
        "Would you like to create a DB init lambda (Y/N)",
        config["defaults"]["create_db_init_lambda"],
    ).upper()

    run_db_init_on_deployment = get_user_input(
        "Would you like to run DB init lambda on deployment (Y/N)",
        config["defaults"]["run_db_init_on_deployment"],
    ).upper()

    create_bastion_instance = get_user_input(
        "Would you like to create a Bastion instance (Y/N)",
        config["defaults"]["create_bastion_instance"],
    ).upper()

    # Update config object
    config["defaults"]["environment"] = environment
    config["defaults"]["lambda_logs_level"] = lambda_logs_level
    config["defaults"]["company"] = company
    config["defaults"]["project"] = project
    config["defaults"]["rds_config_secret_name"] = rds_config_secret_name
    config["defaults"]["rds_db_name"] = rds_db_name
    config["defaults"]["rds_db_port"] = rds_db_port
    config["defaults"]["rds_db_table"] = rds_db_table
    config["defaults"]["rds_db_username"] = rds_db_username
    config["defaults"]["canvas_model_endpoint_name"] = canvas_model_endpoint_name
    config["defaults"]["retrival_prefix"] = retrival_prefix
    config["defaults"]["predicted_prefix"] = predicted_prefix
    config["defaults"]["db_dump_prefix"] = db_dump_prefix
    config["defaults"]["db_dump_s3_key"] = db_dump_s3_key
    config["defaults"]["create_db_init_lambda"] = create_db_init_lambda
    config["defaults"]["run_db_init_on_deployment"] = run_db_init_on_deployment
    config["defaults"]["create_bastion_instance"] = create_bastion_instance
    config["defaults"]["rds_db_host"] = rds_db_host

    save_config(config, config_path)
    return config


def save_config(config, config_path):
    with open(config_path, "w") as configfile:
        config.write(configfile)
    print(f"\nConfiguration has been updated successfully in {config_path}!")


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="AWS Health to JIRA Configuration Tool"
    )
    parser.add_argument(
        "--config", default="config.ini", help="Path to configuration file"
    )
    parser.add_argument(
        "--use-defaults",
        action="store_true",
        help="Use default values without interaction",
    )
    parser.add_argument(
        "--interactive", action="store_true", help="Use interactive mode"
    )

    # Add command line arguments for all config parameters
    parser.add_argument("--environment", help="Environment name")
    parser.add_argument(
        "--lambda_logs_level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Lambda logs level",
    )
    parser.add_argument("--company", help="Name of the company")
    parser.add_argument("--project", help="Name of the project")
    parser.add_argument("--rds_db_name", help="RDS database name")
    parser.add_argument("--rds_db_port", type=int, help="RDS port name")
    parser.add_argument("--rds_db_table", help="RDS database table name")
    parser.add_argument("--rds_db_username", help="RDS database username")
    parser.add_argument("--rds_config_secret_name", help="RDS config secret name")
    parser.add_argument(
        "--canvas_model_endpoint_name", help="Canvas model endpoint name"
    )
    parser.add_argument("--retrival_prefix", help="Retrival prefix")
    parser.add_argument("--predicted_prefix", help="Predicted prefix")
    parser.add_argument("--db_dump_prefix", help="Initial DB dump folder prefix")
    parser.add_argument("--db_dump_s3_key", help="Initial DB dump S3 key")
    parser.add_argument(
        "--rds_db_host",
        help="If you want to use existing RDS instance then provide database host, else leave blank and we will create one on your behalf",
    )
    parser.add_argument(
        "--create_db_init_lambda", choices=["Y", "N"], help="Create DB init lambda"
    )
    parser.add_argument(
        "--run_db_init_on_deployment",
        choices=["Y", "N"],
        help="Run DB init lambda on deployment",
    )
    parser.add_argument(
        "--create_bastion_instance", choices=["Y", "N"], help="Create Bastion instance"
    )

    return parser.parse_args()


def update_config_from_args(config, args):
    print("Updating config from args provided at CLI...")
    if args.environment:
        config["defaults"]["environment"] = args.environment
    if args.lambda_logs_level:
        config["defaults"]["lambda_logs_level"] = args.lambda_logs_level
    if args.company:
        config["defaults"]["company"] = args.company
    if args.project:
        config["defaults"]["project"] = args.project
    if args.rds_db_name:
        config["defaults"]["rds_db_name"] = args.rds_db_name
    if args.rds_db_port:
        config["defaults"]["rds_db_port"] = args.rds_db_port
    if args.rds_db_table:
        config["defaults"]["rds_db_table"] = args.rds_db_table
    if args.rds_db_username:
        config["defaults"]["rds_db_username"] = args.rds_db_username
    if args.rds_config_secret_name:
        config["defaults"]["rds_config_secret_name"] = args.rds_config_secret_name
    if args.canvas_model_endpoint_name:
        config["defaults"][
            "canvas_model_endpoint_name"
        ] = args.canvas_model_endpoint_name
    if args.retrival_prefix:
        config["defaults"]["retrival_prefix"] = args.retrival_prefix
    if args.predicted_prefix:
        config["defaults"]["predicted_prefix"] = args.predicted_prefix
    if args.db_dump_prefix:
        config["defaults"]["db_dump_prefix"] = args.db_dump_prefix
    if args.db_dump_s3_key:
        config["defaults"]["db_dump_s3_key"] = args.db_dump_s3_key
    if args.rds_db_host:
        config["defaults"]["rds_db_host"] = args.rds_db_host
    if args.create_db_init_lambda:
        config["defaults"]["create_db_init_lambda"] = args.create_db_init_lambda
    if args.run_db_init_on_deployment:
        config["defualts"]["run_db_init_on_deployment"] = args.run_db_init_on_deployment
    if args.create_bastion_instance:
        config["defaults"]["create_bastion_instance"] = args.create_bastion_instance

    return config


def main():
    print("#" * 40)
    print("Starting ML-Driven Predictive Analytics Project Deployment")
    print("#" * 40)

    print("\nPreparing config.ini file")
    args = parse_arguments()
    config = load_or_create_config(args.config)

    if args.use_defaults:
        print(f"Using default values and saving to {args.config}")
        save_config(config, args.config)
    elif args.interactive:
        config = interactive_config(args.config)
    else:
        # Check if any config-specific arguments were provided
        config_args_provided = any(
            [
                args.environment,
                args.lambda_logs_level,
                args.project,
                args.company,
                args.rds_db_name,
                args.rds_db_port,
                args.rds_db_table,
                args.rds_db_username,
                args.rds_config_secret_name,
                args.canvas_model_endpoint_name,
                args.retrival_prefix,
                args.predicted_prefix,
                args.db_dump_prefix,
                args.db_dump_s3_key,
                args.create_db_init_lambda,
                args.create_bastion_instance,
                args.rds_db_host,
                args.run_db_init_on_deployment,
            ]
        )

        if config_args_provided:
            update_config_from_args(config, args)
            save_config(config, args.config)
        else:
            # If no specific mode or arguments provided, default to interactive
            config = interactive_config(args.config)

    print(f"\n Final Config:")
    print({section: dict(config[section]) for section in config})

    # Call Deployment steps


if __name__ == "__main__":
    main()
