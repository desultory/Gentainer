"""
Gentoo container configuration dictionary
"""

__author__ = 'desultory'
__version__ = '0.0.2'


from .zen_custom import loggify

from importlib import import_module
from tomllib import load


@loggify
class ContainerConfig(dict):
    """
    Dictionary container gentoo container configuration
    """
    # Parameters are added when modules are loaded
    parameters = {}

    def __init__(self, config_file, *args, **kwargs):
        """
        Initialize a ContainerConfig object
        """
        self.config_file = config_file
        self.load_config()

    @staticmethod
    def load_module(module_name):
        """
        Loads a module and adds its parameters to the config
        """
        module_name, class_name = module_name.rsplit('.', 1)
        module = import_module("." + module_name, __package__)

        class_object = getattr(module, class_name)

        # If the module has parameters, add them to the class
        if hasattr(class_object, 'parameters'):
            ContainerConfig.parameters.update(class_object.parameters)
            for paramater in class_object.parameters:
                # If the module has a validate function for the parameter, add it to the class
                if hasattr(class_object, f'validate_{paramater}'):
                    setattr(ContainerConfig, f'validate_{paramater}', getattr(class_object, f'validate_{paramater}'))

    def load_config(self):
        """
        Reads a container config file
        """
        self.logger.info("Loading container config: %s" % self.config_file)
        with open(self.config_file, 'rb') as config_file:
            toml_data = load(config_file)

        self.logger.debug("Read TOML data: %s" % toml_data)

        for key, value in toml_data.items():
            if hasattr(self, f"validate_{key}"):
                self.logger.debug("Validating parameter %s: %s" % (key, value))
                getattr(self, f"validate_{key}")(value)

            if key in self.parameters:
                if isinstance(value, self.parameters[key]):
                    self[key] = value
                else:
                    raise TypeError("Invalid type for %s: %s" % (key, type(value)))
            else:
                raise ValueError("Unknown parameter: %s" % key)

    def __str__(self):
        """
        Returns a string representation of the object
        """
        return '\n'.join(["  %s: %s" % (key, value) for key, value in self.items()])

