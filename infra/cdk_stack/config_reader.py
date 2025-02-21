import configparser
import os


class ConfigReader:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "scripts/config.ini"
        )
        self.config.read(self.config_path)

    def get_stack_config(self, environment=None):

        # First get default values
        config_values = {}
        if "defaults" in self.config:
            config_values.update(dict(self.config["defaults"]))

        # Then override with environment-specific values if they exist
        if environment in self.config:
            config_values.update(dict(self.config[environment]))

        return config_values
