"""
Gentoo containers
"""

__author__ = 'desultory'
__version__ = '0.0.1'


from .zen_custom import loggify

from .container_config import ContainerConfig
from .users import UserManagement
from .layers import Layers
from .builder import Builder


from tomllib import load
from pathlib import Path


@loggify
class Gentainer:
    """
    Gentoo container class
    """

    def __init__(self, config="config.toml", force=False, *args, **kwargs):
        """
        Initialize a Gentainer object
        """
        self.containers = {}
        self.force = force  # Force operations
        self.load_config(config)

    def load_containers(self):
        """
        Loads all containers from self.config_dir
        """
        if not self.config_dir.exists():
            raise FileNotFoundError("Container directory does not exist: %s" % self.config_dir)

        self.logger.info("Loading containers from %s" % self.config_dir)
        for container in Path(self.config_dir).glob('*.toml'):
            self.containers[container.stem] = ContainerConfig(config_file=container, logger=self.logger, _log_init=False)

        if not self.containers:
            self.logger.warning("No container config loaded")
        else:
            self.logger.info("Loaded %d containers" % len(self.containers))
            self.logger.debug("Loaded containers: %s" % ', '.join(self.containers.keys()))

    def load_config(self, config):
        """
        Load a configuration
        """
        self.logger.info("Loading configuration from %s" % config)
        with open(config, 'rb') as config_file:
            self.config = load(config_file)

        self.build_dir = Path(self.config.get('build_dir', '/tmp/gentainer_build'))
        self.config_dir = Path(self.config.get('config_dir', './config'))
        self.usernet_file = Path(self.config.get('lxc_usernet_file', '/etc/lxc/lxc-usernet'))

        self.directory_backing = self.config.get('dir_backing', 'btrfs')

        self.load_containers()

    def list(self, filter_string=None):
        """
        List all containers
        """
        for name, container in self.containers.items():
            if filter_string and filter_string in name:
                print(f"{name}:\n{container}")
            elif not filter_string:
                print(f"{name}:\n{container}")

    def prepare(self, container):
        """
        Prepare a container.
        Checks if the user exists and creates it if it doesn't.
        """
        if container not in self.containers:
            raise KeyError("Container does not exist: %s" % container)

        if 'container_user' in self.containers[container]:
            user = UserManagement(self.containers[container], force=self.force, lxc_usernet_file=self.usernet_file, logger=self.logger, _log_init=False)
            user.prepare()

    def build(self, container):
        """
        Build a container
        """
        if container not in self.containers:
            raise KeyError("Container does not exist: %s" % container)

        self.prepare(container)

        layer_args = [container, self.build_dir, self.directory_backing]
        layer_kwargs = {'force': self.force, 'logger': self.logger, '_log_init': False}
        if 'base_image' in self.containers[container]:
            base_image = self.containers[container]['base_image']
            self.logger.info("Building base image `%s` for container: %s" % (base_image, container))
            self.build(base_image)
            layer_kwargs['base_image'] = base_image

        layer = Layers(*layer_args, **layer_kwargs)
        layer.prepare()

        builder = Builder(container, layer.layer_dir, self.containers[container]['packages'], force=self.force, logger=self.logger, _log_init=False)
        builder.build()

