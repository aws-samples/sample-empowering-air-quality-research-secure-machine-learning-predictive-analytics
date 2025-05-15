from aws_cdk import Stack
from constructs import Construct
from .network_stack import NetworkStack
from .database_stack import DatabaseStack
from .storage_stack import StorageStack
from .sagemaker_stack import SageMakerStack
from .lambda_stack import LambdaStack
from .step_functions_stack import StepFunctionsStack
from .eventbridge_scheduler_stack import EventBridgeSchedulerStack
from .config_reader import ConfigReader
from .nag_suppressions import add_nag_suppressions

class MainStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Read configuration using the ConfigReader class
        config_reader = ConfigReader()
        config = config_reader.get_stack_config()
        
        # Get project_prefix from config (with fallback to default)
        project_prefix = config.get("project_prefix", "demoapp")
        print(f"Using project prefix: {project_prefix}")
        
        # Configure resources using project_prefix
        config["lambda_logs_level"] = "INFO"
        config["rds_db_name"] = f"{project_prefix}db"
        config["rds_db_table"] = f"{project_prefix}_dataset"
        config["rds_db_port"] = 5432
        config["rds_db_username"] = "postgres"
        config["rds_config_secret_name"] = f"{project_prefix}-db-credentials"
        
        # Use initial_data_file from config
        config["initial_data_file"] = config.get("initial_data_file", "init_data.csv")
        config["initial_data_path"] = "data"  # Default relative to project root

        network_stack = NetworkStack(self, "NetworkStack", config=config)

        database_stack = DatabaseStack(
            self,
            "DatabaseStack",
            vpc=network_stack.vpc,
            db_security_group=network_stack.db_security_group,
            config=config,
        )

        storage_stack = StorageStack(self, "StorageStack", config=config)

        SageMakerStack(
            self,
            "SageMakerStack",
            vpc=network_stack.vpc,
            sagemaker_security_group=network_stack.sagemaker_security_group,
            source_bucket=storage_stack.source_bucket,
            config=config,
        )

        lambda_stack = LambdaStack(
            self,
            "LambdaStack",
            vpc=network_stack.vpc,
            lambda_sg=network_stack.lambda_sg,
            aurora=database_stack.aurora,
            source_bucket=storage_stack.source_bucket,
            config=config,
        )

        step_functions_stack = StepFunctionsStack(
            self,
            "StepFunctionsStack",
            query_function=lambda_stack.query_function,
            make_inference_function=lambda_stack.make_inference_lambda,
            write_results_function=lambda_stack.write_results_function,
            config=config,
        )

        EventBridgeSchedulerStack(
            self,
            "EventBridgeSchedulerStack",
            state_machine=step_functions_stack.state_machine,
            config=config,
        )

        # Add CDK nag suppressions
        add_nag_suppressions(self)
