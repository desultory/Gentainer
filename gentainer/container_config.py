"""
Gentoo container configuration dictionary
"""

__author__ = 'desultory'
__version__ = '0.0.1'


from .zen_custom import loggify

from tomllib import load

import portage


@loggify
class ContainerConfig(dict):
    """
    Dictionary container gentoo container configuration
    """
    # Parameter key is the name
    # Parameter value is the type
    required_parameters = {'packages': list}  # Packages to install

    optional_parameters = {'base_image': str,  # Base image to use when building
                           'container_user': str,  # Container user to create/use when running the container
                           'usernet_allocation': dict}  # Usernet allocation in the form {"interace name": count}

    def __init__(self, config_file, *args, **kwargs):
        """
        Initialize a ContainerConfig object
        """
        self.config_file = config_file
        self.load_config()

    def load_config(self):
        """
        Reads a container config file
        """
        self.logger.info("Loading container config: %s" % self.config_file)
        with open(self.config_file, 'rb') as config_file:
            toml_data = load(config_file)

        self.logger.debug("Read TOML data: %s" % toml_data)

        for key, value in self.required_parameters.items():
            if key not in toml_data:
                raise KeyError("Missing required parameter: %s" % key)
            elif not isinstance(toml_data[key], value):
                raise TypeError("Invalid type for %s: %s" % (key, type(toml_data[key])))
            else:
                self.logger.debug("Setting required parameter %s: %s" % (key, toml_data[key]))
                self[key] = toml_data[key]

        for key, value in toml_data.items():
            if hasattr(self, f"validate_{key}"):
                self.logger.debug("Validating parameter %s: %s" % (key, value))
                getattr(self, f"validate_{key}")(value)

            if key in self.optional_parameters:
                if isinstance(value, self.optional_parameters[key]):
                    self.logger.debug("Setting optional parameter %s: %s" % (key, value))
                    self[key] = value
                else:
                    self.logger.warning("Invalid type for %s: %s" % (key, type(value)))
            elif key not in self.required_parameters:
                self.logger.warning("Unknown parameter in config: %s" % key)

    def validate_packages(self, packages):
        """
        Checks if the package exists in the porgage database
        """
        for package in packages:
            if not portage.db[portage.root]['porttree'].dbapi.match(package):
                raise KeyError("Package does not exist: %s" % package)

    def __str__(self):
        """
        Returns a string representation of the object
        """
        return '\n'.join(["  %s: %s" % (key, value) for key, value in self.items()])

