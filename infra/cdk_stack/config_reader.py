import configparser
import os


class ConfigReader:
    def __init__(self):
        self.pre_config = configparser.ConfigParser()
        self.post_config = configparser.ConfigParser()
        self.pre_config_path = "scripts/pre-deployment-config.ini"
        self.post_config_path = "scripts/post-deployment-config.ini"

        # Read pre-deployment config
        if os.path.exists(self.pre_config_path):
            self.pre_config.read(self.pre_config_path)
        else:
            raise FileNotFoundError(
                f"Pre-deployment config file not found: {self.pre_config_path}"
            )

        # Read post-deployment config
        if os.path.exists(self.post_config_path):
            self.post_config.read(self.post_config_path)
        else:
            raise FileNotFoundError(
                f"Post-deployment config file not found: {self.post_config_path}"
            )

    def get_stack_config(self):
        config = {}

        # Add pre-deployment configurations
        if "defaults" in self.pre_config:
            config.update(self.pre_config["defaults"])

        # Add post-deployment configurations (overwriting pre-deployment if there are conflicts)
        if "defaults" in self.post_config:
            config.update(self.post_config["defaults"])

        return config
