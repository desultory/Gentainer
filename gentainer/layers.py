"""
Gentoo container layer management
"""

__author__ = 'desultory'
__version__ = '0.0.1'


from .zen_custom import loggify

from pathlib import Path
from subprocess import run


@loggify
class Layers:
    """
    Gentoo container layers
    """

    def __init__(self, container, build_dir, directory_backing, base_image=None, force=False, *args, **kwargs):
        """
        Initialize a Gentainer object
        """
        self.build_dir = Path(build_dir)
        self.container = container
        self.directory_backing = directory_backing
        self.base_image = base_image
        self.force = force

        self.layer_dir = self.build_dir / self.container

    def prepare(self):
        """
        Prepares the image layer for the specified container.
        If a base layer is specified, it will be used as a base for the new layer.
        """
        if not self.build_dir.exists():
            self.logger.info("Creating build directory: %s" % self.build_dir)
            self.build_dir.mkdir(parents=True)

        if self.layer_dir.exists():
            if self.force:
                self.clean()
            else:
                raise RuntimeError("Layer already exists for container: %s" % self.container)

        try:
            getattr(self, 'prepare_%s' % self.directory_backing)()
        except AttributeError:
            raise NotImplementedError("Directory backing '%s' not implemented" % self.directory_backing)

    def prepare_btrfs(self):
        """
        Prepares the image layer for the specified container using btrfs
        """
        if self.base_image:
            self.logger.info("Creating btrfs snapshot of base layer '%s' for container: %s" % (self.base_image, self.container))
            args = ['btrfs', 'subvolume', 'snapshot', str(self.build_dir / self.base_image), str(self.layer_dir)]
        else:
            self.logger.info("Creating btrfs subvolume for container: %s" % self.container)
            args = ['btrfs', 'subvolume', 'create', str(self.layer_dir)]

        cmd_out = run(args, capture_output=True)
        if cmd_out.returncode != 0:
            raise RuntimeError(cmd_out.stderr.decode('utf-8'))

    def clean(self):
        """
        Cleans the image layer for the specified container.
        """
        if self.layer_dir.exists():
            self.logger.info("Cleaning layer for container: %s" % self.container)
            try:
                getattr(self, 'clean_%s' % self.directory_backing)()
            except AttributeError:
                raise NotImplementedError("Directory backing '%s' not implemented" % self.directory_backing)
        else:
            raise RuntimeError("Layer does not exist for container: %s" % self.container)

    def clean_btrfs(self):
        """
        Cleans the image layer for the specified container using btrfs
        """
        self.logger.info("Deleting btrfs subvolume for container: %s" % self.container)
        args = ['btrfs', 'subvolume', 'delete', str(self.layer_dir)]

        cmd_out = run(args, capture_output=True)
        if cmd_out.returncode != 0:
            raise RuntimeError(cmd_out.stderr.decode('utf-8'))

