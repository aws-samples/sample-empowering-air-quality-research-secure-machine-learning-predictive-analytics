from configparser import ConfigParser
import os
import argparse

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

def create_default_pre_config():
    config = ConfigParser()
    config["defaults"] = {
        "initial_data_file": "init_data.csv",
        "project_prefix": "demoapp",  # Added project_prefix with default value
    }
    return config

def create_default_post_config():
    config = ConfigParser()
    config["defaults"] = {
        "canvas_model_endpoint_name": "canvas-demo-deployment",
    }
    return config

def load_or_create_config(config_path, is_pre_config):
    config = ConfigParser()
    if os.path.exists(config_path):
        print(f"{config_path} found, reading file...")
        config.read(config_path)
    else:
        print(f"No {config_path} file found, creating a default config file...")
        config = (
            create_default_pre_config()
            if is_pre_config
            else create_default_post_config()
        )
    return config

def interactive_pre_config(config_path="pre-deployment-config.ini"):
    config = load_or_create_config(config_path, is_pre_config=True)

    # Get project_prefix input
    project_prefix = get_user_input(
        "Enter your project prefix (used for resource naming)",
        config["defaults"].get("project_prefix", "demoapp"),
    ).lower()

    initial_data_file = get_user_input(
        "Enter the name of your initial data file (e.g., init_data.csv)",
        config["defaults"].get("initial_data_file", "init_data.csv"),
    ).lower()
    
    # Update config with user input
    config["defaults"]["initial_data_file"] = initial_data_file
    config["defaults"]["project_prefix"] = project_prefix

    save_config(config, config_path)
    return config

def interactive_post_config(config_path="post-deployment-config.ini"):
    config = load_or_create_config(config_path, is_pre_config=False)

    canvas_model_endpoint_name = get_user_input(
        "Enter your SageMaker Canvas Model Endpoint Name.",
        config["defaults"].get("canvas_model_endpoint_name", "canvas-demo-deployment"),
    )

    # Update config object
    config["defaults"]["canvas_model_endpoint_name"] = canvas_model_endpoint_name

    save_config(config, config_path)
    return config

def save_config(config, config_path):
    with open(config_path, "w") as configfile:
        config.write(configfile)
    print(f"\nConfiguration has been updated successfully in {config_path}!")

def parse_arguments():
    parser = argparse.ArgumentParser(
        description="AWS demo machine learning prediction solution"
    )
    parser.add_argument(
        "--pre", action="store_true", help="Run pre-deployment configuration"
    )
    parser.add_argument(
        "--post", action="store_true", help="Run post-deployment configuration"
    )
    parser.add_argument("--config", default=None, help="Path to configuration file")
    parser.add_argument(
        "--interactive", action="store_true", help="Use interactive mode"
    )
    return parser.parse_args()

def main():
    print("#" * 40)
    print("ML-Driven Predictive Analytics Project Configuration")
    print("#" * 40)

    args = parse_arguments()

    if args.pre and args.post:
        print("Error: Please specify either --pre or --post, not both.")
        return

    if not (args.pre or args.post):
        print("Error: Please specify either --pre or --post.")
        return

    if args.pre:
        config_path = args.config or "pre-deployment-config.ini"
        print("\nPreparing pre-deployment configuration")
        if args.interactive:
            config = interactive_pre_config(config_path)
        else:
            config = load_or_create_config(config_path, is_pre_config=True)
            save_config(config, config_path)

    elif args.post:
        config_path = args.config or "post-deployment-config.ini"
        print("\nPreparing post-deployment configuration")
        if args.interactive:
            config = interactive_post_config(config_path)
        else:
            config = load_or_create_config(config_path, is_pre_config=False)
            save_config(config, config_path)

    print(f"\nFinal Config:")
    print({section: dict(config[section]) for section in config})

if __name__ == "__main__":
    main()
