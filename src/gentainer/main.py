#! /usr/bin/env python3

from zenlib.util import get_kwargs

from gentainer import Gentainer


def process_args(kwargs, gentainer):
    """Process the arguments and call the appropriate method."""
    action = kwargs["action"].lower()
    if action in ["list"]:
        process_single_arg_action(kwargs, gentainer)
    else:
        process_multi_arg_action(kwargs, gentainer)


def process_single_arg_action(kwargs, gentainer):
    """Process the single argument action."""
    action = kwargs["action"].lower()
    match action:
        case "list":
            gentainer.list()


def process_multi_arg_action(kwargs, gentainer):
    """Process the multi argument action."""
    action = kwargs["action"].lower()
    container_name = kwargs["container_name"]
    match action:
        case "prepare":
            gentainer.prepare(container_name)
        case "build":
            gentainer.build(container_name)
        case "run":
            gentainer.run(container_name)
        case "net_prepare":
            gentainer.net_prepare(container_name)
        case "net_clean":
            gentainer.net_clean(container_name)


def main():
    arguments = [
        {"flags": ["-c", "--config"], "action": "store", "help": "set the config file location"},
        {
            "flags": ["action"],
            "action": "store",
            "help": "Action to perform",
            "choices": ["list", "prepare", "build", "run", "net_prepare", "net_clean"],
        },
        {"flags": ["container_name"], "action": "store", "help": "Name of the container to run", "nargs": "?"},
        {"flags": ["--force"], "action": "store_true", "help": "Force action"},
    ]
    kwargs = get_kwargs(
        package=__package__, description="Gentoo Container Maker", arguments=arguments, drop_default=True
    )
    gentainer = Gentainer(**kwargs)
    process_args(kwargs, gentainer)


if __name__ == "__main__":
    main()
