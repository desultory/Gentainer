"""
Gentoo container user management
"""

__author__ = 'desultory'
__version__ = '0.0.2'


from .zen_custom import loggify, replace_file_line

from pathlib import Path
from pwd import getpwnam
from subprocess import run
from os import chmod, mkdir, chown


@loggify
class UserManagement:
    """
    Gentoo container user management class
    """

    parameters = {"username": str,  # User name for the unprivileged container user
                  "usernet_allocation": dict}  # {interface: count} for the container user

    def __init__(self, user_config, container, force=False, lxc_usernet_file='/etc/lxc/lxc-usernet', *args, **kwargs):
        """
        Initialize the user maangement class for the specified user
        """
        self.container = container  # Container name
        self.force = force  # Force operations
        self.lxc_usernet_file = Path(lxc_usernet_file)
        self.load_config(user_config)

    def prepare(self):
        """
        Run preparation actions, such as creating the user and usernet entries
        """
        self.create_user()
        self.create_container_home()
        self.prepare_usernets()

    def load_config(self, container_config):
        """
        Loads the user configuration from the container configuration
        """
        self.config = container_config
        self.username = self.config['username']
        self.usernet_allocation = self.config['usernet_allocation']

    def check_user(self):
        """
        Check if a user exists.
        """
        try:
            getpwnam(self.username)
            return True
        except KeyError:
            self.logger.warning("User does not exist: %s" % self.username)
            return False

    def create_user(self):
        """
        Creates a user along with a home directory.
        Also adds the user to the lxc group.
        """
        if self.check_user():
            self.logger.warning("User already exists: %s" % self.username)
            return False

        self.logger.info("Creating user: %s" % self.username)

        user_cmd = run(['useradd', '--create-home', '--groups', 'lxc', self.username], capture_output=True)
        self.logger.debug("[%s] Useradd output: %s" % (self.username, user_cmd.stdout.decode('utf-8')))

        if user_cmd.returncode != 0:
            raise RuntimeError("Failed to create user: %s; Error: %s" % (self.username, user_cmd.stderr.decode('utf-8')))

    def create_container_home(self):
        """
        Creates LXC folders for the container user.
        Owns the folders to the container user if necessary.
        """
        user_home = Path(getpwnam(self.username).pw_dir)
        path_parts = ['.local', 'share', 'lxc', self.container]

        lxc_dir = user_home

        for part in path_parts:
            lxc_dir = lxc_dir.joinpath(part)
            if not lxc_dir.exists():
                self.logger.info("[%s] Creating LXC directory: %s" % (self.username, lxc_dir))
                mkdir(lxc_dir)
            else:
                self.logger.debug("[%s] LXC directory already exists: %s" % (self.username, lxc_dir))

            uid = getpwnam(self.username).pw_uid
            gid = getpwnam(self.username).pw_gid
            if lxc_dir.stat().st_uid != uid or lxc_dir.stat().st_gid != gid:
                self.logger.warning("[%s] Incorrect ownership of LXC directory: %s" % (self.username, lxc_dir))
                chown(lxc_dir, getpwnam(self.username).pw_uid, getpwnam(self.username).pw_gid)
                self.logger.debug("[%s] Setting ownership of LXC directory: %s" % (self.username, lxc_dir))

    def parse_usernet_user(self):
        """
        Checks /etc/lxc/lxc-usernet for an existing usernets entry.
        Returns a list containing the usernet interface and count as strings packed into a list.
        """
        usernet_entries = {}
        try:
            with open(self.lxc_usernet_file, 'r') as usernet:
                for line in usernet.readlines():
                    user, interface_type, interface_name, count = line.split()
                    if user == self.username and interface_type == 'veth':
                        usernet_entries[interface_name] = int(count)
        except FileNotFoundError:
            raise FileNotFoundError("Usernet file does not exist: %s" % self.lxc_usernet_file)
        except ValueError:
            if line.startswith('#'):
                self.logger.log(5, "Skipping commented line: %s" % line)
            elif line == '\n':
                self.logger.log(5, "Skipping empty line")
            else:
                raise ValueError("Invalid usernet entry: %s" % line)

        self.logger.log(5, "Existing usernet entries for %s: %s" % (self.username, usernet_entries))
        return usernet_entries

    def create_usernet_file(self):
        """
        Creates an empty usernet file with 0644 permissions.
        """
        if self.lxc_usernet_file.exists():
            self.logger.warning("[%s] Usernet file already exists: %s" % (self.username, self.lxc_usernet_file))
            if self.force:
                self.logger.info("[%s] Forcing usernet file creation: %s" % (self.username, self.lxc_usernet_file))
            else:
                return False

        self.logger.info("[%s] Creating usernet file: %s" % (self.username, self.lxc_usernet_file))
        self.lxc_usernet_file.touch()
        chmod(self.lxc_usernet_file, 0o644)

    def prepare_usernets(self):
        """
        Prepares the usernet for the specified container
        """
        if not self.usernet_allocation:
            self.logger.warning("No usernet allocation specified for user: %s" % self.username)
            return False

        if not self.lxc_usernet_file.exists():
            self.logger.warning("[%s] Usernet file does not exist: %s" % (self.username, self.lxc_usernet_file))
            self.create_usernet_file()

        self.add_usernet_entries()

    def add_usernet_entries(self):
        """
        Iterates over self.usernet_allocation {interface: count} and adds them to the usernet file.
        """
        existing_usernets = self.parse_usernet_user()

        for interface, count in self.usernet_allocation.items():
            self.logger.debug("[%s] Considering usernet entry: %s - %s" % (self.username, interface, count))
            if interface in existing_usernets and existing_usernets[interface] != count:
                self.logger.warning("[%s] Usernet '%s' already exists with a different allocation: %s != %s" % (self.username, interface, existing_usernets[interface], count))
                if self.force:
                    self.logger.info("Forcing usernet entry for user %s, %s: %s" % (self.username, interface, count))
                    old_usernet_string = f"{self.username} veth {interface} {existing_usernets[interface]}\n"
                    new_usernet_string = f"{self.username} veth {interface} {count}\n"
                    replace_file_line(self.lxc_usernet_file, old_usernet_string, new_usernet_string)
            elif interface in existing_usernets and existing_usernets[interface] == count:
                self.logger.debug("[%s] Usernet '%s' already exists with the same allocation: %s" % (self.username, interface, count))
            else:
                self.add_usernet_entry(interface, count)

    def add_usernet_entry(self, interface, count):
        """
        Adds the specified usernet entry to the usernet file.
        """
        if interface in self.parse_usernet_user():
            raise RuntimeError("Usernet entry already exists: %s" % interface)

        usernet_entry = f"{self.username} veth {interface} {count}\n"
        with open(self.lxc_usernet_file, 'a') as f:
            f.write(usernet_entry)

        self.logger.info("[%s] Added usernet entry: %s" % (self.username, usernet_entry.strip()))



