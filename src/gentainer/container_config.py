__author__ = "desultory"
__version__ = "0.1.0"


from importlib import import_module
from pathlib import Path
from tomllib import load

from zenlib.logging import loggify
from zenlib.util import pretty_print


@loggify
class ContainerConfig(dict):
    """Dictionary for gentoo container configuration"""
    # Parameters are added when modules are loaded
    parameters = {"parent_config": dict,
                  "config_file": Path,
                  "name": str}

    def __init__(self, parent_config, config_file, *args, **kwargs):
        """Initialize the config by loading the config file"""
        self.parent_config = parent_config
        self.config_file = Path(config_file)
        self.load_config()

    def __setattr__(self, key, value):
        """Set an attribute"""
        if key not in self.parameters and key != "logger":
            raise AttributeError("Unknown parameter: %s" % key)
        super().__setattr__(key, value)

    def __getitem__(self, key):
        """Get an item, if it's not in this dict, check the parent"""
        return super().__getitem__(key) or self.parent_config.__getitem__(key)

    @staticmethod
    def load_module(module_name):
        """Loads a module and adds its parameters to the config"""
        module_name, class_name = module_name.rsplit(".", 1)
        module = import_module("." + module_name, __package__)

        class_object = getattr(module, class_name)

        # If the module has parameters, add them to the class
        if hasattr(class_object, "parameters"):
            for parameter, value in class_object.parameters.items():
                if hasattr(ContainerConfig, parameter):
                    raise AttributeError("[%s] Parameter already exists: %s" % (class_name, parameter))
                ContainerConfig.parameters[parameter] = value

                # If the module has a validate function for the parameter, add it to the class
                if hasattr(class_object, f"validate_{parameter}"):
                    setattr(ContainerConfig, f"validate_{parameter}", getattr(class_object, f"validate_{parameter}"))

    def load_config(self):
        """Reads a container config file"""
        self.logger.info("Loading container config: %s" % self.config_file)
        with open(self.config_file, "rb") as config_file:
            toml_data = load(config_file)

        # Get the file name of the config file - the extension
        self.name = self.config_file.name.split(".")[0]
        self.logger.debug("[%s] Read TOML data: %s" % (self.name, toml_data))

        for key, value in toml_data.items():
            if hasattr(self, f"validate_{key}"):
                self.logger.debug("[%s] Validating parameter '%s':\n%s" % (self.name, key, pretty_print(value)))
                getattr(self, f"validate_{key}")(value)

            if key in self.parameters:
                if isinstance(value, self.parameters[key]):
                    self[key] = value
                else:
                    raise TypeError("[%s] Invalid type for %s: %s" % (self.config_file, key, type(value)))
            else:
                raise ValueError("[%s] Unknown parameter: %s" % (self.config_file, key))

        self.logger.debug("[%s] Loaded container config:\n%s" % (self.name, self))

    def __str__(self):
        return pretty_print({self.name: self})
