import configparser
import os


class ConfigReader:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config_path = "scripts/config.ini"

        # Read config file
        if os.path.exists(self.config_path):
            self.config.read(self.config_path)
        else:
            raise FileNotFoundError(
                f"Config file not found: {self.config_path}"
            )

    def get_stack_config(self):
        config = {}

        # Add configurations from defaults section
        if "defaults" in self.config:
            config.update(self.config["defaults"])

        return config
