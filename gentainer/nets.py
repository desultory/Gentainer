"""
Gentoo container network management
"""

__author__ = "desultory"
__version__ = "0.0.5"

from tomllib import load

from gentainer.zen_custom import loggify, pretty_print, handle_plural

from pyroute2 import IPRoute


def get_interface_names():
    """
    Get a list of network interface names
    """
    ip_route = IPRoute()
    links = ip_route.get_links()
    interface_names = []

    for link in links:
        for attr in link['attrs']:
            if attr[0] == 'IFLA_IFNAME':
                interface_names.append(attr[1])

    return interface_names


@loggify
class ContainerNet:
    """
    Manage network configuration for a container
    """
    parameters = {'networks': dict}  # A dict containing network configuration, where the key name is the interface name

    def __init__(self, net_config, force=False, *args, **kwargs):
        self.force = force
        self.load_config(net_config)

    def load_config(self, net_config):
        """
        Load network configuration from the networks dict.
        """
        self.config = net_config
        self.name = self.config.name
        self.networks = self.config['networks']

    def validate_networks(self, networks):
        """
        Validates supplied network information
        """
        interface_names = get_interface_names()
        self.logger.log(5, "Detected interfaces: %s" % interface_names)

        for network in networks:
            if network not in interface_names:
                self.logger.warning("[%s] Network interface does not exist: %s" % (self.name, network))
                return False
        return True

    def to_config(self):
        """
        Print a list containing a representation of the network configuration as LXC config directives
        """
        if not self.validate_networks(self.networks):
            raise ValueError("Invalid network configuration")


@loggify
class HostNet:
    """
    Manage network configuration for the host
    """
    interface_parameters = ['type', 'address', 'mask']

    def __init__(self, config_file, force=False, *args, **kwargs):
        self.config_file = config_file
        self.force = force
        self.load_config()

    def __str__(self):
        """
        Returns a string representation of all networks
        """
        return pretty_print(self.config)

    def load_config(self):
        """
        Load network configuration from the config file
        """
        self.logger.info("Loading network configuration: %s" % self.config_file)
        with open(self.config_file, 'rb') as f:
            self.config = load(f)

        self.logger.debug("Network configuration:\n%s" % pretty_print(self.config))
        self.validate_config()

    def validate_config(self):
        """
        Validates the config and sets defaults
        """
        for interface in self.config:
            bad_params = [param for param in self.config[interface] if param not in self.interface_parameters]
            if bad_params:
                self.logger.error("[%s] Invalid parameters detected and dropped: %s" % (interface, bad_params))
                for param in bad_params:
                    self.config[interface].pop(param)

            if 'type' not in self.config[interface]:
                self.logger.warning("[%s] No interface type specified, defaulting to 'bridge'" % interface)
                self.config[interface]['type'] = 'bridge'

            if 'address' not in self.config[interface]:
                self.logger.warning("[%s] No interface address specified." % interface)
                if 'mask' in self.config[interface]:
                    self.logger.error("[%s] Interface mask specified without address." % interface)
                    self.config[interface].pop('mask')
            elif 'mask' not in self.config[interface]:
                self.logger.warning("[%s] No interface mask specified, defaulting to '/32'" % interface)
                self.config[interface]['mask'] = 32

            self.logger.debug("[%s] Validated network configuration:\n%s" % (interface, pretty_print(self.config[interface])))

    def prepare(self):
        """
        Configures network interfaces
        """
        self.logger.debug("Network configuration: %s" % self.config)
        self.configure_interface(self.config.keys())

    def clean(self):
        """
        Cleans all managed network interfaces
        """
        self.logger.info("Cleaning network interfaces:\n%s" % pretty_print(self.config.keys()))
        self.clean_interface(self.config.keys())

    @handle_plural
    def clean_interface(self, interface):
        """
        Clean a network interface
        """
        if interface in get_interface_names():
            self.logger.info("Cleaning interface: %s" % interface)
            with IPRoute() as ip_route:
                ip_route.link('del', ifname=interface)
        else:
            self.logger.warning("Cannot clean, interface does not exist: %s" % interface)

    @handle_plural
    def configure_interface(self, interface):
        """
        Configure a network interface
        """
        self.logger.info("Configuring network interface: %s" % interface)
        if interface in get_interface_names():
            self.logger.warning("Interface already exists: %s" % interface)
            if self.force:
                self.logger.info("Forcing interface configuration")
                self.clean_interface(interface)
            else:
                raise ValueError("Interface already exists: %s" % interface)

        self.logger.info("Configuring interface: %s" % interface)
        interface_config = self.config[interface]
        self.logger.debug("Interface configuration: \n%s" % pretty_print(interface_config))

        with IPRoute() as ip_route:
            ip_route.link('add', ifname=interface, kind=interface_config['type'])
            device_index = ip_route.link_lookup(ifname=interface)[0]
            self.logger.debug("[%s] Created interface with index: %s" % (interface, device_index))

            if 'address' in interface_config and 'mask' in interface_config:
                ip_route.addr('add', index=device_index, address=interface_config['address'], mask=interface_config['mask'])

            interface_info = ip_route.get_links(device_index)[0]
            self.logger.info("Interface configured: %s" % interface)
            self.logger.log(5, "[%s] Interface info: %s" % (interface, pretty_print(interface_info)))
