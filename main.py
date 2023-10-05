#! /usr/bin/env python3

from gentainer.gentainer import Gentainer

import logging
from argparse import ArgumentParser


if __name__ == '__main__':
    logger = logging.getLogger()
    logger.setLevel(20)

    parser = ArgumentParser(description='Gentainer')
    parser.add_argument('--config', type=str, help='Path to config file', default='config.toml')
    parser.add_argument('action', type=str, help='Action to perform', choices=['list', 'prepare', 'build', 'run'])
    parser.add_argument('container_name', type=str, help='Name of the container to run', nargs='?')
    parser.add_argument('--force', action='store_true', help='Force action')
    parser.add_argument('-d', '--debug', action='store_true', help='Debug mode')
    parser.add_argument('-dd', '--verbose-debug', action='store_true', help='Verbose debug mode')

    if parser.parse_args().verbose_debug:
        logger.setLevel(5)
    elif parser.parse_args().debug:
        logger.setLevel(10)

    args = parser.parse_args()

    gentainer = Gentainer(config=args.config, logger=logger, force=args.force)

    getattr(gentainer, args.action)(args.container_name)
