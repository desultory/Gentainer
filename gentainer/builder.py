"""
Gentoo container image builder
"""

__author__ = 'desultory'
__version__ = '0.0.1'


from .zen_custom import loggify

from pathlib import Path
from subprocess import run


@loggify
class Builder:
    """
    Gentoo container layer builder
    """

    def __init__(self, container, build_dir, packages, force=False, *args, **kwargs):
        """
        Initialize a builder object
        """
        self.container = container
        self.build_dir = Path(build_dir)
        self.packages = packages
        self.logger.info("[%s] Build directory: %s" % (self.container, self.build_dir))

    def build(self):
        """
        Build the image layer for a specific container
        """
        if not self.build_dir.exists():
            raise FileNotFoundError("Build directory does not exist: %s" % self.build_dir)

        args = ['emerge', '--root', str(self.build_dir), *self.packages]
        cmd_out = run(args, capture_output=True)

        if cmd_out.returncode != 0:
            raise RuntimeError(cmd_out.stderr.decode('utf-8'))

        self.logger.debug("[%s] Build output: %s" % (self.container, cmd_out.stdout.decode('utf-8')))
        self.logger.info("[%s] Built packages: %s" % (self.container, self.packages))
