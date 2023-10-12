"""
Gentoo containers
"""

__author__ = 'desultory'
__version__ = '0.0.3'


from gentainer.zen_custom import loggify, pretty_print

from gentainer.container_config import ContainerConfig
from gentainer.users import UserManager
from gentainer.layers import Layers
from gentainer.nets import ContainerNet, HostNet
from gentainer.builder import Builder


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

        self.logger.info("Loading containers from: %s" % self.config_dir)
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

        for module in self.config['modules']:
            self.logger.info("Loading module: %s" % module)
            ContainerConfig.load_module(module)

        self.logger.debug("Parameters: %s" % ContainerConfig.parameters)

        self.build_dir = Path(self.config.get('build_dir', '/tmp/gentainer_build'))
        self.config_dir = Path(self.config.get('config_dir', './config'))
        self.usernet_file = Path(self.config.get('lxc_usernet_file', '/etc/lxc/lxc-usernet'))
        self.network_config = HostNet(self.config.get('network_config', 'networks.toml'), force=self.force, logger=self.logger)

        self.directory_backing = self.config.get('dir_backing', 'btrfs')

        self.logger.debug("Configuration: %s" % pretty_print(self.config))

        self.load_containers()

    def list(self, filter_string=None):
        """
        List all containers
        """
        print("Containers:")
        pretty_print(self.containers, print_out=True)

        print("=" * 80)
        print("Networks:")
        print(self.network_config)

    def net_clean(self, interface=None):
        """
        Cleans the specified network
        """
        if interface:
            self.network_config.clean_interface(interface)
        else:
            self.network_config.clean()

    def net_prepare(self, interface=None):
        """
        Prepares the specified network
        """
        if interface:
            if isinstance(interface, dict):
                self.network_config.configure_interface(interface.keys())
            else:
                self.network_config.configure_interface(interface)
        else:
            self.network_config.prepare()

    def prepare(self, container):
        """
        Prepare a container.
        Checks if the user exists and creates it if it doesn't.
        """
        if container not in self.containers:
            raise KeyError("Container does not exist: %s" % container)

        if 'networks' in self.containers[container]:
            net = ContainerNet(self.containers[container], force=self.force, logger=self.logger)
            self.net_prepare(net.networks)

        if 'username' in self.containers[container]:
            user = UserManager(self.containers[container], force=self.force, lxc_usernet_file=self.usernet_file, logger=self.logger)
            user.prepare()

    def build(self, container):
        """
        Build a container
        """
        if container not in self.containers:
            raise KeyError("Container does not exist: %s" % container)

        self.prepare(container)

        layer_args = [container, self.build_dir, self.directory_backing]
        layer_kwargs = {'force': self.force, 'logger': self.logger}
        if 'base_image' in self.containers[container]:
            base_image = self.containers[container]['base_image']
            self.logger.info("Building base image `%s` for container: %s" % (base_image, container))
            self.build(base_image)
            layer_kwargs['base_image'] = base_image

        layer = Layers(*layer_args, **layer_kwargs)
        layer.prepare()

        builder = Builder(container, layer.layer_dir, self.containers[container]['packages'], force=self.force, logger=self.logger)
        builder.build()

